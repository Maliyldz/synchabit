"""
SyncHabit NLP - DistilBERT Fine-Tuning
=======================================
Türkçe DistilBERT modelini (dbmdz/distilbert-base-turkish-cased) SyncHabit
görev metinleri üzerine fine-tune eder.

Önceki TF-IDF + LogReg modeli:
  - In-distribution: ~%92 F1
  - Adversarial set: ~%57 başarı  ← KELİME BAZLI SINIR

DistilBERT hedefi:
  - Adversarial set'te ciddi iyileşme (bağlamsal anlama)
  - In-distribution korunması

KULLANIM:
  cd ai/nlp_model
  python train_bert.py

ÇIKTILAR:
  models/distilbert/                ← eğitilmiş model (~265MB)
  training_report_bert.txt          ← detaylı metrikler
  confusion_matrix_bert.png         ← görsel
  training_loss_bert.png            ← loss/accuracy eğrileri

GEREKSİNİMLER:
  - PyTorch CUDA destekli
  - transformers, datasets, accelerate
  - 4GB+ VRAM (RTX 3050 yeterli)
  - ~30 dakika eğitim süresi
"""

import csv
import json
import random
from pathlib import Path
from collections import Counter

import numpy as np
import pandas as pd
import torch
import torch.nn as nn
from torch.utils.data import Dataset, DataLoader
from torch.optim import AdamW
from transformers import (
    AutoTokenizer,
    AutoModelForSequenceClassification,
    get_linear_schedule_with_warmup,
)

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from sklearn.metrics import (
    accuracy_score, classification_report, confusion_matrix,
    f1_score, precision_score, recall_score, roc_auc_score,
)

# --------------------------------------------------------------------
# Reproducibility
# --------------------------------------------------------------------
RANDOM_SEED = 42
random.seed(RANDOM_SEED)
np.random.seed(RANDOM_SEED)
torch.manual_seed(RANDOM_SEED)
torch.cuda.manual_seed_all(RANDOM_SEED)

# --------------------------------------------------------------------
# Configuration
# --------------------------------------------------------------------
MODEL_NAME = "dbmdz/distilbert-base-turkish-cased"
MAX_LENGTH = 64           # Görev metinleri kısa, 64 token yeter
BATCH_SIZE = 16           # 4GB VRAM için güvenli
EPOCHS = 3                # DistilBERT için yeterli
LEARNING_RATE = 2e-5      # BERT fine-tuning standardı
WARMUP_RATIO = 0.1        # %10 warmup
WEIGHT_DECAY = 0.01
USE_FP16 = True           # Mixed precision — RTX 3050 destekli

# --------------------------------------------------------------------
# Paths
# --------------------------------------------------------------------
ROOT = Path(__file__).resolve().parent
DATA_DIR = ROOT / "data" / "processed"
MODEL_DIR = ROOT / "models" / "distilbert"
REPORT_FILE = ROOT / "training_report_bert.txt"
CONFUSION_PNG = ROOT / "confusion_matrix_bert.png"
LOSS_PNG = ROOT / "training_loss_bert.png"

MODEL_DIR.mkdir(parents=True, exist_ok=True)

# --------------------------------------------------------------------
# Device
# --------------------------------------------------------------------
device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
print("=" * 80)
print(f"  SyncHabit DistilBERT Fine-Tuning")
print("=" * 80)
print(f"Device:        {device}")
if device.type == "cuda":
    print(f"GPU:           {torch.cuda.get_device_name(0)}")
    print(f"CUDA version:  {torch.version.cuda}")
    print(f"VRAM total:    {torch.cuda.get_device_properties(0).total_memory / 1e9:.2f} GB")
print(f"PyTorch:       {torch.__version__}")
print(f"Model:         {MODEL_NAME}")
print(f"Batch size:    {BATCH_SIZE}")
print(f"Max length:    {MAX_LENGTH}")
print(f"Epochs:        {EPOCHS}")
print(f"Learning rate: {LEARNING_RATE}")
print(f"Mixed prec:    {USE_FP16}")
print("=" * 80)

# --------------------------------------------------------------------
# Load data
# --------------------------------------------------------------------
print("\n📂 Veriler yükleniyor...")
train_df = pd.read_csv(DATA_DIR / "train.csv")
val_df = pd.read_csv(DATA_DIR / "val.csv")
test_df = pd.read_csv(DATA_DIR / "test.csv")

print(f"  Train: {len(train_df)} satır | safe={(train_df['label']==0).sum()}, unsafe={(train_df['label']==1).sum()}")
print(f"  Val:   {len(val_df)} satır | safe={(val_df['label']==0).sum()}, unsafe={(val_df['label']==1).sum()}")
print(f"  Test:  {len(test_df)} satır | safe={(test_df['label']==0).sum()}, unsafe={(test_df['label']==1).sum()}")

# --------------------------------------------------------------------
# Tokenizer
# --------------------------------------------------------------------
print(f"\n🔤 Tokenizer indiriliyor: {MODEL_NAME}")
tokenizer = AutoTokenizer.from_pretrained(MODEL_NAME)
print(f"  Vocabulary size: {tokenizer.vocab_size}")

# Quick sample
sample_text = "Bileğimi keseceğim bu gece"
tokens = tokenizer.tokenize(sample_text)
print(f"  Örnek tokenization: '{sample_text}'")
print(f"  → {tokens}")

# --------------------------------------------------------------------
# Dataset class
# --------------------------------------------------------------------
class ToxicTextDataset(Dataset):
    """PyTorch Dataset wrapper — text + label tokenize edilmiş halde tutar."""
    
    def __init__(self, texts, labels, tokenizer, max_length):
        self.texts = list(texts)
        self.labels = list(labels)
        self.tokenizer = tokenizer
        self.max_length = max_length
    
    def __len__(self):
        return len(self.texts)
    
    def __getitem__(self, idx):
        text = str(self.texts[idx])
        label = int(self.labels[idx])
        
        encoding = self.tokenizer(
            text,
            truncation=True,
            padding="max_length",
            max_length=self.max_length,
            return_tensors="pt",
        )
        
        return {
            "input_ids": encoding["input_ids"].squeeze(0),
            "attention_mask": encoding["attention_mask"].squeeze(0),
            "label": torch.tensor(label, dtype=torch.long),
        }


train_dataset = ToxicTextDataset(train_df["text"], train_df["label"], tokenizer, MAX_LENGTH)
val_dataset = ToxicTextDataset(val_df["text"], val_df["label"], tokenizer, MAX_LENGTH)
test_dataset = ToxicTextDataset(test_df["text"], test_df["label"], tokenizer, MAX_LENGTH)

train_loader = DataLoader(train_dataset, batch_size=BATCH_SIZE, shuffle=True, num_workers=0)
val_loader = DataLoader(val_dataset, batch_size=BATCH_SIZE, shuffle=False, num_workers=0)
test_loader = DataLoader(test_dataset, batch_size=BATCH_SIZE, shuffle=False, num_workers=0)

print(f"\n📦 DataLoaders hazır")
print(f"  Train batches: {len(train_loader)}")
print(f"  Val batches:   {len(val_loader)}")
print(f"  Test batches:  {len(test_loader)}")

# --------------------------------------------------------------------
# Model
# --------------------------------------------------------------------
print(f"\n🧠 Model indiriliyor: {MODEL_NAME}")
model = AutoModelForSequenceClassification.from_pretrained(
    MODEL_NAME,
    num_labels=2,  # binary: safe (0) / unsafe (1)
)
model.to(device)
print(f"  Parameters: {sum(p.numel() for p in model.parameters()):,}")
print(f"  Trainable:  {sum(p.numel() for p in model.parameters() if p.requires_grad):,}")

# --------------------------------------------------------------------
# Optimizer + Scheduler
# --------------------------------------------------------------------
total_steps = len(train_loader) * EPOCHS
warmup_steps = int(total_steps * WARMUP_RATIO)

# Class imbalance var mı diye kontrol et
class_counts = Counter(train_df["label"])
n_safe, n_unsafe = class_counts[0], class_counts[1]
total = n_safe + n_unsafe
class_weights = torch.tensor([
    total / (2 * n_safe),
    total / (2 * n_unsafe),
], dtype=torch.float, device=device)
print(f"\n⚖️  Class weights: safe={class_weights[0]:.3f}, unsafe={class_weights[1]:.3f}")

loss_fn = nn.CrossEntropyLoss(weight=class_weights)

optimizer = AdamW(
    model.parameters(),
    lr=LEARNING_RATE,
    weight_decay=WEIGHT_DECAY,
)
scheduler = get_linear_schedule_with_warmup(
    optimizer,
    num_warmup_steps=warmup_steps,
    num_training_steps=total_steps,
)

# Mixed precision
scaler = torch.amp.GradScaler("cuda", enabled=USE_FP16 and device.type == "cuda")

# --------------------------------------------------------------------
# Training Loop
# --------------------------------------------------------------------
print(f"\n🚀 Eğitim başlıyor — {EPOCHS} epoch, toplam {total_steps} step")
print(f"   Warmup: {warmup_steps} step\n")

history = {"train_loss": [], "val_loss": [], "val_f1": [], "val_recall": []}

best_val_f1 = 0.0

for epoch in range(EPOCHS):
    # ----- TRAIN -----
    model.train()
    train_losses = []
    
    for step, batch in enumerate(train_loader):
        input_ids = batch["input_ids"].to(device)
        attention_mask = batch["attention_mask"].to(device)
        labels = batch["label"].to(device)
        
        optimizer.zero_grad()
        
        with torch.amp.autocast("cuda", enabled=USE_FP16 and device.type == "cuda"):
            outputs = model(input_ids=input_ids, attention_mask=attention_mask)
            loss = loss_fn(outputs.logits, labels)
        
        scaler.scale(loss).backward()
        scaler.unscale_(optimizer)
        torch.nn.utils.clip_grad_norm_(model.parameters(), max_norm=1.0)
        scaler.step(optimizer)
        scaler.update()
        scheduler.step()
        
        train_losses.append(loss.item())
        
        # Progress
        if (step + 1) % 50 == 0 or step == 0:
            print(f"  [Epoch {epoch+1}/{EPOCHS}] Step {step+1}/{len(train_loader)} | loss: {loss.item():.4f}")
    
    avg_train_loss = np.mean(train_losses)
    
    # ----- VAL -----
    model.eval()
    val_losses, val_preds, val_labels, val_probs = [], [], [], []
    
    with torch.no_grad():
        for batch in val_loader:
            input_ids = batch["input_ids"].to(device)
            attention_mask = batch["attention_mask"].to(device)
            labels = batch["label"].to(device)
            
            with torch.amp.autocast("cuda", enabled=USE_FP16 and device.type == "cuda"):
                outputs = model(input_ids=input_ids, attention_mask=attention_mask)
                loss = loss_fn(outputs.logits, labels)
            
            val_losses.append(loss.item())
            probs = torch.softmax(outputs.logits, dim=1)[:, 1].cpu().numpy()
            preds = (probs >= 0.5).astype(int)
            
            val_preds.extend(preds.tolist())
            val_labels.extend(labels.cpu().numpy().tolist())
            val_probs.extend(probs.tolist())
    
    avg_val_loss = np.mean(val_losses)
    val_f1 = f1_score(val_labels, val_preds, pos_label=1)
    val_recall = recall_score(val_labels, val_preds, pos_label=1)
    val_precision = precision_score(val_labels, val_preds, pos_label=1)
    
    history["train_loss"].append(avg_train_loss)
    history["val_loss"].append(avg_val_loss)
    history["val_f1"].append(val_f1)
    history["val_recall"].append(val_recall)
    
    print(f"\n  📊 Epoch {epoch+1} özet:")
    print(f"     Train loss: {avg_train_loss:.4f}")
    print(f"     Val loss:   {avg_val_loss:.4f}")
    print(f"     Val F1:     {val_f1:.4f}")
    print(f"     Val Recall: {val_recall:.4f}")
    print(f"     Val Prec:   {val_precision:.4f}")
    
    # Save best
    if val_f1 > best_val_f1:
        best_val_f1 = val_f1
        print(f"     💾 Yeni best model kaydediliyor (F1={val_f1:.4f})")
        model.save_pretrained(MODEL_DIR)
        tokenizer.save_pretrained(MODEL_DIR)
    
    print()
    
    # GPU memory durumu
    if device.type == "cuda":
        mem_alloc = torch.cuda.memory_allocated() / 1e9
        mem_max = torch.cuda.max_memory_allocated() / 1e9
        print(f"     VRAM: {mem_alloc:.2f} GB allocated, {mem_max:.2f} GB peak\n")

# --------------------------------------------------------------------
# Load best model and evaluate on TEST set
# --------------------------------------------------------------------
print("=" * 80)
print("  TEST SETİ DEĞERLENDİRMESİ")
print("=" * 80)

# Best model yüklü (training'de zaten kaydedildi)
model = AutoModelForSequenceClassification.from_pretrained(MODEL_DIR).to(device)
model.eval()

test_preds, test_labels_list, test_probs = [], [], []

with torch.no_grad():
    for batch in test_loader:
        input_ids = batch["input_ids"].to(device)
        attention_mask = batch["attention_mask"].to(device)
        labels = batch["label"].to(device)
        
        with torch.amp.autocast("cuda", enabled=USE_FP16 and device.type == "cuda"):
            outputs = model(input_ids=input_ids, attention_mask=attention_mask)
        
        probs = torch.softmax(outputs.logits, dim=1)[:, 1].cpu().numpy()
        preds = (probs >= 0.5).astype(int)
        
        test_preds.extend(preds.tolist())
        test_labels_list.extend(labels.cpu().numpy().tolist())
        test_probs.extend(probs.tolist())

test_preds = np.array(test_preds)
test_labels_arr = np.array(test_labels_list)
test_probs = np.array(test_probs)

# Metrics
test_acc = accuracy_score(test_labels_arr, test_preds)
test_f1 = f1_score(test_labels_arr, test_preds, pos_label=1)
test_recall = recall_score(test_labels_arr, test_preds, pos_label=1)
test_precision = precision_score(test_labels_arr, test_preds, pos_label=1)
test_auc = roc_auc_score(test_labels_arr, test_probs)

print(f"\nTest Accuracy:  {test_acc:.4f}")
print(f"Test Precision: {test_precision:.4f}")
print(f"Test Recall:    {test_recall:.4f}")
print(f"Test F1-score:  {test_f1:.4f}")
print(f"Test ROC-AUC:   {test_auc:.4f}")

print(f"\n{classification_report(test_labels_arr, test_preds, target_names=['safe', 'unsafe'], digits=4)}")

# Confusion matrix
cm = confusion_matrix(test_labels_arr, test_preds)
tn, fp, fn, tp = cm.ravel()
print(f"Confusion Matrix:")
print(f"               Predicted Safe   Predicted Unsafe")
print(f"  Actual Safe    {tn:5d} (TN)       {fp:5d} (FP)")
print(f"  Actual Unsafe  {fn:5d} (FN)        {tp:5d} (TP)")

# --------------------------------------------------------------------
# Save 3-tier metadata
# --------------------------------------------------------------------
metadata = {
    "model_name": MODEL_NAME,
    "model_type": "DistilBERT",
    "framework": "PyTorch + transformers",
    "max_length": MAX_LENGTH,
    "epochs": EPOCHS,
    "batch_size": BATCH_SIZE,
    "learning_rate": LEARNING_RATE,
    "random_seed": RANDOM_SEED,
    "thresholds": {
        "block": 0.70,
        "warn": 0.40,
    },
    "test_metrics": {
        "accuracy": float(test_acc),
        "precision": float(test_precision),
        "recall": float(test_recall),
        "f1": float(test_f1),
        "auc": float(test_auc),
        "tn": int(tn), "fp": int(fp), "fn": int(fn), "tp": int(tp),
    },
    "vocab_size": tokenizer.vocab_size,
    "best_val_f1": float(best_val_f1),
}

with open(MODEL_DIR / "metadata.json", "w", encoding="utf-8") as f:
    json.dump(metadata, f, indent=2, ensure_ascii=False)

# --------------------------------------------------------------------
# Visualizations
# --------------------------------------------------------------------
# 1) Loss/F1 curve
fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(12, 4))
epochs_range = range(1, EPOCHS + 1)

ax1.plot(epochs_range, history["train_loss"], "b-o", label="Train Loss")
ax1.plot(epochs_range, history["val_loss"], "r-s", label="Val Loss")
ax1.set_xlabel("Epoch"); ax1.set_ylabel("Loss")
ax1.set_title("Training & Validation Loss")
ax1.legend(); ax1.grid(True, alpha=0.3)

ax2.plot(epochs_range, history["val_f1"], "g-o", label="Val F1")
ax2.plot(epochs_range, history["val_recall"], "m-s", label="Val Recall")
ax2.set_xlabel("Epoch"); ax2.set_ylabel("Score")
ax2.set_title("Validation F1 & Recall")
ax2.legend(); ax2.grid(True, alpha=0.3)

plt.tight_layout()
plt.savefig(LOSS_PNG, dpi=150)
plt.close()

# 2) Confusion matrix
fig, ax = plt.subplots(figsize=(7, 6))
im = ax.imshow(cm, cmap="Blues")
ax.set_xticks([0, 1]); ax.set_yticks([0, 1])
ax.set_xticklabels(["Predicted Safe", "Predicted Unsafe"])
ax.set_yticklabels(["Actual Safe", "Actual Unsafe"])
for i in range(2):
    for j in range(2):
        ax.text(j, i, str(cm[i, j]), ha="center", va="center",
                fontsize=18, fontweight="bold",
                color="white" if cm[i, j] > cm.max()/2 else "black")
ax.set_title(f"DistilBERT — Test Confusion Matrix (n={len(test_labels_arr)})")
plt.colorbar(im, ax=ax)
plt.tight_layout()
plt.savefig(CONFUSION_PNG, dpi=150)
plt.close()

# --------------------------------------------------------------------
# Text report
# --------------------------------------------------------------------
lines = []
lines.append("=" * 80)
lines.append("  SyncHabit NLP — DistilBERT Fine-Tuning Raporu")
lines.append("=" * 80)
lines.append(f"Model:           {MODEL_NAME}")
lines.append(f"Tip:             Türkçe DistilBERT (cased)")
lines.append(f"Framework:       PyTorch + HuggingFace Transformers")
lines.append(f"Random seed:     {RANDOM_SEED}")
lines.append("")
lines.append("HİPERPARAMETRELER:")
lines.append(f"  Epochs:        {EPOCHS}")
lines.append(f"  Batch size:    {BATCH_SIZE}")
lines.append(f"  Max length:    {MAX_LENGTH} token")
lines.append(f"  Learning rate: {LEARNING_RATE}")
lines.append(f"  Weight decay:  {WEIGHT_DECAY}")
lines.append(f"  Warmup ratio:  {WARMUP_RATIO}")
lines.append(f"  Mixed prec:    {USE_FP16}")
lines.append("")
lines.append("VERİ:")
lines.append(f"  Train: {len(train_df)} | Val: {len(val_df)} | Test: {len(test_df)}")
lines.append("")
lines.append("EĞİTİM SÜRECİ:")
for i, (tl, vl, vf1, vr) in enumerate(zip(
        history["train_loss"], history["val_loss"],
        history["val_f1"], history["val_recall"]), 1):
    lines.append(f"  Epoch {i}: train_loss={tl:.4f}, val_loss={vl:.4f}, "
                 f"val_f1={vf1:.4f}, val_recall={vr:.4f}")
lines.append("")
lines.append("TEST SETİ METRİKLERİ:")
lines.append(f"  Accuracy:    {test_acc:.4f}")
lines.append(f"  Precision:   {test_precision:.4f}")
lines.append(f"  Recall:      {test_recall:.4f}")
lines.append(f"  F1-score:    {test_f1:.4f}")
lines.append(f"  ROC-AUC:     {test_auc:.4f}")
lines.append("")
lines.append("CONFUSION MATRIX:")
lines.append(f"  TN={tn}  FP={fp}")
lines.append(f"  FN={fn}  TP={tp}")
lines.append("")
lines.append(classification_report(test_labels_arr, test_preds,
                                    target_names=["safe", "unsafe"], digits=4))

with open(REPORT_FILE, "w", encoding="utf-8") as f:
    f.write("\n".join(lines))

# --------------------------------------------------------------------
# Summary
# --------------------------------------------------------------------
print("\n" + "=" * 80)
print("  EĞİTİM TAMAMLANDI ✓")
print("=" * 80)
print(f"\nKaydedilen dosyalar:")
print(f"  Model:         {MODEL_DIR}")
print(f"  Rapor:         {REPORT_FILE}")
print(f"  Loss grafiği:  {LOSS_PNG}")
print(f"  Confusion:     {CONFUSION_PNG}")
print(f"\nMetadata: {MODEL_DIR}/metadata.json")
print(f"\nSıradaki adımlar:")
print(f"  1. python scripts/evaluate_adversarial_report.py --model-name DistilBERT")
print(f"     (önce inference_server'ı BERT'e güncelle)")
print(f"  2. TF-IDF vs DistilBERT karşılaştırma raporu")
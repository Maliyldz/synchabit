"""
SyncHabit NLP - Model Training
==============================
TF-IDF + Logistic Regression ile Türkçe toxic content detection modeli eğitir.

Strateji:
- Binary classification (safe=0, unsafe=1)
- TF-IDF n-gram (1,2) feature extraction
- LogReg + class_weight (unsafe sınıfa daha fazla ağırlık → FN düşür)
- Validation set'te threshold tuning (default 0.5 → optimal F1 threshold)
- Test set'te final değerlendirme

Çıktılar:
- synchabit_toxic_model.pkl (model + vectorizer + threshold)
- training_report.txt (detaylı metrikler)
- confusion_matrix.png (görsel rapor)
"""

import csv
import json
import pickle
import re
import warnings
from collections import Counter
from pathlib import Path

import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")  # Headless ortam için
import matplotlib.pyplot as plt
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import (
    classification_report,
    confusion_matrix,
    f1_score,
    precision_recall_curve,
    precision_score,
    recall_score,
    roc_auc_score,
    roc_curve,
)
from sklearn.svm import LinearSVC
from sklearn.calibration import CalibratedClassifierCV

warnings.filterwarnings("ignore")

# --------------------------------------------------------------------
# Reproducibility
# --------------------------------------------------------------------
RANDOM_SEED = 42
np.random.seed(RANDOM_SEED)

# --------------------------------------------------------------------
# Paths (taşınabilir)
# --------------------------------------------------------------------
ROOT = Path(__file__).resolve().parent
DATA_DIR = ROOT / "data" / "processed"
TRAIN_FILE = DATA_DIR / "train.csv"
VAL_FILE = DATA_DIR / "val.csv"
TEST_FILE = DATA_DIR / "test.csv"

MODEL_FILE = ROOT / "synchabit_toxic_model.pkl"
REPORT_FILE = ROOT / "training_report.txt"
CONFUSION_PNG = ROOT / "confusion_matrix.png"
ROC_PNG = ROOT / "roc_curve.png"
PR_PNG = ROOT / "precision_recall_curve.png"

# --------------------------------------------------------------------
# Türkçe Text Preprocessing
# --------------------------------------------------------------------
URL_PATTERN = re.compile(r"https?://\S+|www\.\S+")
NUMBER_PATTERN = re.compile(r"\b\d+\b")
MULTI_SPACE = re.compile(r"\s+")
# Noktalama: bazılarını koru (! emphasis), bazılarını sil
PUNCT_PATTERN = re.compile(r"[^\wğüşıöçĞÜŞİÖÇ!\s]")

def preprocess(text):
    """Türkçe-aware light preprocessing.
    
    Notlar:
    - Türkçe-aware lowercase: İ→i, I→ı (Python lower() bozuk).
    - URL'leri normalize ediyoruz (görev metinlerinde nadir ama olabilir).
    - Sayıları normalize ediyoruz ("50 saat uyumayacağım" → "NUM saat uyumayacağım").
    - "!" işaretini koruyoruz (vurgu sinyali olabilir).
    - Aşırı temizleme yapmıyoruz — augmentation'daki çeşitliliği kaybetmeyelim.
    """
    if not isinstance(text, str):
        return ""
    # Türkçe-aware lowercase (Python'un standart lower()'ı İ→i̇ yapıyor)
    text = text.replace("İ", "i").replace("I", "ı").lower()
    text = URL_PATTERN.sub("URL", text)
    text = NUMBER_PATTERN.sub("NUM", text)
    text = PUNCT_PATTERN.sub(" ", text)
    text = MULTI_SPACE.sub(" ", text).strip()
    return text


# --------------------------------------------------------------------
# Load Data
# --------------------------------------------------------------------
print("=" * 70)
print("VERİ YÜKLENİYOR")
print("=" * 70)

train_df = pd.read_csv(TRAIN_FILE)
val_df = pd.read_csv(VAL_FILE)
test_df = pd.read_csv(TEST_FILE)

print(f"Train: {len(train_df)} satır  | safe={(train_df['label']==0).sum()}, unsafe={(train_df['label']==1).sum()}")
print(f"Val:   {len(val_df)} satır  | safe={(val_df['label']==0).sum()}, unsafe={(val_df['label']==1).sum()}")
print(f"Test:  {len(test_df)} satır  | safe={(test_df['label']==0).sum()}, unsafe={(test_df['label']==1).sum()}")

# Preprocess
print("\nText preprocessing...")
train_df["text_clean"] = train_df["text"].apply(preprocess)
val_df["text_clean"] = val_df["text"].apply(preprocess)
test_df["text_clean"] = test_df["text"].apply(preprocess)

print(f"Örnek preprocessing:")
print(f"  Original: {train_df['text'].iloc[0]}")
print(f"  Cleaned : {train_df['text_clean'].iloc[0]}")

X_train, y_train = train_df["text_clean"].values, train_df["label"].values
X_val, y_val = val_df["text_clean"].values, val_df["label"].values
X_test, y_test = test_df["text_clean"].values, test_df["label"].values

# --------------------------------------------------------------------
# TF-IDF Vectorization
# --------------------------------------------------------------------
print("\n" + "=" * 70)
print("TF-IDF VECTORIZATION")
print("=" * 70)

vectorizer = TfidfVectorizer(
    ngram_range=(1, 2),   # tekli + ikili kelime grupları
    min_df=2,             # en az 2 dokümanda geçen kelimeler
    max_df=0.95,          # %95'ten fazla dokümanda geçenleri at (çok genel)
    max_features=10000,   # üst sınır
    sublinear_tf=True,    # log(tf+1) — uzun cümlelerin etkisini azalt
    strip_accents=None,   # Türkçe karakterleri koru!
    lowercase=False,      # zaten preprocess'te yaptık
)

X_train_vec = vectorizer.fit_transform(X_train)
X_val_vec = vectorizer.transform(X_val)
X_test_vec = vectorizer.transform(X_test)

print(f"Vocabulary size: {len(vectorizer.vocabulary_)}")
print(f"Feature matrix shape (train): {X_train_vec.shape}")
print(f"Sparsity: {(1 - X_train_vec.nnz / (X_train_vec.shape[0] * X_train_vec.shape[1])) * 100:.2f}%")

# --------------------------------------------------------------------
# Model Training - Logistic Regression
# --------------------------------------------------------------------
print("\n" + "=" * 70)
print("LOGISTIC REGRESSION EĞİTİMİ")
print("=" * 70)

# class_weight: unsafe (1) sınıfına daha fazla ağırlık ver — False Negative'i azalt
# 'balanced' otomatik olarak frekansa ters orantılı ağırlık verir
# Bizim durumda safe=53%, unsafe=47% → neredeyse dengeli, ama yine de 'balanced'
# kullanıyoruz çünkü unsafe yakalamak daha kritik.
clf_lr = LogisticRegression(
    C=1.0,
    class_weight="balanced",
    max_iter=2000,
    solver="liblinear",  # küçük datasetler için ideal, L1/L2 destekler
    random_state=RANDOM_SEED,
)
clf_lr.fit(X_train_vec, y_train)
print("✅ Logistic Regression eğitildi")

# --------------------------------------------------------------------
# Model Training - Linear SVM (karşılaştırma için)
# --------------------------------------------------------------------
print("\n" + "=" * 70)
print("LINEAR SVM EĞİTİMİ (karşılaştırma için)")
print("=" * 70)

# LinearSVC predict_proba vermez, calibrated wrapper ile sarıyoruz
base_svm = LinearSVC(
    C=1.0,
    class_weight="balanced",
    max_iter=2000,
    random_state=RANDOM_SEED,
)
clf_svm = CalibratedClassifierCV(base_svm, cv=3, method="sigmoid")
clf_svm.fit(X_train_vec, y_train)
print("✅ Linear SVM (calibrated) eğitildi")

# --------------------------------------------------------------------
# Validation Performance — model seçimi için
# --------------------------------------------------------------------
print("\n" + "=" * 70)
print("VALIDATION SETİNDE MODEL KARŞILAŞTIRMA")
print("=" * 70)

def evaluate(clf, X, y, name=""):
    probs = clf.predict_proba(X)[:, 1]
    preds_default = (probs >= 0.5).astype(int)
    precision = precision_score(y, preds_default, pos_label=1)
    recall = recall_score(y, preds_default, pos_label=1)
    f1 = f1_score(y, preds_default, pos_label=1)
    auc = roc_auc_score(y, probs)
    print(f"\n[{name}] @ threshold=0.5")
    print(f"  Precision (unsafe): {precision:.4f}")
    print(f"  Recall    (unsafe): {recall:.4f}")
    print(f"  F1-score  (unsafe): {f1:.4f}")
    print(f"  ROC-AUC           : {auc:.4f}")
    return {"precision": precision, "recall": recall, "f1": f1, "auc": auc, "probs": probs}

lr_val = evaluate(clf_lr, X_val_vec, y_val, "Logistic Regression")
svm_val = evaluate(clf_svm, X_val_vec, y_val, "Linear SVM")

# Model seçimi: F1 + Recall öncelikli
if lr_val["recall"] >= svm_val["recall"] - 0.02 and lr_val["f1"] >= svm_val["f1"] - 0.01:
    chosen_model = clf_lr
    chosen_name = "LogisticRegression"
    chosen_val = lr_val
elif svm_val["f1"] > lr_val["f1"]:
    chosen_model = clf_svm
    chosen_name = "LinearSVM"
    chosen_val = svm_val
else:
    chosen_model = clf_lr
    chosen_name = "LogisticRegression"
    chosen_val = lr_val

print(f"\n🏆 Seçilen Model: {chosen_name}")

# --------------------------------------------------------------------
# Threshold Tuning (validation set üzerinde)
# --------------------------------------------------------------------
print("\n" + "=" * 70)
print("THRESHOLD TUNING (False Negative minimize)")
print("=" * 70)

val_probs = chosen_val["probs"]
precisions, recalls, thresholds = precision_recall_curve(y_val, val_probs)
# F1 hesapla her threshold için
f1_scores = 2 * (precisions * recalls) / (precisions + recalls + 1e-10)

# En iyi F1 threshold
best_f1_idx = np.argmax(f1_scores[:-1])  # son element threshold'suz
best_f1_threshold = thresholds[best_f1_idx]

# En iyi recall'lu (precision >= 0.85 kısıt) threshold — FN minimize için
recall_priority_mask = precisions[:-1] >= 0.85
if recall_priority_mask.any():
    candidates = np.where(recall_priority_mask)[0]
    # Bunlar içinde en yüksek recall
    best_recall_idx = candidates[np.argmax(recalls[:-1][candidates])]
    best_recall_threshold = thresholds[best_recall_idx]
else:
    best_recall_threshold = best_f1_threshold

print(f"Best F1 threshold      : {best_f1_threshold:.4f}  (F1={f1_scores[best_f1_idx]:.4f})")
print(f"Best Recall threshold  : {best_recall_threshold:.4f}  (Precision≥0.85)")
print(f"  → Recall@best_recall : {recalls[best_recall_idx if recall_priority_mask.any() else best_f1_idx]:.4f}")
print(f"  → Precision@best_rec : {precisions[best_recall_idx if recall_priority_mask.any() else best_f1_idx]:.4f}")

# Tez tercihi: FN düşür → Recall priority
FINAL_THRESHOLD = float(best_recall_threshold)
print(f"\n🎯 Production Threshold: {FINAL_THRESHOLD:.4f}")
print(f"   (Bu threshold False Negative'i minimize eder)")

# --------------------------------------------------------------------
# Test Set Final Değerlendirme
# --------------------------------------------------------------------
print("\n" + "=" * 70)
print("TEST SETİ FINAL DEĞERLENDİRME")
print("=" * 70)

test_probs = chosen_model.predict_proba(X_test_vec)[:, 1]
test_preds = (test_probs >= FINAL_THRESHOLD).astype(int)

print(f"\n[{chosen_name}] @ threshold={FINAL_THRESHOLD:.4f}")
print("\n" + classification_report(y_test, test_preds, target_names=["safe (0)", "unsafe (1)"], digits=4))

cm = confusion_matrix(y_test, test_preds)
tn, fp, fn, tp = cm.ravel()
print(f"\nConfusion Matrix:")
print(f"                 Predicted Safe   Predicted Unsafe")
print(f"Actual Safe      {tn:5d} (TN)       {fp:5d} (FP)")
print(f"Actual Unsafe    {fn:5d} (FN) ⚠️     {tp:5d} (TP)")

test_auc = roc_auc_score(y_test, test_probs)
print(f"\nROC-AUC: {test_auc:.4f}")

# False Negative analizi — kritik!
fn_indices = np.where((y_test == 1) & (test_preds == 0))[0]
print(f"\n⚠️  FALSE NEGATIVE COUNT: {len(fn_indices)}  (kaçırılan zararlı içerikler)")
if len(fn_indices) > 0 and len(fn_indices) <= 30:
    print("False Negative örnekleri (model bunları 'safe' dedi ama gerçekte 'unsafe'):")
    for idx in fn_indices[:30]:
        orig_text = test_df.iloc[idx]["text"]
        prob = test_probs[idx]
        subcategory = test_df.iloc[idx].get("subcategory", "?")
        print(f"  [{subcategory:20s}] prob={prob:.3f}  '{orig_text}'")

# False Positive analizi
fp_indices = np.where((y_test == 0) & (test_preds == 1))[0]
print(f"\n📌 False Positive Count: {len(fp_indices)}  (yanlışlıkla zararlı denilen)")
if len(fp_indices) > 0 and len(fp_indices) <= 15:
    print("False Positive örnekleri:")
    for idx in fp_indices[:15]:
        orig_text = test_df.iloc[idx]["text"]
        prob = test_probs[idx]
        subcategory = test_df.iloc[idx].get("subcategory", "?")
        print(f"  [{subcategory:20s}] prob={prob:.3f}  '{orig_text}'")

# --------------------------------------------------------------------
# Feature Importance — hangi kelimeler unsafe sinyali?
# --------------------------------------------------------------------
print("\n" + "=" * 70)
print("EN ÖNEMLİ KELİMELER (model interpretability)")
print("=" * 70)

if chosen_name == "LogisticRegression":
    feature_names = vectorizer.get_feature_names_out()
    coefs = chosen_model.coef_[0]
    # En yüksek pozitif (unsafe sinyali)
    top_unsafe_idx = np.argsort(coefs)[-25:][::-1]
    print("\nUNSAFE sinyali en güçlü 25 kelime/n-gram:")
    for idx in top_unsafe_idx:
        print(f"  {feature_names[idx]:30s}  coef={coefs[idx]:+.3f}")
    # En düşük (safe sinyali)
    top_safe_idx = np.argsort(coefs)[:15]
    print("\nSAFE sinyali en güçlü 15 kelime/n-gram:")
    for idx in top_safe_idx:
        print(f"  {feature_names[idx]:30s}  coef={coefs[idx]:+.3f}")

# --------------------------------------------------------------------
# Visualizations
# --------------------------------------------------------------------
print("\n" + "=" * 70)
print("GRAFİKLER OLUŞTURULUYOR")
print("=" * 70)

# 1) Confusion Matrix
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
ax.set_title(f"Confusion Matrix — {chosen_name}\n"
             f"Threshold={FINAL_THRESHOLD:.3f} | Test set (n={len(y_test)})")
plt.colorbar(im, ax=ax)
plt.tight_layout()
plt.savefig(CONFUSION_PNG, dpi=150)
plt.close()
print(f"  ✅ {CONFUSION_PNG.name}")

# 2) ROC Curve
fpr, tpr, _ = roc_curve(y_test, test_probs)
fig, ax = plt.subplots(figsize=(7, 6))
ax.plot(fpr, tpr, label=f"{chosen_name} (AUC={test_auc:.3f})", linewidth=2)
ax.plot([0, 1], [0, 1], "k--", alpha=0.4, label="Random")
ax.set_xlabel("False Positive Rate")
ax.set_ylabel("True Positive Rate (Recall)")
ax.set_title("ROC Curve — Test Set")
ax.legend(loc="lower right")
ax.grid(True, alpha=0.3)
plt.tight_layout()
plt.savefig(ROC_PNG, dpi=150)
plt.close()
print(f"  ✅ {ROC_PNG.name}")

# 3) Precision-Recall Curve
fig, ax = plt.subplots(figsize=(7, 6))
ax.plot(recalls, precisions, linewidth=2, label="LR (val)")
ax.axvline(x=recalls[best_recall_idx if recall_priority_mask.any() else best_f1_idx],
           color='r', linestyle='--', alpha=0.6, label=f"Chosen thr={FINAL_THRESHOLD:.3f}")
ax.set_xlabel("Recall")
ax.set_ylabel("Precision")
ax.set_title("Precision-Recall Curve — Validation Set")
ax.legend()
ax.grid(True, alpha=0.3)
plt.tight_layout()
plt.savefig(PR_PNG, dpi=150)
plt.close()
print(f"  ✅ {PR_PNG.name}")

# --------------------------------------------------------------------
# Save Model + Vectorizer + Threshold
# --------------------------------------------------------------------
print("\n" + "=" * 70)
print("MODEL KAYDEDİLİYOR")
print("=" * 70)

model_bundle = {
    "model": chosen_model,
    "vectorizer": vectorizer,
    "threshold": FINAL_THRESHOLD,
    "model_name": chosen_name,
    "metadata": {
        "train_size": len(train_df),
        "val_size": len(val_df),
        "test_size": len(test_df),
        "test_precision": float(precision_score(y_test, test_preds, pos_label=1)),
        "test_recall": float(recall_score(y_test, test_preds, pos_label=1)),
        "test_f1": float(f1_score(y_test, test_preds, pos_label=1)),
        "test_auc": float(test_auc),
        "false_negatives": int(fn),
        "false_positives": int(fp),
        "true_positives": int(tp),
        "true_negatives": int(tn),
        "vocabulary_size": len(vectorizer.vocabulary_),
        "random_seed": RANDOM_SEED,
    },
}

with open(MODEL_FILE, "wb") as f:
    pickle.dump(model_bundle, f)
print(f"  ✅ {MODEL_FILE.name}  ({MODEL_FILE.stat().st_size / 1024:.1f} KB)")

# --------------------------------------------------------------------
# Save Text Report
# --------------------------------------------------------------------
report_lines = []
report_lines.append("=" * 70)
report_lines.append("SyncHabit NLP - Training Report")
report_lines.append("=" * 70)
report_lines.append(f"Model: {chosen_name}")
report_lines.append(f"Threshold: {FINAL_THRESHOLD:.4f}")
report_lines.append(f"Random Seed: {RANDOM_SEED}")
report_lines.append("")
report_lines.append(f"Dataset:")
report_lines.append(f"  Train: {len(train_df)}  | safe={(train_df['label']==0).sum()}, unsafe={(train_df['label']==1).sum()}")
report_lines.append(f"  Val:   {len(val_df)}  | safe={(val_df['label']==0).sum()}, unsafe={(val_df['label']==1).sum()}")
report_lines.append(f"  Test:  {len(test_df)}  | safe={(test_df['label']==0).sum()}, unsafe={(test_df['label']==1).sum()}")
report_lines.append("")
report_lines.append(f"TF-IDF:")
report_lines.append(f"  Vocabulary: {len(vectorizer.vocabulary_)}")
report_lines.append(f"  n-gram: (1, 2)")
report_lines.append(f"  min_df=2, max_df=0.95, max_features=10000")
report_lines.append("")
report_lines.append(f"Test Set Performance:")
report_lines.append(classification_report(y_test, test_preds, target_names=["safe", "unsafe"], digits=4))
report_lines.append("")
report_lines.append(f"Confusion Matrix:")
report_lines.append(f"  TN={tn}  FP={fp}")
report_lines.append(f"  FN={fn}  TP={tp}")
report_lines.append(f"")
report_lines.append(f"ROC-AUC: {test_auc:.4f}")
report_lines.append(f"False Negative Rate: {fn/(fn+tp):.4f}  (kritik metrik)")
report_lines.append(f"False Positive Rate: {fp/(fp+tn):.4f}")

with open(REPORT_FILE, "w", encoding="utf-8") as f:
    f.write("\n".join(report_lines))
print(f"  ✅ {REPORT_FILE.name}")

print("\n" + "=" * 70)
print("EĞİTİM TAMAMLANDI ✅")
print("=" * 70)
print(f"\nÇıktılar:")
print(f"  - {MODEL_FILE}")
print(f"  - {REPORT_FILE}")
print(f"  - {CONFUSION_PNG}")
print(f"  - {ROC_PNG}")
print(f"  - {PR_PNG}")
print(f"\nKullanım örneği:")
print('''
import pickle
with open("synchabit_toxic_model.pkl", "rb") as f:
    bundle = pickle.load(f)

model = bundle["model"]
vectorizer = bundle["vectorizer"]
threshold = bundle["threshold"]

def predict(text):
    from <bu_script> import preprocess  # preprocess fonksiyonunu import et
    clean = preprocess(text)
    vec = vectorizer.transform([clean])
    prob = model.predict_proba(vec)[0, 1]
    is_unsafe = prob >= threshold
    return {"is_unsafe": bool(is_unsafe), "probability": float(prob)}

print(predict("Bileğimi keseceğim"))
# {'is_unsafe': True, 'probability': 0.97}
''')

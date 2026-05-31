"""
Adversarial Set ile NLP Sunucusunu Değerlendirme — TEZ İÇİN HAZIR RAPOR
=======================================================================
Bu script:
  1. Çalışan NLP sunucusuna (port 8001) HTTP istekleri atar
  2. Adversarial test set'indeki cümleleri gönderir
  3. Hem TERMİNALE basar (canlı görmek için)
  4. Hem de tez-için-hazır formatlı bir RAPOR dosyası üretir

KULLANIM:
  Terminal 1:  python inference_server.py
  Terminal 2:  python scripts/evaluate_adversarial_report.py
  Terminal 2:  python scripts/evaluate_adversarial_report.py --model-name "DistilBERT"

ÇIKTILAR:
  data/adversarial/evaluation_results.csv     ← detaylı CSV (her cümle)
  data/adversarial/report_TFIDF.txt           ← tezde kullanılabilir terminal-format raporu
  
  (model-name parametresi ile dosya adı değişir, böylece TF-IDF ve BERT
   raporlarını ayrı ayrı saklayabilirsin)
"""

import argparse
import csv
import io
import json
import sys
import urllib.error
import urllib.request
from collections import defaultdict
from datetime import datetime
from pathlib import Path

# --------------------------------------------------------------------
# Argümanlar
# --------------------------------------------------------------------
parser = argparse.ArgumentParser(description="Adversarial evaluation with text report")
parser.add_argument("--model-name", default="TFIDF",
                    help="Rapor dosyası ismi için model adı (örn. TFIDF, DistilBERT)")
parser.add_argument("--nlp-url", default="http://localhost:8001/predict",
                    help="NLP sunucu URL'i")
args = parser.parse_args()

MODEL_NAME = args.model_name
NLP_URL = args.nlp_url

# --------------------------------------------------------------------
# Paths
# --------------------------------------------------------------------
ROOT = Path(__file__).resolve().parent.parent
ADVERSARIAL_FILE = ROOT / "data" / "adversarial" / "adversarial_test.csv"
RESULTS_CSV = ROOT / "data" / "adversarial" / f"evaluation_results_{MODEL_NAME}.csv"
REPORT_TXT = ROOT / "data" / "adversarial" / f"report_{MODEL_NAME}.txt"

# --------------------------------------------------------------------
# Dual Output: hem terminale hem dosyaya yaz
# --------------------------------------------------------------------
class TeeWriter:
    """Birden fazla stream'e aynı anda yazar (terminal + dosya)."""
    def __init__(self, *streams):
        self.streams = streams
    def write(self, msg):
        for s in self.streams:
            s.write(msg)
            s.flush()
    def flush(self):
        for s in self.streams:
            s.flush()


# --------------------------------------------------------------------
# HTTP call
# --------------------------------------------------------------------
def call_nlp(text):
    body = json.dumps({"text": text}).encode("utf-8")
    req = urllib.request.Request(
        NLP_URL, data=body,
        headers={"Content-Type": "application/json; charset=utf-8"},
        method="POST"
    )
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except urllib.error.URLError as e:
        print(f"\n❌ NLP server erişilemedi: {e}")
        print(f"Önce 'python inference_server.py' başlat.")
        sys.exit(1)


# --------------------------------------------------------------------
# Load adversarial set
# --------------------------------------------------------------------
if not ADVERSARIAL_FILE.exists():
    print(f"❌ Adversarial set bulunamadı: {ADVERSARIAL_FILE}")
    sys.exit(1)

with open(ADVERSARIAL_FILE, "r", encoding="utf-8") as f:
    cases = list(csv.DictReader(f))

# --------------------------------------------------------------------
# Açılış (sadece terminale)
# --------------------------------------------------------------------
print(f"📂 {len(cases)} adversarial test cümlesi yüklendi")
print(f"🔗 NLP sunucusu: {NLP_URL}")
print(f"🏷️  Model: {MODEL_NAME}")
print(f"💾 Rapor dosyası: {REPORT_TXT}")

# Health check
print("\nHealth check...")
result = call_nlp("test")
print(f"  ✓ Sunucu cevap veriyor (action={result.get('action')})\n")

# --------------------------------------------------------------------
# RAPOR YAZIMI BAŞLIYOR (terminal + dosya aynı anda)
# --------------------------------------------------------------------
REPORT_TXT.parent.mkdir(parents=True, exist_ok=True)
report_file = open(REPORT_TXT, "w", encoding="utf-8")

# Tee setup: bundan sonra "print()" hem terminale hem dosyaya yazacak
original_stdout = sys.stdout
sys.stdout = TeeWriter(original_stdout, report_file)

# --------------------------------------------------------------------
# RAPOR İÇERİĞİ — buradan itibaren her print() hem ekrana hem dosyaya
# --------------------------------------------------------------------

print("=" * 85)
print(f"  SyncHabit NLP — Adversarial Test Değerlendirme Raporu")
print(f"  Model: {MODEL_NAME}")
print(f"  Tarih: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
print(f"  Toplam Test Cümlesi: {len(cases)}")
print("=" * 85)
print()
print("Adversarial test seti, kelime tabanlı modellerin sınırlarını sınamak için")
print("özel olarak tasarlanmış cümleleri içerir. Anlamsal tehlike, mecaz, deyim,")
print("homonym (çok-anlamlılık), eufemizm ve örtük şiddet gibi bağlamsal anlama")
print("gerektiren senaryoları kapsar.")
print()

# --------------------------------------------------------------------
# Run evaluation
# --------------------------------------------------------------------
print("-" * 85)
print(f"{'#':<4}{'Beklenen':<11}{'Tahmin':<8}{'Prob':<7}{'Kategori':<20}{'Cümle'}")
print("-" * 85)

results = []
for i, case in enumerate(cases, 1):
    text = case["text"]
    true_label = int(case["label"])
    category = case["category"]
    
    # NLP isteği (geçici olarak orijinal stdout'a yaz, dosyaya gitmesin progress)
    sys.stdout = original_stdout  # geçici
    sys.stdout.write(f"\r  İşleniyor: {i}/{len(cases)}...")
    sys.stdout.flush()
    sys.stdout = TeeWriter(original_stdout, report_file)  # tekrar tee

    pred = call_nlp(text)
    pred_label = 1 if pred["action"] in ("block", "warn") else 0
    correct = (true_label == pred_label)
    
    results.append({
        "text": text,
        "category": category,
        "true_label": true_label,
        "pred_label": pred_label,
        "action": pred["action"],
        "probability": pred["probability"],
        "reason": pred.get("reason", ""),
        "correct": correct,
    })

# Progress satırını temizle
sys.stdout = original_stdout
sys.stdout.write("\r" + " " * 50 + "\r")
sys.stdout = TeeWriter(original_stdout, report_file)

# Şimdi tüm sonuçları yazdır (rapora gidiyor)
for i, r in enumerate(results, 1):
    exp = "UNSAFE" if r["true_label"]==1 else "SAFE"
    got = r["action"].upper()
    icon = "✓" if r["correct"] else "✗"
    text = r["text"]
    if len(text) > 38:
        text = text[:35] + "..."
    print(f"{icon}{i:<3}{exp:<11}{got:<8}{r['probability']:<7.3f}{r['category']:<20}{text}")

print("-" * 85)
print()

# --------------------------------------------------------------------
# Aggregate statistics
# --------------------------------------------------------------------
total = len(results)
correct_total = sum(1 for r in results if r["correct"])
overall = correct_total / total * 100

print("=" * 85)
print(f"  GENEL BAŞARI: {correct_total}/{total} = {overall:.1f}%")
print("=" * 85)
print()

# Per category
print("KATEGORİ BAZINDA BAŞARI:")
print("-" * 60)
by_cat = defaultdict(list)
for r in results:
    by_cat[r["category"]].append(r)

# Sort by accuracy ascending (worst first — gözünü acıtsın)
cat_stats = []
for cat in by_cat:
    items = by_cat[cat]
    c = sum(1 for r in items if r["correct"])
    t = len(items)
    cat_stats.append((cat, c, t, c/t*100))

cat_stats.sort(key=lambda x: x[3])  # accuracy ascending

for cat, c, t, pct in cat_stats:
    icon = "✓" if pct == 100 else ("~" if pct >= 70 else ("?" if pct >= 50 else "✗"))
    bar_length = int(pct / 5)  # 20-char bar
    bar = "█" * bar_length + "░" * (20 - bar_length)
    print(f"  [{icon}] {cat:<20s} {bar} {c:>2}/{t:<2}  {pct:>5.1f}%")

print()

# Confusion matrix
print("CONFUSION MATRIX:")
print("-" * 60)
tp = sum(1 for r in results if r["true_label"] == 1 and r["pred_label"] == 1)
tn = sum(1 for r in results if r["true_label"] == 0 and r["pred_label"] == 0)
fp = sum(1 for r in results if r["true_label"] == 0 and r["pred_label"] == 1)
fn = sum(1 for r in results if r["true_label"] == 1 and r["pred_label"] == 0)

print(f"                       Tahmin: SAFE   Tahmin: UNSAFE")
print(f"  Gerçek: SAFE         {tn:>4} (TN)      {fp:>4} (FP)")
print(f"  Gerçek: UNSAFE       {fn:>4} (FN)      {tp:>4} (TP)")
print()

# Precision / Recall / F1 for unsafe class
prec = tp / (tp + fp) if (tp + fp) > 0 else 0
rec = tp / (tp + fn) if (tp + fn) > 0 else 0
f1 = 2 * prec * rec / (prec + rec) if (prec + rec) > 0 else 0
accuracy = (tp + tn) / total if total > 0 else 0

print("METRİKLER (Unsafe sınıfı):")
print("-" * 60)
print(f"  Accuracy:    {accuracy:.4f}    (toplam doğru / toplam)")
print(f"  Precision:   {prec:.4f}    (TP / (TP+FP))")
print(f"  Recall:      {rec:.4f}    (TP / (TP+FN))   ← tehlike yakalama")
print(f"  F1-score:    {f1:.4f}    (precision-recall harmonic mean)")
print()

# Show failures
print("=" * 85)
print(f"  HATA ANALİZİ — Yanlış Sınıflandırılan {total-correct_total} Cümle")
print("=" * 85)
print()

# False Negative (tehlikeyi kaçırma — daha kritik)
fns = [r for r in results if r["true_label"] == 1 and r["pred_label"] == 0]
if fns:
    print(f"⚠️  FALSE NEGATIVE — Kaçırılan Tehlikeler ({len(fns)} adet, kritik!)")
    print("-" * 85)
    for r in fns:
        text = r["text"] if len(r["text"]) <= 60 else r["text"][:57] + "..."
        print(f"  • [{r['category']:<18s}] (prob={r['probability']:.2f})")
        print(f"    \"{text}\"")
        print(f"    → Model: {r['action'].upper()} | Olması gereken: BLOCK")
        print()

# False Positive (yanlış engelleme)
fps = [r for r in results if r["true_label"] == 0 and r["pred_label"] == 1]
if fps:
    print(f"⚠️  FALSE POSITIVE — Yanlış Engellenen Masum Cümleler ({len(fps)} adet)")
    print("-" * 85)
    for r in fps:
        text = r["text"] if len(r["text"]) <= 60 else r["text"][:57] + "..."
        print(f"  • [{r['category']:<18s}] (prob={r['probability']:.2f})")
        print(f"    \"{text}\"")
        print(f"    → Model: {r['action'].upper()} | Olması gereken: ALLOW")
        print()

print("=" * 85)
print("Rapor sonu.")
print("=" * 85)

# --------------------------------------------------------------------
# Cleanup: stdout'u geri yükle
# --------------------------------------------------------------------
sys.stdout = original_stdout
report_file.close()

# Save CSV
with open(RESULTS_CSV, "w", encoding="utf-8", newline="") as f:
    writer = csv.DictWriter(f, fieldnames=list(results[0].keys()))
    writer.writeheader()
    writer.writerows(results)

print(f"\n✓ Rapor kaydedildi: {REPORT_TXT}")
print(f"✓ Detaylı CSV:      {RESULTS_CSV}")
print(f"\nÖZET: {MODEL_NAME} adversarial başarısı = {overall:.1f}%")
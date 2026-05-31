"""
SyncHabit NLP - DistilBERT Inference Server
============================================
TF-IDF inference_server.py'nin DistilBERT versiyonu.

Aynı API kontratı:
  POST /predict  {"text": "..."}  →  {"action": "...", "probability": ..., ...}
  GET  /health
  Port: 8001

3-Tier:
  Block (≥0.70), Warn (0.40-0.70), Allow (<0.40)

Keyword Override:
  TF-IDF versiyonundaki kurallar aynen korunur — defense-in-depth.

C# tarafı için hiçbir değişiklik gerekmez (response format aynı).

KULLANIM:
  python inference_server_bert.py     ← BU script'i çalıştır
  (TF-IDF inference_server.py'i durdur, ikisi aynı port'u kullanamaz)
"""

import json
import logging
import re
import sys
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path

import torch
from transformers import AutoTokenizer, AutoModelForSequenceClassification

# --------------------------------------------------------------------
# Configuration
# --------------------------------------------------------------------
HOST = "0.0.0.0"
PORT = 8001

ROOT = Path(__file__).resolve().parent
MODEL_DIR = ROOT / "models" / "distilbert"

BLOCK_THRESHOLD = 0.70
WARN_THRESHOLD = 0.40

MAX_LENGTH = 64

# --------------------------------------------------------------------
# Logging
# --------------------------------------------------------------------
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
log = logging.getLogger("synchabit-nlp-bert")


# --------------------------------------------------------------------
# Turkish-aware lowercase (İ→i bug fix)
# --------------------------------------------------------------------
def tr_lower(text):
    return text.replace("İ", "i").replace("I", "ı").lower()


# --------------------------------------------------------------------
# KEYWORD OVERRIDE (TF-IDF versiyonundan birebir aynı)
# --------------------------------------------------------------------
NEGATION_PATTERNS = [
    "kesmeyeceğim", "kesmeyecem", "kesmem", "kesmiyorum",
    "atlamayacağım", "atlamicem", "atlamayacak",
    "öldürmeyeceğim", "öldürmem", "öldürmüyorum",
    "yapmayacağım", "yapmam",
    "asmayacağım", "asmam",
    "vermeyeceğim", "vermem",
    "etmeyeceğim", "etmem",
    "almayacağım",
    "içmeyeceğim",
    "yaralamayacağım", "yaralamam",
    "kıymayacağım", "kıymam",
    "bıraktım", "atlattım", "yendim", "yenmek istiyorum",
    "geçmişte", "eskiden", "iyileşmeye",
    "asla ", " asla", "hiç bir", "hiçbir zaman",
]

POSITIVE_FRAME_INDICATORS = [
    "bıraktım", "atlattım", "yendim", "yenmek istiyorum",
    "geçmişte", "eskiden", "iyileşmeye karar verdim",
    "hayatı seviyorum", "yaşama tutunac", "umut",
    "terapide", "iyileşiyorum", "iyiyim artık",
]

HARD_BLOCK_RULES = [
    # ===== Self-harm / Suicidal (1. tekil) =====
    (("bileğim", "kes"), "self_harm", "Bilek kesme niyeti"),
    (("bileklerim", "kes"), "self_harm", "Bilek kesme niyeti"),
    (("kolum", "kes"), "self_harm", "Kol kesme niyeti"),
    (("kollarım", "kes"), "self_harm", "Kol kesme niyeti"),
    (("kendim", "öldür"), "self_harm", "İntihar niyeti"),
    (("kendimi", "öldür"), "self_harm", "İntihar niyeti"),
    (("kendime", "kıy"), "self_harm", "İntihar niyeti"),
    (("intihar", "edec"), "self_harm", "Açık intihar niyeti"),
    (("intihar", "ediyor"), "self_harm", "Açık intihar niyeti"),
    (("hayatım", "son ver"), "self_harm", "İntihar niyeti"),
    (("hayatima", "son ver"), "self_harm", "İntihar niyeti"),
    (("kendim", "as"), "self_harm", "Kendini asma niyeti"),
    (("kendimi", "as"), "self_harm", "Kendini asma niyeti"),
    (("ip", "kendim"), "self_harm", "Kendini asma niyeti"),
    (("kendime", "zarar"), "self_harm", "Kendine zarar"),
    (("aşırı doz", "alac"), "self_harm", "Overdose niyeti"),
    (("yüksek doz", "hap"), "self_harm", "Overdose niyeti"),
    (("gaz", "kapatac"), "self_harm", "Gaz ile intihar"),
    (("gaz", "açıp uyu"), "self_harm", "Gaz ile intihar"),

    # ===== Self-harm / Suicidal (2. tekil - EMİR KİPİ) =====
    (("bileğin", "kes"), "self_harm", "Emir kipi - bilek kesme"),
    (("bileklerin", "kes"), "self_harm", "Emir kipi - bilek kesme"),
    (("kolun", "kes"), "self_harm", "Emir kipi - kol kesme"),
    (("kollarin", "kes"), "self_harm", "Emir kipi - kol kesme"),
    (("kollarını", "kes"), "self_harm", "Emir kipi - kol kesme"),
    (("kendine", "zarar ver"), "self_harm", "Emir - kendine zarar"),
    (("kendine", "acı"), "self_harm", "Emir - kendine acı"),
    (("kendini", "kes"), "self_harm", "Emir - kesme"),
    (("kendini", "yarala"), "self_harm", "Emir - yaralama"),
    (("kendini", "öldür"), "self_harm", "Emir - intihar"),
    (("kendini", "as"), "self_harm", "Emir - asılma"),
    (("hayatına", "son ver"), "self_harm", "Emir - intihar"),
    (("yüksekten", "atla"), "self_harm", "Emir - intihar/dare"),
    (("köprüden", "atla"), "self_harm", "Emir - intihar"),
    (("pencereden", "atla"), "self_harm", "Emir - intihar"),
    (("trene", "atla"), "self_harm", "Emir - intihar"),
    (("aşırı doz", "al"), "self_harm", "Emir - overdose"),
    (("yüksek doz", "al"), "self_harm", "Emir - overdose"),

    # ===== Risky Dare / Mavi Balina =====
    (("mavi balina",), "blue_whale", "Mavi balina oyunu"),
    (("mavi balina", "görev"), "blue_whale", "Mavi balina görevleri"),
    (("balina oyunu",), "blue_whale", "Mavi balina referansı"),
    (("son görev", "atmak"), "blue_whale", "Mavi balina pattern"),
    (("son görev", "atlamak"), "blue_whale", "Mavi balina pattern"),

    # ===== Violence to others =====
    (("birini", "öldür"), "violence", "Başkasını öldürme"),
    (("birini", "bıçakla"), "violence", "Bıçaklama"),
    (("silahla", "okul"), "violence", "Okula silahlı saldırı"),
    (("silahla", "gid"), "violence", "Silahlı saldırı"),
    (("silahla", "git"), "violence", "Emir - silahlı saldırı"),
    (("bombayla",), "violence", "Bombalı saldırı"),
    (("zehir", "ver"), "violence", "Zehirleme"),
    (("asit", "at"), "violence", "Asit saldırısı"),
    (("birini", "döv"), "violence", "Emir - dövme"),
    (("birini", "yarala"), "violence", "Emir - yaralama"),
    (("birini", "boğ"), "violence", "Emir - boğma"),
    (("kediyi", "tekmele"), "violence", "Emir - hayvan istismarı"),
    (("köpeği", "tekmele"), "violence", "Emir - hayvan istismarı"),
    (("hayvana", "zarar"), "violence", "Emir - hayvan istismarı"),

    # ===== Vandalism =====
    (("anahtarla", "çiz"), "vandalism", "Anahtarla çizme"),
    (("anahtarla", "araba"), "vandalism", "Anahtarla araba kazıma"),
    (("camını", "kır"), "vandalism", "Cam kırma"),
    (("lastiğini", "patlat"), "vandalism", "Lastik patlatma"),
    (("birinin", "yak"), "vandalism", "Eşya yakma"),
]


def has_negation(text_lower):
    """Cümlede olumsuzluk veya iyileşme çerçevesi var mı?"""
    if any(neg in text_lower for neg in NEGATION_PATTERNS):
        return True
    if any(ind in text_lower for ind in POSITIVE_FRAME_INDICATORS):
        return True
    return False


def keyword_override(text):
    """Hard-block keyword kontrolü. Negation guard ile."""
    text_lower = tr_lower(text)
    if has_negation(text_lower):
        return False, None, [], None
    for required_words, category, reason in HARD_BLOCK_RULES:
        if all(word in text_lower for word in required_words):
            return True, category, list(required_words), reason
    return False, None, [], None


# --------------------------------------------------------------------
# Model Loading
# --------------------------------------------------------------------
if not MODEL_DIR.exists():
    log.error("❌ Model dizini bulunamadı: %s", MODEL_DIR)
    log.error("   Önce 'python train_bert.py' çalıştır.")
    sys.exit(1)

log.info("Model yükleniyor: %s", MODEL_DIR)
device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
log.info("Device: %s", device)
if device.type == "cuda":
    log.info("GPU: %s", torch.cuda.get_device_name(0))

tokenizer = AutoTokenizer.from_pretrained(MODEL_DIR)
model = AutoModelForSequenceClassification.from_pretrained(MODEL_DIR)
model.to(device)
model.eval()

# Metadata
metadata_file = MODEL_DIR / "metadata.json"
metadata = {}
if metadata_file.exists():
    with open(metadata_file, "r", encoding="utf-8") as f:
        metadata = json.load(f)

log.info("✅ Model yüklendi: DistilBERT")
log.info("   Test F1:     %.4f", metadata.get("test_metrics", {}).get("f1", 0.0))
log.info("   Test Recall: %.4f", metadata.get("test_metrics", {}).get("recall", 0.0))
log.info("   3-tier: BLOCK≥%.2f, WARN≥%.2f", BLOCK_THRESHOLD, WARN_THRESHOLD)


# --------------------------------------------------------------------
# Inference
# --------------------------------------------------------------------
def predict_with_bert(text):
    """DistilBERT ile inference. Returns probability of unsafe (label=1)."""
    inputs = tokenizer(
        text,
        truncation=True,
        padding="max_length",
        max_length=MAX_LENGTH,
        return_tensors="pt",
    ).to(device)
    
    with torch.no_grad():
        outputs = model(**inputs)
        probs = torch.softmax(outputs.logits, dim=1)
        unsafe_prob = float(probs[0, 1].item())
    
    return unsafe_prob


def predict(text):
    """Full prediction pipeline: keyword override → BERT → 3-tier decision."""
    if not text or not isinstance(text, str):
        return {
            "action": "allow",
            "probability": 0.0,
            "category": None,
            "matched_keywords": [],
            "reason": "empty_text",
            "is_safe": True,
        }
    
    # Layer 1: Keyword override
    overridden, category, keywords, kw_reason = keyword_override(text)
    if overridden:
        return {
            "action": "block",
            "probability": 1.0,
            "category": category,
            "matched_keywords": keywords,
            "reason": "hard_block",
            "is_safe": False,
        }
    
    # Layer 2: BERT inference
    try:
        prob = predict_with_bert(text)
    except Exception as e:
        log.exception("BERT inference hatası")
        return {
            "action": "allow",
            "probability": 0.0,
            "category": None,
            "matched_keywords": [],
            "reason": f"bert_error: {e}",
            "is_safe": True,
        }
    
    # Layer 3: 3-tier decision
    if prob >= BLOCK_THRESHOLD:
        action, reason = "block", "ml_high_confidence"
        is_safe = False
    elif prob >= WARN_THRESHOLD:
        action, reason = "warn", "ml_uncertain"
        is_safe = False
    else:
        action, reason = "allow", "ml_safe"
        is_safe = True
    
    return {
        "action": action,
        "probability": round(prob, 4),
        "category": None,
        "matched_keywords": [],
        "reason": reason,
        "is_safe": is_safe,
    }


# --------------------------------------------------------------------
# HTTP Handler
# --------------------------------------------------------------------
class SyncHabitNLPHandler(BaseHTTPRequestHandler):
    def log_message(self, format, *args):
        return  # quiet
    
    def _send_json(self, status, payload):
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)
    
    def do_GET(self):
        if self.path == "/health":
            self._send_json(200, {
                "status": "ok",
                "model": "DistilBERT",
                "model_path": str(MODEL_DIR),
                "device": str(device),
                "thresholds": {"block": BLOCK_THRESHOLD, "warn": WARN_THRESHOLD},
                "metadata": metadata,
            })
        else:
            self._send_json(404, {"error": "Not found"})
    
    def do_POST(self):
        if self.path != "/predict":
            self._send_json(404, {"error": "Not found"})
            return
        
        try:
            content_length = int(self.headers.get("Content-Length", 0))
        except (TypeError, ValueError):
            self._send_json(400, {"error": "Invalid Content-Length"})
            return
        
        if content_length == 0:
            self._send_json(400, {"error": "Empty body"})
            return
        if content_length > 10_000:
            self._send_json(413, {"error": "Payload too large"})
            return
        
        try:
            raw = self.rfile.read(content_length)
            payload = json.loads(raw.decode("utf-8"))
        except (json.JSONDecodeError, UnicodeDecodeError) as e:
            self._send_json(400, {"error": f"Invalid JSON: {e}"})
            return
        
        text = payload.get("text")
        if not isinstance(text, str):
            self._send_json(400, {"error": "'text' field required (string)"})
            return
        
        try:
            result = predict(text)
            short = text[:50] + "…" if len(text) > 50 else text
            log.info("predict | action=%s prob=%.3f | %r",
                     result["action"], result["probability"], short)
            self._send_json(200, result)
        except Exception as e:
            log.exception("Prediction error")
            self._send_json(500, {"error": "Internal error", "detail": str(e)})


# --------------------------------------------------------------------
# Main
# --------------------------------------------------------------------
def main():
    server = HTTPServer((HOST, PORT), SyncHabitNLPHandler)
    log.info("🚀 SyncHabit NLP (DistilBERT) server başladı")
    log.info("   http://%s:%d/predict (POST)", HOST, PORT)
    log.info("   http://%s:%d/health  (GET)", HOST, PORT)
    log.info("   Ctrl+C ile durdur")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        log.info("Server durduruluyor...")
        server.server_close()


if __name__ == "__main__":
    main()
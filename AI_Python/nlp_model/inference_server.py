import json
import logging
import pickle
import re
import sys
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path

# --------------------------------------------------------------------
# Configuration
# --------------------------------------------------------------------
HOST = "0.0.0.0"
PORT = 8001

ROOT = Path(__file__).resolve().parent
MODEL_FILE = ROOT / "synchabit_toxic_model.pkl"

# 3-tier thresholds
BLOCK_THRESHOLD = 0.70   # >= 0.70 → otomatik blok
WARN_THRESHOLD = 0.40    # 0.40 - 0.70 → moderasyon
# < 0.40 → allow

# --------------------------------------------------------------------
# Logging
# --------------------------------------------------------------------
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
log = logging.getLogger("synchabit-nlp")


# --------------------------------------------------------------------
# Text Preprocessing (train.py ile aynı olmalı)
# --------------------------------------------------------------------
URL_PATTERN = re.compile(r"https?://\S+|www\.\S+")
NUMBER_PATTERN = re.compile(r"\b\d+\b")
MULTI_SPACE = re.compile(r"\s+")
PUNCT_PATTERN = re.compile(r"[^\wğüşıöçĞÜŞİÖÇ!\s]")


def preprocess(text):
    """train.py'deki preprocess ile birebir aynı (Türkçe-aware lowercase)."""
    if not isinstance(text, str):
        return ""
    text = text.replace("İ", "i").replace("I", "ı").lower()
    text = URL_PATTERN.sub("URL", text)
    text = NUMBER_PATTERN.sub("NUM", text)
    text = PUNCT_PATTERN.sub(" ", text)
    text = MULTI_SPACE.sub(" ", text).strip()
    return text


# --------------------------------------------------------------------
# KEYWORD OVERRIDE LAYER
# --------------------------------------------------------------------
# Bu kombinasyonlar ML'den BAĞIMSIZ olarak BLOCK üretir.
# Her kural: (gerekli_kelimeler_tuple, kategori, açıklama)
# Aynı cümlede TÜM kelimeler geçmeli — bağlam koruması.
#
# NOT: Negation (olumsuzluk) basit kontrolle yakalanır:
#      "kesmeyeceğim", "kesmem", "kesmiyorum" → tetiklenmez

NEGATION_PATTERNS = [
    # 1. şahıs negatif fiil çekimleri
    "kesmeyeceğim", "kesmeyecem", "kesmem", "kesmiyorum",
    "atlamayacağım", "atlamicem", "atlamayacak",
    "öldürmeyeceğim", "öldürmem", "öldürmüyorum",
    "yapmayacağım", "yapmam",
    "asmayacağım", "asmam",
    "vermeyeceğim", "vermem",  # "zarar vermeyeceğim", "son vermeyeceğim"
    "etmeyeceğim", "etmem",    # "intihar etmem"
    "almayacağım",             # "hap almayacağım"
    "içmeyeceğim",             # "hap içmeyeceğim"
    "yaralamayacağım", "yaralamam",
    "kıymayacağım", "kıymam",
    # 2. şahıs EMİR KİPİ negatif çekimleri (-me/-ma ekleri)
    "kesme ", " kesme",        # "bileğini kesme"
    "öldürme ", " öldürme",    # "kendini öldürme"
    "atlama ", " atlama",      # "yüksekten atlama"
    "verme ", " verme",        # "kendine zarar verme"
    "etme ", " etme",          # "intihar etme"
    "yapma ", " yapma",
    "asma ", " asma",
    "alma ", " alma",
    "içme ", " içme",
    "yaralama ", " yaralama",
    "döveme ", " dövme",
    "boğma ", " boğma",
    # Recovery / past-tense indicators
    "bıraktım", "atlattım", "yendim", "yenmek istiyorum",
    "geçmişte", "eskiden", "iyileşmeye",
    # General negation words
    "asla ", " asla", "hiç bir", "hiçbir zaman",
]

# Belirli BLOCK keyword'leri için ek context guard:
# Eğer cümlede recovery/positive frame varsa, keyword override'ı atla
POSITIVE_FRAME_INDICATORS = [
    "bıraktım", "atlattım", "yendim", "yenmek istiyorum",
    "geçmişte", "eskiden", "iyileşmeye karar verdim",
    "hayatı seviyorum", "yaşama tutunac", "umut",
    "terapide", "iyileşiyorum", "iyiyim artık",
]

HARD_BLOCK_RULES = [
    # ===== Self-harm / Suicidal (1. şahıs) =====
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

    # ===== Self-harm / Suicidal (2. şahıs EMİR) =====
    (("bileğini", "kes"), "self_harm", "Emir: bilek kesme"),
    (("bileklerini", "kes"), "self_harm", "Emir: bilek kesme"),
    (("kolunu", "kes"), "self_harm", "Emir: kol kesme"),
    (("kollarını", "kes"), "self_harm", "Emir: kol kesme"),
    (("kendini", "öldür"), "self_harm", "Emir: intihar"),
    (("kendine", "kıy"), "self_harm", "Emir: intihar"),
    (("intihar", "et"), "self_harm", "Emir: intihar"),  # "intihar et" çok kısa - bağlam guard ile birlikte
    (("hayatına", "son ver"), "self_harm", "Emir: intihar"),
    (("kendini", "as"), "self_harm", "Emir: asma"),
    (("kendine", "zarar"), "self_harm", "Emir: kendine zarar"),
    (("kendine", "acı"), "self_harm", "Emir: kendine acı"),
    (("yüksekten", "at"), "self_harm", "Emir: yüksekten atlama"),
    (("pencereden", "at"), "self_harm", "Emir: pencereden atlama"),
    (("köprüden", "atla"), "self_harm", "Emir: köprüden atlama"),
    (("çatıdan", "atla"), "self_harm", "Emir: çatıdan atlama"),

    # ===== Risky Dare / Mavi Balina =====
    (("mavi balina",), "blue_whale", "Mavi balina oyunu"),
    (("balina oyunu",), "blue_whale", "Mavi balina referansı"),
    (("son görev", "atmak"), "blue_whale", "Mavi balina son görev pattern"),
    (("son görev", "atlamak"), "blue_whale", "Mavi balina son görev pattern"),

    # ===== Violence to others (1. şahıs) =====
    (("birini", "öldür"), "violence", "Başkasını öldürme niyeti"),
    (("birini", "bıçakla"), "violence", "Bıçaklama niyeti"),
    (("silahla", "okul"), "violence", "Okula silahlı saldırı"),
    (("silahla", "gid"), "violence", "Silahlı saldırı niyeti"),
    (("bombayla",), "violence", "Bombalı saldırı niyeti"),
    (("zehir", "ver"), "violence", "Zehirleme niyeti"),
    (("asit", "at"), "violence", "Asit saldırısı niyeti"),

    # ===== Violence to others (2. şahıs EMİR) =====
    (("birini", "döv"), "violence", "Emir: birini dövme"),
    (("birini", "yarala"), "violence", "Emir: birini yaralama"),
    (("birini", "boğ"), "violence", "Emir: birini boğma"),
    (("kediyi", "tekmele"), "violence", "Emir: hayvan istismarı"),
    (("köpeği", "tekmele"), "violence", "Emir: hayvan istismarı"),
    (("hayvana", "zarar"), "violence", "Emir: hayvan istismarı"),

    # ===== Vandalism (yeni — "çiz" homonym sorunu için) =====
    # NOT: "Ahmet'in arabasını çiz" tek başına ambigü (resim/kazıma).
    # Net vandalism işaretleri: anahtarla/taşla + çiz/kır kombinasyonları
    (("anahtarla", "çiz"), "vandalism", "Anahtarla çizme - vandalizm"),
    (("anahtarla", "araba"), "vandalism", "Anahtarla araba kazıma"),
    (("camını", "kır"), "vandalism", "Cam kırma vandalizmi"),
    (("lastiğini", "patlat"), "vandalism", "Lastik patlatma"),
    (("birinin", "yak"), "vandalism", "Eşya yakma vandalizmi"),
]


def tr_lower(text):
    """Türkçe-aware lowercase. Python'un standart lower()'ı İ→i̇ (combining diacritic)
    yapıyor, bu da substring match'i bozuyor. Manuel mapping kullanıyoruz.
    """
    # Türkçe karakter çiftleri
    return (text
            .replace("İ", "i")
            .replace("I", "ı")
            .lower())


def has_negation(text_lower):
    """Cümlede olumsuzluk veya pozitif iyileşme çerçevesi var mı?"""
    # 1. Direkt negation
    if any(neg in text_lower for neg in NEGATION_PATTERNS):
        return True
    # 2. Recovery / positive frame indicators
    if any(ind in text_lower for ind in POSITIVE_FRAME_INDICATORS):
        return True
    return False


def keyword_override(text):
    """Hard-block keyword kontrolü.
    
    Returns:
        (matched: bool, category: str|None, keywords: list, reason: str|None)
    """
    text_lower = tr_lower(text)

    # Negation varsa keyword override'ı atla (model karar versin)
    if has_negation(text_lower):
        return False, None, [], None

    for required_words, category, reason in HARD_BLOCK_RULES:
        if all(word in text_lower for word in required_words):
            return True, category, list(required_words), reason

    return False, None, [], None


# --------------------------------------------------------------------
# Model Loading
# --------------------------------------------------------------------
log.info("Model yükleniyor: %s", MODEL_FILE)
if not MODEL_FILE.exists():
    log.error("❌ Model dosyası bulunamadı! Önce 'python train.py' çalıştır.")
    sys.exit(1)

with open(MODEL_FILE, "rb") as f:
    bundle = pickle.load(f)

MODEL = bundle["model"]
VECTORIZER = bundle["vectorizer"]
MODEL_NAME = bundle.get("model_name", "unknown")
METADATA = bundle.get("metadata", {})

log.info("✅ Model yüklendi: %s", MODEL_NAME)
log.info("   Vocabulary: %d kelime", METADATA.get("vocabulary_size", "?"))
log.info("   Test recall: %.4f, precision: %.4f", 
         METADATA.get("test_recall", 0), METADATA.get("test_precision", 0))
log.info("   3-tier thresholds: BLOCK≥%.2f, WARN≥%.2f, ALLOW<%.2f",
         BLOCK_THRESHOLD, WARN_THRESHOLD, WARN_THRESHOLD)


# --------------------------------------------------------------------
# Prediction Pipeline
# --------------------------------------------------------------------
def predict(text):
    """3-tier prediction pipeline.
    
    Returns:
        dict with action, probability, category, matched_keywords, reason, is_safe
    """
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

    # Layer 2: ML model
    clean = preprocess(text)
    if not clean:
        return {
            "action": "allow",
            "probability": 0.0,
            "category": None,
            "matched_keywords": [],
            "reason": "empty_after_preprocess",
            "is_safe": True,
        }

    vec = VECTORIZER.transform([clean])
    prob = float(MODEL.predict_proba(vec)[0, 1])

    # Layer 3: 3-tier decision
    if prob >= BLOCK_THRESHOLD:
        action, reason = "block", "ml_high_confidence"
        is_safe = False
    elif prob >= WARN_THRESHOLD:
        action, reason = "warn", "ml_uncertain"
        is_safe = False  # warn = "şüpheli", false safe yorumla
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
    """HTTP handler — POST /predict, GET /health."""

    # Default log_message çok gürültülü, sessize alalım (kendi logger kullanıyoruz)
    def log_message(self, format, *args):
        return  # suppressed

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
                "model": MODEL_NAME,
                "thresholds": {
                    "block": BLOCK_THRESHOLD,
                    "warn": WARN_THRESHOLD,
                },
                "metadata": METADATA,
            })
        else:
            self._send_json(404, {"error": "Not found"})

    def do_POST(self):
        if self.path != "/predict":
            self._send_json(404, {"error": "Not found"})
            return

        # Read body
        try:
            content_length = int(self.headers.get("Content-Length", 0))
        except (TypeError, ValueError):
            self._send_json(400, {"error": "Invalid Content-Length"})
            return

        if content_length == 0:
            self._send_json(400, {"error": "Empty body"})
            return

        if content_length > 10_000:  # 10KB sınır (görev metni için fazlasıyla yeter)
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
            # Log decision (tez raporu için faydalı)
            short_text = text[:50] + "…" if len(text) > 50 else text
            log.info("predict | action=%s prob=%.3f | %r",
                     result["action"], result["probability"], short_text)
            self._send_json(200, result)
        except Exception as e:
            log.exception("Prediction error")
            self._send_json(500, {"error": "Internal error", "detail": str(e)})


# --------------------------------------------------------------------
# Run Server
# --------------------------------------------------------------------
def main():
    server = HTTPServer((HOST, PORT), SyncHabitNLPHandler)
    log.info("🚀 SyncHabit NLP server başladı")
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

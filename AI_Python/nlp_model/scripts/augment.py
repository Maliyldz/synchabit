"""
SyncHabit NLP - Data Augmentation Script
========================================
Seed dataset'i (~526 satır) çoğaltarak ~6000 satırlık eğitim seti üretir.

Stratejiler:
1. Future tense variants  (keseceğim -> kesicem, kesecem, ...)
2. Time modifiers         (bu gece, yarın, şimdi ekleme)
3. Subject prefixes       (ben, bugün ben, kararlıyım)
4. Synonym swaps          (LABEL-PRESERVING; kategori-aware)
5. Case variations        (lower / capitalize / mixed)
6. Punctuation noise      (!, ..., son nokta ekle/çıkar)
7. Light typo injection   (Türkçe diakritik düşürme)
8. Filler word injection  (yani, artık, sanırım)

Output: data/processed/augmented_dataset.csv  (+ train/val/test splits)

Notlar:
- Reproducibility için random seed sabit.
- Synonym swap unsafe kategorilerde dikkatli (label-preserving).
- Duplicate'ler sonda elenir.
"""

import csv
import random
import re
from pathlib import Path
from collections import Counter

# --------------------------------------------------------------------
# Reproducibility
# --------------------------------------------------------------------
RANDOM_SEED = 42
random.seed(RANDOM_SEED)

# --------------------------------------------------------------------
# Paths (taşınabilir: script ai/nlp_model/scripts/ içindeyse parent.parent → ai/nlp_model/)
# --------------------------------------------------------------------
ROOT = Path(__file__).resolve().parent.parent
SEED_FILE = ROOT / "data" / "synthetic" / "seed_dataset.csv"
OUT_FILE = ROOT / "data" / "processed" / "augmented_dataset.csv"
TRAIN_FILE = ROOT / "data" / "processed" / "train.csv"
VAL_FILE = ROOT / "data" / "processed" / "val.csv"
TEST_FILE = ROOT / "data" / "processed" / "test.csv"

# --------------------------------------------------------------------
# 1) FUTURE TENSE VARIANTS
# --------------------------------------------------------------------
# "-eceğim/-acağım" -> "-icem/-icam", "-ecem/-acam", "-iyor olacağım", ...
# Sadece basit son ek değişimleri. Çok agresif yapmıyoruz ki anlam bozulmasın.

FUTURE_PATTERNS = [
    # (regex_pattern, replacements)
    # NOT: 1. tekil şahıs ekini koruyoruz (-ım/-im). "yapacağım" -> "yapacak"
    # gibi dönüşümler yapmıyoruz, çünkü kişi sapması anlamı bozuyor.
    (r"(\w+)eceğim\b", [r"\1ecem", r"\1icem"]),
    (r"(\w+)acağım\b", [r"\1acam", r"\1ıcam"]),
    (r"(\w+)eceğiz\b", [r"\1ecez", r"\1icez"]),
    (r"(\w+)acağız\b", [r"\1acaz", r"\1ıcaz"]),
]

def future_tense_variant(text):
    """Rastgele bir future tense varyantı uygula. Bulamazsa text'i aynen döndür."""
    candidates = []
    for pattern, replacements in FUTURE_PATTERNS:
        if re.search(pattern, text):
            for rep in replacements:
                candidates.append(re.sub(pattern, rep, text, count=1))
    if not candidates:
        return text
    return random.choice(candidates)


# --------------------------------------------------------------------
# 2) TIME MODIFIERS  (başa veya sona ekleme)
# --------------------------------------------------------------------
TIME_PREFIXES = [
    "bu gece", "bu akşam", "yarın", "şimdi", "az sonra",
    "yakında", "bugün", "yarın sabah", "akşam olunca",
    "gece olunca", "saatler içinde", "bu hafta",
]
TIME_SUFFIXES = [
    "bu gece", "yarın", "akşama", "sabaha", "az sonra",
    "bugün içinde", "bu hafta", "yakında",
]

def add_time_modifier(text):
    """%50 ihtimalle başa, %50 sona time modifier ekle."""
    if random.random() < 0.5:
        return f"{random.choice(TIME_PREFIXES)} {text.lower()[0] + text[1:] if text else text}"
    else:
        return f"{text} {random.choice(TIME_SUFFIXES)}"


# --------------------------------------------------------------------
# 3) SUBJECT PREFIXES
# --------------------------------------------------------------------
SUBJECT_PREFIXES = [
    "ben", "bugün ben", "kararımı verdim", "artık",
    "sanırım", "bence", "ben de", "ya", "evet",
    "karar verdim", "kesin olarak",
]

def add_subject_prefix(text):
    prefix = random.choice(SUBJECT_PREFIXES)
    # ilk harfi küçült (cümle akışı)
    if text and text[0].isupper():
        text = text[0].lower() + text[1:]
    return f"{prefix} {text}"


# --------------------------------------------------------------------
# 4) SYNONYM SWAPS  (LABEL-PRESERVING)
# --------------------------------------------------------------------
# DİKKAT: Sadece etiketi DEĞİŞTİRMEYECEK eş anlamlılar.
# "aç kalacağım" -> "tok kalacağım" YAPMIYORUZ.
# "koşacağım" -> "yürüyeceğim" SAFE -> SAFE, OK.
# "keseceğim" (self-harm context) -> "yaralayacağım" UNSAFE -> UNSAFE, OK.

SYNONYMS = {
    # safe synonyms - intensity korunur, doğal eş anlamlılar
    "koşacağım":     ["tempo yapacağım"],
    "yürüyüş":       ["gezinti"],
    "okuyacağım":    ["inceleyeceğim"],
    "alacağım":      ["edineceğim"],
    "gideceğim":     ["uğrayacağım"],
    "izleyeceğim":   ["seyredeceğim"],
    # NOT: "yapacağım" -> "gerçekleştireceğim" KALDIRILDI, çünkü
    # "yoga gerçekleştireceğim", "yüz maskesi gerçekleştireceğim" gibi
    # absürt cümleler üretiyordu.

    # unsafe self-harm synonyms - severity korunur ya da ARTAR
    "keseceğim":     ["yaralayacağım", "doğrayacağım", "biçeceğim"],
    "kesicem":       ["yaralayıcam", "doğrayıcam"],
    "yaralayacağım": ["keseceğim", "yırtacağım"],
    "döveceğim":     ["yumruklayacağım", "tartaklayacağım"],
    "vuracağım":     ["yumruklayacağım", "tokatlayacağım"],
    "yakacağım":     ["yandıracağım", "ateşe vereceğim"],
    "öldüreceğim":   ["yok edeceğim", "icabına bakacağım", "öldürtüceğim"],
    "atlayacağım":   ["zıplayacağım", "kendimi bırakacağım"],

    # eating/sleep severity korunur
    "uyumayacağım":  ["gözümü kırpmayacağım", "uyanık kalacağım"],
    "yemeyeceğim":   ["aç kalacağım", "öğün atlayacağım"],
}

def synonym_swap(text):
    """Cümlede bir kelime için synonym swap dene."""
    words = text.split()
    candidates = []
    for i, w in enumerate(words):
        # Lowercase normalize for lookup
        key = w.lower().strip(".,!?")
        if key in SYNONYMS:
            for syn in SYNONYMS[key]:
                new_words = words.copy()
                new_words[i] = syn
                candidates.append(" ".join(new_words))
    if not candidates:
        return text
    return random.choice(candidates)


# --------------------------------------------------------------------
# 5) CASE VARIATIONS
# --------------------------------------------------------------------
def case_variant(text):
    choice = random.choice(["lower", "capitalize", "title", "as_is"])
    if choice == "lower":
        return text.lower()
    elif choice == "capitalize":
        return text.capitalize()
    elif choice == "title":
        # Sadece bazı kelimeleri büyük yapsın, agresif değil
        words = text.split()
        if len(words) > 2:
            idx = random.randint(0, len(words)-1)
            words[idx] = words[idx].capitalize()
        return " ".join(words)
    return text


# --------------------------------------------------------------------
# 6) PUNCTUATION VARIATION
# --------------------------------------------------------------------
def punctuation_variant(text):
    text = text.rstrip(".!? ")
    suffix = random.choice(["", ".", "..", "...", "!", ".!"])
    return text + suffix


# --------------------------------------------------------------------
# 7) LIGHT TYPO INJECTION  (Türkçe yaygın hatalar)
# --------------------------------------------------------------------
TYPO_RULES = [
    # (find, replace) - en yaygın gerçek kullanıcı yazım pratikleri
    ("ğ", "g"),  # yapacağım -> yapacagım
    ("ı", "i"),  # alıcam -> alicam (bazı kullanıcılar)
    ("ş", "s"),  # koşacağım -> kosacagım
    ("ç", "c"),
    ("ü", "u"),
    ("ö", "o"),
]

def inject_typo(text):
    """%30 ihtimalle 1-2 diakritik düşür."""
    if random.random() > 0.3:
        return text
    rule = random.choice(TYPO_RULES)
    # Sadece 1-2 yer değiştir, hepsini değil
    indexes = [i for i, ch in enumerate(text) if ch == rule[0]]
    if not indexes:
        return text
    n_swap = min(random.randint(1, 2), len(indexes))
    chosen = random.sample(indexes, n_swap)
    chars = list(text)
    for i in chosen:
        chars[i] = rule[1]
    return "".join(chars)


# --------------------------------------------------------------------
# 8) FILLER WORDS
# --------------------------------------------------------------------
FILLERS = ["yani", "artık", "sanırım", "galiba", "kesin", "valla", "aslında"]

def add_filler(text):
    pos = random.choice(["start", "end"])
    filler = random.choice(FILLERS)
    if pos == "start":
        return f"{filler} {text.lower()[0] + text[1:] if text else text}"
    return f"{text} {filler}"


# --------------------------------------------------------------------
# AUGMENTATION PIPELINE
# --------------------------------------------------------------------
# Her seed örnekten ~11-12 varyant üretiyoruz.
# Pipeline: aynı seed'e farklı kombinasyonlarda transformasyonlar uygula.

AUGMENTERS = [
    ("future_tense", future_tense_variant),
    ("time_modifier", add_time_modifier),
    ("subject_prefix", add_subject_prefix),
    ("synonym_swap", synonym_swap),
    ("case_variant", case_variant),
    ("punctuation", punctuation_variant),
    ("typo", inject_typo),
    ("filler", add_filler),
]

def augment_one(text, label, subcategory, n_variants=11):
    """Bir seed'den n_variants kadar varyant üret."""
    out = [(text, label, subcategory, "original")]  # orijinali de tut
    seen = {text.lower().strip()}
    attempts = 0
    while len(out) < n_variants + 1 and attempts < n_variants * 4:
        attempts += 1
        # 1-3 transformasyon kombinasyonu uygula
        n_ops = random.randint(1, 3)
        ops = random.sample(AUGMENTERS, n_ops)
        new_text = text
        applied = []
        for op_name, op_fn in ops:
            new_text = op_fn(new_text)
            applied.append(op_name)
        # Whitespace normalize
        new_text = re.sub(r"\s+", " ", new_text).strip()
        if not new_text:
            continue
        norm = new_text.lower().strip()
        if norm in seen:
            continue
        seen.add(norm)
        out.append((new_text, label, subcategory, "+".join(applied)))
    return out


# --------------------------------------------------------------------
# LOAD SEED
# --------------------------------------------------------------------
seeds = []
with open(SEED_FILE, "r", encoding="utf-8") as f:
    reader = csv.DictReader(f)
    for row in reader:
        seeds.append((row["text"], int(row["label"]), row["subcategory"]))

print(f"Loaded {len(seeds)} seed examples")

# --------------------------------------------------------------------
# RUN AUGMENTATION
# --------------------------------------------------------------------
N_VARIANTS_PER_SEED = 11  # Hedef: 526 * 12 = 6312
augmented = []
for text, label, subcategory in seeds:
    variants = augment_one(text, label, subcategory, n_variants=N_VARIANTS_PER_SEED)
    augmented.extend(variants)

print(f"Augmented total: {len(augmented)}")

# --------------------------------------------------------------------
# DEDUPLICATE (text bazlı, case-insensitive)
# --------------------------------------------------------------------
seen_texts = set()
deduped = []
for text, label, sub, method in augmented:
    norm = text.lower().strip()
    if norm in seen_texts:
        continue
    seen_texts.add(norm)
    deduped.append((text, label, sub, method))

print(f"After dedup: {len(deduped)}")

# --------------------------------------------------------------------
# WRITE FULL AUGMENTED DATASET
# --------------------------------------------------------------------
OUT_FILE.parent.mkdir(parents=True, exist_ok=True)
with open(OUT_FILE, "w", encoding="utf-8", newline="") as f:
    w = csv.writer(f)
    w.writerow(["text", "label", "subcategory", "method"])
    for row in deduped:
        w.writerow(row)
print(f"\nFull augmented written to: {OUT_FILE}")

# --------------------------------------------------------------------
# STRATIFIED TRAIN/VAL/TEST SPLIT (70/15/15)
# --------------------------------------------------------------------
# Stratify by label so balance is preserved in each split.
random.shuffle(deduped)
by_label = {0: [], 1: []}
for row in deduped:
    by_label[row[1]].append(row)

train, val, test = [], [], []
for lbl, rows in by_label.items():
    n = len(rows)
    n_train = int(n * 0.70)
    n_val = int(n * 0.15)
    train.extend(rows[:n_train])
    val.extend(rows[n_train:n_train + n_val])
    test.extend(rows[n_train + n_val:])

random.shuffle(train)
random.shuffle(val)
random.shuffle(test)

def write_split(path, rows):
    with open(path, "w", encoding="utf-8", newline="") as f:
        w = csv.writer(f)
        w.writerow(["text", "label", "subcategory", "method"])
        for r in rows:
            w.writerow(r)

write_split(TRAIN_FILE, train)
write_split(VAL_FILE, val)
write_split(TEST_FILE, test)

# --------------------------------------------------------------------
# REPORT
# --------------------------------------------------------------------
def report(name, rows):
    labels = Counter(r[1] for r in rows)
    print(f"  {name:6s} total={len(rows):5d}  safe={labels[0]:5d}  unsafe={labels[1]:5d}  "
          f"(safe={labels[0]/len(rows)*100:.1f}%)")

print(f"\n--- Split Statistics ---")
report("FULL", deduped)
report("train", train)
report("val", val)
report("test", test)

print(f"\n--- Subcategory in FULL ---")
sub_counts = Counter(r[2] for r in deduped)
for sc, c in sorted(sub_counts.items(), key=lambda x: -x[1]):
    print(f"  {sc:25s} {c}")

print(f"\n--- Method Distribution (sample) ---")
methods = Counter(r[3] for r in deduped)
for m, c in sorted(methods.items(), key=lambda x: -x[1])[:10]:
    print(f"  {m:50s} {c}")

print(f"\nFiles written:")
print(f"  {TRAIN_FILE}")
print(f"  {VAL_FILE}")
print(f"  {TEST_FILE}")
print(f"  {OUT_FILE}")
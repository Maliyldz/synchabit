"""
Seed Dataset Zenginleştirme v2 — "İç/Ye/At/Tüket" Spurious Correlation Çözümü
==============================================================================
BERT v2'nin tanı testinde ortaya çıkan en büyük sorun: "iç" fiili.
13 false positive'den 11 tanesi sadece "iç" fiilinden geliyor.

Çözüm: Bu fiillerin SAFE bağlamdaki kullanımlarını seed'e eklemek.

Hedeflenenler:
  1. iç (~70 örnek) — su, süt, çay, kahve, ilaç (normal doz), takviye
  2. tüket (~15 örnek) — su, sebze, meyve, vitamin
  3. at (~10 örnek) — top atma, çöp atma, mektup atma
  4. ye (~5 örnek) — ek pozitif yemek örnekleri
  5. ek genel pozitif sağlık görevleri (~10 örnek)

Toplam: ~110 yeni örnek (HEPSİ SAFE = label 0)
"""

import csv
from pathlib import Path


# ============================================================
# "İÇ" — Sağlık ve günlük içecek görevleri (SAFE)
# ============================================================
ic_safe = [
    # Su içme — gün boyunca
    "1 litre su iç bugün",
    "2 litre su iç gün boyunca",
    "Günde en az 8 bardak su iç",
    "Sabahları aç karnına su iç",
    "Yatmadan önce bir bardak su iç",
    "Yemekten önce su iç",
    "Yemekten sonra su iç",
    "Antrenmandan sonra bol su iç",
    "Spordan önce su iç",
    "Yarım saatte bir su iç çalışırken",
    "Sıcakta daha çok su iç",
    "Soğuk havada da bol su iç",
    "Limonlu su iç sabah",
    "Maden suyu iç günde bir tane",
    "Şişen suyunu iç bitirmeden uyuma",
    "Su iç ama plastik şişeden değil",
    "Filtre edilmiş su iç",
    "Susadıkça su iç bekleme",
    "Sıcak su iç boğazına iyi gelir",
    "Ilık su iç sabah",
    
    # Süt
    "Bir bardak süt iç günde",
    "Sabah kahvaltısında süt iç",
    "Akşam yatmadan süt iç",
    "Yağsız süt iç diyet için",
    "Soğuk süt iç yaz aylarında",
    "Sıcak süt iç soğuk havada",
    "Bal ve süt iç akşam",
    
    # Çay/Kahve
    "Çayını iç soğumadan",
    "Bir fincan kahve iç sabah",
    "Yeşil çay iç günde 2 kere",
    "Bitki çayı iç akşam",
    "Nane çayı iç mide rahatlatır",
    "Adaçayı iç soğuk algınlığında",
    "Ihlamur iç soğukta",
    "Türk kahvesi iç köpüklü",
    "Filtre kahve iç sabah",
    "Soğuk kahve iç yazın",
    
    # Meyve/Sebze suyu
    "Portakal suyu iç sabah taze sıkılmış",
    "Limonata iç ev yapımı",
    "Karışık meyve suyu iç sabahları",
    "Yeşil smoothie iç antrenmandan önce",
    "Domates suyu iç vitamin için",
    "Havuç suyu iç haftada bir",
    
    # Reçeteli ilaç (doktor tavsiyesi)
    "İlacını zamanında iç",
    "Sabah ilacını iç kahvaltıdan sonra",
    "Akşam ilacını iç uyumadan önce",
    "Doktorun verdiği ilacı iç",
    "Antibiyotiği iç düzenli zamanlarda",
    "Reçeteli ilacını iç günde 2 kez",
    "İlacını iç bardakla suyla",
    
    # Vitamin / Takviye
    "Vitamin D damlasını iç",
    "C vitamini iç soğuk havalarda",
    "B12 takviyesi iç doktor önerdi",
    "Şurup iç öksürük için",
    "Probiyotik içeceği iç akşam",
    "Demir şurubu iç eksiklik var",
    
    # Spor / sağlık
    "Protein içeceği iç antrenmandan sonra",
    "Elektrolit içeceği iç maçtan sonra",
    "Sporcu içeceği iç efor sonrası",
    
    # Genel pozitif
    "Çorbanı iç soğumadan kahvaltıda",
    "Sıcak çorba iç soğuk havada",
    "Komposto iç yaz aylarında",
    "Ayran iç yemek yanında",
    "Yoğurt suyu iç ferahlatır",
    "Limonlu çay iç boğaz ağrısına",
    "Sebze suyu iç günde bir kere",
    "Sıcak kakao iç soğuk akşamlarda",
    "Smoothie iç kahvaltı yerine",
]


# ============================================================
# "TÜKET" — Sağlık (SAFE)
# ============================================================
tuket_safe = [
    "Günde 2 litre su tüket",
    "Günde 3 litre su tüket spor yapıyorsan",
    "Bol bol su tüket yazın",
    "Düzenli su tüket susama beklemeden",
    "Beyaz et tüket haftada 3 kez",
    "Balık tüket haftada 2 kez",
    "Tam tahıllı ekmek tüket",
    "Süt ürünleri tüket günde bir kere",
    "Kuruyemiş tüket bir avuç",
    "Yumurta tüket kahvaltıda",
    "Yeşil yapraklı sebze tüket",
    "Mevsim meyvesi tüket günde 2 tane",
    "Kuru baklagil tüket haftada 2 kez",
    "Zeytinyağı tüket salata üzerinde",
    "Bal tüket günde bir kaşık",
]


# ============================================================
# "AT" — Spor ve günlük (SAFE)
# ============================================================
at_safe = [
    "Top at çocuğa parkta",
    "Topu arkadaşına at",
    "Topu yukarı at ve yakala",
    "Frizbiyi at köpeğin getirsin",
    "Selfie at sosyal medyaya",
    "Fotoğraf at ailene gönder",
    "İmza at belgeye",
    "Mektup at posta kutusuna",
    "Adım at hedefe doğru",
    "Tekme at futbol topuna",
    "Çekiç at çiviyi sapla duvara",
    "Yumurta at pastaya karıştır",
]


# ============================================================
# "YE" — Ek pozitif yemek örnekleri (SAFE)
# ============================================================
ye_safe = [
    "Bir tabak yemek ye öğlen",
    "Sağlıklı atıştırmalık ye akşamüstü",
    "Bademleri ye antrenmadan önce",
    "Tam tahıl ekmek ye kahvaltıda",
    "Sebze tabağı ye akşam",
    "Meyve salatası ye tatlı yerine",
    "Yumurta ye kahvaltıda",
]


# ============================================================
# Genel pozitif sağlık görevleri
# ============================================================
genel_saglik = [
    "Bol bol su iç ve dinlen",
    "Sağlıklı atıştırmalıklar iç ve ye",
    "Vitamin al ve düzenli su iç",
    "Doktorun verdiği şurubu iç",
    "Sıcak içecek iç soğuktan korunmak için",
    "Detoks suyu iç sabahları",
    "Termos hazırla yanına su iç",
    "Çayını iç ve kitap oku",
    "İlacını iç ve dinlenmeye çek",
    "Bol su iç ve egzersiz yap",
]


# ============================================================
# WRITE
# ============================================================
ROOT = Path(__file__).resolve().parent.parent
SEED_FILE = ROOT / "data" / "synthetic" / "seed_dataset.csv"

rows_to_add = []
for text in ic_safe:
    rows_to_add.append((text, 0, "health_drink_ic"))
for text in tuket_safe:
    rows_to_add.append((text, 0, "health_tuket"))
for text in at_safe:
    rows_to_add.append((text, 0, "sport_at_safe"))
for text in ye_safe:
    rows_to_add.append((text, 0, "health_ye_extra"))
for text in genel_saglik:
    rows_to_add.append((text, 0, "general_health"))

# Mevcut satır sayısı
with open(SEED_FILE, "r", encoding="utf-8") as f:
    existing_count = sum(1 for _ in f) - 1

print(f"Mevcut seed: {existing_count} satır")
print(f"Eklenecek: {len(rows_to_add)} satır (HEPSİ SAFE)")
print()
print("Kategori dağılımı:")
print(f"  health_drink_ic   :  {len(ic_safe)} ('iç' fiili - asıl hedef)")
print(f"  health_tuket      :  {len(tuket_safe)} ('tüket' fiili)")
print(f"  sport_at_safe     :  {len(at_safe)} ('at' fiili - safe bağlam)")
print(f"  health_ye_extra   :  {len(ye_safe)} ('ye' fiili - ek)")
print(f"  general_health    :  {len(genel_saglik)} (genel sağlık)")
print()

# Append
with open(SEED_FILE, "a", encoding="utf-8", newline="") as f:
    w = csv.writer(f)
    for row in rows_to_add:
        w.writerow(row)

# Duplicate kontrolü
import pandas as pd
df = pd.read_csv(SEED_FILE)
before = len(df)
df_clean = df.drop_duplicates(subset=['text'], keep='first').reset_index(drop=True)
after = len(df_clean)

if before != after:
    print(f"⚠️  {before - after} duplicate temizlendi")
    df_clean.to_csv(SEED_FILE, index=False, encoding='utf-8')

print(f"✅ Yeni toplam: {len(df_clean)} unique satır")
print(f"   Safe:   {(df_clean['label']==0).sum()}  ({(df_clean['label']==0).mean()*100:.1f}%)")
print(f"   Unsafe: {(df_clean['label']==1).sum()}  ({(df_clean['label']==1).mean()*100:.1f}%)")
print(f"   Dosya: {SEED_FILE}")

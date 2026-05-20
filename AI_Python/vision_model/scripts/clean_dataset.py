import tensorflow as tf
import os
from pathlib import Path

DATASET_DIR = "dataset"

# TF'nin desteklediği uzantılar
VALID_EXTENSIONS = {'.jpg', '.jpeg', '.png', '.gif', '.bmp', '.webp'}


def is_image_readable(filepath: str) -> bool:
    """TF ile görseli açmayı dener, başarısız olursa False döner."""
    try:
        img = tf.io.read_file(filepath)
        tf.io.decode_image(img)
        return True
    except Exception:
        return False


def clean_dataset():
    print(f"'{DATASET_DIR}' temizleniyor...")
    print("   Her dosya TF ile açılmaya çalışılıyor\n")

    total_checked = 0
    total_removed = 0
    removed_files = []

    for category in sorted(os.listdir(DATASET_DIR)):
        cat_path = os.path.join(DATASET_DIR, category)
        if not os.path.isdir(cat_path):
            continue

        cat_removed = 0
        cat_checked = 0

        for fname in os.listdir(cat_path):
            fpath = os.path.join(cat_path, fname)
            if not os.path.isfile(fpath):
                continue

            cat_checked += 1
            total_checked += 1

            ext = Path(fname).suffix.lower()

            # 1. Uzantı kontrolü
            if ext not in VALID_EXTENSIONS:
                os.remove(fpath)
                cat_removed += 1
                removed_files.append((fpath, f"geçersiz uzantı: {ext}"))
                continue

            # 2. TF ile açılabiliyor mu kontrolü
            if not is_image_readable(fpath):
                os.remove(fpath)
                cat_removed += 1
                removed_files.append((fpath, "TF tarafından açılamıyor (bozuk)"))
                continue

            # 3. Boyut kontrolü — 0 byte dosyalar
            if os.path.getsize(fpath) < 1024:  # 1 KB altı
                os.remove(fpath)
                cat_removed += 1
                removed_files.append((fpath, "çok küçük (muhtemelen bozuk)"))
                continue

        status = "✅" if cat_removed == 0 else "🗑️ "
        print(f"  {status} {category:<20} {cat_checked} kontrol edildi, {cat_removed} silindi")
        total_removed += cat_removed

    print(f"\n{'═'*50}")
    print(f" Özet: {total_checked} dosya kontrol edildi, {total_removed} dosya silindi")

    if removed_files:
        print("\n🗑️  Silinen dosyalar:")
        for fpath, reason in removed_files[:20]:
            print(f"   {fpath}")
            print(f"      → sebep: {reason}")
        if len(removed_files) > 20:
            print(f"   ... ve {len(removed_files) - 20} dosya daha")

    print("\n✅ Temizlik tamamlandı!.")


if __name__ == "__main__":
    clean_dataset()
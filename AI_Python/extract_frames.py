import cv2
import os

UCF101_DIR = r"C:\Users\MehmetAli\Downloads\UCF-101"
OUTPUT_DIR = "dataset"

FRAME_INTERVAL = 10           # Kaç karede bir frame alınsın
MAX_FRAMES_PER_VIDEO = 3      # Bir videodan maksimum kaç frame — tüm videolara girmek için düşük tut
MAX_FRAMES_PER_CATEGORY = 500 # Kategori başına toplam maksimum — tavan yüksek, video sayısı belirler

CATEGORIES = {
    "PushUps":         "spor_yapma",
    "PlayingGuitar":   "gitar_calma",
    "WalkingWithDog":  "evcil_hayvan",
    "Typing":          "kod_yazma",
    "Knitting":        "orgu_orme",
    "Archery":         "okculuk",
    "JumpRope":        "ip_atlama",
    "Biking":          "bisiklet",
    "Basketball":      "basketbol",
    "VolleyballSpiking": "voleybol",
}

def check_ucf_folders():
    """UCF101 klasöründeki tüm kategori isimlerini listeler."""
    if not os.path.exists(UCF101_DIR):
        print(f"❌ '{UCF101_DIR}' bulunamadı. UCF101_DIR yolunu kontrol et.")
        return

    folders = sorted([
        f for f in os.listdir(UCF101_DIR)
        if os.path.isdir(os.path.join(UCF101_DIR, f))
    ])

    print(f"\n UCF101'deki tüm kategoriler ({len(folders)} adet):")
    for f in folders:
        print(f"  {f}")

    print(f"\n Kategoriler için kontrol:")
    for ucf_name, our_name in CATEGORIES.items():
        exists = ucf_name in folders
        status = "✅" if exists else "❌ BULUNAMADI"
        print(f"  {status}  {ucf_name:<20} → {our_name}")

    # Benzer isimler öner
    print(f"\n Eksik kategoriler için benzer klasör isimleri:")
    missing = [k for k in CATEGORIES if k not in folders]
    for m in missing:
        similar = [f for f in folders if m.lower()[:4] in f.lower()]
        if similar:
            print(f"  '{m}' yerine olabilir: {similar}")
        else:
            print(f"  '{m}' için benzer klasör bulunamadı")


def extract_frames_from_video(video_path, output_dir, interval, max_per_video, start_count, max_total):
    """Tek videodan sınırlı sayıda frame çıkarır."""
    cap = cv2.VideoCapture(video_path)
    if not cap.isOpened():
        return 0

    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    video_name = os.path.splitext(os.path.basename(video_path))[0]

    # Videoyu eşit aralıklarla böl — her videodan MAX_FRAMES_PER_VIDEO kadar al
    # Böylece videonun başından sonuna eşit dağılmış kareler alınır
    if total_frames <= 0:
        cap.release()
        return 0

    step = max(1, total_frames // max_per_video)
    target_frames = list(range(0, total_frames, step))[:max_per_video]

    saved = 0
    for target_idx in target_frames:
        if start_count + saved >= max_total:
            break

        cap.set(cv2.CAP_PROP_POS_FRAMES, target_idx)
        ret, frame = cap.read()
        if not ret:
            continue

        filename = f"{video_name}_f{target_idx:04d}.jpg"
        out_path = os.path.join(output_dir, filename)
        cv2.imwrite(out_path, frame)
        saved += 1

    cap.release()
    return saved


def process_category(ucf_folder, category_name):
    input_dir = os.path.join(UCF101_DIR, ucf_folder)
    output_dir = os.path.join(OUTPUT_DIR, category_name)

    if not os.path.exists(input_dir):
        print(f"Klasör bulunamadı: {input_dir}")
        return 0

    os.makedirs(output_dir, exist_ok=True)

    videos = sorted([
        f for f in os.listdir(input_dir)
        if f.lower().endswith(('.avi', '.mp4'))
    ])

    if not videos:
        print(f"Video bulunamadı")
        return 0

    print(f" {len(videos)} video — her birinden max {MAX_FRAMES_PER_VIDEO} frame")

    total_saved = 0
    for video_file in videos:
        if total_saved >= MAX_FRAMES_PER_CATEGORY:
            break
        video_path = os.path.join(input_dir, video_file)
        saved = extract_frames_from_video(
            video_path, output_dir,
            FRAME_INTERVAL, MAX_FRAMES_PER_VIDEO,
            total_saved, MAX_FRAMES_PER_CATEGORY
        )
        total_saved += saved

    return total_saved


def print_summary():
    print(f"\n{'═'*50}")
    print("Özet:")
    total = 0
    for category_name in CATEGORIES.values():
        cat_path = os.path.join(OUTPUT_DIR, category_name)
        if os.path.isdir(cat_path):
            count = len([f for f in os.listdir(cat_path) if f.endswith('.jpg')])
            status = "✅" if count >= 100 else "⚠️ "
            print(f"  {status} {category_name:<25} {count:>4} frame")
            total += count
        else:
            print(f"  ❌ {category_name:<25}    0 frame")
    print(f"  {'─'*38}")
    print(f"  {'TOPLAM':<27} {total:>4} frame")


def main():
    if not os.path.exists(UCF101_DIR):
        print(f"❌ '{UCF101_DIR}' bulunamadı!")
        print("   UCF101_DIR değişkenini doğru yola ayarla.")
        return

    print("Frame çıkarma başlıyor...")
    print(f"   Video başına max frame : {MAX_FRAMES_PER_VIDEO}")
    print(f"   Kategori başına max    : {MAX_FRAMES_PER_CATEGORY}")

    os.makedirs(OUTPUT_DIR, exist_ok=True)

    for ucf_folder, category_name in CATEGORIES.items():
        print(f"\n{'─'*50}")
        print(f"{ucf_folder} → {category_name}")
        count = process_category(ucf_folder, category_name)
        print(f"{count} frame kaydedildi")

    print_summary()
    print("\n Tamamlandı!")


if __name__ == "__main__":
    import sys
    if len(sys.argv) > 1 and sys.argv[1] == "--check":
        check_ucf_folders()
    else:
        main()
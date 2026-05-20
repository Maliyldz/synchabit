import urllib.request
import json
import sys
import os
from pathlib import Path

API_URL = "http://localhost:8000/predict"
HEALTH_URL = "http://localhost:8000/health"


def check_server():
    """Sunucu ayakta mı kontrol et."""
    try:
        with urllib.request.urlopen(HEALTH_URL, timeout=3) as response:
            data = json.loads(response.read().decode("utf-8"))
            print(f"Sunucu çalışıyor — {len(data['categories'])} kategori yüklü\n")
            return True
    except Exception as e:
        print(f"Sunucuya bağlanılamadı: {e}")
        print("   server.py çalışıyor mu kontrol et")
        return False


def predict_single(image_path):
    """Tek görsel test et."""
    if not os.path.exists(image_path):
        print(f"❌ Dosya bulunamadı: {image_path}")
        return None

    with open(image_path, "rb") as f:
        image_bytes = f.read()

    req = urllib.request.Request(API_URL, data=image_bytes, method="POST")
    req.add_header("Content-Type", "application/octet-stream")
    req.add_header("Content-Length", str(len(image_bytes)))

    try:
        with urllib.request.urlopen(req, timeout=30) as response:
            return json.loads(response.read().decode("utf-8"))
    except Exception as e:
        print(f"❌ Hata: {e}")
        return None


def print_result(image_path, result):
    """Sonucu okunabilir formatla yazdır."""
    name = os.path.basename(image_path)
    if result is None or not result.get("is_success"):
        print(f"❌ {name} — hata")
        return

    confident = result["is_confident"]
    mark = "✅" if confident else "⚠️ "
    conf = result["confidence"]
    cat = result["predicted_class"]

    print(f"{mark} {name}")
    print(f"   Tahmin    : {cat} ({conf}%)")
    print(f"   Güvenli mi: {'Evet' if confident else 'HAYIR — eşik altı'}")

    # Top-3
    top3 = result.get("top_3", [])
    if top3:
        top3_str = ", ".join([f"{t['category']}={t['confidence']}%" for t in top3])
        print(f"   Top-3     : {top3_str}")
    print()


def test_folder(folder_path):
    """Klasördeki tüm görselleri test et."""
    extensions = (".jpg", ".jpeg", ".png", ".bmp", ".webp")

    # Alt klasör varsa onları da tara
    images = []
    for root, _, files in os.walk(folder_path):
        for f in files:
            if f.lower().endswith(extensions):
                images.append(os.path.join(root, f))

    if not images:
        print(f"❌ '{folder_path}' içinde görsel bulunamadı")
        return

    print(f"{len(images)} görsel test ediliyor...\n")

    confident_count = 0
    for img_path in sorted(images):
        result = predict_single(img_path)
        print_result(img_path, result)
        if result and result.get("is_confident"):
            confident_count += 1

    print(f"{'═'*50}")
    print(f"📊 Toplam: {len(images)}, Güvenli tahmin: {confident_count}")


def main():
    if not check_server():
        return

    # Argüman: dosya veya klasör
    target = sys.argv[1] if len(sys.argv) > 1 else "test_foto.jpg"

    if os.path.isdir(target):
        test_folder(target)
    elif os.path.isfile(target):
        result = predict_single(target)
        print_result(target, result)
    else:
        print(f"Bulunamadı: {target}")
        print("Kullanım: python test_client.py [dosya_veya_klasör]")


if __name__ == "__main__":
    main()
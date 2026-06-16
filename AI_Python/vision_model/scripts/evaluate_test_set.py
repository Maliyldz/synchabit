import tensorflow as tf
import matplotlib.pyplot as plt
import numpy as np
import json
import os
from pathlib import Path
from sklearn.metrics import confusion_matrix, classification_report, ConfusionMatrixDisplay

MODEL_PATH        = "synchabit_model_v8.keras"
CLASS_NAMES_PATH  = "class_names.json"
TEST_DIR          = "test_images"
IMG_SIZE          = (224, 224)
CONFIDENCE_THRESHOLD = 0.70


def load_model_and_classes():
    if not os.path.exists(MODEL_PATH):
        print(f"❌ Model bulunamadı: {MODEL_PATH}")
        exit(1)

    print(f"📥 Model yükleniyor: {MODEL_PATH}")
    model = tf.keras.models.load_model(MODEL_PATH)

    with open(CLASS_NAMES_PATH, "r", encoding="utf-8") as f:
        class_names = json.load(f)

    print(f"{len(class_names)} kategori: {class_names}\n")
    return model, class_names


def predict_image(model, class_names, image_path):
    """Tek görseli tahmin et, top-3 sonucu döndür."""
    try:
        img = tf.keras.utils.load_img(image_path, target_size=IMG_SIZE)
    except Exception as e:
        return None, None, None

    img_array = tf.keras.utils.img_to_array(img)
    img_array = np.expand_dims(img_array, axis=0)
    predictions = model.predict(img_array, verbose=0)[0]

    predicted_idx = int(np.argmax(predictions))
    predicted_name = class_names[predicted_idx]
    confidence = float(predictions[predicted_idx])

    top_3_idx = np.argsort(predictions)[-3:][::-1]
    top_3 = [(class_names[i], float(predictions[i]) * 100) for i in top_3_idx]

    return predicted_idx, predicted_name, confidence, top_3


def evaluate_test_set(model, class_names):
    """Tüm test setini değerlendir."""
    if not os.path.exists(TEST_DIR):
        print(f"❌ Test klasörü bulunamadı: {TEST_DIR}")
        return

    all_true_labels = []
    all_pred_labels = []
    all_results = []  # (kategori, dosya, doğru/yanlış, güven, top3)

    # Test klasöründeki her alt klasörü dolaş
    for category in sorted(os.listdir(TEST_DIR)):
        cat_path = os.path.join(TEST_DIR, category)
        if not os.path.isdir(cat_path):
            continue

        if category not in class_names:
            print(f"⚠️  '{category}' modelde tanımlı değil, atlanıyor")
            continue

        true_idx = class_names.index(category)
        print(f"\n📂 {category}")
        print("─" * 50)

        # Tüm görselleri test et
        extensions = ('.jpg', '.jpeg', '.png', '.bmp', '.webp')
        images = sorted([
            f for f in Path(cat_path).iterdir()
            if f.suffix.lower() in extensions
        ])

        if not images:
            print(f"   ⚠️  Görsel yok")
            continue

        for img_path in images:
            result = predict_image(model, class_names, str(img_path))
            if result[0] is None:
                print(f"   ❌ Okunamadı: {img_path.name}")
                continue

            pred_idx, pred_name, confidence, top_3 = result

            is_correct = (pred_idx == true_idx)
            confidence_pct = confidence * 100

            all_true_labels.append(true_idx)
            all_pred_labels.append(pred_idx)
            all_results.append({
                'category': category,
                'file': img_path.name,
                'correct': is_correct,
                'predicted': pred_name,
                'confidence': confidence_pct,
                'top3': top_3
            })

            # Konsola sonucu yazdır
            mark = "✅" if is_correct else "❌"
            low_conf = " ⚠️ DÜŞÜK GÜVEN" if confidence < CONFIDENCE_THRESHOLD else ""
            print(f"   {mark} {img_path.name}")
            print(f"      Tahmin: {pred_name} ({confidence_pct:.1f}%){low_conf}")
            if not is_correct:
                # Top-3'ü göster
                top3_str = ", ".join([f"{n}={c:.0f}%" for n, c in top_3])
                print(f"      Top-3: {top3_str}")

    return all_true_labels, all_pred_labels, all_results


def print_summary(all_results, class_names):
    """Genel başarı özeti."""
    print(f"\n{'═'*60}")
    print("GENEL ÖZET")
    print(f"{'═'*60}")

    total = len(all_results)
    correct = sum(1 for r in all_results if r['correct'])
    accuracy = correct / total * 100 if total > 0 else 0

    print(f"  Toplam görsel    : {total}")
    print(f"  Doğru tahmin     : {correct}")
    print(f"  Yanlış tahmin    : {total - correct}")
    print(f"  Genel doğruluk   : {accuracy:.1f}%")

    # Kategori bazlı
    print(f"\n Kategori Bazlı Başarı:")
    by_category = {}
    for r in all_results:
        cat = r['category']
        if cat not in by_category:
            by_category[cat] = {'total': 0, 'correct': 0, 'confidences': []}
        by_category[cat]['total'] += 1
        by_category[cat]['confidences'].append(r['confidence'])
        if r['correct']:
            by_category[cat]['correct'] += 1

    for cat in sorted(by_category.keys()):
        stats = by_category[cat]
        acc = stats['correct'] / stats['total'] * 100
        avg_conf = sum(stats['confidences']) / len(stats['confidences'])
        status = "✅" if acc == 100 else ("⚠️ " if acc >= 50 else "❌")
        print(f"  {status} {cat:<20} {stats['correct']}/{stats['total']} ({acc:.0f}%) - ort. güven: {avg_conf:.0f}%")


def plot_confusion_matrix(all_true_labels, all_pred_labels, class_names):
    """Test seti için confusion matrix çiz."""
    if not all_true_labels:
        return

    cm = confusion_matrix(all_true_labels, all_pred_labels,
                          labels=list(range(len(class_names))))
    disp = ConfusionMatrixDisplay(confusion_matrix=cm, display_labels=class_names)

    fig, ax = plt.subplots(figsize=(12, 10))
    disp.plot(ax=ax, xticks_rotation=45, colorbar=False, cmap='Blues')
    ax.set_title("Test Seti Confusion Matrix", fontsize=14, fontweight='bold')
    plt.tight_layout()
    plt.savefig("test_confusion_matrix_v8.png", dpi=150)
    print(f"\n test_confusion_matrix_v8.png kaydedildi")
    plt.show()

    # Classification report
    print("\n Test Seti Classification Report:")
    report = classification_report(
        all_true_labels, all_pred_labels,
        labels=list(range(len(class_names))),
        target_names=class_names,
        zero_division=0
    )
    print(report)

    with open("test_classification_report_v8.txt", "w", encoding="utf-8") as f:
        f.write(report)
    print(" test_classification_report_v8.txt kaydedildi")


if __name__ == "__main__":
    model, class_names = load_model_and_classes()
    result = evaluate_test_set(model, class_names)

    if result is None or not result[0]:
        print("\n❌ Test edilebilecek görsel bulunamadı")
        exit(1)

    all_true_labels, all_pred_labels, all_results = result
    print_summary(all_results, class_names)
    plot_confusion_matrix(all_true_labels, all_pred_labels, class_names)

    print(f"\n{'═'*60}")
    print("🎉 Test tamamlandı!")
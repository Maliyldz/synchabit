import tensorflow as tf
import matplotlib.pyplot as plt
import numpy as np
import json
import os
import random
from sklearn.metrics import confusion_matrix, classification_report, ConfusionMatrixDisplay
from sklearn.utils.class_weight import compute_class_weight

# RANDOM SEED — tekrarlanabilir sonuçlar için
SEED = 7
random.seed(SEED)
np.random.seed(SEED)
tf.random.set_seed(SEED)

DATASET_DIR = "dataset"
IMG_SIZE    = (224, 224)
BATCH_SIZE  = 32
EPOCHS_TOP  = 15
EPOCHS_FINE = 10
MODEL_PATH  = "synchabit_model_v8.keras"


# 1. VERİ YÜKLEME + CLASS WEIGHTS
def load_data():
    print("Veri seti yükleniyor...")

    train_ds = tf.keras.utils.image_dataset_from_directory(
        DATASET_DIR,
        validation_split=0.2,
        subset="training",
        seed=123,
        image_size=IMG_SIZE,
        batch_size=BATCH_SIZE
    )

    val_ds = tf.keras.utils.image_dataset_from_directory(
        DATASET_DIR,
        validation_split=0.2,
        subset="validation",
        seed=123,
        image_size=IMG_SIZE,
        batch_size=BATCH_SIZE
    )

    class_names = train_ds.class_names

    # Her kategoride kaç görsel var
    print(f"\n Kategori başına görsel sayısı:")
    counts = []
    for category in class_names:
        cat_path = os.path.join(DATASET_DIR, category)
        count = len([
            f for f in os.listdir(cat_path)
            if os.path.isfile(os.path.join(cat_path, f))
        ])
        counts.append(count)
        print(f"  {category:<20} {count:>4} görsel")

    # ── CLASS WEIGHTS hesapla ──
    # Az veri olan kategorilere daha yüksek ağırlık verir
    # Böylece model "az ama önemli" kategorileri ihmal etmez
    print("\n Class weights hesaplanıyor...")
    all_labels = []
    for _, labels in train_ds.unbatch():
        all_labels.append(labels.numpy())

    weights = compute_class_weight(
        class_weight='balanced',
        classes=np.array(range(len(class_names))),
        y=np.array(all_labels)
    )
    class_weights = {i: w for i, w in enumerate(weights)}

    print(" Class weights:")
    for i, name in enumerate(class_names):
        print(f"  {name:<20} {class_weights[i]:.3f}")

    with open("class_names.json", "w", encoding="utf-8") as f:
        json.dump(class_names, f, ensure_ascii=False, indent=2)

    AUTOTUNE = tf.data.AUTOTUNE
    train_ds = train_ds.cache().shuffle(1000).prefetch(buffer_size=AUTOTUNE)
    val_ds   = val_ds.cache().prefetch(buffer_size=AUTOTUNE)

    return train_ds, val_ds, class_names, class_weights

# 2. MODEL
def build_model(num_classes):
    data_augmentation = tf.keras.Sequential([
        tf.keras.layers.RandomFlip("horizontal"),
        tf.keras.layers.RandomRotation(0.25),
        tf.keras.layers.RandomZoom(0.25),
        tf.keras.layers.RandomBrightness(0.25),
        tf.keras.layers.RandomContrast(0.25),
        tf.keras.layers.RandomTranslation(0.1, 0.1),
    ])

    preprocess_input = tf.keras.applications.mobilenet_v2.preprocess_input

    base_model = tf.keras.applications.MobileNetV2(
        input_shape=IMG_SIZE + (3,),
        include_top=False,
        weights='imagenet'
    )
    base_model.trainable = False

    inputs = tf.keras.Input(shape=IMG_SIZE + (3,))
    x = data_augmentation(inputs)
    x = preprocess_input(x)
    x = base_model(x, training=False)
    x = tf.keras.layers.GlobalAveragePooling2D()(x)
    x = tf.keras.layers.Dropout(0.4)(x)
    outputs = tf.keras.layers.Dense(num_classes, activation='softmax')(x)

    return tf.keras.Model(inputs, outputs), base_model


# 3. EĞİTİM
def train(model, base_model, train_ds, val_ds, class_weights):
    early_stop = tf.keras.callbacks.EarlyStopping(
        monitor='val_loss',
        patience=4,
        restore_best_weights=True
    )

    # Aşama 1
    print(f"\n{'─'*50}\n Aşama 1: Transfer Learning")
    model.compile(
        optimizer=tf.keras.optimizers.Adam(learning_rate=0.001),
        loss=tf.keras.losses.SparseCategoricalCrossentropy(),
        metrics=['accuracy']
    )
    history_top = model.fit(
        train_ds,
        epochs=EPOCHS_TOP,
        validation_data=val_ds,
        callbacks=[early_stop],
        class_weight=class_weights
    )

    # Aşama 2 — Fine-tuning
    print(f"\n{'─'*50}\n Aşama 2: Fine-tuning")
    base_model.trainable = True
    for layer in base_model.layers[:-30]:
        layer.trainable = False

    model.compile(
        optimizer=tf.keras.optimizers.Adam(learning_rate=0.0001),
        loss=tf.keras.losses.SparseCategoricalCrossentropy(),
        metrics=['accuracy']
    )
    history_fine = model.fit(
        train_ds,
        epochs=EPOCHS_FINE,
        validation_data=val_ds,
        callbacks=[early_stop],
        class_weight=class_weights 
    )

    return history_top, history_fine


# 4. DEĞERLENDİRME
def evaluate_and_plot(model, val_ds, class_names, history_top, history_fine):
    print(f"\n{'─'*50}\n Model değerlendiriliyor...")

    acc      = history_top.history['accuracy']      + history_fine.history['accuracy']
    val_acc  = history_top.history['val_accuracy']  + history_fine.history['val_accuracy']
    loss     = history_top.history['loss']          + history_fine.history['loss']
    val_loss = history_top.history['val_loss']      + history_fine.history['val_loss']
    fine_start = len(history_top.history['accuracy'])

    fig, axes = plt.subplots(1, 2, figsize=(14, 5))
    fig.suptitle("SyncHabit v8 - Eğitim Sonuçları", fontsize=14, fontweight='bold')
    for ax, m, vm, title in zip(axes, [acc, loss], [val_acc, val_loss], ["Accuracy", "Loss"]):
        ax.plot(m, label='Eğitim')
        ax.plot(vm, label='Doğrulama')
        ax.axvline(fine_start, color='red', linestyle='--', label='Fine-tuning')
        ax.set_title(title)
        ax.set_xlabel("Epoch")
        ax.legend()
        ax.grid(True, alpha=0.3)
    plt.tight_layout()
    plt.savefig("training_history_v8.png", dpi=150)
    plt.show()

    all_labels, all_preds = [], []
    for images, labels in val_ds:
        preds = model.predict(images, verbose=0)
        all_preds.extend(np.argmax(preds, axis=1))
        all_labels.extend(labels.numpy())

    cm = confusion_matrix(all_labels, all_preds)
    disp = ConfusionMatrixDisplay(confusion_matrix=cm, display_labels=class_names)
    fig, ax = plt.subplots(figsize=(12, 10))
    disp.plot(ax=ax, xticks_rotation=45, colorbar=False, cmap='Blues')
    ax.set_title("Confusion Matrix v8", fontsize=14, fontweight='bold')
    plt.tight_layout()
    plt.savefig("confusion_matrix_v8.png", dpi=150)
    plt.show()

    report = classification_report(all_labels, all_preds, target_names=class_names)
    print("\n Classification Report:\n", report)

    with open("classification_report_v8.txt", "w", encoding="utf-8") as f:
        f.write(report)


if __name__ == "__main__":
    train_ds, val_ds, class_names, class_weights = load_data()

    model, base_model = build_model(num_classes=len(class_names))
    history_top, history_fine = train(model, base_model, train_ds, val_ds, class_weights)

    model.save(MODEL_PATH)
    print(f"\n Model kaydedildi: {MODEL_PATH}")

    evaluate_and_plot(model, val_ds, class_names, history_top, history_fine)

    print(f"\n{'═'*50}\n Tamamlandı!")
    print(f"Test için: test_model.py'deki MODEL_PATH'i '{MODEL_PATH}' yap ve çalıştır")
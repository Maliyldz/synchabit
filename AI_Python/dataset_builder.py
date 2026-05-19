import os
import pandas as pd

DATASET_DIR = "dataset"
CATEGORIES = {
    "kitap_okuma": 0, "kod_yazma": 1, "ders_calisma": 2, "spor_yapma": 3,
    "yemek_yapma": 4, "temizlik_yapma": 5, "enstruman_calma": 6, 
    "bitki_bakimi": 7, "evcil_hayvan_bakimi": 8, "resim_cizme": 9
}

def create_structure():
    os.makedirs(DATASET_DIR, exist_ok=True)
    
    data = []
    
    for category, label_id in CATEGORIES.items():
        category_path = os.path.join(DATASET_DIR, category)
        os.makedirs(category_path, exist_ok=True)
        print(f"Klasör oluşturuldu: {category_path}")
        
        data.append({"Dosya_Adi": f"ornek_{category}.jpg", "Kategori": category, "Label_ID": label_id})

    df = pd.DataFrame(data)
    csv_path = os.path.join(DATASET_DIR, "labels.csv")
    df.to_csv(csv_path, index=False)
    print(f"\nBaşarılı! CSV dosyası oluşturuldu: {csv_path}")

if __name__ == "__main__":
    create_structure()
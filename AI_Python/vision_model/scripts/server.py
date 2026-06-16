import json
import io
import os
from http.server import BaseHTTPRequestHandler, HTTPServer
import tensorflow as tf
import numpy as np
from PIL import Image

MODEL_PATH = "./synchabit_model_v8.keras"
CLASS_NAMES_PATH = "class_names.json"
PORT = 8000
CONFIDENCE_THRESHOLD = 70.0

# MODEL YÜKLE
print("Model yükleniyor, lütfen bekleyin...")
model = tf.keras.models.load_model(MODEL_PATH)

with open(CLASS_NAMES_PATH, "r", encoding="utf-8") as f:
    class_names = json.load(f)

print(f"Model hazır. {len(class_names)} kategori: {class_names}\n")


# HTTP HANDLE
class SyncHabitAPIHandler(BaseHTTPRequestHandler):

    def _send_json(self, status, data):
        """JSON yanıt gönderen yardımcı."""
        body = json.dumps(data, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        # CORS — mobilden ve tarayıcıdan erişim için
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "POST, GET, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()
        self.wfile.write(body)

    def do_OPTIONS(self):
        """CORS preflight isteği için."""
        self.send_response(204)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "POST, GET, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()

    def do_GET(self):
        if self.path == "/health":
            self._send_json(200, {
                "status": "ok",
                "model": MODEL_PATH,
                "categories": class_names
            })
        else:
            self._send_json(404, {"error": "Endpoint bulunamadı"})

    def do_POST(self):
        if self.path != "/predict":
            self._send_json(404, {"error": "Endpoint bulunamadı"})
            return

        try:
            content_length = int(self.headers.get("Content-Length", 0))
            if content_length == 0:
                self._send_json(400, {
                    "is_success": False,
                    "error": "Boş istek gönderildi"
                })
                return

            post_data = self.rfile.read(content_length)

            # Görsel işle
            img = Image.open(io.BytesIO(post_data)).convert("RGB")
            img = img.resize((224, 224))
            img_array = tf.keras.utils.img_to_array(img)
            img_array = tf.expand_dims(img_array, 0)

            # Tahmin
            predictions = model.predict(img_array, verbose=0)
            scores = predictions[0]
            max_index = int(np.argmax(scores))

            predicted_class = class_names[max_index]
            confidence = float(scores[max_index]) * 100

            # Top-3 (mobil tarafa ekstra bilgi)
            top_3_idx = np.argsort(scores)[-3:][::-1]
            top_3 = [
                {
                    "category": class_names[i],
                    "confidence": round(float(scores[i]) * 100, 2)
                }
                for i in top_3_idx
            ]

            response = {
                "is_success": True,
                "predicted_class": predicted_class,
                "confidence": round(confidence, 2),
                "is_confident": confidence >= CONFIDENCE_THRESHOLD,
                "top_3": top_3
            }

            self._send_json(200, response)

            mark = "✅" if confidence >= CONFIDENCE_THRESHOLD else "⚠️"
            print(f"  {mark} {predicted_class} ({confidence:.2f}%)")

        except Exception as e:
            print(f"❌ Hata: {e}")
            self._send_json(400, {
                "is_success": False,
                "error": str(e)
            })


# SUNUCUYU BAŞLAT
def run_server(port=PORT):
    server_address = ("", port)
    httpd = HTTPServer(server_address, SyncHabitAPIHandler)

    print(f"{'═'*55}")
    print("SyncHabit Inference Server")
    print(f"{'═'*55}")
    print(f"   Port             : {port}")
    print(f"   Health check     : http://localhost:{port}/health")
    print(f"   Tahmin endpoint  : POST http://localhost:{port}/predict")
    print(f"   Confidence eşiği : %{CONFIDENCE_THRESHOLD}")
    print(f"   Durdurmak için   : CTRL+C")
    print(f"{'═'*55}\n")

    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\n Sunucu durduruluyor...")
        httpd.server_close()


if __name__ == "__main__":
    run_server()
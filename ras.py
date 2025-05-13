import cv2 
import requests
import sounddevice as sd
import scipy.io.wavfile as wav
import numpy as np
import time
import io

FLASK_SERVER = 'http://192.168.137.185:5000'  # ⚠️ Sửa lại IP đúng nếu bạn đang chạy Flask trên máy khác

AUDIO_RATE = 16000
AUDIO_DURATION = 3  # giây

cap = cv2.VideoCapture(0)
if not cap.isOpened():
    print("❌ Không thể mở camera.")
    exit()

customer_id = None
trip_id = None
trip_duration = None

def send_image():
    ret, frame = cap.read()
    if not ret:
        print("❌ Không đọc được ảnh từ camera.")
        return

    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    _, img_encoded = cv2.imencode('.jpg', gray)
    files = {'file': ('image.jpg', img_encoded.tobytes(), 'image/jpeg')}
    data = {'customer_id': customer_id, 'trip_id': trip_id}

    try:
        res = requests.post(f'{FLASK_SERVER}/upload_image', files=files, data=data)
        print(f"[Ảnh] Status: {res.status_code}, Response: {res.text}")
    except Exception as e:
        print("[Ảnh] ❌ Lỗi khi gửi:", e)

def send_audio():
    print("🎙️  Ghi âm...")
    audio = sd.rec(int(AUDIO_DURATION * AUDIO_RATE), samplerate=AUDIO_RATE, channels=1, dtype='int16')
    sd.wait()

    wav_buffer = io.BytesIO()
    wav.write(wav_buffer, AUDIO_RATE, audio)
    wav_buffer.seek(0)

    files = {'file': ('temp.wav', wav_buffer, 'audio/wav')}
    try:
        res = requests.post(f'{FLASK_SERVER}/upload_audio', files=files)
        print(f"[Âm thanh] Status: {res.status_code}, Response: {res.text}")
    except Exception as e:
        print("[Âm thanh] ❌ Lỗi khi gửi:", e)

# Check server availability before polling start signal
def check_server_connection():
    try:
        res = requests.get(f'{FLASK_SERVER}/')
        print(f"🌐 Kết nối Flask server thành công! Status: {res.status_code}")
        return True
    except Exception as e:
        print("❌ Không thể kết nối tới Flask server:", e)
        return False

# Đợi tín hiệu bắt đầu
try:
    if not check_server_connection():
        print("🚫 Không thể tiếp tục do không kết nối được server.")
        exit()

    print("⏳ Đang chờ tín hiệu từ server để bắt đầu...")
    while True:
        try:
            res = requests.get(f'{FLASK_SERVER}/start_signal')
            print(f"[Polling] Status: {res.status_code}, Response: {res.text}")
            if res.ok:
                data = res.json()
                if data.get('start'):
                    customer_id = data.get('customer_id')
                    trip_id = data.get('trip_id')
                    trip_duration = data.get('trip_duration')
                    print(f"✅ Bắt đầu thu thập dữ liệu cho Trip ID {trip_id} (Customer ID: {customer_id}) trong {trip_duration} phút.")
                    break
        except Exception as e:
            print("❌ Lỗi khi lấy tín hiệu bắt đầu:", e)

        time.sleep(2)

    # Start sending data
    start_time = time.time()
    while time.time() - start_time < trip_duration * 60:
        send_image()
        time.sleep(2)  # Gửi mỗi 2 giây

except KeyboardInterrupt:
    print("🛑 Dừng chương trình.")
finally:
    cap.release()

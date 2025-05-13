from picamera2 import Picamera2
import cv2
import requests
import sounddevice as sd
import scipy.io.wavfile as wav
import numpy as np
import time
import io

# Thay đổi địa chỉ IP sau thành địa chỉ của máy chạy Flask server
FLASK_SERVER = 'http://localhost:5000'

# Cấu hình audio
AUDIO_RATE = 16000
AUDIO_DURATION = 3  # giây

# Khởi tạo camera
picam2 = Picamera2()
picam2.configure(picam2.create_preview_configuration(main={"format": 'RGB888', "size": (640, 480)}))
picam2.start()

# Global variables for customer details
customer_id = None
trip_id = None
trip_duration = None

def send_image():
    try:
        frame = picam2.capture_array()
    except Exception as e:
        print("Không đọc được ảnh từ camera:", e)
        return

    gray = cv2.cvtColor(frame, cv2.COLOR_RGB2GRAY)
    _, img_encoded = cv2.imencode('.jpg', gray)
    files = {'file': ('image.jpg', img_encoded.tobytes(), 'image/jpeg')}
    data = {
        'customer_id': customer_id,
        'trip_id': trip_id
    }

    try:
        res = requests.post(f'{FLASK_SERVER}/upload_image', files=files, data=data)
        if res.ok:
            print("[Ảnh] Gửi thành công:", res.json())
        else:
            print("[Ảnh] Lỗi từ server:", res.status_code)
    except Exception as e:
        print("[Ảnh] Lỗi khi gửi:", e)

def send_audio():
    print("🎙️  Ghi âm...")
    audio = sd.rec(int(AUDIO_DURATION * AUDIO_RATE), samplerate=AUDIO_RATE, channels=1, dtype='int16')
    sd.wait()

    # Ghi vào buffer thay vì file tạm
    wav_buffer = io.BytesIO()
    wav.write(wav_buffer, AUDIO_RATE, audio)
    wav_buffer.seek(0)

    files = {'file': ('temp.wav', wav_buffer, 'audio/wav')}
    try:
        res = requests.post(f'{FLASK_SERVER}/upload_audio', files=files)
        if res.ok:
            print("[Âm thanh] Gửi thành công:", res.json())
        else:
            print("[Âm thanh] Lỗi từ server:", res.status_code)
    except Exception as e:
        print("[Âm thanh] Lỗi khi gửi:", e)

# Wait for server signal to start
try:
    print("⏳ Đang chờ tín hiệu từ server để bắt đầu...")
    while True:
        res = requests.get(f'{FLASK_SERVER}/start_signal')
        if res.ok and res.json().get('start'):
            customer_id = res.json().get('customer_id')
            trip_id = res.json().get('trip_id')
            trip_duration = res.json().get('trip_duration')
            print(f"✅ Bắt đầu thu thập dữ liệu cho Trip ID {trip_id} (Customer ID: {customer_id}) trong {trip_duration} phút.")
            break
        time.sleep(2)

    # Start sending data
    start_time = time.time()
    while time.time() - start_time < trip_duration * 60:
        send_image()
        time.sleep(2)  # Gửi mỗi 2 giây

except KeyboardInterrupt:
    print("🛑 Dừng chương trình.")

finally:
    picam2.stop()

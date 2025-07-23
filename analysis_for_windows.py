# analyzer.py
import os
import time
import shutil
import cv2
from ultralytics import YOLO
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler

# --- 경로 설정 ---
input_folder = 'saved_videos'
danger_folder = 'danger_videos'
normal_folder = 'normal_videos'
os.makedirs(danger_folder, exist_ok=True)
os.makedirs(normal_folder, exist_ok=True)

# --- 위험 클래스 설정 ---
DANGER_CLASSES = ['fall','fight','fire','gas','weapons']  # 이 모델 내 클래스

# --- YOLO 모델 로드 ---
model = YOLO('best.pt') #이 모델은 현재 부정확하므로 epoch 늘려서 정확도 올릴 생각

# --- 위험 판단 함수 ---
def is_dangerous(results):
    for result in results:
        for box in result.boxes:
            class_id = int(box.cls[0])
            class_name = model.names[class_id]
            if class_name in DANGER_CLASSES:
                return True
    return False

# --- 영상 분석 및 이동 ---
def analyze_video(video_path):
    cap = cv2.VideoCapture(video_path)
    is_danger = False
    frame_count = 0

    while True:
        ret, frame = cap.read()
        if not ret:
            break
        frame_count += 1
        if frame_count % 5 != 0:
            continue
        results = model(frame)
        if is_dangerous(results):
            is_danger = True
            break

    cap.release()

    dst_folder = danger_folder if is_danger else normal_folder
    dst_path = os.path.join(dst_folder, os.path.basename(video_path))
    shutil.move(video_path, dst_path)
    print(f"[ANALYZE] {'위험 감지됨' if is_danger else '이상 없음'} → {os.path.basename(video_path)}")

# --- 파일 감지 핸들러 ---
class VideoHandler(FileSystemEventHandler):
    def on_created(self, event):
        if not event.is_directory and event.src_path.endswith('.avi'):
            print(f"[EVENT] 새 파일 감지: {event.src_path}")
            time.sleep(20)  # 파일 저장 완료 기다리기 (15초동안 녹화다 보니 여유 시간 5초 가량 둠 -> 15초 + 5초 = 20초)
            analyze_video(event.src_path)

# --- 감시 시작 ---
if __name__ == "__main__":
    print("[ANALYZE] 감시 시작...")

    event_handler = VideoHandler()
    observer = Observer()
    observer.schedule(event_handler, input_folder, recursive=False)
    observer.start()

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        observer.stop()
    observer.join()

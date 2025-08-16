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
thumbnail_folder = 'thumbnails'
os.makedirs(danger_folder, exist_ok=True)
os.makedirs(normal_folder, exist_ok=True)
os.makedirs(thumbnail_folder, exist_ok=True)

# --- 위험 클래스 설정 ---

DANGER_CLASSES = ['fall', 'fight', 'fire', 'gas', 'weapons']

# --- YOLO 모델 로드 ---

model = YOLO('best.pt')

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
    thumbnail_saved = False
    
    # 원본 파일명에서 확장자 제거
    original_filename = os.path.splitext(os.path.basename(video_path))[0]
    print(f"[정보] 영상 분석 시작: {os.path.basename(video_path)}")
    while True:
        ret, frame = cap.read()
        if not ret:
            break
        frame_count += 1
        if frame_count % 10 != 0:
            continue
        results = model(frame)
        if is_dangerous(results):
            is_danger = True        
            if not thumbnail_saved:
                # 원본 파일명(확장자 제외) + .jpg로 썸네일 파일명 생성
                thumbnail_filename = f"{original_filename}.jpg"
                thumbnail_path = os.path.join(thumbnail_folder, thumbnail_filename)              
                cv2.imwrite(thumbnail_path, frame)
                print(f"[알림] 위험 감지! 썸네일이 {thumbnail_path}에 저장되었습니다. 🖼️")              
                thumbnail_saved = True
            break
    cap.release()
    final_folder = danger_folder if is_danger else normal_folder
    final_path = os.path.join(final_folder, os.path.basename(video_path))
    shutil.move(video_path, final_path)
    print(f"[분석 결과 : {'위험 감지됨' if is_danger else '이상 없음'}] -> '{os.path.basename(video_path)}'가 '{os.path.basename(final_folder)}'로 이동되었습니다.")
    print("--------------------------------------------------")

# --- 파일 감지 핸들러 ---

class VideoHandler(FileSystemEventHandler):
    def process_file_event(self, path):
        if not os.path.isdir(path) and path.endswith('.avi'):
            print(f"[!] 파일 이벤트 감지: {path}")
            if self.wait_for_file_completion(path):
                analyze_video(path)
            else:
                print(f"[경고] 파일 분석을 건너뜝니다: {path}")
    def on_moved(self, event):
        self.process_file_event(event.dest_path)
    def on_created(self, event):
        self.process_file_event(event.src_path)
    def wait_for_file_completion(self, file_path, timeout=60, check_interval=1.0):
        start_time = time.time()
        last_size = -1
        print(f"[정보] 파일 '{os.path.basename(file_path)}' 쓰기 완료 대기 중...")
        while time.time() - start_time < timeout:
            if not os.path.exists(file_path):
                print(f"[경고] 대기 중 파일이 사라짐: {file_path}")
                return False
            try:
                current_size = os.path.getsize(file_path)
            except OSError:
                time.sleep(check_interval)
                continue

            if current_size == last_size and current_size > 0
                print(f"[정보] 파일 '{os.path.basename(file_path)}' 쓰기 완료 감지. 크기: {current_size} bytes")
                return True
            last_size = current_size
            time.sleep(check_interval)
        print(f"[경고] 파일 '{os.path.basename(file_path)}' 쓰기 완료 시간 초과. (최종 크기: {last_size} bytes)")
        return False

# --- 감시 시작 ---

if __name__ == "__main__":
    print("--------------------------------------------------")
    print(f"폴더 '{input_folder}'에서 새 .avi 파일 대기 중...")
    print(f"위험 감지 시 '{danger_folder}'로, 이상 없으면 '{normal_folder}'로 이동됩니다.")
    print("--------------------------------------------------")
    event_handler = VideoHandler()
    observer = Observer()
    observer.schedule(event_handler, input_folder, recursive=False)
    observer.start()

    try:
        while True:
            time.sleep(1)
            
    except KeyboardInterrupt:
        print("\n[알림] KeyboardInterrupt 발생. 감시 중지 요청.")
        observer.stop()
    observer.join()
    print("[알림] 감시가 중지되었습니다.")

    print("--------------------------------------------------

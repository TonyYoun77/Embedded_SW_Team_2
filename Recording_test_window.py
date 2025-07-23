#for Window Test

import cv2
import datetime
import numpy as np
import time
from PIL import ImageFont, ImageDraw, Image
import sys
import signal
import os

# --- 경로 설정 ---
save_video_folder = 'saved_videos'
os.makedirs(save_video_folder, exist_ok=True)

# --- 녹화 설정 ---
is_record = False
record_start_time = 0
record_duration = 15
video = None
video_filename = None

# --- 녹화 파일명 생성 함수 ---
def generate_filename():
    now = datetime.datetime.now()
    return now.strftime("CCTV_%Y-%m-%d_%H-%M-%S.avi")

# --- 녹화 시작 ---
def start_recording(frame_shape, fourcc):
    global video, video_filename
    filename = generate_filename()
    video_filename = os.path.join(save_video_folder, filename)
    video = cv2.VideoWriter(video_filename, fourcc, 20, (frame_shape[1], frame_shape[0]))
    print(f"[REC] 녹화 시작: {filename}")

# --- 녹화 종료 ---
def stop_recording():
    global video
    if video:
        print("[REC] 녹화 종료")
        video.release()
        video = None
        
# --- 종료 핸들러 ---
def signal_handler(sig, frame):
    stop_recording()
    capture.release()
    cv2.destroyAllWindows()
    sys.exit(0)

signal.signal(signal.SIGINT, signal_handler)

# --- 카메라 초기화 ---
capture = cv2.VideoCapture(0)
capture.set(cv2.CAP_PROP_FRAME_WIDTH, 1280)
capture.set(cv2.CAP_PROP_FRAME_HEIGHT, 720)
fourcc = cv2.VideoWriter_fourcc(*'XVID')
font = ImageFont.truetype('fonts/SCDream6.otf', 20)

ret, frame1 = capture.read()
if not ret:
    print("[ERROR] 카메라를 열 수 없습니다.")
    sys.exit(1)

frame1_gray = cv2.cvtColor(frame1, cv2.COLOR_BGR2GRAY)
frame1_gray = cv2.GaussianBlur(frame1_gray, (21, 21), 0)

print("[REC] 시스템 시작 (q 누르면 종료)")

while True:
    ret, frame2 = capture.read()
    if not ret:
        break

    frame2_gray = cv2.cvtColor(frame2, cv2.COLOR_BGR2GRAY)
    frame2_gray = cv2.GaussianBlur(frame2_gray, (21, 21), 0)

    frame_diff = cv2.absdiff(frame1_gray, frame2_gray)
    thresh = cv2.threshold(frame_diff, 25, 255, cv2.THRESH_BINARY)[1]
    motion_level = np.sum(thresh) / 255
    motion_detected = motion_level > 2000

    now = datetime.datetime.now()
    nowDatetime = now.strftime("%Y-%m-%d %H:%M:%S")

    # 타임스탬프 표시
    cv2.rectangle(frame2, (10, 15), (320, 35), (0, 0, 0), -1)
    frame_pil = Image.fromarray(frame2)
    draw = ImageDraw.Draw(frame_pil)
    draw.text((10, 15), f"CCTV {nowDatetime}", font=font, fill=(255, 255, 255))
    frame2 = np.array(frame_pil)

    if motion_detected and not is_record:
        start_recording(frame2.shape, fourcc)
        is_record = True
        record_start_time = time.time()

    if is_record:
        video.write(frame2)
        cv2.circle(frame2, (620, 15), 5, (0, 0, 255), -1)
        if time.time() - record_start_time > record_duration:
            stop_recording()
            is_record = False

    cv2.imshow("output", frame2)
    frame1_gray = frame2_gray.copy()

    if cv2.waitKey(30) & 0xFF == ord('q'):
        signal_handler(None, None)

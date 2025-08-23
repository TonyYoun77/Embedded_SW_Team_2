import cv2
import datetime
import numpy as np
import time
from PIL import ImageFont, ImageDraw, Image
import sys
import shutil
import os
from picamera2 import Picamera2, Preview
from picamera2.encoders import H264Encoder

# --- 경로 설정 ---
save_video_folder = 'saved_videos'
tmp_video_folder = 'temporary_saved'
os.makedirs(tmp_video_folder, exist_ok=True)
os.makedirs(save_video_folder, exist_ok=True)

# --- 녹화 설정 ---
is_record = False
record_start_time = 0
record_duration = 15
video_filename = None

# --- Picamera2 설정
picam2 = Picamera2()
video_config = picam2.create_video_configuration(main={"size": (1280, 720)})
picam2.configure(video_config)
picam2.start()

# --- 녹화 파일명 생성 함수 ---
def generate_filename():
    now = datetime.datetime.now()
    return now.strftime("CCTV_%Y-%m-%d_%H-%M-%S.mp4")

# --- 움직임 감지 함수 ---

def motion_detected(a, b):
    a_gray = cv2.cvtColor(a, cv2.COLOR_BGR2GRAY)
    a_gray = cv2.GaussianBlur(a_gray, (21, 21), 0)
    b_gray = cv2.cvtColor(b, cv2.COLOR_BGR2GRAY)
    b_gray = cv2.GaussianBlur(b, (21, 21), 0)
    frame_diff = cv2.absdiff(a_gray, b_gray)
    thresh = cv2.threshold(frame_diff, 25, 255, cv2.THRESH_BINARY)[1]
    motion_level = np.sum(thresh) / 255
    if motion_level > 2000:
        return True
    else:
        return False


# --- 녹화 시작 ---
def start_recording(output_filename):
    global video_filename
    video_filename = os.path.join(tmp_video_folder, output_filename)
    
    # H.264Encoder를 사용하여 하드웨어 인코딩 지정
    encoder = H264Encoder(10000000) # 10Mbps 비트레이트
    picam2.start_recording(encoder, video_filename)
    print(f"[REC] recording start: {output_filename}")

# --- 녹화 종료 ---
def stop_recording():
    global video_filename
    print("[REC] recording end")
    picam2.stop_recording()
    if os.path.exists(video_filename):
        # 파일이 완전히 저장된 후, saved_videos 폴더로 이동
        shutil.move(video_filename, os.path.join(save_video_folder, os.path.basename(video_filename)))

# --- 초기 설정 ---
font_path = 'fonts/SCDream6.otf'
if not os.path.exists(font_path):
    print("[ERROR] Font file not found. Please check the font path.")
    sys.exit(1)
font = ImageFont.truetype(font_path, 20)

print("[REC] start recording (press q to stop)")

# 프레임 변수 초기화
frame1 = picam2.capture_array("main")
frame1 = cv2.cvtColor(frame1, cv2.COLOR_RGB2BGR)

try:
    while True:
        frame2 = picam2.capture_array("main")
        frame2 = cv2.cvtColor(frame2, cv2.COLOR_RGB2BGR)
        if frame2 is None:
            break
        
        motion = motion_detected(frame1, frame2)

        now = datetime.datetime.now()
        nowDatetime = now.strftime("%Y-%m-%d %H:%M:%S")

        # 타임스탬프 표시
        cv2.rectangle(frame2, (10, 15), (300, 35), (0, 0, 0), -1)
        frame_pil = Image.fromarray(frame2)
        draw = ImageDraw.Draw(frame_pil)
        draw.text((10, 15), f"CCTV {nowDatetime}", font=font, fill=(255, 255, 255))
        frame2 = np.array(frame_pil)

        if motion and not is_record:
            filename = generate_filename()
            start_recording(filename)
            is_record = True
            record_start_time = time.time()

        if is_record:
            cv2.circle(frame2, (620, 15), 5, (0, 0, 255), -1)
            if time.time() - record_start_time > record_duration:
                stop_recording()
                is_record = False

        cv2.imshow("output", frame2)
        frame1 = frame2.copy()
        key = cv2.waitKey(1) & 0xFF
        if key == ord('q') or key == 27:
            raise KeyboardInterrupt

except KeyboardInterrupt:
    print("System stopped because of keyboardinterrupt.")
    if is_record:
        picam2.stop_recording()
        shutil.move(video_filename, os.path.join(save_video_folder, os.path.basename(video_filename)))
    
    picam2.stop()
    cv2.destroyAllWindows()
    sys.exit(0)

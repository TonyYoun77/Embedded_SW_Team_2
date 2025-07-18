import cv2
import datetime
import numpy as np
import time
import RPi.GPIO as GPIO
import sys
import signal
import os

# --- GPIO 핀 설정 ---
PIR_PIN = 4      # PIR 센서 GPIO4
LED_PIN = 18     # PWM LED GPIO18

GPIO.setmode(GPIO.BCM)
GPIO.setup(PIR_PIN, GPIO.IN)


# 경로 설정
save_video_folder = 'saved_videos'
os.makedirs(save_video_folder, exist_ok=True)


# --- 녹화 관련 변수 ---
is_record = False #초기 녹화 상태 -> False
record_start_time = 0 #초기화
record_duration = 15  # 녹화 시간 (초)
video = None


# --- 녹화 파일명 생성 함수 ---
def generate_filename():
    now = datetime.datetime.now()
    return now.strftime("CCTV_%Y-%m-%d_%H-%M-%S.avi")

# --- 녹화 시작 함수 ---
def start_recording(frame_shape, fourcc):
    global video
    filename = generate_filename()
    print(f"[INFO] 녹화 시작: {filename}")
    video_filename = os.path.join(save_video_folder, f"CCTV {filename}.avi")
    video = cv2.VideoWriter(video_filename, fourcc, 20, (frame_shape[1], frame_shape[0]))

# --- 녹화 종료 함수 ---
def stop_recording():
    global video
    if video:
        print("[INFO] 녹화 종료")
        video.release()
        video = None

# --- 종료 시그널 핸들러 ---
def signal_handler(sig, frame):
    print("\n[INFO] 종료 시그널 받음... 시스템 강제 종료")
    stop_recording()
    GPIO.cleanup()
    capture.release()
    cv2.destroyAllWindows()
    sys.exit(0)

signal.signal(signal.SIGINT, signal_handler)

# --- 메인 코드 ---


# 카메라 초기화
capture = cv2.VideoCapture(1) #웹카메라 사용
capture.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
capture.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)

fourcc = cv2.VideoWriter_fourcc(*'XVID')

ret, frame1 = capture.read() #첫 프레임 읽기
if not ret:
    print("[ERROR] 카메라를 열 수 없습니다.")
    GPIO.cleanup()
    sys.exit(1)

frame1_gray = cv2.cvtColor(frame1, cv2.COLOR_BGR2GRAY) #색상 흑백으로 변경
frame1_gray = cv2.GaussianBlur(frame1_gray, (21, 21), 0) #이미지 블러 처리

print("[INFO] 시스템 시작. 'q' 누르면 종료합니다.")

while True:
    ret, frame2 = capture.read()
    if not ret: #ret가 참이 아니면 오류 뜬 거임.
        print("[ERROR] 프레임을 읽을 수 없습니다.")
        break

    frame2_gray = cv2.cvtColor(frame2, cv2.COLOR_BGR2GRAY) #이전 프레임과 비교를 위해 흑백 변경
    frame2_gray = cv2.GaussianBlur(frame2_gray, (21, 21), 0) # 블러 처리

    # 움직임 감지용 프레임 차분
    frame_diff = cv2.absdiff(frame1_gray, frame2_gray)
    thresh = cv2.threshold(frame_diff, 25, 255, cv2.THRESH_BINARY)[1]
    motion_level = np.sum(thresh) / 255  # 픽셀 수 계산
    motion_detected = motion_level > 2000  # [튜닝가능] 움직임 기준 설정 2000픽셀 이상 다르면 움직임 감지

    pir_detected = GPIO.input(PIR_PIN) == GPIO.HIGH

    # 녹화 조건: PIR 또는 움직임 감지 및 녹화 중이 아닐 때
    if (pir_detected or motion_detected) and not is_record:
        start_recording(frame2.shape, fourcc)
        is_record = True
        record_start_time = time.time()

    # 녹화 중이면 비디오에 프레임 저장
    if is_record:
        video.write(frame2)
        # 녹화 중 표시 (빨간 점)
        cv2.circle(frame2, (620, 15), 5, (0, 0, 255), -1)
        # 녹화 시간 체크 후 종료
        if time.time() - record_start_time > record_duration:
            stop_recording()
            is_record = False

    cv2.imshow("output", frame2)
    frame1_gray = frame2_gray.copy()

    key = cv2.waitKey(30) & 0xFF
    if key == ord('q'):
        signal_handler(None, None)

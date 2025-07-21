import os
import cv2
import numpy as np
import datetime
import shutil
import time
import tflite_runtime.interpreter as tflite  # 라즈베리파이 최적용 -> yolo v8 축소모델로 기존보다 가벼운 부하.

# ---- 경로 설정 ----
input_folder = 'saved_videos'
danger_folder = 'danger_videos'
normal_folder = 'normal_videos'
os.makedirs(danger_folder, exist_ok=True)
os.makedirs(normal_folder, exist_ok=True)

# ---- 위험 판단 기준 클래스 ---- -> 수정 필요!! 커스텀 데이터를 추가할 예정.
DANGER_CLASSES = ['fire', 'fall', 'suspicious']

# ---- YOLOv8 tflite 모델 로드 ----
interpreter = tflite.Interpreter(model_path="yolov8n.tflite")
interpreter.allocate_tensors()
input_details = interpreter.get_input_details() 
output_details = interpreter.get_output_details()

input_shape = input_details[0]['shape'][1:3] #영상 내 프레임의 크기를 640/640 으로 변환해야 한다.

# ---- 위험 판단 함수 ----
def is_dangerous(predictions):
    for pred in predictions:
        class_id = int(pred[0])
        if class_id < len(DANGER_CLASSES):
            class_name = DANGER_CLASSES[class_id]
            if class_name in DANGER_CLASSES:
                return True
    return False

# ---- TFLite YOLO Inference ----
def run_inference(image):
    image_resized = cv2.resize(image, tuple(input_shape))
    input_tensor = np.expand_dims(image_resized, axis=0).astype(np.uint8)

    interpreter.set_tensor(input_details[0]['index'], input_tensor)
    interpreter.invoke()

    output = interpreter.get_tensor(output_details[0]['index'])[0]
    return output

# ---- 영상 분석 루프 ----
def process_videos():
    for filename in os.listdir(input_folder):
        if not filename.endswith('.avi'):
            continue

        full_path = os.path.join(input_folder, filename)
        cap = cv2.VideoCapture(full_path)
        is_danger = False
        frame_count = 0

        while True:
            ret, frame = cap.read()
            if not ret:
                break
            frame_count += 1
            if frame_count % 5 != 0:
                continue  # 5프레임마다 추론하여 연산량 줄임

            detections = run_inference(frame)
            if is_dangerous(detections):
                is_danger = True
                break  # 위험 감지 시 더 이상 분석하지 않음

        cap.release()

        # ---- 분류 및 이동 ----
        dst_folder = danger_folder if is_danger else normal_folder
        print(f"[INFO] {'위험 감지됨' if is_danger else '이상 없음'}: {filename}")
        shutil.move(full_path, os.path.join(dst_folder, filename))

# ---- 실행 ----
if __name__ == '__main__':
    print("[시작] 저장된 영상 분석 및 분류")
    process_videos()
    print("[완료] 영상 분류 작업 종료")

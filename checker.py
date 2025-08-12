import os
import time
import threading
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler

file_total_amount = 30 * 1024**3 #30GB 가 기준입니다. 30GB가 넘어가면 자동으로 30% 이상 오래된 파일들을 순서로 삭제시킬 겁니다.
saved_videos_list = []
danger = 'danger_videos'
normal = 'normal_videos'
total = 0

list_lock = threading.Lock() #파일 삭제 시 오류 방지

def get_current_video_size():
    global total, saved_videos_list
    with list_lock:
        print("현재 총 용량 파악 중..")
        for i in [danger, normal]:
            for file_name in os.listdir(i):
                file_path = os.path.join(i, file_name)
                if os.path.isfile(file_path) and file_path.endswith('.avi'):
                    try:
                        file_size = os.path.getsize(file_path)
                        made_time = os.path.getatime(file_path)
                        saved_videos_list.append((file_path,file_size, made_time))
                        total += file_size
                    except (FileNotFoundError, OSError) as e:
                        print(f'{e}')
        saved_videos_list.sort(key = lambda x : x[2])
        print(f"계산 완료. 현재 총 용량 : {total / 1024**3:.2f}GB, 파일 개수 : {len(saved_videos_list)}")

               

def add_to_list(video_path):
    global total, saved_videos_list
    with list_lock:
        try:
            file_size = os.path.getsize(video_path)
            made_time = os.path.getatime(video_path)
            saved_videos_list.append((video_path, file_size, made_time))
            total += file_size
            saved_videos_list.sort(key = lambda x : x[2])
        except (FileNotFoundError, OSError) as e:
            print(f'{e}')


def check_all_amount_and_delete():
    global saved_videos_list, total
    print("총 저장된 영상 용량 확인 중..")
    print(f"현재 총 용량 : {total/1024**3:.2f}GB")
    with list_lock:
        if (total >= file_total_amount):
            print("자동 삭제를 시작합니다..")
            while(total > file_total_amount*0.7):
                file_path, file_size, _ = saved_videos_list[0]
                try:
                    os.remove(file_path)
                    total -= file_size
                    saved_videos_list.pop(0)
                except (FileNotFoundError, PermissionError, OSError) as e:
                    print(f"{e}")
                    total -= file_size
            print(f"자동 삭제 완료. 현재 총 파일 용량 : {total/1024**3:.2f} GB")
        else:
            print("자동 삭제 미실시.")

# --- 파일 감지 핸들러 ---
class VideoHandler(FileSystemEventHandler):
    def on_moved(self, event):
        if not event.is_directory and event.dest_path.endswith('.avi'):
            print(f"[!] 파일 이동 감지: {event.dest_path}")
            self.wait_for_file_completion(event.dest_path)
            add_to_list(event.dest_path)
            check_all_amount_and_delete()
        else:
            print(f"[DEBUG-EVENT] on_moved: .avi 파일이 아니거나 디렉토리 이벤트입니다. 스킵.")

    def on_created(self, event):
        if not event.is_directory and event.src_path.endswith('.avi'):
            print(f"[!] 새 파일 생성 감지: {event.src_path}")
            self.wait_for_file_completion(event.src_path)
            add_to_list(event.src_path)
            check_all_amount_and_delete()
        else:
            print(f"[DEBUG-EVENT] on_created: .avi 파일이 아니거나 디렉토리 이벤트입니다. 스킵.")

    def wait_for_file_completion(self, file_path, timeout=30, check_interval=0.5):
        start_time = time.time()
        last_size = -1
        print(f"[정보] 파일 '{os.path.basename(file_path)}' 쓰기 완료 대기 중...")

        while time.time() - start_time < timeout:
            if not os.path.exists(file_path):
                print(f"[경고] 대기 중 파일이 사라짐: {file_path}")
                return False # 파일이 없어졌다면 중단

            current_size = os.path.getsize(file_path)
            # print(f"[DEBUG] 현재 크기: {current_size} bytes, 이전 크기: {last_size} bytes") # 디버그용

            # 파일 크기가 동일하고 0이 아닐 때 (즉, 쓰기가 멈췄을 때)
            if current_size == last_size and current_size > 0:
                print(f"[정보] 파일 '{os.path.basename(file_path)}' 쓰기 완료 감지. 크기: {current_size/1024**3:.2f} GB")
                return True

            last_size = current_size
            time.sleep(check_interval)

        print(f"[경고] 파일 '{os.path.basename(file_path)}' 쓰기 완료 시간 초과. (최종 크기: {last_size} bytes)")
        return False


if __name__ == "__main__":
    get_current_video_size()
    print("대기 중...")
    event_handler = VideoHandler()
    observer = Observer()
    observer.schedule(event_handler, danger, recursive=False)
    observer.schedule(event_handler, normal, recursive=False)
    observer.start()

    try:
        while True:
            time.sleep(0.5)
    except KeyboardInterrupt:
        observer.stop()
    observer.join()

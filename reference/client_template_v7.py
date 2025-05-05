import time
import json
import requests
import pytesseract
import cv2
import numpy as np
from PIL import Image
import os
import sys
import re
import threading
from datetime import datetime
from pystray import Icon, MenuItem, Menu
from PIL import Image as PILImage
import traceback
from ctypes import windll, c_bool, byref
import mss

# ────────────── 기본 설정 ──────────────
if getattr(sys, 'frozen', False):
    base_dir = os.path.dirname(sys.executable)
else:
    base_dir = os.path.dirname(os.path.abspath(__file__))

config_path = os.path.join(base_dir, "config.json")
log_path = os.path.join(base_dir, "client_log.txt")
template_path = os.path.join(base_dir, "round_setting_sample.png")

try:
    with open(config_path, "r", encoding="utf-8-sig") as f:
        config = json.load(f)
except Exception as e:
    with open(log_path, "a", encoding="utf-8") as log_file:
        log_file.write(f"[CONFIG LOAD ERROR] {e}\n")
    sys.exit(1)

BOOTH_NAME = config.get("booth", "unknown")
SERVER_URL = config.get("server_url", "http://localhost:5000/update")
CROP_AREAS = config.get("crop_areas", [])
TESSERACT_PATH = config.get("tesseract_path", r"C:\\Program Files\\Tesseract-OCR\\tesseract.exe")
SEND_INTERVAL = config.get("send_interval", 3)
FAIL_THRESHOLD = config.get("fail_threshold", 4)
USE_TEMPLATE_MATCHING = config.get("use_template_matching", True)

pytesseract.pytesseract.tesseract_cmd = TESSERACT_PATH
last_time = None
fail_count = 0
consecutive_errors = 0
MAX_ERROR_COUNT = 10
running = True

# ───────────── 로그 기록 ─────────────

def log(text):
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    try:
        with open(log_path, "a", encoding="utf-8") as f:
            f.write(f"[{timestamp}] {text}\n")
    except:
        pass

# ───────────── 유틸 함수 ─────────────

def restart_program():
    python = sys.executable
    os.execl(python, python, *sys.argv)

def is_screensaver_active():
    try:
        is_active = c_bool()
        windll.user32.SystemParametersInfoA(114, 0, byref(is_active), 0)
        return is_active.value
    except:
        return False

def normalize_colon(text):
    return re.sub(r'[·•.・:;⠂∘ː꞉’”"|]', ':', text)

def clean_ocr_text(text):
    return text.strip()

# 연속적으로 01:xx 형태의 시간이 두 번 인식되었는지 추적하는 변수
previous_time = None

# 글로벌 변수 초기화
consecutive_01_count = 0  # 01:xx가 연속으로 나타날 때 카운트

def extract_time(text):
    global previous_time, consecutive_01_count

    # 콜론을 정규화하고 텍스트 정리
    text = normalize_colon(text)
    text = clean_ocr_text(text)

# 19초 이하 시간이 명확히 텍스트에 있으면 "00:00"으로 처리
    matches = re.findall(r'(\d{1,2}):(\d{2})', text)
    for m, s in matches:
        try:
            minute = int(m)
            second = int(s)
            if (minute * 60 + second) <= 19:
                return "00:00"
        except:
            continue


    # mm:ss 형식에 맞는 패턴 추출
    matches = re.findall(r'(\d{2,3}):(\d{2})', text)

    for match in matches:
        h_or_m, m_or_s = match

        minute = int(h_or_m)
        second = int(m_or_s)

        # 01:xx 형식이 두 번 연속으로 나타난 경우 hh:mm으로 전환
        if len(h_or_m) == 2 and minute == 1:
            if previous_time == "01" or consecutive_01_count >= 2:
                previous_time = "hh:mm"
                consecutive_01_count = 0
                total_minutes = minute * 60 + second
                if total_minutes > 70:
                    return None
                return f"{total_minutes:02}:00"
            else:
                consecutive_01_count += 1
                previous_time = "01"

        elif len(h_or_m) > 2 or minute > 1:  # 02:xx 이상
            previous_time = "mm:ss"
            if minute > 70:
                return None
            return f"{h_or_m}:{m_or_s}"

        # 기본적으로 mm:ss 형식
        if previous_time == "mm:ss":
            if minute > 70:
                return None
            return f"{h_or_m}:{m_or_s}"

    return None


def decrease_time_str(time_str, seconds=SEND_INTERVAL):
    try:
        m, s = map(int, time_str.split(":"))
        total_sec = m * 60 + s - seconds
        if total_sec < 5:
            return "00:00"
        new_m, new_s = divmod(total_sec, 60)
        return f"{new_m:02}:{new_s:02}"
    except:
        return None

def send_status(time_value, status):
    try:
        payload = {
            "booth": BOOTH_NAME,
            "status": status
        }
        res = requests.post(SERVER_URL, json=payload, timeout=10)
        log(f"OCR: {time_value}, Sent: {payload}, Response: {res.status_code}")
    except Exception as e:
        log(f"[SEND ERROR] {e}")

# ───────────── 메인 OCR 루프 ─────────────

def main_loop():
    global last_time, fail_count, consecutive_errors, running
    log("[START] Client running...")

    template_img = None
    if os.path.exists(template_path):
        template_img = cv2.imread(template_path, cv2.IMREAD_GRAYSCALE)

    # 기존 코드 시작 부분 (수정되지 않음)
    with mss.mss() as sct:
        while running:
            try:
                if is_screensaver_active():
                    send_status("-", "사용가능")
                    log("[SCREEN SAVER] OCR 생략, 사용가능 전송됨")
                    time.sleep(SEND_INTERVAL)
                    continue

                time_text = None
                for idx, area in enumerate(CROP_AREAS):
                    try:
                        x, y, w, h = area["x"], area["y"], area["width"], area["height"]
                        monitor = {"top": y, "left": x, "width": w, "height": h}
                        screenshot = np.array(sct.grab(monitor))
                        img_np = cv2.cvtColor(screenshot, cv2.COLOR_BGRA2BGR)
                        gray = cv2.cvtColor(img_np, cv2.COLOR_BGR2GRAY)

                        # ─── 템플릿 매칭 시도 ───────────────────
                        if idx == 0 and USE_TEMPLATE_MATCHING and template_img is not None:
                            res = cv2.matchTemplate(gray, template_img, cv2.TM_CCOEFF_NORMED)
                            _, max_val, _, _ = cv2.minMaxLoc(res)
                            log(f"[MATCH] 템플릿 매칭 점수: {max_val:.2f}")
                            if max_val > 0.8:
                                # 템플릿 매칭 성공 시 OCR을 건너뛰고 바로 종료
                                if last_time and last_time != "사용가능":
                                    decreased = decrease_time_str(last_time)
                                    if decreased:
                                        m, s = map(int, decreased.split(":"))
                                        if m * 60 + s <= 19:
                                            decreased = "00:00"
                                        last_time = decreased
                                        send_status(decreased, decreased)
                                        log(f"[TEMPLATE MATCH] {decreased} 전송됨")
                                        fail_count = 0
                                else:
                                    last_time = "사용가능"
                                    send_status("-", "사용가능")
                                    log("[TEMPLATE MATCH INIT] 사용가능 전송됨")
                                time.sleep(SEND_INTERVAL)  # OCR 건너뛰고 기다린다.
                                break  # OCR 시도 없이 바로 종료
                            else:
                                # 템플릿 매칭 실패시 1번 영역은 건너뛰고 2번과 3번 영역에서 OCR 시도
                                continue  # 1번 영역은 건너뛰고 2번, 3번에서 OCR을 시도할 수 있도록 넘어간다.

                        # ─── OCR 처리 ───────────────────
                        if idx > 0:  # 템플릿 매칭 실패 후 2번, 3번 영역에서만 OCR을 시도
                            resized = cv2.resize(gray, (gray.shape[1]*3, gray.shape[0]*3), interpolation=cv2.INTER_LINEAR)
                            _, binary = cv2.threshold(resized, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
                            processed_img = Image.fromarray(binary)
                            matched_text = pytesseract.image_to_string(
                                processed_img,
                                config='--psm 7 -c tessedit_char_whitelist=0123456789:.',
                                timeout=10
                            )
                            log(f"[CROP AREA {idx+1}] OCR Raw: {matched_text.strip()}")
                            time_text = extract_time(matched_text)
                            if time_text:
                                break

                    except Exception as e:
                        log(f"[OCR PROCESSING ERROR] {e}")

                # OCR 성공 시 상태 업데이트
                if time_text:
                    m, s = map(int, time_text.split(":"))
                    if m * 60 + s <= 19:
                        time_text = "00:00"
                    last_time = time_text
                    fail_count = 0
                    send_status(time_text, time_text)

                else:
                    fail_count += 1
                    log(f"[OCR FAIL] 실패 {fail_count}회")
                    if 1 <= fail_count < FAIL_THRESHOLD and last_time != "사용가능":
                        decreased = decrease_time_str(last_time, SEND_INTERVAL)
                        if decreased:
                            last_time = decreased
                            send_status(decreased, decreased)
                            log(f"[FAIL BACKUP] {decreased} 전송됨")
                    elif fail_count >= FAIL_THRESHOLD:
                        if last_time != "사용가능":
                            last_time = "사용가능"
                            send_status("-", "사용가능")
                            log("[FAIL THRESHOLD] 사용가능 전환 전송됨")
                        else:
                            send_status("-", "사용가능")
                            log("[FAIL THRESHOLD] 여전히 사용가능 재전송됨")

                consecutive_errors = 0

            except Exception as e:
                log(f"[UNEXPECTED ERROR] {e}")
                traceback.print_exc()
                consecutive_errors += 1
                if consecutive_errors >= MAX_ERROR_COUNT:
                    log("[RESTARTING] 오류 누적 재시작")
                    restart_program()

            time.sleep(SEND_INTERVAL)
    # 기존 코드 끝 (수정되지 않음)


# ───────────── 트레이 아이콘 ─────────────

def show_logs(icon, item):
    try:
        os.startfile(log_path)
    except Exception as e:
        log(f"[LOG OPEN ERROR] {e}")

def exit_app(icon, item):
    global running
    running = False
    icon.stop()

def setup_tray():
    tray_icon = Icon("OCR Client")
    tray_icon.menu = Menu(
        MenuItem("로그 열기", show_logs),
        MenuItem("종료", exit_app)
    )
    icon_img = PILImage.new("RGB", (64, 64), color="black")
    tray_icon.icon = icon_img
    threading.Thread(target=main_loop, daemon=True).start()
    tray_icon.run()

# ───────────── 시작 ─────────────

if __name__ == "__main__":
    setup_tray()

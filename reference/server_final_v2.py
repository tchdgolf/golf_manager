from flask import Flask, request, render_template, redirect, url_for
from datetime import datetime, timedelta
from collections import defaultdict
import os, json, sys, calendar, time
from threading import Thread
from waitress import serve

# --- 상수 및 유틸 함수 ---

pending_signal = defaultdict(lambda: None)

def time_str_to_seconds(time_str):
    try:
        mins, secs = map(int, time_str.strip().split(":"))
        return mins * 60 + secs
    except:
        return 0

def mask_name(name):
    if len(name) <= 1:
        return "*"
    elif len(name) == 2:
        return name[0] + "*"
    else:
        return name[0] + "*" * (len(name) - 2) + name[-1]

# --- Flask 초기화 및 경로 세팅 ---
app = Flask(__name__)
BASE_DIR = os.path.dirname(os.path.abspath(sys.executable if getattr(sys, 'frozen', False) else __file__))
STATE_FILE = os.path.join(BASE_DIR, 'server_state.json')
CONFIG_FILE = os.path.join(BASE_DIR, 'server_config.json')
QUEUE_FILE = os.path.join(BASE_DIR, 'queue.json')

# --- 초기 데이터 및 상태 ---
status_data = defaultdict(lambda: {'status': '사용가능', 'time': '-', 'last_update': datetime.min})
booth_assignments = defaultdict(lambda: None)
ignored_state = defaultdict(lambda: {'in_ignore': False, 'start_time': None, 'start_remaining': None})

def load_json(filename, default=[]):
    if not os.path.exists(filename):
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(default, f, ensure_ascii=False, indent=2)
        return default

    try:
        with open(filename, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception as e:
        print(f"[ERROR] Failed to load {filename}: {e}")
        return default


def load_config():
    default_config = {
        "offline_threshold_seconds": 300,
        "offline_sundays": [1, 3],
        "custom_holidays": [],
        "operating_hours": {
            "mon": [9, 23], "tue": [9, 23], "wed": [9, 23],
            "thu": [9, 23], "fri": [9, 23], "sat": [10, 21], "sun": [10, 21]
        },
        "wait_before_enforce_client_seconds": 60
    }
    try:
        if os.path.exists(CONFIG_FILE):
            return load_json(CONFIG_FILE, default=default_config)
    except Exception as e:
        print(f"[ERROR] Failed to load config: {e}")
    return default_config




config = load_config()
OFFLINE_THRESHOLD_SECONDS = config["offline_threshold_seconds"]
OPERATING_HOURS = config["operating_hours"]
OFFLINE_SUNDAYS = config["offline_sundays"]
CUSTOM_HOLIDAYS = config["custom_holidays"]
WEEKDAY_KEYS = ['mon', 'tue', 'wed', 'thu', 'fri', 'sat', 'sun']
WAIT_BEFORE_ENFORCE_CLIENT_SECONDS = config.get("wait_before_enforce_client_seconds", 60)

queue = []

def load_state():
    saved = load_json(STATE_FILE, default={'status_data': {}, 'assignments': {}})
    for k, v in saved.get('status_data', {}).items():
        status_data[k] = {
            'status': v.get('status', '사용가능'), # 기본 상태 설정
            'time': v.get('time', '-'), # 기본 시간 설정
            'last_update': datetime.fromisoformat(v.get('last_update', datetime.min.isoformat()))
        }
    for booth, v in saved.get('assignments', {}).items():
        booth_assignments[booth] = {
            'name': v.get('name', ''),
            'assigned_time': v.get('assigned_time', '')
        }
    global queue
    queue = load_json(QUEUE_FILE, default=[])

def save_state():
    try:
        save_data = {
            'status_data': {
                k: {
                    'status': v['status'],
                    'time': v['time'],
                    'last_update': v['last_update'].isoformat()
                } for k, v in status_data.items()
            },
            'assignments': booth_assignments # 직접 할당
        }
        with open(STATE_FILE, 'w', encoding='utf-8') as f:
            json.dump(save_data, f, ensure_ascii=False, indent=2)
        with open(QUEUE_FILE, 'w', encoding='utf-8') as f:
            json.dump(queue, f, ensure_ascii=False, indent=2)
    except Exception as e:
        print(f"[ERROR] Failed to save state: {e}")



def get_offline_days_this_month(now: datetime):
    offline_dates = set()
    year, month = now.year, now.month

    if OFFLINE_SUNDAYS:
        sundays = [d for d in calendar.Calendar().itermonthdates(year, month) if d.weekday() == 6 and d.month == month]
        for idx in OFFLINE_SUNDAYS:
            if 1 <= idx <= len(sundays):
                offline_dates.add(sundays[idx-1])

    for date_str in CUSTOM_HOLIDAYS:
        try:
            d = datetime.strptime(date_str, "%Y-%m-%d").date()
            if d.year == year and d.month == month:
                offline_dates.add(d)
        except ValueError:
            continue

    return sorted(list(offline_dates))

def is_within_operating_hours(now: datetime):
    key = WEEKDAY_KEYS[now.weekday()]
    hrs = OPERATING_HOURS.get(key)
    return bool(hrs and hrs[0] <= now.hour < hrs[1])

def assign_first_queue_to_booth():
    updated = False
    now = datetime.now()

    for booth, status in status_data.items():
        if status['status'] == '사용가능' and queue:
            first_queue = queue.pop(0) # 큐에서 바로 꺼내기

            status_data[booth] = {
                'status': '사용중',
                'time': '70:00',
                'last_update': now
            }
            booth_assignments[booth] = {
                "name": first_queue,
                "assigned_time": now.strftime("%Y-%m-%d %H:%M:%S")
            }

            # ✅ 무시구간 진입
            ignored_state[booth] = {
                'in_ignore': True,
                'start_time': now,
                'start_remaining': 4200
            }

            print(f"{first_queue} 님이 {booth} 타석에 배정되었습니다.")
            updated = True

    if updated:
        save_state()


from threading import Thread


def get_expected_booth_assignments():
    now = datetime.now()
    booth_remaining = []
    for booth, data in status_data.items():
        if data['status'] == '사용중' and ':' in data['time']:
            try:
                mins, secs = map(int, data['time'].split(':'))
                remaining = mins * 60 + secs
                booth_remaining.append((booth, remaining))
            except:
                continue
        elif data['status'] == '사용가능':
            booth_remaining.append((booth, 0))

    booth_remaining.sort(key=lambda x: x[1])

    assignments = []
    for i, name in enumerate(queue):
        if i < len(booth_remaining):
            booth, wait_sec = booth_remaining[i]
            assignments.append({
                'name': name,
                'masked_name': mask_name(name),
                'expected_booth': booth,
                'expected_wait': f"{wait_sec // 60:02d}:{wait_sec % 60:02d}"
            })
        else:
            assignments.append({
                'name': name,
                'masked_name': mask_name(name),
                'expected_booth': '-',
                'expected_wait': '-'
            })
    return assignments

@app.route('/update', methods=['POST'])
def update():
    data = request.get_json() or {}
    booth = data.get('booth')
    status_str = data.get('status')

    if not booth or status_str is None:
        return "Invalid data", 400

    now = datetime.now()
    last_update = status_data[booth]['last_update']
    time_since_update = (now - last_update).total_seconds()

    booth_time_str = status_data[booth]['time']
    booth_seconds = time_str_to_seconds(booth_time_str)
    remaining_seconds = booth_seconds - int(time_since_update)

    ignore = ignored_state[booth]

    if ignore['in_ignore']:
        elapsed = (now - ignore['start_time']).total_seconds()

        # 정상값 (00:01~70:00) 수신 시 무시구간 탈출
        if ':' in status_str:
            try:
                sec = time_str_to_seconds(status_str)
                if 1 <= sec <= 4200:
                    print(f"[EXIT IGNORED] {booth} → 정상값 수신")
                    ignored_state[booth] = {'in_ignore': False, 'start_time': None, 'start_remaining': None}
                    status_data[booth] = {
                        'status': '사용중',
                        'time': status_str,
                        'last_update': now
                    }
                    save_state()
                    return "OK", 200
            except:
                pass

        # 시간 경과에 의한 무시구간 탈출
        if elapsed >= WAIT_BEFORE_ENFORCE_CLIENT_SECONDS:
            print(f"[EXIT IGNORED] {booth} → 시간 경과")
            ignored_state[booth] = {'in_ignore': False, 'start_time': None, 'start_remaining': None}
            return "OK", 200
        else:
            # 여전히 무시 중 → 시간만 표시 갱신
            remaining = max(0, ignore['start_remaining'] - int(elapsed))
            mins, secs = divmod(remaining, 60)
            status_data[booth]['time'] = f"{mins:02d}:{secs:02d}"
            save_state()
            print(f"[IGNORED] {booth} → {status_str} (무시구간 중)")
            return "IGNORED", 200

    if status_str == "DECREASE":
        # 기존 남은 시간 가져오기
        old_time_str = status_data[booth]['time']
        old_sec = time_str_to_seconds(old_time_str)
        try:
            interval = int(data.get('interval', 3))
        except (ValueError, TypeError):
            print(f"[ERROR] Invalid interval value from client: {data.get('interval')} ({e})")
            return "Invalid interval", 400


        new_sec = max(0, old_sec - interval)

        if new_sec == 0:
            # 시간이 0이면 사용가능 처리 + 큐 자동 배정
            status_data[booth] = {
                'status': '사용가능',
                'time': '-',
                'last_update': now
            }
            assign_first_queue_to_booth()
            print(f"[DECREASE → 사용가능] {booth} → {old_time_str} → 00:00")
        else:
            mins, secs = divmod(new_sec, 60)
            new_time_str = f"{mins:02d}:{secs:02d}"
            status_data[booth] = {
                'status': '사용중',
                'time': new_time_str,
                'last_update': now
            }
            print(f"[DECREASE] {booth} → {old_time_str} → {new_time_str}")

        save_state()
        return "OK", 200



    if status_str == "00:00":
        ignore = ignored_state[booth]
        if ignore['in_ignore']:
            elapsed_since_ignore = (now - ignore['start_time']).total_seconds()
            if elapsed_since_ignore < WAIT_BEFORE_ENFORCE_CLIENT_SECONDS:
                print(f"[IGNORED] {booth} → 00:00 (무시구간 타이머 내)")
                return "IGNORED", 200
            else:
                print(f"[EXIT IGNORED] {booth} → 00:00 수신, 시간 경과")
                ignored_state[booth] = {'in_ignore': False, 'start_time': None, 'start_remaining': None}
        # 무시구간이 아니거나 시간이 충분히 경과함 → 사용가능 처리
        status_data[booth] = {
            'status': '사용가능',
            'time': '-',
            'last_update': now
        }
        save_state()
        return "OK", 200


    # 기본 처리
    if ':' in status_str and status_str.replace(':', '').isdigit():
        status_data[booth] = {'status': '사용중', 'time': status_str, 'last_update': now}
    elif status_str == '사용가능':
        status_data[booth] = {'status': '사용가능', 'time': '-', 'last_update': now}
        assign_first_queue_to_booth()
    else:
        return "Invalid status format", 400

    if status_data[booth]['status'] == '사용가능' and status_data[booth]['time'] != '-':
        status_data[booth]['time'] = '-'

    save_state()
    return "OK", 200




@app.route('/status')
def status():
    now = datetime.now()
    today = now.date()
    offline_days = get_offline_days_this_month(now)

    processed = {}
    for name in sorted(status_data.keys()):
        d = status_data[name]
        diff = (now - d['last_update']).total_seconds()
        if diff > OFFLINE_THRESHOLD_SECONDS:
            if today in offline_days:
                st = 'OFFLINE'
            elif is_within_operating_hours(now):
                st = '사용가능'
            else:
                st = 'OFFLINE'
            tm = '-'
        else:
            st, tm = d['status'], d['time']
        processed[name] = {'status': st, 'time': tm}

    expected_assignments = get_expected_booth_assignments()
    msg = request.args.get('msg')  # ✅ 메시지 코드 받기

    return render_template(
        'dashboard.html',
        status_data=processed,
        time=now,
        offline_sundays=offline_days,
        queue_display=expected_assignments,
        msg=msg  # ✅ 템플릿에 넘겨주기
    )

@app.route('/')
def home():
    return redirect(url_for('status'))

@app.route('/queue', methods=['POST'])
def join_queue():
    name = request.form.get('name', '').strip()
    if name in queue:
        return redirect(url_for('status', msg='already'))
    if name:
        queue.append(name)
        assign_first_queue_to_booth() 
        save_state()
    return redirect(url_for('status', msg='joined'))


@app.route('/cancel', methods=['POST'])
def cancel_queue():
    name = request.form.get('name', '').strip()
    if name in queue:
        queue.remove(name)
        save_state()
    return redirect(url_for('status'))




@app.route("/admin", methods=["GET", "POST"])
def admin():
    load_state()  # 항상 최신 상태를 반영
    global queue, status_data, booth_assignments

    if request.method == "POST":
        action = request.form.get("action")
        name = request.form.get("name")
        booth = request.form.get("booth")
        status = request.form.get("status")
        time_str = request.form.get("time")

        if action == "add" and name:
            if name not in queue:
                queue.append(name)
        elif action == "remove" and name in queue:
            queue.remove(name)
        elif action == "up" and name in queue:
            idx = queue.index(name)
            if idx > 0:
                queue[idx], queue[idx - 1] = queue[idx - 1], queue[idx]
        elif action == "down" and name in queue:
            idx = queue.index(name)
            if idx < len(queue) - 1:
                queue[idx], queue[idx + 1] = queue[idx + 1], queue[idx]
        elif action == "update_booth" and booth in status_data:
            status_data[booth]['status'] = status
            status_data[booth]['time'] = time_str
            status_data[booth]['last_update'] = datetime.now()

        save_state()
        return redirect("/admin")

    # GET 요청 처리
    booth_data = {
        booth: {
            'status': status_data[booth]['status'],
            'time': status_data[booth]['time'],
            'last_update': status_data[booth]['last_update'].strftime('%Y-%m-%d %H:%M:%S')
        }
        for booth in sorted(status_data)
    }

    # ✅ 최근 배정 5개만 추출
    recent_assignments = sorted(
        [(booth, info) for booth, info in booth_assignments.items() if info and info.get('assigned_time')],
        key=lambda x: x[1]['assigned_time'],
        reverse=True
    )[:5]

    # 🔧 시간 포맷 변경: %H:%M:%S → %H:%M
    for booth, info in recent_assignments:
        try:
            t = datetime.strptime(info['assigned_time'], "%Y-%m-%d %H:%M:%S")
            info['assigned_time'] = t.strftime("%m/%d %H:%M")
        except:
            pass

    return render_template(
        "admin.html",
        booths=booth_data,
        queue=queue,
        booth_assignments=dict(recent_assignments)  # ✅ 최신 5개만 넘김
    )



@app.route('/admin/update', methods=['POST'])
def admin_update():
    booth = request.form.get('booth')
    new_status = request.form.get('status')
    now = datetime.now()

    if booth and new_status:
        if new_status == '사용가능':
            status_data[booth] = {
                'status': '사용가능',
                'time': '-',
                'last_update': now
            }
            # ✅ 무시구간 해제
            ignored_state[booth] = {
                'in_ignore': False,
                'start_time': None,
                'start_remaining': None
            }

        elif new_status == '사용중':
            status_data[booth] = {
                'status': '사용중',
                'time': '70:00',
                'last_update': now
            }
            # ✅ 무시구간 진입
            ignored_state[booth] = {
                'in_ignore': True,
                'start_time': now,
                'start_remaining': 4200
            }

        save_state()

    return redirect(url_for('admin'))



if __name__ == '__main__':
    load_state()
    serve(app, host='0.0.0.0', port=5000)

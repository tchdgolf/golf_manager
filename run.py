# run.py
import os
import click # click 임포트 추가
from flask.cli import with_appcontext # 데코레이터 임포트 추가
from app import create_app, db # app/__init__.py 에서 create_app 함수와 db 객체 가져오기
from app.models import User, Pro, Booth
from app.models.enums import BoothSystemType, BoothStatus

# .env 파일 로드 (config.py에서도 로드하지만, 여기서도 명시적으로 로드 가능)
from dotenv import load_dotenv
dotenv_path = os.path.join(os.path.dirname(__file__), '.env')
if os.path.exists(dotenv_path):
    load_dotenv(dotenv_path)

# 앱 인스턴스 생성 (기본값: development 설정 사용)
config_name = os.getenv('FLASK_CONFIG') or 'development'
app = create_app(config_name)

@app.shell_context_processor
def make_shell_context():
    return {'db': db, 'User': User, 'Pro': Pro, 'Booth': Booth}

# --- ▼ 초기 타석 생성 CLI 명령어 추가 ▼ ---
@app.cli.command('init-booths')
@with_appcontext
def init_booths_command():
    """초기 타석 데이터(카카오 3, QED 4)를 생성합니다."""
    booths_to_create = []
    # 카카오 타석
    for i in range(1, 4): # 1, 2, 3
        booths_to_create.append({'name': f'카카오 {i}번 타석', 'system_type': BoothSystemType.KAKAO})
    # QED 타석
    for i in range(1, 5): # 1, 2, 3, 4
        booths_to_create.append({'name': f'QED {i}번 타석', 'system_type': BoothSystemType.QED})

    created_count = 0
    skipped_count = 0
    error_count = 0
    print("초기 타석 데이터 생성을 시작합니다...")
    try:
        for booth_data in booths_to_create:
            # 이미 같은 이름의 타석이 있는지 확인
            existing_booth = Booth.query.filter_by(name=booth_data['name']).first()
            if existing_booth:
                # print(f"타석 '{booth_data['name']}' 은(는) 이미 존재하여 건너<0xEB><0x9C><0x89>니다.") # 스킵 로그는 생략 가능
                skipped_count += 1
                continue # 이미 있으면 다음 타석으로

            # 새 타석 생성
            new_booth = Booth(
                name=booth_data['name'],
                system_type=booth_data['system_type'],
                is_available=True, # 기본값: 예약 가능
                current_status=BoothStatus.AVAILABLE # 기본값: 사용 가능
            )
            db.session.add(new_booth)
            created_count += 1

        db.session.commit() # 모든 추가 작업 후 한번에 커밋
        print(f"초기 타석 데이터 생성 완료: {created_count}개 생성, {skipped_count}개 건너<0xEB><0x9C><0x89> (이미 존재).")

    except Exception as e:
        db.session.rollback() # 오류 발생 시 롤백
        error_count = len(booths_to_create) - skipped_count # 오류 수를 대략적으로 계산
        print(f"초기 타석 생성 중 오류 발생: {e}")
        print(f"오류 발생 전까지 {created_count}개 시도, {skipped_count}개 건너<0xEB><0x9C><0x89>.")

# --- ▲ 초기 타석 생성 CLI 명령어 끝 ▲ ---

# --- ▼ 초기 관리자 생성 CLI 명령어 추가 ▼ ---
@app.cli.command('init-admin')
@with_appcontext # 앱 컨텍스트 내에서 실행되도록 함
def init_admin_command():
    """데이터베이스에 사용자가 없을 경우 초기 관리자 계정을 생성합니다."""
    if db.session.query(User).first() is not None:
        print('이미 사용자가 존재합니다. 초기 관리자를 생성하지 않습니다.')
        return

    print("초기 관리자 계정을 생성합니다...")
    try:
        admin_phone = os.environ.get('INITIAL_ADMIN_PHONE', '010-0000-0000')
        admin_password = os.environ.get('INITIAL_ADMIN_PASSWORD') or 'changeme'

        if not admin_password or admin_password == 'changeme':
             print("경고: .env 파일에 초기 관리자 비밀번호(INITIAL_ADMIN_PASSWORD)가 설정되지 않았거나 기본값('changeme')입니다.")

        admin_user = User(name='관리자', phone=admin_phone, is_admin=True)
        admin_user.set_password(admin_password)
        admin_user.set_phone_last4()
        db.session.add(admin_user)
        db.session.commit()
        print(f"초기 관리자 계정이 생성되었습니다. 연락처: {admin_phone}")
        print(f"비밀번호는 .env 파일의 INITIAL_ADMIN_PASSWORD 값을 확인하거나 기본값('changeme')입니다.")
        print("!!! 중요: 생성된 관리자 계정으로 로그인 후 반드시 비밀번호를 변경하세요 !!!")
    except Exception as e:
        db.session.rollback()
        print(f"초기 관리자 계정 생성 중 오류 발생: {e}")
# --- ▲ 초기 관리자 생성 CLI 명령어 끝 ▲ ---

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8080)
# run.py
import os
import click # click 임포트 추가
from flask.cli import with_appcontext # 데코레이터 임포트 추가
from app import create_app, db # app/__init__.py 에서 create_app 함수와 db 객체 가져오기
from app.models import User, Pro, Booth

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
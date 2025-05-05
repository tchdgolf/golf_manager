# run.py
import os
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
    # Pro, Booth 모델도 shell context에 추가
    return {'db': db, 'User': User, 'Pro': Pro, 'Booth': Booth}

# 애플리케이션 실행 (개발 서버)
if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8080)
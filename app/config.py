# app/config.py
import os
from dotenv import load_dotenv

# .env 파일 로드
basedir = os.path.abspath(os.path.dirname(__file__))
dotenv_path = os.path.join(basedir, '..', '.env') # .env 파일은 app 폴더 밖에 있음
if os.path.exists(dotenv_path):
    load_dotenv(dotenv_path)
else:
    print(f"Warning: .env file not found at {dotenv_path}")


class Config:
    """기본 설정"""
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'you-will-never-guess'
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL') or \
        'sqlite:///' + os.path.join(basedir, 'golf_manager.db') # 기본값으로 SQLite 사용
    SQLALCHEMY_TRACK_MODIFICATIONS = False # SQLAlchemy 이벤트 처리 안 함 (성능 향상)
    BOOTSTRAP_SERVE_LOCAL = False # Bootstrap 로컬 파일 대신 CDN 사용 (True로 변경 시 로컬 파일 필요)

    # 향후 추가될 설정들...
    # MAIL_SERVER = os.environ.get('MAIL_SERVER')
    # MAIL_PORT = int(os.environ.get('MAIL_PORT') or 25)
    # MAIL_USE_TLS = os.environ.get('MAIL_USE_TLS') is not None
    # MAIL_USERNAME = os.environ.get('MAIL_USERNAME')
    # MAIL_PASSWORD = os.environ.get('MAIL_PASSWORD')
    # ADMINS = ['your-email@example.com']


class DevelopmentConfig(Config):
    """개발 환경 설정"""
    DEBUG = True


class ProductionConfig(Config):
    """운영 환경 설정"""
    DEBUG = False
    # 운영 환경에서는 더 강력한 SECRET_KEY 사용 권장
    # 데이터베이스 URL도 운영 DB로 변경 필요


# 설정 이름과 클래스를 매핑
config = {
    'development': DevelopmentConfig,
    'production': ProductionConfig,
    'default': DevelopmentConfig
}
# app/__init__.py
import os # os 모듈 임포트 추가
from flask import Flask, render_template
from .config import config
from .extensions import db, migrate, login_manager, bcrypt, csrf, bootstrap

def create_app(config_name='default'):
    app = Flask(__name__)
    app.config.from_object(config[config_name])

    # 확장 기능 초기화 (db.init_app 등)
    db.init_app(app)
    migrate.init_app(app, db)
    login_manager.init_app(app)
    bcrypt.init_app(app)
    csrf.init_app(app)
    bootstrap.init_app(app)

    # # --- ▼ 초기 관리자 생성 로직 추가 ▼ ---
    # with app.app_context():
    #     from .models import User # User 모델 임포트 (컨텍스트 내에서)

    #     # 데이터베이스에 사용자가 한 명도 없는지 확인
    #     if db.session.query(User).first() is None:
    #         print("데이터베이스에 사용자가 없습니다. 초기 관리자 계정을 생성합니다...")
    #         try:
    #             # .env 파일에서 관리자 정보 읽기 (없으면 기본값 사용 - 실제 배포시 주의)
    #             admin_phone = os.environ.get('INITIAL_ADMIN_PHONE', '010-0000-0000')
    #             # .env 에 비밀번호 설정이 없거나 비어있으면 기본값 사용 (보안상 실제 배포 전 확인 필수!)
    #             admin_password = os.environ.get('INITIAL_ADMIN_PASSWORD') or 'changeme'

    #             if not admin_password or admin_password == 'changeme':
    #                  print("경고: .env 파일에 초기 관리자 비밀번호(INITIAL_ADMIN_PASSWORD)가 설정되지 않았거나 기본값('changeme')입니다. 보안을 위해 설정해주세요.")

    #             admin_user = User(
    #                 name='관리자',
    #                 phone=admin_phone,
    #                 is_admin=True
    #             )
    #             admin_user.set_password(admin_password)
    #             admin_user.set_phone_last4()
    #             db.session.add(admin_user)
    #             db.session.commit()
    #             print(f"초기 관리자 계정이 생성되었습니다. 연락처: {admin_phone}")
    #             print(f"비밀번호는 .env 파일의 INITIAL_ADMIN_PASSWORD 값을 확인하거나 기본값('changeme')입니다.")
    #             print("!!! 중요: 생성된 관리자 계정으로 로그인 후 반드시 비밀번호를 변경하세요 !!!")
    #         except Exception as e:
    #             db.session.rollback() # 오류 발생 시 롤백
    #             print(f"초기 관리자 계정 생성 중 오류 발생: {e}")
    #             # 여기서 프로그램을 중단하거나 다른 처리를 할 수 있습니다.
    #     # else: # 사용자가 이미 있으면 아무 작업 안 함
    #         # print("기존 사용자가 존재하여 초기 관리자를 생성하지 않습니다.")
    # # --- ▲ 초기 관리자 생성 로직 끝 ▲ ---

    # 모델 및 user_loader 임포트 (앱 컨텍스트 내부 또는 함수 호출 후)
    # 순환 참조를 피하기 위해 이 위치에서 임포트하거나,
    # 블루프린트 등록 전에 필요한 모델을 임포트합니다.
    # 주의: 이 방식보다 블루프린트 내에서 필요시 임포트하는 것이 더 안전할 수 있습니다.
    with app.app_context():
         from . import models # 모델 로드 (user_loader 포함)

    # 블루프린트 등록
    from .routes.auth import bp as auth_bp
    app.register_blueprint(auth_bp, url_prefix='/auth')
    from .routes.admin import bp as admin_bp # admin 블루프린트 임포트
    app.register_blueprint(admin_bp) # admin 블루프린트 등록 (url_prefix는 admin/__init__.py 에 이미 정의됨

    # 임시 메인 라우트
    @app.route('/')
    def index():
        return render_template('base.html')
    

    # 나중에 다른 블루프린트들도 여기에 등록합니다.
    # from .routes.admin import bp as admin_bp
    # app.register_blueprint(admin_bp, url_prefix='/admin')
    # ...

    return app
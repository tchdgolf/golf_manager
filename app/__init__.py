# app/__init__.py
from flask import Flask, render_template
from .config import config
from .extensions import db, migrate, login_manager, bcrypt, csrf, bootstrap # extensions.py 에서 가져오기

def create_app(config_name='default'):
    app = Flask(__name__)
    app.config.from_object(config[config_name])

    # 확장 기능 앱 인스턴스에 연결 (init_app 사용)
    db.init_app(app)
    migrate.init_app(app, db)
    login_manager.init_app(app)
    bcrypt.init_app(app)
    csrf.init_app(app)
    bootstrap.init_app(app)

    # 모델 및 user_loader 임포트 (앱 컨텍스트 내부 또는 함수 호출 후)
    # 순환 참조를 피하기 위해 이 위치에서 임포트하거나,
    # 블루프린트 등록 전에 필요한 모델을 임포트합니다.
    # 주의: 이 방식보다 블루프린트 내에서 필요시 임포트하는 것이 더 안전할 수 있습니다.
    with app.app_context():
         from . import models # 모델 로드 (user_loader 포함)

    # 블루프린트 등록
    from .routes.auth import bp as auth_bp
    app.register_blueprint(auth_bp, url_prefix='/auth')

    # 임시 메인 라우트
    @app.route('/')
    def index():
        return render_template('base.html')
    

    # 나중에 다른 블루프린트들도 여기에 등록합니다.
    # from .routes.admin import bp as admin_bp
    # app.register_blueprint(admin_bp, url_prefix='/admin')
    # ...

    return app
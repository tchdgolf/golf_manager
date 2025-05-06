# app/__init__.py
import os # os 모듈 임포트 추가
from flask import Flask, render_template
from .config import config
from .extensions import db, migrate, login_manager, bcrypt, csrf, bootstrap
from markupsafe import Markup, escape

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

    # --- ▼ 커스텀 Jinja2 필터 등록 ▼ ---
    def nl2br(value):
        """Jinja2 필터: 개행 문자를 <br> 태그로 변환"""
        if not value: # 값이 없으면 빈 문자열 반환
            return ''
        # 1. HTML 특수 문자를 이스케이프 처리 (XSS 방지)
        escaped_value = escape(value)
        # 2. 개행 문자를 <br> 태그로 변환하고 Markup 객체로 감싸서 HTML로 렌더링되도록 함
        return Markup(escaped_value.replace('\n', '<br>\n'))

    app.jinja_env.filters['nl2br'] = nl2br
    # --- ▲ 커스텀 Jinja2 필터 등록 끝 ▲ ---

    # 임시 메인 라우트
    @app.route('/')
    def index():
        return render_template('base.html')
    

    # 나중에 다른 블루프린트들도 여기에 등록합니다.
    # from .routes.admin import bp as admin_bp
    # app.register_blueprint(admin_bp, url_prefix='/admin')
    # ...

    return app
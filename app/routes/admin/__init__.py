# app/routes/admin/__init__.py
from flask import Blueprint

# 'admin' 블루프린트 정의
# template_folder 를 지정하여 이 블루프린트의 템플릿 경로를 설정
bp = Blueprint('admin', __name__, url_prefix='/admin', template_folder='../../templates/admin')

# 관리자 전용 블루프린트이므로, 모든 라우트에 접근 제어 적용 (선택적)
# @bp.before_request 를 사용하면 이 블루프린트의 모든 요청 전에 실행됨
from flask_login import login_required
from app.routes.auth import admin_required # auth.py 에 정의된 데코레이터 사용

@bp.before_request
@login_required  # 최소 로그인 필요
@admin_required # 관리자 권한 필요
def before_request():
    """이 블루프린트의 모든 라우트는 관리자만 접근 가능"""
    pass

# Pro, Booth, User 관련 라우트 파일들을 여기서 임포트하여 블루프린트에 등록
from . import views_pro
from . import views_booth
from . import views_user
from . import views_ticket_template
from . import views_ticket
# app/routes/auth.py
import datetime # 시간 기록 위해 추가
from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_user, logout_user, login_required, current_user
from werkzeug.urls import url_parse # 리디렉션 URL 검증용
from app.extensions import db # db 객체 임포트
from app.models import User # User 모델 임포트
from app.forms.auth_forms import LoginForm, RegistrationForm # 만든 폼 임포트


# 블루프린트 객체 생성 (이전 코드 유지)
bp = Blueprint('auth', __name__, template_folder='../templates/auth')

# app/routes/auth.py 상단 (Blueprint 정의 아래) 에 추가
from functools import wraps
from flask import abort

def admin_required(f):
    """관리자 권한을 확인하는 데코레이터"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated or not current_user.is_admin:
            abort(403) # 권한 없음 오류 발생
            # 또는 로그인 페이지로 리디렉션하고 메시지 표시:
            # flash('관리자 권한이 필요합니다.', 'danger')
            # return redirect(url_for('auth.login'))
        return f(*args, **kwargs)
    return decorated_function

# app/routes/auth.py 에 추가

@bp.route('/login', methods=['GET', 'POST'])
def login():
    # 이미 로그인된 사용자는 메인 페이지로 리디렉션
    if current_user.is_authenticated:
        return redirect(url_for('index')) # 'index'는 app/__init__.py 의 메인 라우트 (@app.route('/'))

    form = LoginForm()
    if form.validate_on_submit():
        # 입력된 연락처로 사용자 검색
        user = User.query.filter_by(phone=form.phone.data).first()

        # 사용자가 존재하고 비밀번호가 맞는지 확인
        if user is None or not user.check_password(form.password.data):
            flash('연락처 또는 비밀번호가 올바르지 않습니다.', 'danger') # 실패 메시지
            return redirect(url_for('auth.login')) # 로그인 페이지 다시 보여주기

        # 사용자 로그인 처리 (Flask-Login 함수 사용)
        login_user(user, remember=form.remember_me.data)

        # 마지막 로그인 시간 업데이트
        user.last_login_at = datetime.datetime.utcnow()
        db.session.commit()

        flash(f'{user.name}님, 환영합니다!', 'success') # 성공 메시지

        # 사용자가 원래 가려던 페이지('next' 파라미터)가 있으면 거기로 리디렉션
        next_page = request.args.get('next')
        # next_page가 없거나, 외부 사이트로의 리디렉션을 방지하기 위한 검증
        if not next_page or url_parse(next_page).netloc != '':
            next_page = url_for('index') # 기본 리디렉션 페이지 (메인)
        return redirect(next_page)

    # GET 요청이거나 폼 유효성 검증 실패 시 로그인 템플릿 렌더링
    return render_template('login.html', title='로그인', form=form)

# app/routes/auth.py 에 추가

@bp.route('/logout')
@login_required # 로그아웃은 로그인된 사용자만 가능
def logout():
    logout_user() # Flask-Login 함수로 사용자 로그아웃 처리 (세션에서 사용자 ID 제거)
    flash('로그아웃되었습니다.', 'info')
    return redirect(url_for('auth.login')) # 로그아웃 후 로그인 페이지로 이동

# app/routes/auth.py 에 추가

@bp.route('/register', methods=['GET', 'POST'])
@login_required  # 일단 로그인 필요
@admin_required # 관리자만 접근 가능
def register():
    form = RegistrationForm()
    if form.validate_on_submit():
        # User 객체 생성
        user = User(
            name=form.name.data,
            phone=form.phone.data,
            memo=form.memo.data
        )
        # 초기 비밀번호 '0000' 설정
        user.set_password('0000')
        # 연락처 마지막 4자리 저장
        user.set_phone_last4()

        # 데이터베이스에 추가 및 저장
        db.session.add(user)
        db.session.commit()

        flash(f'회원 {user.name} ({user.phone}) 님이 성공적으로 등록되었습니다. 초기 비밀번호는 0000 입니다.', 'success')
        # 등록 후 어디로 보낼지 결정 (예: 관리자 회원 목록 페이지 - 나중에 구현)
        # 지금은 임시로 로그인 페이지로 리디렉션
        return redirect(url_for('auth.login'))

    # GET 요청 시 등록 폼 템플릿 렌더링
    return render_template('register.html', title='회원 등록 (관리자)', form=form)


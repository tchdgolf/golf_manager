# app/routes/auth.py
from flask import Blueprint, render_template

# 'auth' 라는 이름의 Blueprint 객체 생성
# 첫번째 인자: 블루프린트의 이름
# 두번째 인자: __name__ (파이썬 모듈의 이름)
# template_folder: 이 블루프린트가 사용할 템플릿 파일이 위치한 폴더 지정 (app/templates/auth/)
bp = Blueprint('auth', __name__, template_folder='../templates/auth')

@bp.route('/login_test') # /auth/login_test 경로
def login_test():
    # return "Auth Blueprint Test - Login Page Placeholder"
    # templates/auth/login.html 파일을 렌더링 (아직 파일 없음)
    # return render_template('login.html') # 지금은 에러 발생함
    return "Auth Blueprint Test - Login Page Placeholder"

# 여기에 나중에 실제 로그인, 로그아웃, 회원가입(관리자용) 라우트 함수들을 추가합니다.
# @bp.route('/login', methods=['GET', 'POST'])
# def login():
#     # ... 로그인 로직 ...
#     pass

# @bp.route('/logout')
# def logout():
#     # ... 로그아웃 로직 ...
#     pass
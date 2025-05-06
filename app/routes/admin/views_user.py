# app/routes/admin/views_user.py
import datetime
from flask import render_template, redirect, url_for, flash, request
from flask_login import current_user # 현재 로그인 사용자 정보
from . import bp # admin 블루프린트
from app.extensions import db
from app.models import User, Ticket
from app.forms.admin_forms import UserEditForm, UserPasswordResetForm

# 회원 목록 조회
@bp.route('/users')
def list_users():
    page = request.args.get('page', 1, type=int)
    # 검색 기능 (간단 예시 - 이름 또는 연락처로 검색)
    search_term = request.args.get('search', '')
    query = User.query

    if search_term:
        # SQLite는 ILIKE를 직접 지원하지 않으므로 lower 함수와 like 사용 또는 SQLAlchemy의 ilike 사용
        # 여기서는 간단히 like 사용 (대소문자 구분 가능성 있음)
        search_pattern = f"%{search_term}%"
        query = query.filter(User.name.like(search_pattern) | User.phone.like(search_pattern))

    pagination = query.order_by(User.created_at.desc()).paginate(page=page, per_page=10, error_out=False)
    users = pagination.items
    return render_template('user/list_users.html', users=users, pagination=pagination, title="회원 목록", search_term=search_term)

# 회원 상세 정보 조회
@bp.route('/users/<int:user_id>')
def view_user(user_id):
    user = db.session.get(User, user_id)
    if user is None:
        flash('해당 회원을 찾을 수 없습니다.', 'warning')
        return redirect(url_for('admin.list_users'))

    password_reset_form = UserPasswordResetForm()

    # 회원 보유 티켓 미리 정렬
    user_tickets_query = user.tickets.order_by(
        Ticket.is_active.desc(), # Ticket 모델 직접 사용
        Ticket.expiry_date.desc(),
        Ticket.created_at.desc()
    )
    user_tickets = user_tickets_query.all() # 정렬된 리스트 가져오기

    return render_template('user/view_user.html',
                           user=user,
                           title=f"회원 정보: {user.name}",
                           password_reset_form=password_reset_form,
                           user_tickets=user_tickets) # 정렬된 티켓 리스트 전달

# 회원 정보 수정
@bp.route('/users/edit/<int:user_id>', methods=['GET', 'POST'])
def edit_user(user_id):
    user_to_edit = db.session.get(User, user_id)
    if user_to_edit is None:
        flash('해당 회원을 찾을 수 없습니다.', 'warning')
        return redirect(url_for('admin.list_users'))

    form = UserEditForm(current_user_id=current_user.id, editing_user_id=user_to_edit.id)

    if form.validate_on_submit():
        user_to_edit.name = form.name.data
        user_to_edit.memo = form.memo.data
        user_to_edit.is_admin = form.is_admin.data
        try:
            db.session.commit()
            flash(f'회원 "{user_to_edit.name}" 님의 정보가 수정되었습니다.', 'success')
            return redirect(url_for('admin.view_user', user_id=user_to_edit.id))
        except Exception as e:
            db.session.rollback()
            flash(f'회원 정보 수정 중 오류가 발생했습니다: {e}', 'danger')
    elif request.method == 'GET':
        form.name.data = user_to_edit.name
        form.memo.data = user_to_edit.memo
        form.is_admin.data = user_to_edit.is_admin

    return render_template('user/edit_user_form.html', form=form, title="회원 정보 수정", user=user_to_edit)

# 회원 비밀번호 초기화
@bp.route('/users/reset_password/<int:user_id>', methods=['POST'])
def reset_user_password(user_id):
    user_to_reset = db.session.get(User, user_id)
    if user_to_reset is None:
        flash('해당 회원을 찾을 수 없습니다.', 'warning')
        return redirect(url_for('admin.list_users'))

    # 비밀번호 초기화 폼 (실제로는 버튼 클릭으로 바로 실행되므로 폼 유효성 검사는 불필요할 수 있음)
    form = UserPasswordResetForm() # CSRF 토큰 사용을 위해 폼 인스턴스 생성
    if form.validate_on_submit(): # POST 요청이고 CSRF 토큰이 유효하면 실행
        # 자기 자신의 비밀번호를 초기화하는 것을 막는 로직 (선택적)
        # if current_user.id == user_to_reset.id:
        #     flash('자기 자신의 비밀번호는 이 방법으로 초기화할 수 없습니다.', 'danger')
        #     return redirect(url_for('admin.view_user', user_id=user_to_reset.id))

        user_to_reset.set_password('0000')
        user_to_reset.last_login_at = None # 마지막 로그인 기록 초기화 (선택적)
        try:
            db.session.commit()
            flash(f'회원 "{user_to_reset.name}" 님의 비밀번호가 "0000"으로 초기화되었습니다.', 'success')
        except Exception as e:
            db.session.rollback()
            flash(f'비밀번호 초기화 중 오류가 발생했습니다: {e}', 'danger')
    else:
        # 폼 유효성 검증 실패 시 (보통 CSRF 오류)
        for field, errors in form.errors.items():
            for error in errors:
                flash(f"{getattr(form, field).label.text} 필드 오류: {error}", 'danger')

    return redirect(url_for('admin.view_user', user_id=user_to_reset.id))
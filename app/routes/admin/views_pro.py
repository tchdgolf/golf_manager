# app/routes/admin/views_pro.py
from flask import render_template, redirect, url_for, flash, request
from . import bp # admin 블루프린트 객체 가져오기 (__init__.py 에서 정의)
from app.extensions import db
from app.models import Pro
from app.forms.admin_forms import ProForm

# 프로 목록 조회
@bp.route('/pros')
def list_pros():
    page = request.args.get('page', 1, type=int)
    per_page = 10 # 페이지당 보여줄 프로 수 (조절 가능)
    pagination = Pro.query.order_by(Pro.name.asc()).paginate(page=page, per_page=per_page, error_out=False)
    pros = pagination.items
    return render_template('pro/list_pros.html', pros=pros, pagination=pagination, title="프로 목록")

# 프로 추가
@bp.route('/pros/add', methods=['GET', 'POST'])
def add_pro():
    form = ProForm()
    if form.validate_on_submit():
        pro = Pro(name=form.name.data)
        db.session.add(pro)
        try:
            db.session.commit()
            flash(f'프로 "{pro.name}" 님이 성공적으로 추가되었습니다.', 'success')
            return redirect(url_for('admin.list_pros'))
        except Exception as e:
            db.session.rollback()
            flash(f'프로 추가 중 오류가 발생했습니다: {e}', 'danger')
    return render_template('pro/pro_form.html', form=form, title="프로 추가", is_edit=False)

# 프로 수정
@bp.route('/pros/edit/<int:pro_id>', methods=['GET', 'POST'])
def edit_pro(pro_id):
    pro = db.session.get(Pro, pro_id) # SQLAlchemy 2.0 스타일 조회
    if pro is None:
        flash('해당 프로를 찾을 수 없습니다.', 'warning')
        return redirect(url_for('admin.list_pros'))

    # 수정 시에는 original_name 을 폼에 전달 (중복 검사용)
    form = ProForm(original_name=pro.name)

    if form.validate_on_submit():
        pro.name = form.name.data
        try:
            db.session.commit()
            flash(f'프로 "{pro.name}" 님의 정보가 수정되었습니다.', 'success')
            return redirect(url_for('admin.list_pros'))
        except Exception as e:
            db.session.rollback()
            flash(f'프로 정보 수정 중 오류가 발생했습니다: {e}', 'danger')
    elif request.method == 'GET':
        # GET 요청 시, 현재 프로 이름으로 폼 필드 채우기
        form.name.data = pro.name

    return render_template('pro/pro_form.html', form=form, title="프로 수정", pro=pro, is_edit=True)

# 프로 삭제
@bp.route('/pros/delete/<int:pro_id>', methods=['POST']) # GET 대신 POST 로 변경 (CSRF 보호 활용)
def delete_pro(pro_id):
    pro = db.session.get(Pro, pro_id)
    if pro is None:
        flash('해당 프로를 찾을 수 없습니다.', 'warning')
        return redirect(url_for('admin.list_pros'))

    # TODO: 삭제 전, 해당 프로와 연결된 티켓이나 예약이 있는지 확인하는 로직 추가 필요
    # if Ticket.query.filter_by(pro_id=pro_id).first() or Booking.query.filter_by(pro_id=pro_id).first():
    #     flash(f'"{pro.name}" 프로는 사용 중인 이용권 또는 예약이 있어 삭제할 수 없습니다.', 'danger')
    #     return redirect(url_for('admin.list_pros'))

    try:
        pro_name = pro.name # 삭제 메시지용 이름 저장
        db.session.delete(pro)
        db.session.commit()
        flash(f'프로 "{pro_name}" 님이 삭제되었습니다.', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'프로 삭제 중 오류가 발생했습니다: {e}', 'danger')

    return redirect(url_for('admin.list_pros'))
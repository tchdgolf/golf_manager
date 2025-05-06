# app/routes/admin/views_booth.py
from flask import render_template, redirect, url_for, flash, request
from . import bp # admin 블루프린트 객체
from app.extensions import db
from app.models import Booth
from app.models.enums import BoothSystemType, BoothStatus # Enum 필요시 사용
from app.forms.admin_forms import BoothForm

# 타석 목록 조회
@bp.route('/booths')
def list_booths():
    page = request.args.get('page', 1, type=int)
    per_page = 10 # 페이지당 타석 수
    pagination = Booth.query.order_by(Booth.name.asc()).paginate(page=page, per_page=per_page, error_out=False)
    booths = pagination.items
    return render_template('booth/list_booths.html', booths=booths, pagination=pagination, title="타석 목록")

# 타석 추가
@bp.route('/booths/add', methods=['GET', 'POST'])
def add_booth():
    form = BoothForm()
    if form.validate_on_submit():
        booth = Booth(
            name=form.name.data,
            system_type=form.system_type.data, # Enum 값으로 저장됨
            is_available=form.is_available.data,
            memo=form.memo.data,
            current_status=BoothStatus.AVAILABLE # 초기 상태는 사용 가능으로 설정
        )
        db.session.add(booth)
        try:
            db.session.commit()
            flash(f'타석 "{booth.name}" 이(가) 성공적으로 추가되었습니다.', 'success')
            return redirect(url_for('admin.list_booths'))
        except Exception as e:
            db.session.rollback()
            flash(f'타석 추가 중 오류가 발생했습니다: {e}', 'danger')
    return render_template('booth/booth_form.html', form=form, title="타석 추가", is_edit=False)

# 타석 수정
@bp.route('/booths/edit/<int:booth_id>', methods=['GET', 'POST'])
def edit_booth(booth_id):
    booth = db.session.get(Booth, booth_id)
    if booth is None:
        flash('해당 타석을 찾을 수 없습니다.', 'warning')
        return redirect(url_for('admin.list_booths'))

    form = BoothForm(original_name=booth.name) # 폼 초기화는 그대로

    if form.validate_on_submit():
        booth.name = form.name.data
        booth.system_type = form.system_type.data # POST 요청 시에는 폼에서 값을 가져옴
        booth.is_available = form.is_available.data
        booth.memo = form.memo.data
        try:
            db.session.commit()
            flash(f'타석 "{booth.name}" 의 정보가 수정되었습니다.', 'success')
            return redirect(url_for('admin.list_booths'))
        except Exception as e:
            db.session.rollback()
            flash(f'타석 정보 수정 중 오류가 발생했습니다: {e}', 'danger')
    elif request.method == 'GET':
        # GET 요청 시, 현재 타석 정보로 폼 필드 채우기
        form.name.data = booth.name
        # form.system_type.data = booth.system_type  # <<< 이 줄 추가!
        form.system_type.data = booth.system_type.name  # <<< Enum 멤버의 'value' (문자열)를 할당하도록 변경!
        form.is_available.data = booth.is_available
        form.memo.data = booth.memo

    return render_template('booth/booth_form.html', form=form, title="타석 수정", booth=booth, is_edit=True)


# 타석 삭제
@bp.route('/booths/delete/<int:booth_id>', methods=['POST'])
def delete_booth(booth_id):
    booth = db.session.get(Booth, booth_id)
    if booth is None:
        flash('해당 타석을 찾을 수 없습니다.', 'warning')
        return redirect(url_for('admin.list_booths'))

    # TODO: 삭제 전, 해당 타석과 연결된 예약(Booking)이 있는지 확인하는 로직 추가 필요
    # if Booking.query.filter_by(booth_id=booth_id).filter(Booking.status == BookingStatus.SCHEDULED).first():
    #     flash(f'"{booth.name}" 타석은 예정된 예약이 있어 삭제할 수 없습니다.', 'danger')
    #     return redirect(url_for('admin.list_booths'))

    try:
        booth_name = booth.name
        db.session.delete(booth)
        db.session.commit()
        flash(f'타석 "{booth_name}" 이(가) 삭제되었습니다.', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'타석 삭제 중 오류가 발생했습니다: {e}', 'danger')

    return redirect(url_for('admin.list_booths'))
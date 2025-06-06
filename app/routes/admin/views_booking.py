# app/routes/admin/views_booking.py
import datetime
from flask import render_template, redirect, url_for, flash, request, jsonify
from . import bp # admin 블루프린트
from app.extensions import db
from app.models import User, Booth, Pro, Ticket, Booking # 필요한 모델 임포트
from app.models.enums import BookingType, BookingStatus # Enum 임포트
# from app.forms.admin_forms import BookingForm, BookingFilterForm # 나중에 만들 폼 임포트
from app.services.booking_service import create_booking, cancel_booking # 서비스 함수 임포트
from sqlalchemy import or_ # 검색용
from app.forms.admin_forms import BookingForm # BookingForm 임포트



# 예약 목록 조회 (기본 틀)
@bp.route('/bookings')
def list_bookings():
    # TODO: 필터링 및 페이지네이션 구현
    page = request.args.get('page', 1, type=int)
    per_page = 15

    # 예시: 모든 예약을 최신순으로
    pagination = Booking.query.order_by(Booking.start_time.desc()).paginate(page=page, per_page=per_page, error_out=False)
    bookings = pagination.items

    return render_template('booking/list_bookings.html',
                           bookings=bookings,
                           pagination=pagination,
                           title="전체 예약 목록",
                           BookingStatus=BookingStatus)

# 관리자 예약 생성 페이지 (GET)
@bp.route('/bookings/create', methods=['GET'])
def create_booking_form():
    form = BookingForm() # 폼 객체 생성

    users = User.query.order_by(User.name).all()
    booths = Booth.query.filter_by(is_available=True).order_by(Booth.name).all()
    pros = Pro.query.order_by(Pro.name).all()

    # SelectField choices 동적 할당 (이제 users, booths, pros 사용 가능)
    form.user_id.choices = [('', '--- 회원 선택 ---')] + [(u.id, f"{u.name} ({u.phone})") for u in users]
    form.booth_id.choices = [('', '--- 타석 선택 ---')] + [(b.id, b.name) for b in booths]
    form.pro_id.choices = [('', '--- 프로 선택 (레슨 시) ---')] + [(p.id, p.name) for p in pros]

    # 오늘 날짜를 시작 날짜 기본값으로 설정 (선택적)
    if not form.start_date.data:
         form.start_date.data = datetime.date.today()

    return render_template('booking/create_booking_form.html',
                           title="관리자 예약 생성",
                           form=form,
                           BookingType=BookingType) # JS에서 비교 위해 전달


# 관리자 예약 생성 처리 (POST)
@bp.route('/bookings/create', methods=['POST'])
def create_booking_post():
    form = BookingForm() # POST 데이터로 폼 인스턴스 생성

    # SelectField choices 다시 로드 (유효성 검증 실패 시 폼 다시 보여줄 때 필요)
    form.user_id.choices = [('', '--- 회원 선택 ---')] + [(u.id, f"{u.name} ({u.phone})") for u in User.query.order_by(User.name).all()]
    form.booth_id.choices = [('', '--- 타석 선택 ---')] + [(b.id, b.name) for b in Booth.query.filter_by(is_available=True).order_by(Booth.name).all()]
    form.pro_id.choices = [('', '--- 프로 선택 (레슨 시) ---')] + [(p.id, p.name) for p in Pro.query.order_by(Pro.name).all()]

    if form.validate_on_submit():
        # --- ▼ 날짜 및 시간 데이터 조합 ▼ ---
        try:
            start_dt = datetime.datetime.combine(
                form.start_date.data,
                datetime.time(hour=form.start_hour.data, minute=form.start_minute.data)
            )
            end_dt = start_dt + datetime.timedelta(minutes=form.duration.data)
        except Exception as e:
            flash(f"날짜 또는 시간 값 오류: {e}", "danger")
            return render_template('booking/create_booking_form.html', title="관리자 예약 생성", form=form, BookingType=BookingType)
        # --- ▲ 날짜 및 시간 데이터 조합 끝 ▲ ---
        # 폼 데이터 가져오기
        user_id = form.user_id.data
        booth_id = form.booth_id.data
        pro_id = form.pro_id.data
        booking_type = form.booking_type.data
        lesson_count_to_use = form.lesson_count_to_use.data or 1
        memo = form.memo.data

        # create_booking 서비스 함수 호출
        success, message, new_booking = create_booking(
            user_id=user_id,
            booth_id=booth_id,
            pro_id=pro_id,
            start_time=start_dt,
            end_time=end_dt,
            booking_type=booking_type,
            memo=memo,
            lesson_count_to_use=lesson_count_to_use if booking_type == BookingType.LESSON else 0
        )

        if success:
            flash(message, 'success')
            # 생성된 예약 상세 페이지 또는 예약 목록으로 리디렉션
            return redirect(url_for('admin.view_booking', booking_id=new_booking.id))
        else:
            flash(message, 'danger')
            # 실패 시 폼 다시 렌더링 -> 여기서 BookingType 전달 필요!
            return render_template('booking/create_booking_form.html',
                                   title="관리자 예약 생성",
                                   form=form,
                                   BookingType=BookingType) # <<< 여기!
    else:
        flash("입력 값을 확인해주세요.", "warning")
        # 폼 유효성 검증 실패 시 폼 다시 렌더링 -> 여기서 BookingType 전달 필요!
        return render_template('booking/create_booking_form.html',
                               title="관리자 예약 생성",
                               form=form,
                               BookingType=BookingType) # <<< 여기!



# 예약 상세 보기 (필요시)
@bp.route('/bookings/<int:booking_id>')
def view_booking(booking_id):
    booking = db.session.get(Booking, booking_id)
    if not booking:
        flash("예약 정보를 찾을 수 없습니다.", "warning")
        return redirect(url_for('admin.list_bookings'))
    return render_template('booking/view_booking.html',
                           booking=booking,
                           title="예약 상세 정보",
                           BookingStatus=BookingStatus) # <<< BookingStatus 전달 추가!


# 예약 취소 처리 (관리자)
@bp.route('/bookings/cancel/<int:booking_id>', methods=['POST'])
def cancel_booking_admin(booking_id):
    success, message = cancel_booking(booking_id, cancelled_by_admin=True)
    if success:
        flash(message, 'success')
    else:
        flash(message, 'danger')
    # 이전 페이지 또는 예약 목록으로 리디렉션 (referer 사용 가능)
    return redirect(request.referrer or url_for('admin.list_bookings'))
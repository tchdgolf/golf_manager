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
                           bookings=bookings, pagination=pagination,
                           title="전체 예약 목록")

# 관리자 예약 생성 페이지 (GET)
@bp.route('/bookings/create', methods=['GET'])
def create_booking_form():
    # TODO: 예약 생성 폼(BookingForm) 정의 및 전달
    # 필요한 데이터 로딩 (사용자 목록, 타석 목록, 프로 목록 등)
    users = User.query.order_by(User.name).all()
    booths = Booth.query.order_by(Booth.name).all()
    pros = Pro.query.order_by(Pro.name).all()
    # form = BookingForm() # 폼 객체 생성

    return render_template('booking/create_booking_form.html',
                           title="관리자 예약 생성",
                           # form=form, # 폼 전달
                           users=users, booths=booths, pros=pros) # Select 필드용 데이터 전달

# 관리자 예약 생성 처리 (POST)
@bp.route('/bookings/create', methods=['POST'])
def create_booking_post():
    # TODO: 폼 데이터 받기 및 유효성 검증
    # TODO: create_booking 서비스 함수 호출
    # TODO: 성공/실패 처리 및 리디렉션

    flash("관리자 예약 생성 처리 로직 구현 필요", "info")
    return redirect(url_for('admin.list_bookings'))


# 예약 상세 보기 (필요시)
@bp.route('/bookings/<int:booking_id>')
def view_booking(booking_id):
    booking = db.session.get(Booking, booking_id)
    if not booking:
        flash("예약 정보를 찾을 수 없습니다.", "warning")
        return redirect(url_for('admin.list_bookings'))
    return render_template('booking/view_booking.html', booking=booking, title="예약 상세 정보")


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
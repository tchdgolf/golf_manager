# app/services/booking_service.py
import datetime
from app.extensions import db
from app.models import User, Booth, Ticket, Booking, Pro, TicketTemplate
from app.models.enums import BookingType, BookingStatus, BoothStatus
from app.models.ticket_template import TicketCategory
from sqlalchemy import and_, or_
from .holding_service import recalculate_master_expiry_date


# --- 예약 가능 여부 확인 관련 함수 ---

def is_booth_available(booth_id: int, start_time: datetime.datetime, end_time: datetime.datetime, exclude_booking_id: int = None) -> bool:
    """주어진 시간에 해당 타석이 예약 가능한지 확인 (다른 예약과 겹치는지)"""
    # TODO: 타석의 is_available, current_status (OFFLINE, MAINTENANCE 등) 확인 로직 추가 필요
    booth = db.session.get(Booth, booth_id)
    if not booth or not booth.is_available or booth.current_status != BoothStatus.AVAILABLE:
         # 실제 운영 시에는 타석 상태 세분화 (점검중 등)
         return False # 예약 불가 타석

    # 겹치는 예약 확인 (SCHEDULED 또는 CHECKED_IN 상태 등)
    overlapping_booking_query = Booking.query.filter(
        Booking.booth_id == booth_id,
        Booking.status.in_([BookingStatus.SCHEDULED]), # '예약 확정' 상태만 확인 (향후 CHECKED_IN 등 추가)
        # 기존 예약 종료시간 > 새 예약 시작시간 AND 기존 예약 시작시간 < 새 예약 종료시간
        Booking.end_time > start_time,
        Booking.start_time < end_time
    )
    # 예약 수정 시 자기 자신은 제외
    if exclude_booking_id:
        overlapping_booking_query = overlapping_booking_query.filter(Booking.id != exclude_booking_id)

    return overlapping_booking_query.first() is None

def find_available_ticket_for_taseok(user: User, booking_start_time: datetime.datetime) -> Ticket | None:
    """타석 이용에 사용할 수 있는 유효한 티켓을 찾습니다 (기간권 우선, 다음 횟수권)"""
    booking_date = booking_start_time.date()

    # 1. 유효한 기간권 검색 (시작일 <= 예약일 <= 만료일)
    valid_period_ticket = Ticket.query.filter(
        Ticket.user_id == user.id,
        Ticket.is_active == True,
        or_(Ticket.ticket_template.has(TicketTemplate.category == TicketCategory.PERIOD),
            Ticket.ticket_template.has(TicketTemplate.category == TicketCategory.COMBO)), # 기간권 또는 종합권
        Ticket.start_date <= booking_date,
        Ticket.expiry_date >= booking_date
    ).order_by(Ticket.expiry_date.asc()).first() # 만료일 임박한 것부터 사용? 정책 결정 필요

    if valid_period_ticket:
        return valid_period_ticket

    # 2. 유효한 횟수권/쿠폰 검색 (잔여 횟수 > 0, 시작일 <= 예약일 <= 만료일)
    valid_count_ticket = Ticket.query.filter(
        Ticket.user_id == user.id,
        Ticket.is_active == True,
        or_(Ticket.ticket_template.has(TicketTemplate.category == TicketCategory.COUNT),
            Ticket.ticket_template.has(TicketTemplate.category == TicketCategory.COUPON)), # 횟수권 또는 쿠폰
        Ticket.remaining_taseok_count > 0,
        Ticket.start_date <= booking_date,
        Ticket.expiry_date >= booking_date # 횟수권도 만료일 체크
    ).order_by(Ticket.expiry_date.asc()).first() # 만료일 임박한 것부터 사용

    return valid_count_ticket

def find_available_ticket_for_lesson(user: User, booking_start_time: datetime.datetime) -> tuple[Ticket | None, bool]:
    """
    레슨 이용에 사용할 수 있는 방법을 찾습니다 (쿠폰 우선, 다음 통합 레슨 횟수).

    :return: (사용할 쿠폰 티켓 객체 또는 None, 통합 레슨 횟수 사용 가능 여부)
    """
    booking_date = booking_start_time.date()

    # 1. 유효한 쿠폰 레슨 티켓 검색 (잔여 레슨 횟수 > 0, 기간 유효)
    valid_coupon_ticket = Ticket.query.filter(
        Ticket.user_id == user.id,
        Ticket.is_active == True,
        Ticket.ticket_template.has(TicketTemplate.category == TicketCategory.COUPON),
        Ticket.remaining_lesson_count > 0,
        Ticket.start_date <= booking_date,
        Ticket.expiry_date >= booking_date
    ).order_by(Ticket.expiry_date.asc()).first()

    if valid_coupon_ticket:
        # 쿠폰 사용 시에는 타석 횟수도 같이 차감되므로 타석 권한 별도 확인 불필요
        return valid_coupon_ticket, False # 쿠폰 티켓 반환, 통합 레슨 사용 안 함

    # 2. 사용자 통합 레슨 횟수 확인
    can_use_total_lesson = (user.remaining_lesson_total or 0) > 0

    # 쿠폰 티켓이 없고, 통합 레슨 횟수가 있다면 True 반환
    return None, can_use_total_lesson


# --- 예약 생성 관련 함수 ---

def create_booking(user_id: int, booth_id: int, pro_id: int | None,
                   start_time: datetime.datetime, end_time: datetime.datetime,
                   booking_type: BookingType, memo: str = None) -> tuple[bool, str, Booking | None]:
    """
    새로운 예약을 생성합니다.

    :return: (성공 여부, 메시지, 생성된 예약 객체 또는 None)
    """
    user = db.session.get(User, user_id)
    if not user: return False, "사용자를 찾을 수 없습니다.", None

    # 1. 타석 예약 가능 여부 확인
    if not is_booth_available(booth_id, start_time, end_time):
        return False, "선택한 시간에 해당 타석은 예약할 수 없습니다.", None

    # 2. 이용권 및 레슨 가능 여부 확인 및 차감 대상 결정
    used_taseok_ticket = None
    used_lesson_ticket = None # 쿠폰 사용 시 여기에 할당됨
    use_total_lesson_count = False # User.remaining_lesson_total 사용 여부

    if booking_type == BookingType.LESSON:
        # 레슨 예약 시
        coupon_ticket, can_use_total = find_available_ticket_for_lesson(user, start_time)
        if coupon_ticket:
            # 쿠폰 사용: 쿠폰 티켓이 타석+레슨 역할 모두 수행
            used_taseok_ticket = coupon_ticket
            used_lesson_ticket = coupon_ticket
        elif can_use_total:
            # 통합 레슨 횟수 사용: 별도의 타석 이용권 필요
            use_total_lesson_count = True
            used_taseok_ticket = find_available_ticket_for_taseok(user, start_time)
            if not used_taseok_ticket:
                return False, "레슨 예약에 필요한 유효한 타석 이용권이 없습니다.", None
        else:
            # 레슨 사용 불가 (쿠폰도 없고, 통합 횟수도 없음)
            return False, "사용 가능한 레슨 횟수 또는 쿠폰이 없습니다.", None
    else: # BookingType.TASEOK_ONLY
        # 타석만 예약 시
        used_taseok_ticket = find_available_ticket_for_taseok(user, start_time)
        if not used_taseok_ticket:
            return False, "예약에 필요한 유효한 타석 이용권이 없습니다.", None
        # 타석만 이용 시 쿠폰 레슨 티켓은 사용할 수 없도록 추가 검증 필요 (find_available_ticket_for_taseok 에서 처리하거나 여기서)
        if used_taseok_ticket.ticket_template and used_taseok_ticket.ticket_template.category == TicketCategory.COUPON:
             return False, "쿠폰 레슨 이용권으로는 타석만 예약할 수 없습니다.", None


    # 3. 예약 객체 생성
    try:
        new_booking = Booking(
            user_id=user_id,
            booth_id=booth_id,
            pro_id=pro_id if booking_type == BookingType.LESSON else None, # 레슨 예약 시에만 프로 ID 저장
            booking_type=booking_type,
            start_time=start_time,
            end_time=end_time,
            status=BookingStatus.SCHEDULED,
            memo=memo,
            used_taseok_ticket_id=used_taseok_ticket.id if used_taseok_ticket else None,
            used_lesson_ticket_id=used_lesson_ticket.id if used_lesson_ticket else None # 쿠폰 사용 시에만 값 존재
        )
        # duration_minutes는 __init__에서 자동 계산됨

        # 4. 이용권 및 레슨 횟수 차감
        # 타석 횟수 차감 (횟수권 또는 쿠폰 사용 시)
        if used_taseok_ticket and used_taseok_ticket.remaining_taseok_count is not None:
            if used_taseok_ticket.remaining_taseok_count > 0:
                used_taseok_ticket.remaining_taseok_count -= 1
                used_taseok_ticket.update_status() # 소진 여부 등 상태 업데이트
                db.session.add(used_taseok_ticket)
            else:
                # 이 경우는 find_available... 에서 걸러졌어야 함
                raise Exception("사용 가능한 타석 횟수가 없습니다.")

        # 레슨 횟수 차감
        if booking_type == BookingType.LESSON:
            if used_lesson_ticket: # 쿠폰 사용 시
                if used_lesson_ticket.remaining_lesson_count is not None and used_lesson_ticket.remaining_lesson_count > 0:
                    used_lesson_ticket.remaining_lesson_count -= 1
                    used_lesson_ticket.update_status() # 레슨 횟수 소진 여부도 확인
                    db.session.add(used_lesson_ticket)
                else:
                    raise Exception("사용 가능한 쿠폰 레슨 횟수가 없습니다.")
            elif use_total_lesson_count: # 통합 레슨 횟수 사용 시
                if user.remaining_lesson_total > 0:
                    user.remaining_lesson_total -= 1
                    db.session.add(user)
                else:
                    raise Exception("사용 가능한 통합 레슨 횟수가 없습니다.")

        db.session.add(new_booking)
        db.session.commit()

        return True, "예약이 성공적으로 완료되었습니다.", new_booking

    except Exception as e:
        db.session.rollback()
        print(f"Error creating booking: {e}")
        return False, f"예약 생성 중 오류가 발생했습니다: {e}", None


# --- 예약 취소 관련 함수 ---

def cancel_booking(booking_id: int, cancelled_by_admin: bool = False) -> tuple[bool, str]:
    """
    예약을 취소하고 사용된 횟수를 롤백합니다.

    :param booking_id: 취소할 예약 ID
    :param cancelled_by_admin: 관리자에 의한 취소 여부
    :return: (성공 여부, 메시지)
    """
    booking = db.session.get(Booking, booking_id)
    if not booking: return False, "예약 정보를 찾을 수 없습니다."

    # 이미 완료되었거나 다른 사유로 취소된 예약은 취소 불가
    if booking.status not in [BookingStatus.SCHEDULED]: # '예약 확정' 상태만 취소 가능 (정책 확인 필요)
        return False, f"'{booking.status.value}' 상태의 예약은 취소할 수 없습니다."

    try:
        # 1. 예약 상태 변경
        original_status = booking.status
        booking.status = BookingStatus.CANCELLED_ADMIN if cancelled_by_admin else BookingStatus.CANCELLED_USER

        # 2. 횟수 롤백
        # 타석 횟수 롤백 (차감되었던 티켓이 있다면)
        if booking.used_taseok_ticket_id:
            taseok_ticket = db.session.get(Ticket, booking.used_taseok_ticket_id)
            if taseok_ticket and taseok_ticket.remaining_taseok_count is not None:
                 # 이미 최대 횟수거나 하면 롤백하지 않을 수 있음 (정책 필요)
                 if taseok_ticket.total_taseok_count is None or taseok_ticket.remaining_taseok_count < taseok_ticket.total_taseok_count:
                    taseok_ticket.remaining_taseok_count += 1
                    taseok_ticket.update_status() # 상태 업데이트 (is_used_up 등 변경 가능)
                    db.session.add(taseok_ticket)

        # 레슨 횟수 롤백
        if booking.booking_type == BookingType.LESSON:
            if booking.used_lesson_ticket_id: # 쿠폰 사용 취소
                lesson_ticket = db.session.get(Ticket, booking.used_lesson_ticket_id)
                if lesson_ticket and lesson_ticket.remaining_lesson_count is not None:
                    if lesson_ticket.total_lesson_count is None or lesson_ticket.remaining_lesson_count < lesson_ticket.total_lesson_count:
                        lesson_ticket.remaining_lesson_count += 1
                        lesson_ticket.update_status()
                        db.session.add(lesson_ticket)
            else: # 통합 레슨 횟수 사용 취소
                user = booking.user
                if user:
                    user.remaining_lesson_total = (user.remaining_lesson_total or 0) + 1
                    db.session.add(user)

        db.session.add(booking)
        db.session.commit()
        return True, "예약이 성공적으로 취소되었습니다."

    except Exception as e:
        db.session.rollback()
        print(f"Error cancelling booking: {e}")
        return False, f"예약 취소 중 오류가 발생했습니다: {e}"

# --- 예약 조회 관련 함수 (필요시 추가) ---
# def get_bookings_by_date(date): ...
# def get_user_bookings(user_id): ...
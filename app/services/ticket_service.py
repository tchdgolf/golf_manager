# app/services/ticket_service.py
from app.extensions import db
# from app.models import Ticket, User, Booking # <<< Booking 임포트 주석 처리
from app.models import Ticket, User # Booking 제외하고 임포트
# from app.models.enums import BookingStatus # Booking 모델 구현 후 필요하므로 주석 처리
from .holding_service import recalculate_master_expiry_date

def delete_ticket_by_id(ticket_id: int) -> tuple[bool, str]:
    """
    주어진 ID의 티켓을 삭제하고 관련 데이터를 업데이트합니다.
    """
    ticket = db.session.get(Ticket, ticket_id)
    if not ticket:
        return False, "해당 이용권을 찾을 수 없습니다."

    user = ticket.user
    if not user:
         return False, "이용권에 연결된 사용자 정보를 찾을 수 없습니다."

    # --- ▼ 예약 확인 로직 (Booking 모델 없으므로 주석 처리 유지) ▼ ---
    # has_scheduled_booking = Booking.query.filter(
    #     (Booking.primary_ticket_id == ticket_id) | \
    #     (Booking.used_taseok_ticket_id == ticket_id) | \
    #     (Booking.used_lesson_ticket_id == ticket_id),
    #     Booking.status == BookingStatus.SCHEDULED
    # ).first()
    #
    # if has_scheduled_booking:
    #     return False, f"..."
    # --- ▲ 예약 확인 로직 끝 ▲ ---


    try:
        # ... (레슨 롤백, 티켓 삭제, 만료일 재계산 등 기존 로직) ...
        lessons_to_rollback = ticket.remaining_lesson_count or 0
        if lessons_to_rollback > 0:
            user.remaining_lesson_total = max(0, (user.remaining_lesson_total or 0) - lessons_to_rollback)

        ticket_name = ticket.name
        user_id = user.id # 리디렉션용

        db.session.delete(ticket)

        recalculate_master_expiry_date(user)
        db.session.add(user)

        db.session.commit()

        return True, f"이용권 '{ticket_name}'(ID: {ticket_id})이(가) 성공적으로 삭제되었습니다."


    except Exception as e:
        db.session.rollback()
        print(f"Error deleting ticket: {e}")
        return False, f"이용권 삭제 중 오류가 발생했습니다: {e}"
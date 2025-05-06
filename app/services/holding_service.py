# app/services/holding_service.py
import datetime
from app.extensions import db
from app.models import Ticket, Holding, User # 필요한 모델 임포트
from sqlalchemy import and_ # 겹침 검사용

# User 최종 만료일 재계산 함수 (user_service.py로 옮기는 것이 더 적합할 수 있음)
# 여기서는 임시로 여기에 정의하거나, user_service를 import해서 사용
# from . import user_service # 만약 user_service가 있다면

def recalculate_master_expiry_date(user: User):
    """사용자의 모든 활성 티켓 중 가장 늦은 만료일을 찾아 master_expiry_date를 업데이트합니다."""
    if not user:
        return

    latest_expiry = None
    active_tickets = user.tickets.filter_by(is_active=True).all() # is_active 상태인 티켓만 고려

    for ticket in active_tickets:
        if ticket.expiry_date:
            if latest_expiry is None or ticket.expiry_date > latest_expiry:
                latest_expiry = ticket.expiry_date

    user.master_expiry_date = latest_expiry
    # db.session.add(user) # user 객체는 이미 세션에 있을 수 있음
    # db.session.commit() # 호출하는 쪽에서 커밋하는 것이 좋음


def add_new_holding(ticket_id: int, start_date: datetime.date, end_date: datetime.date, reason: str = None) -> tuple[bool, str, Holding | None]:
    """
    새로운 홀딩을 추가하고 관련 데이터를 업데이트합니다.

    :param ticket_id: 홀딩을 추가할 티켓 ID
    :param start_date: 홀딩 시작일
    :param end_date: 홀딩 종료일
    :param reason: 홀딩 사유
    :return: (성공 여부, 메시지, 생성된 홀딩 객체 또는 None)
    """
    ticket = db.session.get(Ticket, ticket_id)
    if not ticket:
        return False, "해당 이용권을 찾을 수 없습니다.", None

    # 1. 홀딩 기간 겹침 검사
    overlapping_holding = Holding.query.filter(
        Holding.ticket_id == ticket_id,
        # 기존 홀딩의 종료일 >= 새 홀딩의 시작일 AND 기존 홀딩의 시작일 <= 새 홀딩의 종료일
        Holding.end_date >= start_date,
        Holding.start_date <= end_date
    ).first()

    if overlapping_holding:
        return False, f"해당 기간 ({start_date} ~ {end_date})에 이미 홀딩(ID: {overlapping_holding.id})이 존재합니다.", None

    # 2. Holding 객체 생성 및 저장
    try:
        new_holding = Holding(
            ticket_id=ticket_id,
            start_date=start_date,
            end_date=end_date,
            reason=reason
        )
        # duration_days는 Holding.__init__ 에서 자동 계산됨
        if new_holding.duration_days <= 0:
             return False, "홀딩 기간은 최소 1일 이상이어야 합니다.", None

        db.session.add(new_holding)

        # 3. Ticket 만료일 연장 (만료일이 있는 경우에만)
        original_expiry_date = ticket.expiry_date
        if original_expiry_date:
            ticket.expiry_date = original_expiry_date + datetime.timedelta(days=new_holding.duration_days)

        # 4. User 최종 만료일 재계산
        user = ticket.user
        if user:
            # 변경된 ticket.expiry_date를 반영하여 재계산
            recalculate_master_expiry_date(user)
            db.session.add(user) # 변경 사항 세션에 추가

        db.session.add(ticket) # 변경 사항 세션에 추가
        db.session.commit() # 모든 변경사항 한 번에 커밋

        return True, f"홀딩(ID: {new_holding.id})이 성공적으로 추가되었습니다.", new_holding

    except Exception as e:
        db.session.rollback()
        print(f"Error adding holding: {e}") # 로깅 라이브러리 사용 권장
        return False, f"홀딩 추가 중 오류가 발생했습니다: {e}", None


def delete_existing_holding(holding_id: int) -> tuple[bool, str]:
    """
    기존 홀딩을 삭제하고 관련 데이터를 업데이트합니다.

    :param holding_id: 삭제할 홀딩 ID
    :return: (성공 여부, 메시지)
    """
    holding = db.session.get(Holding, holding_id)
    if not holding:
        return False, "해당 홀딩 정보를 찾을 수 없습니다."

    ticket = holding.ticket
    if not ticket:
         # 이론적으로 발생하기 어려움
        return False, "홀딩과 연결된 이용권을 찾을 수 없습니다."

    try:
        holding_duration = holding.duration_days
        db.session.delete(holding)

        # 2. Ticket 만료일 복구 (만료일이 있는 경우에만)
        original_expiry_date = ticket.expiry_date
        if original_expiry_date and holding_duration > 0:
            ticket.expiry_date = original_expiry_date - datetime.timedelta(days=holding_duration)

        # 3. User 최종 만료일 재계산
        user = ticket.user
        if user:
            recalculate_master_expiry_date(user)
            db.session.add(user)

        db.session.add(ticket)
        db.session.commit()

        return True, f"홀딩(ID: {holding_id})이 성공적으로 삭제되었습니다."

    except Exception as e:
        db.session.rollback()
        print(f"Error deleting holding: {e}") # 로깅
        return False, f"홀딩 삭제 중 오류가 발생했습니다: {e}"

# 홀딩 수정 함수는 필요시 추가 (delete 후 add 하는 방식도 가능)
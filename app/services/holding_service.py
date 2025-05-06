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
    
    # --- ▼ 홀딩 기간 유효성 검사 추가 ▼ ---
    # 1. 홀딩 시작일 검사: 티켓 시작일 이후여야 함
    if start_date < ticket.start_date:
        return False, f"홀딩 시작일({start_date})은 이용권 시작일({ticket.start_date}) 이후여야 합니다.", None

    # 2. 홀딩 종료일 검사: 티켓 만료일 이내여야 함 (만료일이 있는 경우)
    if ticket.expiry_date and end_date > ticket.expiry_date:
         # 주의: 이미 연장된 만료일 기준으로 비교해야 할까? 아니면 홀딩 적용 전 만료일?
         # 일반적으로는 홀딩 적용 전/후 관계없이 '현재 시점의' 만료일을 넘어서는 홀딩은 이상함.
         # 하지만 정책적으로 만료일 이후까지 홀딩이 필요하다면 이 검사를 제거하거나 수정해야 함.
         # 여기서는 현재 만료일보다 이후 날짜로 홀딩 종료일을 설정할 수 없도록 제한.
        return False, f"홀딩 종료일({end_date})은 현재 이용권 만료일({ticket.expiry_date}) 이전이어야 합니다.", None

    # 3. 홀딩 기간 자체 검증 (종료일 >= 시작일) - HoldingForm 에서 이미 검증하지만 여기서도 확인 가능
    if end_date < start_date:
        return False, "홀딩 종료일은 시작일보다 이전일 수 없습니다.", None
    # --- ▲ 홀딩 기간 유효성 검사 끝 ▲ ---

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

def update_existing_holding(holding_id: int, new_start_date: datetime.date, new_end_date: datetime.date, new_reason: str = None) -> tuple[bool, str]:
    """
    기존 홀딩 정보를 수정하고 관련 데이터를 업데이트합니다.

    :param holding_id: 수정할 홀딩 ID
    :param new_start_date: 새로운 홀딩 시작일
    :param new_end_date: 새로운 홀딩 종료일
    :param new_reason: 새로운 홀딩 사유
    :return: (성공 여부, 메시지)
    """
    holding = db.session.get(Holding, holding_id)
    if not holding:
        return False, "해당 홀딩 정보를 찾을 수 없습니다."

    ticket = holding.ticket
    if not ticket:
        return False, "홀딩과 연결된 이용권을 찾을 수 없습니다."

    # 수정 전 홀딩 기간 기록
    original_duration = holding.duration_days

    # --- ▼ 유효성 검사 ▼ ---
    # 1. 수정하려는 기간 유효성 검사
    if new_end_date < new_start_date:
        return False, "홀딩 종료일은 시작일보다 이전일 수 없습니다."

    # 2. 티켓 유효 기간 내 검사 (add_new_holding과 동일)
    if new_start_date < ticket.start_date:
        return False, f"홀딩 시작일({new_start_date})은 이용권 시작일({ticket.start_date}) 이후여야 합니다."
    # 만료일 비교는 좀 더 신중해야 함. 수정 시에는 현재 만료일을 기준으로 비교하는 것이 맞을 수 있음.
    if ticket.expiry_date and new_end_date > ticket.expiry_date + datetime.timedelta(days=original_duration): # 복구될 만료일보다 뒤인지? 복잡.. 일단 현재 기준
        # 홀딩 기간 변경으로 인해 최종 만료일이 현재 티켓 만료일을 넘어서는 경우를 어떻게 처리할지 정책 필요.
        # 여기서는 일단 현재 만료일 + 원래 홀딩 기간을 넘어서지 못하게 제한 (보수적 접근)
        pass # 일단 검증 보류

    # 3. 다른 홀딩과의 겹침 검사 (수정 대상 홀딩 제외)
    overlapping_holding = Holding.query.filter(
        Holding.ticket_id == ticket.id,
        Holding.id != holding_id, # 자기 자신은 제외
        Holding.end_date >= new_start_date,
        Holding.start_date <= new_end_date
    ).first()
    if overlapping_holding:
        return False, f"수정하려는 기간 ({new_start_date} ~ {new_end_date})이 다른 홀딩(ID: {overlapping_holding.id})과 겹칩니다."
    # --- ▲ 유효성 검사 끝 ▲ ---

    try:
        # 홀딩 정보 업데이트
        holding.start_date = new_start_date
        holding.end_date = new_end_date
        holding.reason = new_reason
        holding.calculate_duration() # 새 기간으로 duration_days 재계산
        new_duration = holding.duration_days

        if new_duration <= 0:
             return False, "수정된 홀딩 기간은 최소 1일 이상이어야 합니다."

        # 티켓 만료일 업데이트
        if ticket.expiry_date:
            # 1. 원래 홀딩 기간만큼 만료일을 먼저 복구
            expiry_date_before_update = ticket.expiry_date - datetime.timedelta(days=original_duration)
            # 2. 새로운 홀딩 기간만큼 다시 연장
            ticket.expiry_date = expiry_date_before_update + datetime.timedelta(days=new_duration)
        else:
            # 만료일 없는 티켓은 변경 없음
            pass

        # 사용자 최종 만료일 재계산
        user = ticket.user
        if user:
            recalculate_master_expiry_date(user)
            db.session.add(user)

        db.session.add(holding) # 변경된 홀딩 정보
        db.session.add(ticket) # 변경된 티켓 정보
        db.session.commit()

        return True, f"홀딩(ID: {holding_id}) 정보가 성공적으로 수정되었습니다."

    except Exception as e:
        db.session.rollback()
        print(f"Error updating holding: {e}")
        return False, f"홀딩 수정 중 오류가 발생했습니다: {e}"


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
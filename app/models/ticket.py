# app/models/ticket.py
import datetime
from app.extensions import db
# from .ticket_template import TicketTemplate # TicketTemplate과의 관계 설정 시 필요 (아래에서 추가)
# from .user import User # User와의 관계 설정 시 필요
# from .pro import Pro # Pro와의 관계 설정 시 필요

class Ticket(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False, index=True)
    ticket_template_id = db.Column(db.Integer, db.ForeignKey('ticket_template.id'), nullable=True, index=True) # 어떤 템플릿 기반인지 (템플릿 없이 직접 생성도 가능하도록 nullable)

    name = db.Column(db.String(150), nullable=False) # 실제 발급된 이용권 이름 (예: "홍길동님 3개월권", "기간권-1개월 (레슨 5회)")
    # category = db.Column(db.Enum(TicketCategory)) # template 에서 가져오거나, 직접 설정도 가능하도록 할 수 있음

    issue_date = db.Column(db.Date, nullable=False, default=datetime.date.today) # 발급일
    start_date = db.Column(db.Date, nullable=False) # 이용 시작일
    expiry_date = db.Column(db.Date, nullable=True) # 만료일 (기간권, 횟수권 등) - 홀딩으로 변경 가능

    # 횟수 관련
    total_taseok_count = db.Column(db.Integer, nullable=True) # 총 타석 이용 가능 횟수
    remaining_taseok_count = db.Column(db.Integer, nullable=True) # 남은 타석 이용 횟수
    total_lesson_count = db.Column(db.Integer, nullable=True) # 이 티켓에 포함된 총 레슨 횟수
    remaining_lesson_count = db.Column(db.Integer, nullable=True) # 이 티켓의 남은 레슨 횟수

    pro_id = db.Column(db.Integer, db.ForeignKey('pro.id'), nullable=True) # 담당 프로 (선택 사항)
    price = db.Column(db.Integer, nullable=True) # 실제 판매 가격
    memo = db.Column(db.Text, nullable=True) # 발급 시 메모

    is_active = db.Column(db.Boolean, default=True) # 현재 이용권 활성 상태 (만료/소진 시 비활성화)
    is_used_up = db.Column(db.Boolean, default=False) # 모든 횟수 소진 여부
    is_expired = db.Column(db.Boolean, default=False) # 만료일 경과 여부

    created_at = db.Column(db.DateTime, default=db.func.current_timestamp())
    updated_at = db.Column(db.DateTime, default=db.func.current_timestamp(), onupdate=db.func.current_timestamp())

    # Relationships
    user = db.relationship('User', backref=db.backref('tickets', lazy='dynamic')) # User와는 backref 유지 가능
    ticket_template = db.relationship('TicketTemplate', backref=db.backref('issued_tickets', lazy='dynamic')) # Template과도 backref 유지 가능
    pro = db.relationship('Pro', backref=db.backref('assigned_tickets', lazy='dynamic')) # Pro와도 backref 유지 가능
    holdings = db.relationship(
        'Holding',
        back_populates='ticket', # Holding 모델의 'ticket' 속성과 연결됨을 명시
        lazy='dynamic',
        cascade="all, delete-orphan"
    )
    # bookings_primary = db.relationship('Booking', foreign_keys='Booking.primary_ticket_id', backref='primary_for_ticket', lazy='dynamic') # 예약 시 이 티켓이 주 사용 티켓
    # bookings_taseok = db.relationship('Booking', foreign_keys='Booking.used_taseok_ticket_id', backref='used_for_taseok', lazy='dynamic') # 예약 시 타석 차감용으로 사용
    # bookings_lesson = db.relationship('Booking', foreign_keys='Booking.used_lesson_ticket_id', backref='used_for_lesson', lazy='dynamic') # 예약 시 레슨 차감용으로 사용


    def __repr__(self):
        return f'<Ticket {self.id} - {self.name} (User: {self.user_id})>'

    # 만료 여부 확인 프로퍼티
    @property
    def is_truly_expired(self):
        if self.expiry_date and self.expiry_date < datetime.date.today():
            return True
        return False

    # 소진 여부 확인 프로퍼티
    @property
    def is_truly_used_up(self):
        # 기간권은 횟수 개념이 없음
        if self.total_taseok_count is None and self.total_lesson_count is None:
            return False # 횟수제 아닌 경우 항상 False

        taseok_done = self.total_taseok_count is not None and self.remaining_taseok_count is not None and self.remaining_taseok_count <= 0
        lesson_done = self.total_lesson_count is not None and self.remaining_lesson_count is not None and self.remaining_lesson_count <= 0

        # 타석 횟수와 레슨 횟수가 모두 있는 경우 (예: 쿠폰) 둘 다 소진되어야 함
        if self.total_taseok_count is not None and self.total_lesson_count is not None:
            return taseok_done and lesson_done
        # 타석 횟수만 있는 경우
        elif self.total_taseok_count is not None:
            return taseok_done
        # 레슨 횟수만 있는 경우 (예: 레슨 추가권)
        elif self.total_lesson_count is not None:
            return lesson_done
        return False

    # 현재 사용 가능한 상태인지 확인하는 로직 (상태 업데이트 서비스에서 사용)
    def update_status(self):
        self.is_expired = self.is_truly_expired
        self.is_used_up = self.is_truly_used_up
        if self.is_expired or self.is_used_up:
            self.is_active = False
        else:
            self.is_active = True # 만료/소진 안됐으면 다시 활성화 (홀딩 해제 등 경우)
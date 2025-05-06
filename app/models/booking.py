# app/models/booking.py
import datetime
from app.extensions import db
from .enums import BookingType, BookingStatus # 정의한 Enum 임포트

class Booking(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False, index=True)
    booth_id = db.Column(db.Integer, db.ForeignKey('booth.id'), nullable=False, index=True)
    pro_id = db.Column(db.Integer, db.ForeignKey('pro.id'), nullable=True, index=True) # 레슨 예약 시 담당 프로
    used_lesson_count = db.Column(db.Integer, default=0) # 이 예약에서 사용(차감)된 레슨 횟수

    booking_type = db.Column(db.Enum(BookingType), nullable=False, default=BookingType.TASEOK_ONLY) # 예약 유형
    status = db.Column(db.Enum(BookingStatus), nullable=False, default=BookingStatus.SCHEDULED, index=True) # 예약 상태

    start_time = db.Column(db.DateTime, nullable=False, index=True) # 예약 시작 시간 (날짜 포함)
    end_time = db.Column(db.DateTime, nullable=False) # 예약 종료 시간 (날짜 포함)
    duration_minutes = db.Column(db.Integer) # 예약 시간(분) - 자동 계산

    # 이용권 사용 정보 (어떤 티켓을 사용하여 예약했는지)
    # 예약 시점에는 사용될 티켓 ID만 기록하고, 실제 차감은 이용 완료 시? -> v1.0에서는 예약 확정 시 차감
    # primary_ticket_id = db.Column(db.Integer, db.ForeignKey('ticket.id'), nullable=True) # 주 사용 티켓 (기간권 등)
    used_taseok_ticket_id = db.Column(db.Integer, db.ForeignKey('ticket.id'), nullable=True) # 타석 차감에 사용된 티켓 (횟수권, 쿠폰 등)
    used_lesson_ticket_id = db.Column(db.Integer, db.ForeignKey('ticket.id'), nullable=True) # 레슨 차감에 사용된 티켓 (쿠폰) 또는 null (User.remaining_lesson_total 사용 시)

    memo = db.Column(db.Text, nullable=True) # 예약 관련 메모 (관리자 또는 사용자)
    created_at = db.Column(db.DateTime, default=db.func.current_timestamp())
    updated_at = db.Column(db.DateTime, default=db.func.current_timestamp(), onupdate=db.func.current_timestamp())

    # Relationships
    user = db.relationship('User', backref=db.backref('bookings', lazy='dynamic'))
    booth = db.relationship('Booth', backref=db.backref('bookings', lazy='dynamic'))
    pro = db.relationship('Pro', backref=db.backref('assigned_bookings', lazy='dynamic'))

    # 사용된 티켓과의 관계 설정 (외래 키 이름 명시 필요)
    # primary_ticket = db.relationship('Ticket', foreign_keys=[primary_ticket_id], backref=db.backref('primary_bookings', lazy='dynamic'))
    used_taseok_ticket = db.relationship('Ticket', foreign_keys=[used_taseok_ticket_id], backref=db.backref('taseok_bookings', lazy='dynamic'))
    used_lesson_ticket = db.relationship('Ticket', foreign_keys=[used_lesson_ticket_id], backref=db.backref('lesson_bookings', lazy='dynamic'))


    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.calculate_duration()

    def calculate_duration(self):
        if self.start_time and self.end_time:
            delta = self.end_time - self.start_time
            self.duration_minutes = int(delta.total_seconds() / 60)
        else:
            self.duration_minutes = None

    def __repr__(self):
        return f'<Booking {self.id} User:{self.user_id} Booth:{self.booth_id} Time:{self.start_time}>'
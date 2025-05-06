# app/models/holding.py
import datetime
from app.extensions import db
# from .ticket import Ticket # 이제 이 import는 관계 설정에 직접 사용 안 함

class Holding(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    ticket_id = db.Column(db.Integer, db.ForeignKey('ticket.id'), nullable=False, index=True)
    # user_id 필드는 제거했으므로 주석 유지

    start_date = db.Column(db.Date, nullable=False)
    end_date = db.Column(db.Date, nullable=False)
    reason = db.Column(db.String(255), nullable=True)
    duration_days = db.Column(db.Integer, nullable=False)
    created_at = db.Column(db.DateTime, default=db.func.current_timestamp())

    # Relationship
    # ticket = db.relationship('Ticket', backref=db.backref('holdings', lazy='dynamic', cascade="all, delete-orphan")) # <<< 이 줄 수정 또는 삭제
    # Ticket 모델에서 backref='ticket'으로 정의했으므로 여기서는 관계를 명시적으로 정의할 필요 없음
    # ticket_id 외래 키만으로도 Ticket.holdings.append(holding_obj) 등으로 관계 설정 가능하며,
    # holding_obj.ticket 으로 접근도 가능해짐 (Ticket 모델의 backref 덕분에)

    # 만약 Holding 객체에서 .ticket 속성으로 Ticket 객체에 접근해야 한다면, backref 없이 관계 정의
    ticket = db.relationship('Ticket') # backref 없이 정의


    def __init__(self, ticket_id, start_date, end_date, reason=None):
        self.ticket_id = ticket_id
        self.start_date = start_date
        self.end_date = end_date
        self.reason = reason
        self.calculate_duration()

    def calculate_duration(self):
        if self.start_date and self.end_date and self.start_date <= self.end_date:
            self.duration_days = (self.end_date - self.start_date).days + 1
        else:
            self.duration_days = 0

    def __repr__(self):
        return f'<Holding {self.id} for Ticket {self.ticket_id} ({self.start_date} - {self.end_date})>'
# app/models/holding.py
import datetime
from app.extensions import db
# from .ticket import Ticket # Ticket과의 관계 설정 시 필요

class Holding(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    ticket_id = db.Column(db.Integer, db.ForeignKey('ticket.id'), nullable=False, index=True) # 어떤 티켓에 대한 홀딩인지
    # user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False, index=True) # 개발 노트에는 있었으나, ticket_id로 user 추적 가능

    start_date = db.Column(db.Date, nullable=False) # 홀딩 시작일
    end_date = db.Column(db.Date, nullable=False) # 홀딩 종료일
    reason = db.Column(db.String(255), nullable=True) # 홀딩 사유
    duration_days = db.Column(db.Integer, nullable=False) # 홀딩 기간 (일 수) - 자동 계산
    created_at = db.Column(db.DateTime, default=db.func.current_timestamp())

    # Relationship
    ticket = db.relationship('Ticket', backref=db.backref('holdings', lazy='dynamic', cascade="all, delete-orphan"))
    # user = db.relationship('User', backref=db.backref('holdings_by_user', lazy='dynamic')) # User와의 관계는 Ticket을 통해 간접적으로 연결

    def __init__(self, ticket_id, start_date, end_date, reason=None):
        self.ticket_id = ticket_id
        self.start_date = start_date
        self.end_date = end_date
        self.reason = reason
        self.calculate_duration()

    def calculate_duration(self):
        if self.start_date and self.end_date and self.start_date <= self.end_date:
            self.duration_days = (self.end_date - self.start_date).days + 1 # 종료일 포함
        else:
            self.duration_days = 0

    def __repr__(self):
        return f'<Holding {self.id} for Ticket {self.ticket_id} ({self.start_date} - {self.end_date})>'
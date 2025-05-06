# app/models/ticket_template.py
import enum
from app.extensions import db

class TicketCategory(enum.Enum):
    """이용권 대분류 Enum"""
    PERIOD = "기간권"        # 타석만, 기간제
    COUNT = "횟수권"         # 타석만, 횟수제
    COUPON = "쿠폰 레슨"     # 타석+레슨, 횟수제
    LESSON_ADD = "레슨 추가" # 레슨만, 횟수제 (타석 이용권 별도 필요)
    COMBO = "종합권"         # 기간+레슨

class TicketTemplate(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), unique=True, nullable=False) # 템플릿 이름 (예: "3개월 회원권", "주말 20회권")
    category = db.Column(db.Enum(TicketCategory), nullable=False) # 이용권 대분류

    # 기간권/종합권 관련 필드
    duration_days = db.Column(db.Integer, nullable=True) # 유효 기간 (일 수, 예: 30일, 90일)

    # 횟수권/쿠폰/레슨추가/종합권 관련 필드
    total_count = db.Column(db.Integer, nullable=True) # 총 타석 이용 횟수
    total_lesson_count = db.Column(db.Integer, nullable=True) # 총 레슨 횟수

    # 횟수제 이용권의 기본 유효기간 (일 수)
    # 예: 10회권 -> 60일 유효. 이 값을 여기에 저장.
    # 기간제나 종합권은 duration_days 를 우선 사용.
    default_validity_days = db.Column(db.Integer, nullable=True)

    price = db.Column(db.Integer, nullable=True) # 기본 판매 가격 (선택 사항)
    description = db.Column(db.Text, nullable=True) # 설명
    is_active = db.Column(db.Boolean, default=True) # 활성 상태 (관리자가 비활성화 가능)
    created_at = db.Column(db.DateTime, default=db.func.current_timestamp())
    updated_at = db.Column(db.DateTime, default=db.func.current_timestamp(), onupdate=db.func.current_timestamp())

    def __repr__(self):
        return f'<TicketTemplate {self.name}>'

    # 이용권 이름 자동 생성 헬퍼 (발급 시 참고용)
    def generate_ticket_name(self):
        base_name = self.name
        details = []
        if self.category == TicketCategory.PERIOD and self.duration_days:
            # 간단히 개월 수로 표시 (더 정확하게 하려면 계산 필요)
            months = self.duration_days // 30 if self.duration_days else 0
            if months > 0:
                details.append(f"{months}개월")
        elif self.category == TicketCategory.COUNT and self.total_count:
            details.append(f"{self.total_count}회")
        elif self.category == TicketCategory.COUPON and self.total_count and self.total_lesson_count:
            details.append(f"타석+레슨 {self.total_count}회") # 쿠폰은 타석/레슨 횟수 동일 가정
        elif self.category == TicketCategory.LESSON_ADD and self.total_lesson_count:
            details.append(f"레슨 {self.total_lesson_count}회 추가")
        elif self.category == TicketCategory.COMBO:
            if self.duration_days:
                months = self.duration_days // 30 if self.duration_days else 0
                if months > 0:
                     details.append(f"{months}개월")
            if self.total_lesson_count:
                details.append(f"레슨 {self.total_lesson_count}회")

        if details:
            return f"{base_name} ({', '.join(details)})"
        return base_name
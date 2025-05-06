# app/models/enums.py
import enum

class BoothSystemType(enum.Enum):
    QED = "QED"
    KAKAO = "카카오VX"
    # 나중에 추가될 수 있음
    # GOLFZON = "골프존"

class BoothStatus(enum.Enum):
    AVAILABLE = "사용 가능"
    OCCUPIED = "사용중" # 향후 연동 시 사용
    BOOKED = "예약됨"
    OFFLINE = "사용 불가" # 일시적 비활성화
    MAINTENANCE = "점검중"

# --- ▼ 예약 관련 Enum 추가 ▼ ---
class BookingType(enum.Enum):
    """예약 유형"""
    TASEOK_ONLY = "타석 이용" # 일반 타석 예약 (레슨 없음)
    LESSON = "레슨 예약"     # 레슨 포함 예약

class BookingStatus(enum.Enum):
    """예약 상태"""
    SCHEDULED = "예약 확정" # 예정된 예약
    COMPLETED = "이용 완료" # 정상 이용 완료
    CANCELLED_USER = "사용자 취소" # 사용자가 취소
    CANCELLED_ADMIN = "관리자 취소" # 관리자가 취소
    NO_SHOW = "노쇼"        # 예약 시간 미방문
    # CHECKED_IN = "체크인" # 체크인 기능 추가 시
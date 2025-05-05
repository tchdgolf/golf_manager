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

# 다른 Enum들도 필요시 여기에 추가합니다.
# class BookingType(enum.Enum): ...
# class BookingStatus(enum.Enum): ...
# class TicketType(enum.Enum): ... # (템플릿 방식으로 변경되어 사용 안 할 수 있음)
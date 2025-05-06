# app/models/__init__.py
from .user import User
from .pro import Pro
from .booth import Booth
from .enums import BoothSystemType, BoothStatus

from .ticket_template import TicketTemplate, TicketCategory # TicketCategory Enum도 함께
from .ticket import Ticket
from .holding import Holding

# 나중에 추가될 모델들 (예시)
# from .booking import Booking
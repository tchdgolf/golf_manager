# --- app/models/booth.py 수정 ---
import datetime
# from app import db # <- 기존 코드 주석 처리 또는 삭제
from app.extensions import db # <- 수정된 임포트
from .enums import BoothSystemType, BoothStatus

class Booth(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), unique=True, nullable=False)
    system_type = db.Column(db.Enum(BoothSystemType), nullable=False)
    is_available = db.Column(db.Boolean, default=True)
    current_status = db.Column(db.Enum(BoothStatus), default=BoothStatus.AVAILABLE)
    last_status_update = db.Column(db.DateTime, default=datetime.datetime.utcnow)
    memo = db.Column(db.Text, nullable=True)

    def __repr__(self):
        return f'<Booth {self.name} ({self.system_type.value})>'
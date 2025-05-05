# --- app/models/pro.py 수정 ---
# from app import db # <- 기존 코드 주석 처리 또는 삭제
from app.extensions import db # <- 수정된 임포트

class Pro(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), unique=True, nullable=False)

    def __repr__(self):
        return f'<Pro {self.name}>'
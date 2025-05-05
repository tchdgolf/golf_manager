# app/models/user.py 수정
import datetime
# from app import db, login_manager # <- 기존 코드 주석 처리 또는 삭제
from app.extensions import db, login_manager # <- 수정된 임포트
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash

# user_loader 콜백 함수는 login_manager 를 사용하므로 여기에 두거나 extensions.py 로 옮겨도 됩니다.
# 여기서는 유지합니다.
@login_manager.user_loader
def load_user(user_id):
     # return db.session.get(User, int(user_id)) # 이 줄은 User 클래스 정의 후에 와야 함
     # 아래 User 클래스 정의 후 다시 정의하거나 클래스 외부로 빼는 것이 좋습니다.
     # 일단 주석 처리하고 아래 클래스 밖으로 옮깁니다.
     pass # 임시


class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    phone = db.Column(db.String(20), unique=True, nullable=False, index=True)
    phone_last4 = db.Column(db.String(4))
    password_hash = db.Column(db.String(255))
    is_admin = db.Column(db.Boolean, default=False)
    master_expiry_date = db.Column(db.Date, nullable=True)
    remaining_lesson_total = db.Column(db.Integer, default=0)
    memo = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.datetime.utcnow)
    last_login_at = db.Column(db.DateTime, nullable=True)

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        if not self.password_hash:
            return False
        return check_password_hash(self.password_hash, password)

    def set_phone_last4(self):
        if self.phone and len(self.phone) >= 4:
            self.phone_last4 = self.phone[-4:]
        else:
            self.phone_last4 = None

    def __repr__(self):
        return f'<User {self.name} ({self.phone})>'

# user_loader 를 클래스 정의 밖으로 이동하고 User 클래스를 참조하도록 수정
@login_manager.user_loader
def load_user(user_id):
    return db.session.get(User, int(user_id))

# app/extensions.py
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from flask_login import LoginManager
from flask_bcrypt import Bcrypt
from flask_wtf.csrf import CSRFProtect
from flask_bootstrap import Bootstrap

db = SQLAlchemy()
migrate = Migrate()
login_manager = LoginManager()
bcrypt = Bcrypt()
csrf = CSRFProtect()
bootstrap = Bootstrap()

# login_manager 설정 (이곳 또는 __init__.py 에서 해도 됨)
login_manager.login_view = 'auth.login'
login_manager.login_message = "로그인이 필요한 서비스입니다."
login_manager.login_message_category = "warning"
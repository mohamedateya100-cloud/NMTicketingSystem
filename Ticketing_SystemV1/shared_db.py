from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager
from flask_mail import Mail  # <--- (1) ضفنا السطر ده هنا

db = SQLAlchemy()
login_manager = LoginManager()
mail = Mail()  # <--- (2) وضفنا السطر ده هنا

# بنحدد صفحة الدخول الافتراضية للدعم الفني
login_manager.login_view = 'support.login'
from flask import Flask
from config import Config
from shared_db import db, login_manager, mail
from apps.support_app.models import SupportUser
from apps.purchase_app.models import PurchaseUser
from apps.support_app.routes import support_bp
from apps.purchase_app.routes import purchase_bp
import os

def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)
    
    # إعدادات الإيميل
    app.config['MAIL_SERVER'] = 'mail.worldposta.com'
    app.config['MAIL_PORT'] = 587
    app.config['MAIL_USE_TLS'] = True
    app.config['MAIL_USE_SSL'] = False
    app.config['MAIL_USERNAME'] = 'it@nationalmotors.com' 
    app.config['MAIL_PASSWORD'] = 'الباسورد_بتاعك_هنا' 
    app.config['MAIL_DEFAULT_SENDER'] = 'it@nationalmotors.com'

    if not os.path.exists('instance'):
        os.makedirs('instance')

    # تهيئة الإضافات
    db.init_app(app)
    login_manager.init_app(app)
    mail.init_app(app)

    # دالة قراءة الختم المزدوج (عشان تفصل الدعم عن المشتريات)
    @login_manager.user_loader
    def load_user(user_id):
        if user_id.startswith('support_'):
            real_id = int(user_id.split('_')[1])
            return SupportUser.query.get(real_id)
        elif user_id.startswith('purchase_'):
            real_id = int(user_id.split('_')[1])
            return PurchaseUser.query.get(real_id)
        return None

    # تسجيل المسارات
    app.register_blueprint(support_bp)
    app.register_blueprint(purchase_bp)

    with app.app_context():
        db.create_all()
        
    return app


# السطرين دول هما اللي بيقوموا السيرفر (لازم يكونوا في آخر الملف ومفيش قبلهم مسافات)
if __name__ == '__main__':
    app = create_app()
    print("🚀 جاري تشغيل السيرفر المزدوج...")
app.run(host='0.0.0.0', debug=True, port=5000)
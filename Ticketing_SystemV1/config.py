import os

base_dir = os.path.dirname(os.path.abspath(__file__))

class Config:  # تأكد إن السطر ده مكتوب كدة بالظبط
    SECRET_KEY = 'national-motors-it-2026'
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    
    # ربط موديول الدعم وموديول المشتريات بقواعد بيانات منفصلة
    SQLALCHEMY_BINDS = {
        'support_db': 'sqlite:///' + os.path.join(base_dir, 'instance', 'support_it.db'),
        'purchase_db': 'sqlite:///' + os.path.join(base_dir, 'instance', 'purchase_system.db')
    }
    
    # القاعدة الرئيسية (للتوافق مع Flask-SQLAlchemy)
    SQLALCHEMY_DATABASE_URI = 'sqlite:///' + os.path.join(base_dir, 'instance', 'main_system.db')
from run import create_app
from shared_db import db
from apps.support_app.models import SupportUser
from apps.purchase_app.models import PurchaseUser
from werkzeug.security import generate_password_hash

app = create_app()

with app.app_context():
    # 1. إنشاء مدير الـ IT (Admin)
    if not SupportUser.query.filter_by(username='admin_it').first():
        admin = SupportUser(
            username='admin_it', 
            password=generate_password_hash('it123'), 
            role='admin',
            full_name='مدير النظام',
            department='IT',
            branch='القاهرة',
            phone='01000000000'
        )
        db.session.add(admin)

    # 2. إنشاء موظف عادي للتجربة (User)
    if not SupportUser.query.filter_by(username='employee_1').first():
        emp = SupportUser(
            username='employee_1', 
            password=generate_password_hash('emp123'), 
            role='user',
            full_name='أحمد محمود',
            department='الحسابات',
            branch='الإسكندرية',
            phone='01234567890'
        )
        db.session.add(emp)
        
    # موظف تاني في فرع مختلف عشان التجربة
    if not SupportUser.query.filter_by(username='employee_2').first():
        emp2 = SupportUser(
            username='employee_2', 
            password=generate_password_hash('emp456'), 
            role='user',
            full_name='محمود سعيد',
            department='المبيعات',
            branch='أسيوط',
            phone='01111111111'
        )
        db.session.add(emp2)

    # 3. إنشاء حساب المشتريات
    if not PurchaseUser.query.filter_by(username='admin_buy').first():
        buyer = PurchaseUser(
            username='admin_buy', 
            password=generate_password_hash('buy123')
        )
        db.session.add(buyer)

    db.session.commit()
    print("✅ تم إنشاء الحسابات وتحديث بيانات الفروع والأقسام بنجاح!")
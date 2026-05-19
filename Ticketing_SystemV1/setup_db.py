from run import create_app
from shared_db import db
from apps.support_app.models import SupportUser, Branch, Department, TicketCategory, Role
from werkzeug.security import generate_password_hash

app = create_app()
with app.app_context():
    db.drop_all()
    db.create_all()
    
    # 1. إنشاء النوع الخارق
    admin_role = Role(name="مدير نظام (Full Access)", can_manage_settings=True, can_manage_users=True, can_view_all_tickets=True, can_delete_tickets=True, can_edit_status=True)
    db.session.add(admin_role); db.session.commit()
    
    # 2. إنشاء بيانات تجريبية
    b = Branch(name="المركز الرئيسي"); d = Department(name="IT"); db.session.add_all([b, d]); db.session.commit()
    
    # 3. إنشاء حسابك
    u = SupportUser(username="admin", password=generate_password_hash("123456"), full_name="Mohamed Ateya", branch_id=b.id, department_id=d.id, role_id=admin_role.id)
    db.session.add(u); db.session.commit()
    print("✅ Done! Login with admin / 123456")
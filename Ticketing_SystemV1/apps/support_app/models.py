from shared_db import db
from flask_login import UserMixin
from datetime import datetime

class Branch(db.Model):
    __bind_key__ = 'support_db'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), unique=True, nullable=False)
    is_active = db.Column(db.Boolean, default=True)
    users = db.relationship('SupportUser', backref='branch_info', lazy=True)

class Department(db.Model):
    __bind_key__ = 'support_db'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), unique=True, nullable=False)
    is_active = db.Column(db.Boolean, default=True)

    # ميزة الإدارة المركزية (الجديدة)
    is_centralized  = db.Column(db.Boolean, default=False)
    hq_branch_id = db.Column(db.Integer, db.ForeignKey('branch.id'), nullable=True)

    # العلاقات البرمجية (عشان نقدر نوصل للموظفين والفرع الرئيسي بسهولة)
    users = db.relationship('SupportUser', backref='dept_info', lazy=True)
    hq_branch = db.relationship('Branch', foreign_keys=[hq_branch_id], backref='central_departments', lazy=True)
        
class TicketCategory(db.Model):
    __bind_key__ = 'support_db'
    id = db.Column(db.Integer, primary_key=True)
    main_category = db.Column(db.String(50), nullable=False)
    sub_category = db.Column(db.String(100), nullable=False)
    is_active = db.Column(db.Boolean, default=True)

class Role(db.Model):
    __bind_key__ = 'support_db'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), unique=True, nullable=False)
    can_manage_settings = db.Column(db.Boolean, default=False)
    can_manage_users = db.Column(db.Boolean, default=False)
    can_view_all_tickets = db.Column(db.Boolean, default=False)
    can_delete_tickets = db.Column(db.Boolean, default=False)
    can_edit_status = db.Column(db.Boolean, default=False)
    can_access_purchasing = db.Column(db.Boolean, default=False)
    
    # --- 🔥 الصلاحيات الـ 4 الجديدة (الفلترة المتقدمة) ---
    can_view_it_tickets = db.Column(db.Boolean, default=False)
    can_view_admin_tickets = db.Column(db.Boolean, default=False)
    can_view_branch_tickets = db.Column(db.Boolean, default=False)
    can_view_dept_tickets = db.Column(db.Boolean, default=False)

    users = db.relationship('SupportUser', backref='role', lazy=True)
class SupportUser(db.Model, UserMixin):
    __bind_key__ = 'support_db'
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(50), unique=True, nullable=False)
    password = db.Column(db.String(200), nullable=False)
    full_name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(120), nullable=True)
    branch_id = db.Column(db.Integer, db.ForeignKey('branch.id'), nullable=True)
    department_id = db.Column(db.Integer, db.ForeignKey('department.id'), nullable=True)
    role_id = db.Column(db.Integer, db.ForeignKey('role.id'), nullable=True)
    is_active = db.Column(db.Boolean, default=True)
    tickets = db.relationship('SupportTicket', backref='author', lazy=True)
    def get_id(self): return f"support_{self.id}"

class SupportTicket(db.Model):
    __bind_key__ = 'support_db'
    id = db.Column(db.Integer, primary_key=True)
    category_id = db.Column(db.Integer, db.ForeignKey('ticket_category.id'), nullable=True)
    description = db.Column(db.Text, nullable=False)
    contact_phone = db.Column(db.String(20), nullable=False)
    status = db.Column(db.String(20), default='مفتوحة')
    date_posted = db.Column(db.DateTime, default=datetime.now)
    # 🔥 الخانة اللي كانت ناقصة عشان رد الفني
    it_comment = db.Column(db.Text, nullable=True) 
    user_id = db.Column(db.Integer, db.ForeignKey('support_user.id'), nullable=False)
    
    # روابط إضافية بتسهل سحب البيانات في الـ HTML
    category_info = db.relationship('TicketCategory', backref='tickets', lazy=True)
    # 🔥 رابط سجل التحركات مع خاصية المسح التلقائي
    history_logs = db.relationship('TicketHistory', backref='ticket', lazy=True, cascade="all, delete-orphan")

class TicketHistory(db.Model):
    __bind_key__ = 'support_db'
    id = db.Column(db.Integer, primary_key=True)
    ticket_id = db.Column(db.Integer, db.ForeignKey('support_ticket.id'), nullable=False)
    action = db.Column(db.String(200), nullable=False)
    user_name = db.Column(db.String(100), nullable=False)
    timestamp = db.Column(db.DateTime, default=datetime.now)

class EmailSettings(db.Model):
    __bind_key__ = 'support_db'
    id = db.Column(db.Integer, primary_key=True)
    smtp_server = db.Column(db.String(100), default='smtp.worldposta.com')
    smtp_port = db.Column(db.Integer, default=587)
    sender_email = db.Column(db.String(120), nullable=False)
    sender_password = db.Column(db.String(120), nullable=False)
    is_active = db.Column(db.Boolean, default=True)
    

from flask import Blueprint, render_template, redirect, url_for, request, flash
from flask_login import login_user, logout_user, login_required, current_user
from apps.support_app.models import SupportUser, SupportTicket, TicketHistory, Branch, Department, TicketCategory, Role, EmailSettings
from shared_db import db 
from werkzeug.security import check_password_hash, generate_password_hash
from datetime import datetime
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from flask import current_app, jsonify
from sqlalchemy import or_, and_  # استيراد أدوات الفلترة الذكية

support_bp = Blueprint('support', __name__)

# ضيف السطور دي عشان الـ HTML يشوف الدالة والـ getattr كمان
@support_bp.context_processor
def inject_permissions():
    # هنا ضفنا getattr للموسوعة اللي الـ HTML بيقدر يقرأ منها
    return dict(has_p=has_p, getattr=getattr)

# دالة مساعدة للتأكد من الصلاحية
def has_p(perm):
    if not current_user.is_authenticated or not current_user.role: return False
    return getattr(current_user.role, perm, False)

# ----------------- إعدادات الإرسال الديناميكي المحدثة لدعم الـ CC -----------------
def send_dynamic_email(recipient_email, subject, body, cc_emails=None):
    mail_conf = EmailSettings.query.first()
    if not mail_conf or not mail_conf.smtp_server:
        print("🔴 إعدادات البريد الإلكتروني غير مكتملة في قاعدة البيانات")
        return False
    try:
        msg = MIMEMultipart()
        msg['Subject'] = subject
        msg['From'] = str(mail_conf.sender_email).strip()
        msg['To'] = str(recipient_email).strip()

        if cc_emails:
            valid_cc = [str(email).strip() for email in cc_emails if email and str(email).strip()]
            if valid_cc:
                msg['Cc'] = ", ".join(valid_cc)

        # =========================================================
        # 🎨 تصميم الـ HTML الخاص بـ National Motors
        # =========================================================
        # تحويل المسافات العادية (Enters) لسطور HTML عشان التنسيق ميبوظش
        formatted_body = body.replace('\n', '<br>')
        
        html_template = f"""
        <!DOCTYPE html>
        <html lang="ar" dir="rtl">
        <head>
            <meta charset="UTF-8">
        </head>
        <body style="margin: 0; padding: 0; background-color: #f4f7f6; font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;">
            <div style="max-width: 600px; margin: 30px auto; background-color: #ffffff; border-radius: 8px; overflow: hidden; box-shadow: 0 4px 15px rgba(0,0,0,0.1);">
                
                <div style="background-color: #0d47a1; color: #ffffff; padding: 25px; text-align: center; border-bottom: 4px solid #d32f2f;">
                    <h2 style="margin: 0; font-size: 24px; letter-spacing: 1px;">⚙️ National Motors IT Support</h2>
                </div>
                
                <div style="padding: 30px; color: #333333; line-height: 1.8; font-size: 16px; border-bottom: 1px solid #eeeeee;">
                    {formatted_body}
                </div>
                
                <div style="background-color: #f9f9f9; color: #777777; padding: 20px; text-align: center; font-size: 13px;">
                    <p style="margin: 0;">هذا البريد تم إرساله تلقائياً من نظام الدعم الفني لشركة ناشيونال موتورز.<br>برجاء عدم الرد المباشر على هذا الإيميل.</p>
                    <p style="margin: 10px 0 0 0; font-size: 11px; color: #aaaaaa;">&copy; {datetime.now().year} National Motors Co.</p>
                </div>
                
            </div>
        </body>
        </html>
        """

        # تحديد إن نوع الرسالة 'html' مش 'plain'
        msg.attach(MIMEText(html_template, 'html', 'utf-8'))

        server = smtplib.SMTP(str(mail_conf.smtp_server).strip(), int(mail_conf.smtp_port), timeout=15)
        server.starttls() 
        server.login(str(mail_conf.sender_email).strip(), str(mail_conf.sender_password).strip())
        
        server.send_message(msg)
        server.quit()
        return True
    except Exception as e:
        print(f"🔴 Error sending email via dynamic function: {e}")
        return False
# ----------------------------------------------------------------

@support_bp.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        user = SupportUser.query.filter_by(username=request.form.get('username')).first()
        if user and check_password_hash(user.password, request.form.get('password')):
            login_user(user)
            
            # --- التوجيه الذكي للبوابة ---
            if has_p('can_access_purchasing'):
                return redirect(url_for('support.portal'))
            return redirect(url_for('support.index'))
            
        flash("بيانات الدخول غير صحيحة", "danger")
    return render_template('support/login.html')

@support_bp.route('/', methods=['GET', 'POST'])
@login_required 
def index():
    if request.method == 'POST':
        # 1. الحذف المجمع
        ids = request.form.getlist('ticket_ids')
        if ids and has_p('can_delete_tickets'):
            SupportTicket.query.filter(SupportTicket.id.in_(ids)).delete(synchronize_session=False)
            db.session.commit()
            return redirect(url_for('support.index'))

        # 2. إنشاء تذكرة وإرسال إيميل
        cat = TicketCategory.query.filter_by(main_category=request.form.get('main_category'), sub_category=request.form.get('sub_category')).first()
        new_t = SupportTicket(category_id=cat.id if cat else None, description=request.form.get('description'), 
                              contact_phone=request.form.get('phone'), author=current_user)
        db.session.add(new_t); db.session.flush()
        db.session.add(TicketHistory(ticket_id=new_t.id, action="إنشاء طلب", user_name=current_user.full_name))
        db.session.commit() 
        
        # =========================================================
        # 🧠 ميكانيزم تجميع الـ CC المطور (Case-Insensitive & Smart Fallback)
        # =========================================================
        cc_list = []
        creator = current_user 
        print(f"\n🔍 [شاشه المتابعة] جاري تجميع الـ CC لتذكرة الموظف: {creator.full_name}")

        # أ. جلب مدير فرع الموظف (تجاهل حالة الأحرف)
        if creator.branch_id:
            branch_mgr = SupportUser.query.join(Role).filter(
                SupportUser.branch_id == creator.branch_id,
                Role.name.ilike('%branch manager%')
            ).first()
            if branch_mgr and branch_mgr.email:
                cc_list.append(branch_mgr.email.strip())
                print(f"🟢 وجدنا مدير الفرع: {branch_mgr.full_name} ({branch_mgr.email})")

        # ب. جلب مدير الإدارة الذكي (محلي أولاً، ثم مركزي على مستوى الشركة بدون تخمين اسم الفرع)
        if creator.department_id:
            dept_mgr = SupportUser.query.join(Role).filter(
                SupportUser.branch_id == creator.branch_id,
                SupportUser.department_id == creator.department_id,
                Role.name.ilike('%department manager%')
            ).first()
            
            # إذا لم يجد مدير إدارة محلي في نفس الفرع، يبحث عن مدير لهذه الإدارة في أي فرع آخر بالشركة
            if not dept_mgr:
                print("⚠️ لم نجد مدير إدارة محلي، جاري البحث عن مدير الإدارة على مستوى الشركة ككل...")
                dept_mgr = SupportUser.query.join(Role).filter(
                    SupportUser.department_id == creator.department_id,
                    Role.name.ilike('%department manager%')
                ).first()
            
            if dept_mgr and dept_mgr.email:
                cc_list.append(dept_mgr.email.strip())
                print(f"🟢 وجدنا مدير الإدارة: {dept_mgr.full_name} ({dept_mgr.email})")

        # ج. جلب رئيس قسم الدعم الفني أو الأدمن لمتابعتك كـ IT
        main_cat = request.form.get('main_category')
        support_dept = Department.query.filter(Department.name.ilike(f"%{main_cat}%")).first()
        if support_dept:
            support_head = SupportUser.query.join(Role).filter(
                SupportUser.department_id == support_dept.id,
                Role.name.ilike('%department manager%')
            ).first()
            if support_head and support_head.email:
                cc_list.append(support_head.email.strip())
                print(f"🟢 وجدنا رئيس القسم المختص: {support_head.full_name}")

        # تنظيف القائمة نهائياً من الفراغات والتكرار
        final_cc = list(set([email for email in cc_list if email]))
        print(f"📋 القائمة النهائية للـ CC المكتشفة: {final_cc}\n")

        # ==========================================
        # إرسال الإيميلات الفعلي
        # ==========================================
        subject_user = f"National Motors Support - تم استلام طلبك #{new_t.id}"
        body_user = f"مرحباً {current_user.full_name}،\n\nتم استلام طلب الدعم الفني بنجاح.\nرقم الطلب: #{new_t.id}\nالقسم: {main_cat} - {request.form.get('sub_category')}\nوصف المشكلة: {new_t.description}\n\nفريق الدعم سيقوم بمراجعة طلبك قريباً."
        send_dynamic_email(current_user.email, subject_user, body_user)

        if main_cat == 'IT':
            target_email = "it.support@nationalmotorsco.com" 
        elif main_cat == 'Admin':
            target_email = "admin.manager@nationalmotorsco.com"
        else:
            mail_conf = EmailSettings.query.first()
            target_email = mail_conf.sender_email if mail_conf else None

        if target_email:
            subject_admin = f"⚠️ تذكرة جديدة ({main_cat}) من: {current_user.full_name} (#{new_t.id})"
            body_admin = f"برجاء مراجعة التذكرة الجديدة:\n\n" \
                         f"صاحب التذكرة: {current_user.full_name}\n" \
                         f"الفرع: {current_user.branch_info.name if current_user.branch_info else '---'}\n" \
                         f"القسم: {main_cat} - {request.form.get('sub_category')}\n" \
                         f"التفاصيل: {new_t.description}\n\n" \
                         f"رابط التذكرة: {url_for('support.ticket_details', ticket_id=new_t.id, _external=True)}"
            
            send_dynamic_email(target_email, subject_admin, body_admin, cc_emails=final_cc)
            
        return redirect(url_for('support.index'))

    # الفلترة (GET) - The Magic Logic
    query = SupportTicket.query.join(SupportUser)

    if not has_p('can_view_all_tickets'):
        # الأساس: كل موظف يشوف تذاكره هو
        filters = [SupportTicket.user_id == current_user.id]

        if current_user.role:
            
            # صلاحية مدير القسم (can_view_dept_tickets)
            if has_p('can_view_dept_tickets') and current_user.department_id:
                if current_user.dept_info and current_user.dept_info.is_centralized:
                    # قسم مركزي: يشوف كل تذاكر قسمه من كل الفروع
                    filters.append(SupportUser.department_id == current_user.department_id)
                else:
                    # قسم محلي: يشوف قسمه في فرعه بس
                    filters.append(and_(
                        SupportUser.department_id == current_user.department_id,
                        SupportUser.branch_id == current_user.branch_id
                    ))

            # صلاحية مدير الفرع (can_view_branch_tickets)
            if has_p('can_view_branch_tickets') and current_user.branch_id:
                # مدير الفرع يشوف "كل تذاكر فرعه" أياً كانت الإدارة بتاعتهم
                filters.append(SupportUser.branch_id == current_user.branch_id)
                            
            # الصلاحيات الخاصة بـ IT و Admin
            if has_p('can_view_it_tickets') or has_p('can_view_admin_tickets'):
                query = query.outerjoin(TicketCategory, SupportTicket.category_id == TicketCategory.id)
                if has_p('can_view_it_tickets'):
                    filters.append(TicketCategory.main_category == 'IT')
                if has_p('can_view_admin_tickets'):
                    filters.append(TicketCategory.main_category == 'Admin')

        # تطبيق كل الفلاتر
        query = query.filter(or_(*filters))
    
    f_branch = request.args.get('f_branch'); f_status = request.args.get('f_status')
    start = request.args.get('start_date'); end = request.args.get('end_date')

    if f_branch: query = query.filter(SupportUser.branch_id == f_branch)
    if f_status: query = query.filter(SupportTicket.status == f_status)
    if start: query = query.filter(SupportTicket.date_posted >= datetime.strptime(start, '%Y-%m-%d'))
    if end: query = query.filter(SupportTicket.date_posted <= datetime.strptime(end, '%Y-%m-%d').replace(hour=23, minute=59))

    return render_template('support/index.html', 
                           tickets=query.order_by(SupportTicket.date_posted.desc()).all(),
                           branches=Branch.query.filter_by(is_active=True).all(),
                           departments=Department.query.filter_by(is_active=True).all(),
                           categories=TicketCategory.query.filter_by(is_active=True).all())

@support_bp.route('/profile')
@login_required
def profile():
    return render_template('support/profile.html')

@support_bp.route('/manage_users')
@login_required
def manage_users():
    if not has_p('can_manage_users'): return "Forbidden", 403
    return render_template('support/manage_users.html', 
                           users=SupportUser.query.all(),
                           branches = Branch.query.filter_by(is_active=True).all(),
                           departments=Department.query.all(),
                           roles=Role.query.all())

@support_bp.route('/add_user', methods=['POST'])
@login_required
def add_user():
    if has_p('can_manage_users'):
        dept_id = request.form.get('department_id')
        new_u = SupportUser(
            username=request.form.get('username'),
            full_name=request.form.get('full_name'),
            email=request.form.get('email'),
            password=generate_password_hash(request.form.get('password')),
            department_id=dept_id if dept_id else None,
            branch_id=request.form.get('branch_id'),
            role_id=request.form.get('role_id')
        )
        db.session.add(new_u); db.session.commit()
    return redirect(url_for('support.manage_users'))

@support_bp.route('/edit_user/<int:user_id>', methods=['POST'])
@login_required
def edit_user(user_id):
    if has_p('can_manage_users'):
        u = SupportUser.query.get_or_404(user_id)
        u.full_name = request.form.get('full_name'); u.email = request.form.get('email')
        
        dept_id = request.form.get('department_id')
        u.department_id = dept_id if dept_id else None
        
        u.branch_id = request.form.get('branch_id')
        u.role_id = request.form.get('role_id'); db.session.commit()
    return redirect(url_for('support.manage_users'))

@support_bp.route('/settings')
@login_required
def settings():
    if not has_p('can_manage_settings'): return "Forbidden", 403
    
    edit_role_id = request.args.get('edit_role')
    edit_role = Role.query.get(edit_role_id) if edit_role_id else None
    email_settings = EmailSettings.query.first()

    return render_template('support/settings.html', 
                           branches=Branch.query.all(), 
                           departments=Department.query.all(), 
                           categories=TicketCategory.query.all(), 
                           roles=Role.query.all(),
                           edit_role=edit_role,
                           email_settings=email_settings)

@support_bp.route('/settings/save_email', methods=['POST'])
@login_required
def save_email_settings():
    if not has_p('can_manage_settings'): return "Forbidden", 403
    
    settings = EmailSettings.query.first()
    if not settings:
        settings = EmailSettings()
        db.session.add(settings)
        
    settings.sender_email = request.form.get('sender_email')
    settings.sender_password = request.form.get('sender_password')
    settings.smtp_server = request.form.get('smtp_server')
    settings.smtp_port = request.form.get('smtp_port')
    
    db.session.commit()
    flash('تم حفظ إعدادات البريد الإلكتروني بنجاح', 'success')
    return redirect(url_for('support.settings'))

@support_bp.route('/test_email', methods=['POST'])
@login_required
def test_email():
    try:
        mail_conf = EmailSettings.query.first()
        if not mail_conf:
            return jsonify({"status": "error", "message": "لم يتم العثور على أي إعدادات في قاعدة البيانات!"}), 400

        # حماية برمجية: التحقق من وجود داتا قبل عمل strip منعاً لأي كراش
        SMTP_SERVER = str(mail_conf.smtp_server).strip() if mail_conf.smtp_server else ""
        SMTP_PORT = int(mail_conf.smtp_port) if mail_conf.smtp_port else 587
        SENDER_EMAIL = str(mail_conf.sender_email).strip() if mail_conf.sender_email else ""
        SENDER_PASSWORD = str(mail_conf.sender_password).strip() if mail_conf.sender_password else ""

        if not SMTP_SERVER or not SENDER_EMAIL:
            return jsonify({"status": "error", "message": "خطأ: تأكد من كتابة السيرفر والإيميل وحفظهم أولاً"}), 400

        data = request.get_json() or {}
        
        if data.get('test_email'):
            receiver_email = str(data.get('test_email')).strip()
        else:
            receiver_email = SENDER_EMAIL

        # تجهيز الرسالة
        msg = MIMEMultipart()
        msg['From'] = SENDER_EMAIL
        msg['To'] = receiver_email
        msg['Subject'] = "National Motors Portal - Diagnostic Test"
        
        body = f"تم الاتصال بنجاح!\nالراسل الفعلي: {SENDER_EMAIL}\nالمستقبل: {receiver_email}\nالسيرفر المستخدم: {SMTP_SERVER}"
        msg.attach(MIMEText(body, 'plain', 'utf-8'))
        
        # الاتصال الفعلي بالسيرفر
        server = smtplib.SMTP(SMTP_SERVER, SMTP_PORT, timeout=15)
        server.starttls()
        server.login(SENDER_EMAIL, SENDER_PASSWORD)
        server.send_message(msg)
        server.quit()
        
        return jsonify({
            "status": "success", 
            "message": f"تم الإرسال الفعلي عبر سيرفر ({SMTP_SERVER}) إلى ({receiver_email}). راجع الـ Sent والـ Inbox الآن."
        }), 200
        
    except Exception as e:
        return jsonify({"status": "error", "message": f"فشل الاتصال بالـ SMTP: {str(e)}"}), 500

@support_bp.route('/settings/save_role', methods=['POST'])
@login_required
def save_role():
    role_id = request.form.get('role_id')
    role_name = request.form.get('role_name')

    if role_id:
        role = Role.query.get(role_id)
    else:
        role = Role(name=role_name)
        db.session.add(role)

    role.name = role_name
    role.can_manage_settings = 'can_manage_settings' in request.form
    role.can_manage_users = 'can_manage_users' in request.form
    role.can_view_all_tickets = 'can_view_all_tickets' in request.form
    role.can_delete_tickets = 'can_delete_tickets' in request.form
    role.can_edit_status = 'can_edit_status' in request.form
    role.can_view_it_tickets = 'can_view_it_tickets' in request.form
    role.can_view_admin_tickets = 'can_view_admin_tickets' in request.form
    role.can_view_branch_tickets = 'can_view_branch_tickets' in request.form
    role.can_view_dept_tickets = 'can_view_dept_tickets' in request.form
    role.can_view_dept_tickets = 'can_view_dept_tickets' in request.form
    role.can_access_purchasing = 'can_access_purchasing' in request.form # السطر الجديد

    db.session.commit()
    flash("Success", "success")
    return redirect(url_for('support.settings'))

@support_bp.route('/settings/add_branch', methods=['POST'])
def add_branch(): db.session.add(Branch(name=request.form.get('name'))); db.session.commit(); return redirect(url_for('support.settings'))

@support_bp.route('/settings/add_dept', methods=['POST'])
@login_required
def add_dept(): 
    name = request.form.get('name')
    is_centralized = 'is_centralized' in request.form 
    
    if name:
        db.session.add(Department(name=name, is_centralized=is_centralized))
        db.session.commit()
        
    return redirect(url_for('support.settings'))

@support_bp.route('/settings/add_category', methods=['POST'])
def add_category(): 
    db.session.add(TicketCategory(main_category=request.form.get('main_category'), sub_category=request.form.get('sub_category')))
    db.session.commit(); return redirect(url_for('support.settings'))

@support_bp.route('/settings/add_role', methods=['POST'])
def add_role():
    r = Role(
        name=request.form.get('name'),
        can_manage_settings='can_manage_settings' in request.form,
        can_manage_users='can_manage_users' in request.form,
        can_view_all_tickets='can_view_all_tickets' in request.form,
        can_delete_tickets='can_delete_tickets' in request.form,
        can_edit_status='can_edit_status' in request.form,
        can_view_it_tickets='can_view_it_tickets' in request.form,
        can_view_admin_tickets='can_view_admin_tickets' in request.form,
        can_view_branch_tickets='can_view_branch_tickets' in request.form,
        can_view_dept_tickets='can_view_dept_tickets' in request.form
    )
    db.session.add(r)
    db.session.commit()
    return redirect(url_for('support.settings'))

@support_bp.route('/settings/toggle_branch/<int:id>')
def toggle_branch(id): b = Branch.query.get(id); b.is_active = not b.is_active; db.session.commit(); return redirect(url_for('support.settings'))

@support_bp.route('/reset_password/<int:user_id>', methods=['POST'])
@login_required
def reset_password(user_id):
    if not has_p('can_manage_users'): return "Forbidden", 403
    u = SupportUser.query.get(user_id)
    u.password = generate_password_hash(request.form.get('new_password'))
    db.session.commit()
    return redirect(url_for('support.manage_users'))

@support_bp.route('/delete_user/<int:user_id>')
def delete_user(user_id):
    u = SupportUser.query.get(user_id); u.is_active = False; db.session.commit()
    return redirect(url_for('support.manage_users'))

@support_bp.route('/logout')
def logout(): logout_user(); return redirect(url_for('support.login'))

@support_bp.route('/ticket_details/<int:ticket_id>', methods=['GET', 'POST'])
@login_required
def ticket_details(ticket_id):
    ticket = SupportTicket.query.get_or_404(ticket_id)
    
    if request.method == 'POST' and has_p('can_edit_status'):
        if ticket.status == 'مغلقة':
            flash("عفواً، لا يمكن تعديل طلب تم إغلاقه مسبقاً.", "warning")
            return redirect(url_for('support.ticket_details', ticket_id=ticket.id))
        
        new_status = request.form.get('status')
        comment = request.form.get('it_comment')
        
        ticket.status = new_status
        ticket.it_comment = comment
        
        db.session.add(TicketHistory(
            ticket_id=ticket.id, 
            action=f"تغيير الحالة إلى {new_status}", 
            user_name=current_user.full_name
        ))
        db.session.commit()

        # ==========================================
        # 🧠 ميكانيزم تجميع الـ CC الديناميكي عند التحديث/الإغلاق
        # ==========================================
        # =========================================================
        # 🧠 ميكانيزم تجميع الـ CC المطور عند التحديث أو الإغلاق
        # =========================================================
        cc_list = []
        creator = ticket.author 
        print(f"\n🔍 [شاشه المتابعة] جاري تجميع الـ CC لتحديث تذكرة الموظف: {creator.full_name}")

        if creator.branch_id:
            branch_mgr = SupportUser.query.join(Role).filter(
                SupportUser.branch_id == creator.branch_id,
                Role.name.ilike('%branch manager%')
            ).first()
            if branch_mgr and branch_mgr.email:
                cc_list.append(branch_mgr.email.strip())

        if creator.department_id:
            dept_mgr = SupportUser.query.join(Role).filter(
                SupportUser.branch_id == creator.branch_id,
                SupportUser.department_id == creator.department_id,
                Role.name.ilike('%department manager%')
            ).first()
            
            if not dept_mgr:
                dept_mgr = SupportUser.query.join(Role).filter(
                    SupportUser.department_id == creator.department_id,
                    Role.name.ilike('%department manager%')
                ).first()
            
            if dept_mgr and dept_mgr.email:
                cc_list.append(dept_mgr.email.strip())

        ticket_cat = TicketCategory.query.get(ticket.category_id) if ticket.category_id else None
        main_cat = ticket_cat.main_category if ticket_cat else 'IT'
        support_dept = Department.query.filter(Department.name.ilike(f"%{main_cat}%")).first()
        if support_dept:
            support_head = SupportUser.query.join(Role).filter(
                SupportUser.department_id == support_dept.id,
                Role.name.ilike('%department manager%')
            ).first()
            if support_head and support_head.email:
                cc_list.append(support_head.email.strip())

        final_cc = list(set([email for email in cc_list if email]))
        print(f"📋 القائمة النهائية للـ CC المكتشفة للتحديث: {final_cc}\n")

        # --- إرسال إيميل بالتحديث للموظف مع وضع المديرين في الـ CC ليكونوا في الصورة ---
        subject = f"National Motors Support - تحديث بخصوص طلبك #{ticket.id}"
        body = f"مرحباً {ticket.author.full_name}،\n\nتم تحديث حالة طلبك رقم #{ticket.id} إلى: {new_status}.\n\nرد الدعم الفني:\n{comment}\n\nشكراً لتواصلك معنا."
        send_dynamic_email(ticket.author.email, subject, body, cc_emails=final_cc)
        # -----------------------------------

        flash("تم تحديث الطلب وإرسال الإشعار بنجاح", "success")
        return redirect(url_for('support.ticket_details', ticket_id=ticket.id))
    
    history = TicketHistory.query.filter_by(ticket_id=ticket.id).order_by(TicketHistory.timestamp.desc()).all()
    return render_template('support/ticket_details.html', ticket=ticket, history=history)

@support_bp.route('/user_history/<int:user_id>')
@login_required
def user_history(user_id):
    target_user = SupportUser.query.get_or_404(user_id)
    
    is_allowed = (current_user.id == user_id) or has_p('can_manage_users') or has_p('can_view_all_tickets')
    
    if not is_allowed and has_p('can_view_branch_tickets'):
        if current_user.branch_id == target_user.branch_id:
            is_allowed = True
            
    if not is_allowed and has_p('can_view_dept_tickets'):
        if current_user.department_id == target_user.department_id:
            if current_user.dept_info and current_user.dept_info.is_centralized:
                is_allowed = True 
            elif current_user.branch_id == target_user.branch_id:
                is_allowed = True 

    if not is_allowed:
        return "غير مسموح لك بعرض سجل هذا الموظف", 403
        
    user_tickets = SupportTicket.query.filter_by(user_id=target_user.id).order_by(SupportTicket.date_posted.desc()).all()
    return render_template('support/user_history.html', user=target_user, tickets=user_tickets)

@support_bp.route('/portal')
@login_required
def portal():
    if not has_p('can_access_purchasing'):
        return redirect(url_for('support.index'))
    # ⬇️ عدل السطر ده خليه كده لو الملف بره ⬇️
    return render_template('portal.html')
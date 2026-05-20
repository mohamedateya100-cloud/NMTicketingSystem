from flask import Blueprint, render_template, redirect, url_for
from flask_login import login_required, current_user

# تعريف البلوبرينت بتاع المشتريات
purchase_bp = Blueprint('purchase', __name__)

@purchase_bp.route('/purchase/dashboard')
@login_required
def dashboard():
    # حماية الراوت: التأكد إن الموظف اللي داخل معاه صلاحية المشتريات فعلاً
    if not current_user.role or not getattr(current_user.role, 'can_access_purchasing', False):
        return redirect(url_for('support.index'))
        
    # لو معاه الصلاحية، يفتحله صفحة "تحت الإنشاء" اللي عملناها
    return render_template('purchase/under_construction.html')
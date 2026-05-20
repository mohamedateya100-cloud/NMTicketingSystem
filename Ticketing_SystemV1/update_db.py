import sqlite3
import os

# تحديد مسار الداتابيز الفعلي بناءً على شجرة الملفات بتاعتك
db_path = os.path.join('instance', 'support_it.db')

try:
    # الاتصال المباشر بقاعدة البيانات
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # تنفيذ أمر إضافة الصلاحية
    cursor.execute("ALTER TABLE role ADD COLUMN can_access_purchasing BOOLEAN DEFAULT 0;")
    conn.commit()
    conn.close()
    
    print("🟢 الطلقة صابت! تم تحديث قاعدة البيانات وإضافة صلاحية المشتريات بنجاح يا هندسة.")
    
except sqlite3.OperationalError as e:
    # لو العمود كان اتضاف قبل كدة في أي محاولة سابقة
    if "duplicate column name" in str(e).lower():
        print("🟡 العمود موجود بالفعل في الداتابيز، إنت جاهز تماماً!")
    else:
        print(f"🔴 خطأ في قاعدة البيانات: {e}")
except Exception as e:
    print(f"🔴 حدث خطأ غير متوقع: {e}")
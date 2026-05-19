from shared_db import db
from flask_login import UserMixin

class PurchaseUser(db.Model, UserMixin):
    __bind_key__ = 'purchase_db'
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(50), unique=True, nullable=False)
    password = db.Column(db.String(100), nullable=False)

    # دالة تمييز الآي دي الخاصة بالمشتريات
    def get_id(self):
        return f"purchase_{self.id}"

class PurchaseRequest(db.Model):
    __bind_key__ = 'purchase_db'
    id = db.Column(db.Integer, primary_key=True)
    item_name = db.Column(db.String(100), nullable=False)
    quantity = db.Column(db.Integer, default=1)
    status = db.Column(db.String(20), default='pending')
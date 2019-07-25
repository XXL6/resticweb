from flask import current_app
from flask_login import UserMixin
from resticweb import db, login_manager


class User(db.Model, UserMixin):
    __bind_key__ = 'general'
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(20), unique=True, nullable=False)
    password = db.Column(db.String(60), nullable=False)


@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

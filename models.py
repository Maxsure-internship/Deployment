from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
import datetime

db = SQLAlchemy()


class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    mail = db.Column(db.String(100), unique=True, nullable=False)
    password = db.Column(db.String(250), nullable=False)


class Stock(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    symbol = db.Column(db.String(100), nullable=False)
    price = db.Column(db.Float, nullable=False)
    timestamp = db.Column(db.BigInteger, nullable=False)
    exchange = db.Column(db.String(20), nullable=False)
    quote_type = db.Column(db.Integer)
    change_percent=db.Column(db.Float)
    change = db.Column(db.Float)
    price_hint = db.Column(db.Integer)


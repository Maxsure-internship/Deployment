from flask import Flask
from flask_session import Session
from flask_login import LoginManager
from flask_socketio import SocketIO
import yfinance as yf
from models import User, Stock, db
from datetime import datetime

from threading import Thread
from queue import Queue

from extensions import mailer

app = Flask(__name__)

# Session Configuration
from dotenv import load_dotenv
import os

load_dotenv()

app.secret_key = os.environ.get("SESSION_KEY", "")
app.config["SESSION_PERMANENT"] = False
app.config["SESSION_TYPE"] = "filesystem"

Session(app)

# Database
from models import db

app.config["SQLALCHEMY_DATABASE_URI"] = os.environ.get("DB_URI", "")
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
db.init_app(app)

# Login manager
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = "auth.login"


@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))


# Mailer setup
app.config["MAIL_SERVER"] = "smtp.gmail.com"
app.config["MAIL_PORT"] = int(os.environ.get("SMTP_PORT", 587))
app.config["MAIL_USE_TLS"] = True


app.config["MAIL_USERNAME"] = os.environ.get("SMTP_USER", "")
app.config["MAIL_PASSWORD"] = os.environ.get("SMTP_PASS", "")

mailer.init_app(app)

# DB Job Queue
stock_queue = Queue()

# Register blueprints
from auth import auth

app.register_blueprint(auth, url_prefix="/registration")

from home import home

app.register_blueprint(home, url_prefix="/")

from dashboard import dashboard

app.register_blueprint(dashboard, url_prefix="/dashboard")

# Socket IO
socketio = SocketIO(app)


def stock_stream():
    def handler(message):
        # Store new stock in database
        stock_queue.put(
            {
                "symbol": message["id"],
                "price": message["price"],
                "timestamp": message["time"],
                "exchange": message["exchange"],
                "quote_type": message["quote_type"],
                "change_percent": message["change_percent"],
                "change": message["change"],
                "price_hint": message["price_hint"],
            }
        )

        # Send the new stock to
        socketio.emit("stock_update", message)

    with yf.WebSocket() as ws:
        ws.subscribe(["NVDA"])
        ws.listen(handler)


# Max records stored in the database at any given point of time
MAX_RECORDS = 100

from queue import Empty


def db_queue_worker():
    with app.app_context():
        buffer = []

        while True:
            try:
                stock_data = stock_queue.get(timeout=1)
                stock = Stock(**stock_data)
                buffer.append(stock)

                if len(buffer) >= MAX_RECORDS:
                    count = Stock.query.count()

                    # If there are more than 500 records delete
                    if count >= MAX_RECORDS:
                        db.session.query(Stock).delete()
                        db.commit()

                    # Bulk save records to the database
                    db.session.bulk_save_objects(buffer)

                    # commit to saving bulk objects as well as deleting prior data
                    db.session.commit()

                    buffer.clear()

            except Empty:
                continue

            except Exception as e:
                db.session.rollback()


if __name__ == "__main__":
    with app.app_context():
        db.create_all()

    # Stock Stream
    stock_stream_thread = Thread(target=stock_stream, daemon=True)
    stock_stream_thread.start()

    # DB worker
    db_worker = Thread(target=db_queue_worker, daemon=True)
    db_worker.start()

    # registering filters
    @app.template_filter("datetime_from_timestamp")
    def datetime_from_timestamp(ts):
        return datetime.fromtimestamp(ts).strftime("%d %b, %H:%M")

    socketio.run(
        app,
        host="0.0.0.0",
        port=8000,
        debug=os.environ.get("ENV", "development") == "development",
    )

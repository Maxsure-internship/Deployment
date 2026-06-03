# app.py (Abbreviated to highlight structural changes)
import os
from dotenv import load_dotenv
from flask import Flask
from flask_session import Session
from flask_login import LoginManager
from flask_socketio import SocketIO
import yfinance as yf
from models import User, Stock, db
from datetime import datetime

# REMOVE standard Queue and Thread imports
# from threading import Thread
# from queue import Queue

from extensions import mailer

load_dotenv()

app = Flask(__name__)
# ... (Keep your database, session, login manager, and mailer setups exactly as they are) ...

# Initialize SocketIO without breaking context
socketio = SocketIO(app, cors_allowed_origins="*")

# REPLACE queue.Queue with SocketIO's eventlet/gevent safe queue wrapper
stock_queue = socketio.queue.Queue() 

def stock_stream():
    def handler(message):
        stock_queue.put({
            "symbol": message["id"],
            "price": message["price"],
            "timestamp": message["time"],
            "exchange": message["exchange"],
            "quote_type": message["quote_type"],
            "change_percent": message["change_percent"],
            "change": message["change"],
            "price_hint": message["price_hint"],
        })
        # Safe emit from background task
        socketio.emit("stock_update", message)

    # Note: yf.WebSocket blocks. Using eventlet requires monkey patching (handled in Step 2)
    with yf.WebSocket() as ws:
        ws.subscribe(["NVDA"])
        ws.listen(handler)

MAX_RECORDS = 100

def db_queue_worker():
    with app.app_context():
        buffer = []
        while True:
            try:
                # Use a small sleep inside the loop to avoid CPU spiking in async loops
                socketio.sleep(0.1) 
                
                # Fetch data from the queue safely without blocking the event loop
                if not stock_queue.empty():
                    stock_data = stock_queue.get_nowait()
                    stock = Stock(**stock_data)
                    buffer.append(stock)

                    if len(buffer) >= MAX_RECORDS:
                        count = Stock.query.count()
                        if count >= MAX_RECORDS:
                            db.session.query(Stock).delete()
                            db.session.commit() # Fixed typo: db.commit() -> db.session.commit()

                        db.session.bulk_save_objects(buffer)
                        db.session.commit()
                        buffer.clear()
            except Exception as e:
                db.session.rollback()
                socketio.sleep(1) # Back off on database error

# Move filter and table creation here
def datetime_from_timestamp(ts):
    return datetime.fromtimestamp(ts).strftime("%d %b, %H:%M")
app.jinja_env.filters["datetime_from_timestamp"] = datetime_from_timestamp

with app.app_context():
    db.create_all()

# REPLACE Thread.start() with socketio.start_background_task
@socketio.on('connect')
def handle_connect():
    print("Client connected")

# Start background tasks safely through SocketIO
socketio.start_background_task(stock_stream)
socketio.start_background_task(db_queue_worker)

if __name__ == "__main__":
    socketio.run(
        app,
        host="0.0.0.0",
        port=5000,
        debug=os.environ.get("ENV", "development") == "development",
    )

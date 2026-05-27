from flask import Blueprint, render_template, request, session
from models import Stock
from flask_login import login_required, current_user

dashboard = Blueprint(
    "dashboard", __name__, template_folder="templates", static_folder="static"
)

@dashboard.route("/", strict_slashes=True)
@login_required
def index():
    if request.method == "GET":
        stocks = Stock.query.order_by(Stock.timestamp.desc()).limit(100).all()
        return render_template("dashboard.html", user=current_user, stocks=stocks)

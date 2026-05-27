from flask import Blueprint, render_template
from flask_login import login_required, current_user

home = Blueprint("home", __name__, template_folder="templates", static_folder="static")

@home.route("/",  strict_slashes=False)
def index():
    return render_template("index.html", user=current_user)

@home.route("/about", strict_slashes=False)
def about():
    return render_template("about.html", user=current_user)
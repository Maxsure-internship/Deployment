from flask import Blueprint, render_template, request, flash, redirect, url_for
from models import db, User
from flask_mail import Message
from werkzeug.security import generate_password_hash, check_password_hash
from flask_login import login_user, logout_user
from extensions import serializer, mailer
import os

auth = Blueprint("auth", __name__, template_folder="templates", static_folder="static")


@auth.route("/register", methods=["GET", "POST"], strict_slashes=False)
def register():
    if request.method == "GET":
        return render_template("register.html")
    elif request.method == "POST":
        mail, password = request.form.get("mail", None), request.form.get(
            "password", None
        )
        if not mail or not password:
            flash("There are some missing fields in the registration form.")
            return render_template("register.html")

        existing_user = User.query.filter_by(mail=mail).first()
        if existing_user:
            flash("An account with this mail already exists.")
            return redirect(url_for("auth.register"))

        new_user = User(mail=mail, password=generate_password_hash(password))
        db.session.add(new_user)
        db.session.commit()
        flash("Account succesfully registered")

        return redirect(url_for("auth.login"))


@auth.route("/login", methods=["GET", "POST"], strict_slashes=False)
def login():
    if request.method == "GET":
        return render_template("login.html")
    elif request.method == "POST":
        mail, password = request.form.get("mail", None), request.form.get(
            "password", None
        )
        if not mail or not password:
            flash("There are some missing fields in the login form.")

        existing_user = User.query.filter_by(mail=mail).first()
        if existing_user and check_password_hash(existing_user.password, password):
            login_user(existing_user)
            return redirect(url_for("dashboard.index"))
        else:
            flash("Incorrect mail or password.")
            return redirect(url_for("auth.login"))
        
@auth.route("/logout")
def logout():
    logout_user()
    return redirect(url_for("auth.login"))


@auth.route("/forgot-password", methods=["GET", "POST"])
def forgot():
    if request.method == "POST":
        mail = request.form.get("mail", None)
        if not mail:
            flash("Email required.")
            return redirect(url_for("auth.forgot"))
        existing_user = User.query.filter_by(mail=mail).first()
        if existing_user:
            token = serializer.dumps(existing_user.mail)

            # generating reset link
            reset_link = url_for("auth.reset", token=token, _external=True)

            # sending the mail link
            message = Message(
                "Password Reset Request",
                sender= os.environ.get("SMTP_USER", ""),
                recipients=[mail],
            )
            message.body = f""" 
            Click the link below to reset your password\n
            {reset_link}\n
            This link expires in 15min
            """
            mailer.send(message)

            return f"A reset mail has been send to your mail id {mail}"
    return render_template("forgot.html")


@auth.route("/reset-password/<token>", methods=["GET", "POST"])
def reset(token):
    try:
        mail = serializer.loads(token, max_age=15 * 60)
    except:
        return "Invalid or expired reset link."

    existing_user = User.query.filter_by(mail=mail).first()
    if not existing_user:
        return "Invalid mail."

    if request.method == "POST":
        new_password = request.form.get("password", None)
        if not new_password:
            flash("Password required.")
            return "Password required."
        existing_user.password = generate_password_hash(new_password)
        db.session.commit()
        return redirect(url_for("auth.login"))
    return render_template("reset.html")

from datetime import datetime, timedelta, timezone
import os

from flask import Flask, redirect, render_template, request, url_for
from flask_sqlalchemy import SQLAlchemy
from flask_login import (
    current_user,
    login_required,
    login_user,
    LoginManager,
    logout_user,
    UserMixin
)
from werkzeug.security import check_password_hash, generate_password_hash


app = Flask(__name__)
app.config["DEBUG"] = True


# -------------------
# SECURITY (FIXED)
# -------------------
app.secret_key = os.environ.get("SECRET_KEY", "dev-secret-key")


# -------------------
# SQLITE (KUBERNETES FRIENDLY)
# -------------------
# safer default for containers
app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///comments.db"
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
app.config["SQLALCHEMY_ENGINE_OPTIONS"] = {
    "connect_args": {"timeout": 299}
}

db = SQLAlchemy(app)


# -------------------
# LOGIN CONFIG
# -------------------
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = "login"


# -------------------
# USER MODEL
# -------------------
class User(UserMixin, db.Model):
    __tablename__ = "users"

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(128), unique=True, nullable=False)
    password_hash = db.Column(db.String(256), nullable=False)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)


@login_manager.user_loader
def load_user(user_id):
    return db.session.get(User, int(user_id))


# -------------------
# COMMENT MODEL
# -------------------
class Comment(db.Model):
    __tablename__ = "comments"

    id = db.Column(db.Integer, primary_key=True)
    content = db.Column(db.String(4096), nullable=False)

    posted = db.Column(
        db.DateTime,
        default=lambda: datetime.now(timezone.utc)
    )

    user_id = db.Column(db.Integer, db.ForeignKey("users.id"))
    user = db.relationship("User")


# -------------------
# ROUTES
# -------------------
@app.route("/", methods=["GET"])
def index():
    return render_template("main_page.html")


@app.route("/portfolio/")
def portfolio():
    return render_template("portfolio_page.html")


# -------------------
# LOGIN + COMMENTS
# -------------------
@app.route("/login/", methods=["GET", "POST"])
def login():

    # LOGIN
    if request.method == "POST" and "username" in request.form:

        username = request.form["username"]
        password = request.form["password"]

        user = User.query.filter_by(username=username).first()

        if user and user.check_password(password):
            login_user(user)
            return redirect(url_for("index"))  # FIXED

        return render_template("login_page.html", error=True, comments=[])

    # COMMENT
    if request.method == "POST" and "contents" in request.form:

        if current_user.is_authenticated:
            content = request.form.get("contents")

            if content and content.strip():
                db.session.add(Comment(
                    content=content.strip(),
                    user=current_user
                ))
                db.session.commit()

        return redirect(url_for("login"))

    # LOAD COMMENTS
    comments = Comment.query.order_by(Comment.posted.desc()).all()

    # Singapore time
    SGT = timezone(timedelta(hours=8))

    for c in comments:
        if c.posted:
            c.display_time = c.posted.astimezone(SGT)

    return render_template(
        "login_page.html",
        error=False,
        comments=comments
    )


# -------------------
# LOGOUT
# -------------------
@app.route("/logout/")
@login_required
def logout():
    logout_user()
    return redirect(url_for("login"))


# -------------------
# INIT DB + USERS
# -------------------
if __name__ == "__main__":
    with app.app_context():
        db.create_all()

        users = [
            ("admin", "secret"),
            ("bob", "less-secret"),
            ("caroline", "completely-secret"),
            ("tester", "super-secret"),
        ]

        for username, password in users:
            if not User.query.filter_by(username=username).first():
                db.session.add(User(
                    username=username,
                    password_hash=generate_password_hash(password)
                ))

        db.session.commit()

    app.run(host="0.0.0.0", port=5000)
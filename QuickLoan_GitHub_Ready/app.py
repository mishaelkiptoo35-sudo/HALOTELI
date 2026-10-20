import os
import sqlite3
import secrets
import hashlib
from datetime import datetime, timedelta, timezone
from functools import wraps

from flask import (
    Flask, render_template, request, redirect, url_for, flash,
    session, abort
)
from werkzeug.security import check_password_hash, generate_password_hash

app = Flask(__name__)
app.secret_key = os.environ.get("APP_SECRET_KEY", "change-this-development-key")
DATABASE_PATH = os.environ.get("DATABASE_PATH", "quickloan.db")
ADMIN_USERNAME = os.environ.get("ADMIN_USERNAME", "admin")
ADMIN_PASSWORD_HASH = os.environ.get(
    "ADMIN_PASSWORD_HASH",
    generate_password_hash(os.environ.get("ADMIN_PASSWORD", "ChangeMe123!"))
)

def db():
    connection = sqlite3.connect(DATABASE_PATH)
    connection.row_factory = sqlite3.Row
    return connection

def init_db():
    with db() as con:
        con.execute("""
            CREATE TABLE IF NOT EXISTS applications (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                full_name TEXT NOT NULL,
                phone TEXT NOT NULL,
                amount REAL NOT NULL,
                purpose TEXT NOT NULL,
                status TEXT NOT NULL DEFAULT 'Pending',
                created_at TEXT NOT NULL
            )
        """)
        con.execute("""
            CREATE TABLE IF NOT EXISTS admin_links (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                token_hash TEXT NOT NULL UNIQUE,
                expires_at TEXT NOT NULL,
                revoked INTEGER NOT NULL DEFAULT 0,
                created_at TEXT NOT NULL
            )
        """)

def admin_required(view):
    @wraps(view)
    def wrapped(*args, **kwargs):
        if not session.get("admin_logged_in"):
            return redirect(url_for("admin_login"))
        return view(*args, **kwargs)
    return wrapped

@app.context_processor
def inject_year():
    return {"current_year": datetime.now().year}

@app.route("/")
def index():
    return render_template("index.html")

@app.route("/apply", methods=["GET", "POST"])
def apply():
    if request.method == "POST":
        full_name = request.form.get("full_name", "").strip()
        phone = request.form.get("phone", "").strip()
        purpose = request.form.get("purpose", "").strip()
        try:
            amount = float(request.form.get("amount", "0"))
        except ValueError:
            amount = 0

        if not full_name or not phone or not purpose or amount <= 0:
            flash("Please complete every field with valid information.", "error")
            return render_template("apply.html")

        with db() as con:
            cur = con.execute("""
                INSERT INTO applications (full_name, phone, amount, purpose, status, created_at)
                VALUES (?, ?, ?, ?, 'Pending', ?)
            """, (
                full_name, phone, amount, purpose,
                datetime.now(timezone.utc).isoformat()
            ))
            application_id = cur.lastrowid
        return redirect(url_for("received", app_id=application_id))
    return render_template("apply.html")

@app.route("/application/<int:app_id>")
def received(app_id):
    with db() as con:
        application = con.execute(
            "SELECT id, full_name, amount, status FROM applications WHERE id=?",
            (app_id,)
        ).fetchone()
    if not application:
        abort(404)
    return render_template("received.html", application=application)

@app.route("/status", methods=["GET", "POST"])
def status():
    application = None
    searched = False
    if request.method == "POST":
        searched = True
        try:
            app_id = int(request.form.get("application_id", "0"))
        except ValueError:
            app_id = 0
        with db() as con:
            application = con.execute(
                "SELECT id, full_name, amount, status, created_at FROM applications WHERE id=?",
                (app_id,)
            ).fetchone()
    return render_template("status.html", application=application, searched=searched)

@app.route("/admin/login", methods=["GET", "POST"])
def admin_login():
    if request.method == "POST":
        username = request.form.get("username", "")
        password = request.form.get("password", "")
        if username == ADMIN_USERNAME and check_password_hash(ADMIN_PASSWORD_HASH, password):
            session["admin_logged_in"] = True
            return redirect(url_for("admin_dashboard"))
        flash("Incorrect username or password.", "error")
    return render_template("admin_login.html")

@app.route("/admin")
@admin_required
def admin_dashboard():
    with db() as con:
        applications = con.execute(
            "SELECT * FROM applications ORDER BY id DESC"
        ).fetchall()
        links = con.execute(
            "SELECT * FROM admin_links ORDER BY id DESC"
        ).fetchall()
    return render_template("admin.html", applications=applications, links=links)

@app.route("/admin/application/<int:app_id>/status", methods=["POST"])
@admin_required
def update_status(app_id):
    new_status = request.form.get("status", "")
    allowed = {"Pending", "Under Review", "Approved", "Declined"}
    if new_status not in allowed:
        flash("Invalid status.", "error")
    else:
        with db() as con:
            con.execute("UPDATE applications SET status=? WHERE id=?", (new_status, app_id))
        flash(f"Application #{app_id} status updated.", "success")
    return redirect(url_for("admin_dashboard"))

@app.route("/admin/create-link", methods=["POST"])
@admin_required
def create_link():
    try:
        minutes = int(request.form.get("minutes", "60"))
    except ValueError:
        minutes = 60
    minutes = max(5, min(minutes, 10080))
    token = secrets.token_urlsafe(32)
    token_hash = hashlib.sha256(token.encode()).hexdigest()
    now = datetime.now(timezone.utc)
    expires = now + timedelta(minutes=minutes)
    with db() as con:
        con.execute(
            "INSERT INTO admin_links (token_hash, expires_at, created_at) VALUES (?, ?, ?)",
            (token_hash, expires.isoformat(), now.isoformat())
        )
    # The token is shown once to the logged-in admin. Treat it like a password.
    flash("Temporary link (copy it now; it will not be shown again): " +
          url_for("admin_access", token=token, _external=True), "success")
    return redirect(url_for("admin_dashboard"))

@app.route("/admin/access/<token>")
def admin_access(token):
    token_hash = hashlib.sha256(token.encode()).hexdigest()
    with db() as con:
        link = con.execute(
            "SELECT * FROM admin_links WHERE token_hash=?", (token_hash,)
        ).fetchone()
    if not link or link["revoked"]:
        return render_template("expired.html", message="This access link is invalid or has been revoked."), 403
    try:
        expires_at = datetime.fromisoformat(link["expires_at"])
        if expires_at < datetime.now(timezone.utc):
            return render_template("expired.html", message="This access link has expired."), 403
    except ValueError:
        return render_template("expired.html", message="This access link is invalid."), 403
    # This demo link does not bypass the regular admin login.
    flash("Link checked. Please sign in with your admin account.", "success")
    return redirect(url_for("admin_login"))

@app.route("/admin/link/<int:link_id>/revoke", methods=["POST"])
@admin_required
def revoke_link(link_id):
    with db() as con:
        con.execute("UPDATE admin_links SET revoked=1 WHERE id=?", (link_id,))
    flash("Access link revoked.", "success")
    return redirect(url_for("admin_dashboard"))

@app.route("/admin/logout", methods=["POST"])
@admin_required
def admin_logout():
    session.clear()
    return redirect(url_for("index"))

@app.errorhandler(404)
def not_found(_error):
    return render_template("error.html", code=404, message="The page you requested could not be found."), 404

if __name__ == "__main__":
    init_db()
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)), debug=False)

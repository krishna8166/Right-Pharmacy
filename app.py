"""
QuickMart — Web Application
===========================
Run locally:
    pip install flask
    python app.py
    → Customer : http://localhost:5000
    → Admin    : http://localhost:5000/admin   (password: admin123)

Deploy free to Render / Railway:
    Add a Procfile:  web: gunicorn app:app
    pip install gunicorn, push repo, done.
"""

from flask import (Flask, render_template, request, jsonify,
                   session, redirect, url_for)
from functools import wraps
import sqlite3, json
from datetime import datetime
import os

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "right-pharmacy-secret-2026")

DB_PATH        = os.environ.get("DB_PATH", "retail_shop.db")
ADMIN_PASSWORD = os.environ.get("ADMIN_PASSWORD", "admin123")
SHOP_NAME      = "Right Pharmacy"

# Updated SAMPLE_ITEMS in app.py
SAMPLE_ITEMS = [
    ("CTD-M 6.25/52",   "Blood Pressure", 120.00, 50),
    ("FEBUTEC-40",     "Gout",           210.00, 30),
    ("THYRONORM 50",   "Thyroid",        185.00, 100),
    ("NAPROSYN-D 500", "Pain Relief",    95.00,  40),
    ("CETISHAPE",      "Allergy",        55.00,  60),
]

# ═══════════════════════════════════════════════════════
#  DATABASE
# ═══════════════════════════════════════════════════════
def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    with get_db() as c:
        c.executescript("""
            CREATE TABLE IF NOT EXISTS items (
                id       INTEGER PRIMARY KEY AUTOINCREMENT,
                name     TEXT    NOT NULL,
                category TEXT    NOT NULL,
                price    REAL    NOT NULL,
                stock    INTEGER NOT NULL DEFAULT 0
            );
            CREATE TABLE IF NOT EXISTS orders (
                id            INTEGER PRIMARY KEY AUTOINCREMENT,
                customer_name TEXT    NOT NULL,
                items_json    TEXT    NOT NULL,
                total         REAL    NOT NULL,
                status        TEXT    DEFAULT 'pending',
                created_at    TEXT    NOT NULL,
                delivered_at  TEXT
            );
            CREATE TABLE IF NOT EXISTS sales (
                id            INTEGER PRIMARY KEY AUTOINCREMENT,
                order_id      INTEGER NOT NULL,
                customer_name TEXT    NOT NULL,
                items_json    TEXT    NOT NULL,
                amount        REAL    NOT NULL,
                sale_date     TEXT    NOT NULL,
                FOREIGN KEY(order_id) REFERENCES orders(id)
            );
        """)
        if c.execute("SELECT COUNT(*) FROM items").fetchone()[0] == 0:
            c.executemany(
                "INSERT INTO items(name,category,price,stock) VALUES(?,?,?,?)",
                SAMPLE_ITEMS)
        c.commit()

# ═══════════════════════════════════════════════════════
#  AUTH
# ═══════════════════════════════════════════════════════
def admin_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if not session.get("admin_logged_in"):
            return redirect(url_for("admin_login_page"))
        return f(*args, **kwargs)
    return decorated

# ═══════════════════════════════════════════════════════
#  CUSTOMER ROUTES
# ═══════════════════════════════════════════════════════
@app.route("/")
def customer():
    return render_template("customer.html", shop_name=SHOP_NAME)

@app.route("/api/items")
def api_items():
    category = request.args.get("category", "")
    search   = request.args.get("search", "").strip()
    q, p, conds = "SELECT * FROM items", [], []
    if category and category != "All":
        conds.append("category=?"); p.append(category)
    if search:
        conds.append("name LIKE ?"); p.append(f"%{search}%")
    if conds:
        q += " WHERE " + " AND ".join(conds)
    q += " ORDER BY category, name"
    with get_db() as c:
        rows = c.execute(q, p).fetchall()
    return jsonify([dict(r) for r in rows])

@app.route("/api/order", methods=["POST"])
def api_place_order():
    data  = request.get_json()
    name  = data.get("customer_name", "").strip()
    items = data.get("items", [])
    total = data.get("total", 0)
    if not name or not items:
        return jsonify({"error": "Missing name or items"}), 400
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    with get_db() as c:
        cur = c.execute(
            "INSERT INTO orders(customer_name,items_json,total,status,created_at)"
            " VALUES(?,?,?,?,?)",
            (name, json.dumps(items), total, "pending", now))
        c.commit()
    return jsonify({"order_id": cur.lastrowid})

# ═══════════════════════════════════════════════════════
#  ADMIN AUTH ROUTES
# ═══════════════════════════════════════════════════════
@app.route("/admin")
def admin_redirect():
    if session.get("admin_logged_in"):
        return redirect(url_for("admin_dashboard"))
    return redirect(url_for("admin_login_page"))

@app.route("/admin/login", methods=["GET"])
def admin_login_page():
    if session.get("admin_logged_in"):
        return redirect(url_for("admin_dashboard"))
    return render_template("admin.html", shop_name=SHOP_NAME, page="login")

@app.route("/admin/login", methods=["POST"])
def admin_login_post():
    data = request.get_json()
    if data and data.get("password") == ADMIN_PASSWORD:
        session["admin_logged_in"] = True
        return jsonify({"ok": True})
    return jsonify({"ok": False, "error": "Incorrect password"}), 401

@app.route("/admin/logout")
def admin_logout():
    session.pop("admin_logged_in", None)
    return redirect(url_for("admin_login_page"))

@app.route("/admin/dashboard")
@admin_required
def admin_dashboard():
    return render_template("admin.html", shop_name=SHOP_NAME, page="dashboard", now_date=datetime.now().strftime("%Y-%m-%d"))

# ═══════════════════════════════════════════════════════
#  ADMIN API ROUTES
# ═══════════════════════════════════════════════════════
@app.route("/api/admin/stats")
@admin_required
def api_stats():
    today = datetime.now().strftime("%Y-%m-%d")
    with get_db() as c:
        pending  = c.execute("SELECT COUNT(*) FROM orders WHERE status='pending'").fetchone()[0]
        revenue  = c.execute("SELECT COALESCE(SUM(amount),0) FROM sales WHERE sale_date=?",
                             (today,)).fetchone()[0]
        no_stock = c.execute("SELECT COUNT(*) FROM items WHERE stock=0").fetchone()[0]
    return jsonify({"pending": pending, "today_rev": revenue, "out_of_stock": no_stock})

@app.route("/api/admin/orders")
@admin_required
def api_orders():
    with get_db() as c:
        rows = c.execute(
            "SELECT * FROM orders WHERE status='pending'"
            " ORDER BY created_at DESC").fetchall()
    return jsonify([dict(r) for r in rows])

@app.route("/api/admin/deliver/<int:oid>", methods=["POST"])
@admin_required
def api_deliver(oid):
    with get_db() as c:
        o = c.execute("SELECT * FROM orders WHERE id=?", (oid,)).fetchone()
        if not o:
            return jsonify({"error": "Order not found"}), 404
        if o["status"] != "pending":
            return jsonify({"error": "Already delivered"}), 400
        items = json.loads(o["items_json"])
        for it in items:
            c.execute("UPDATE items SET stock=MAX(0,stock-?) WHERE id=?",
                      (it["qty"], it["id"]))
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        c.execute("UPDATE orders SET status='delivered',delivered_at=? WHERE id=?",
                  (now, oid))
        c.execute(
            "INSERT INTO sales(order_id,customer_name,items_json,amount,sale_date)"
            " VALUES(?,?,?,?,?)",
            (oid, o["customer_name"], o["items_json"], o["total"], now[:10]))
        c.commit()
    return jsonify({"ok": True})

@app.route("/api/admin/inventory")
@admin_required
def api_inventory():
    search = request.args.get("search", "").strip()
    q, p = "SELECT * FROM items", []
    if search:
        q += " WHERE name LIKE ?"; p.append(f"%{search}%")
    q += " ORDER BY category, name"
    with get_db() as c:
        rows = c.execute(q, p).fetchall()
    return jsonify([dict(r) for r in rows])

@app.route("/api/admin/stock/<int:iid>", methods=["POST"])
@admin_required
def api_stock(iid):
    data = request.get_json()
    with get_db() as c:
        if "value" in data:
            c.execute("UPDATE items SET stock=MAX(0,?) WHERE id=?",
                      (int(data["value"]), iid))
        elif "delta" in data:
            c.execute("UPDATE items SET stock=MAX(0,stock+?) WHERE id=?",
                      (int(data["delta"]), iid))
        c.commit()
        row = c.execute("SELECT stock FROM items WHERE id=?", (iid,)).fetchone()
    return jsonify({"ok": True, "stock": row["stock"] if row else 0})

@app.route("/api/admin/sales")
@admin_required
def api_sales():
    date = request.args.get("date", "").strip()
    q, p = "SELECT * FROM sales", []
    if date:
        q += " WHERE sale_date=?"; p.append(date)
    q += " ORDER BY id DESC"
    with get_db() as c:
        rows = c.execute(q, p).fetchall()
        total = c.execute(
            "SELECT COALESCE(SUM(amount),0) FROM sales" +
            (" WHERE sale_date=?" if date else ""),
            ([date] if date else [])).fetchone()[0]
    return jsonify({"sales": [dict(r) for r in rows], "total": total})

# ═══════════════════════════════════════════════════════
#  STARTUP
# ═══════════════════════════════════════════════════════
init_db()
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    print(f"\n{'='*50}")
    print(f"  {SHOP_NAME} is running!")
    print(f"  Customer : http://localhost:{port}")
    print(f"  Admin    : http://localhost:{port}/admin")
    print(f"  Password : {ADMIN_PASSWORD}")
    print(f"{'='*50}\n")
    app.run(host="0.0.0.0", port=port, debug=False)

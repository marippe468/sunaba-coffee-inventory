from flask import Flask, render_template, request, redirect, url_for, session, flash
import sqlite3
import re
import secrets
from functools import wraps
from datetime import datetime
from werkzeug.security import check_password_hash, generate_password_hash

app = Flask(__name__)
app.secret_key = "sunaba-coffee-change-this-secret-key"
DB_NAME = "sunaba_coffee.db"


def get_db():
    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row
    return conn


def login_required(view):
    @wraps(view)
    def wrapped_view(*args, **kwargs):
        if "employee_id" not in session:
            return redirect(url_for("login"))
        return view(*args, **kwargs)
    return wrapped_view


def admin_required(view):
    @wraps(view)
    def wrapped_view(*args, **kwargs):
        if "employee_id" not in session:
            return redirect(url_for("login"))
        if session.get("role") != "admin":
            flash("管理者のみ利用できます。", "error")
            return redirect(url_for("home"))
        return view(*args, **kwargs)
    return wrapped_view


@app.route("/login", methods=["GET", "POST"])
def login():
    if "employee_id" in session:
        return redirect(url_for("home"))

    if request.method == "POST":
        employee_id = request.form["employee_id"].strip()
        password = request.form["password"]

        # 従業員ID・パスワードは半角英数字のみ受け付ける
        if not re.fullmatch(r"[A-Za-z0-9]+", employee_id) or not re.fullmatch(r"[A-Za-z0-9]+", password):
            flash("従業員IDとパスワードは半角英数字で入力してください。", "error")
            return render_template("login.html")

        conn = get_db()
        employee = conn.execute(
            "SELECT * FROM employees WHERE employee_id = ?",
            (employee_id,)
        ).fetchone()
        conn.close()

        if employee and check_password_hash(employee["password_hash"], password):
            session.clear()
            session["employee_id"] = employee["employee_id"]
            session["employee_name"] = employee["employee_name"]
            session["role"] = employee["role"]
            return redirect(url_for("home"))

        flash("従業員IDまたはパスワードが違います。", "error")

    return render_template("login.html")


@app.route("/logout")
def logout():
    employee_name = session.get("employee_name", "")
    month = datetime.now().month

    if month in (3, 4, 5):
        seasonal_messages = [
            "春のやわらかな風が心地よい季節ですね。",
            "新緑がきれいな季節になりました。",
            "春の日差しにほっとする季節ですね。",
        ]
    elif month in (6, 7, 8):
        seasonal_messages = [
            "暑い日が続きます。どうぞ涼しくしてお過ごしください。",
            "夏の日差しがまぶしい季節ですね。水分補給もお忘れなく。",
            "今日も暑い一日でしたね。ゆっくりお休みください。",
        ]
    elif month in (9, 10, 11):
        seasonal_messages = [
            "秋の気配を感じる季節になりました。",
            "朝夕の風が少しずつ涼しくなってきましたね。",
            "実りの秋、コーヒーがいっそう美味しい季節ですね。",
        ]
    else:
        seasonal_messages = [
            "寒い日が続きます。暖かくしてお過ごしください。",
            "温かいコーヒーがうれしい季節ですね。",
            "冷え込む季節です。どうぞ暖かくしてお帰りください。",
        ]

    closing_messages = [
        "今日も一日お疲れさまでした。",
        "本日もお疲れさまでした。",
        "今日もありがとうございました。ゆっくりお休みください。",
        "お疲れさまでした。また次回もよろしくお願いします。",
    ]

    seasonal_message = secrets.choice(seasonal_messages)
    closing_message = secrets.choice(closing_messages)
    session.clear()

    return render_template(
        "login.html",
        logged_out=True,
        logout_name=employee_name,
        seasonal_message=seasonal_message,
        closing_message=closing_message,
    )


@app.route("/")
@login_required
def home():
    conn = get_db()
    products = conn.execute(
        "SELECT * FROM products ORDER BY product_id"
    ).fetchall()
    conn.close()
    return render_template("index.html", products=products)


@app.route("/products/<int:product_id>")
@login_required
def product_detail(product_id):
    conn = get_db()
    product = conn.execute(
        "SELECT * FROM products WHERE product_id = ?",
        (product_id,)
    ).fetchone()
    conn.close()

    if product is None:
        flash("商品が見つかりません。", "error")
        return redirect(url_for("home"))

    return render_template("product_detail.html", product=product)


@app.route("/stock", methods=["GET", "POST"])
@login_required
def stock():
    conn = get_db()

    if request.method == "POST":
        product_id = request.form["product_id"]
        process_code = request.form["process_code"]
        quantity = int(request.form["quantity"])
        confirmed = request.form.get("confirmed") == "1"

        product = conn.execute(
            "SELECT * FROM products WHERE product_id = ?",
            (product_id,)
        ).fetchone()
        process = conn.execute(
            "SELECT * FROM process_types WHERE process_code = ? AND is_visible = 1",
            (process_code,)
        ).fetchone()

        if product is None or process is None or quantity < 1:
            conn.close()
            flash("入力内容を確認してください。", "error")
            return redirect(url_for("stock"))

        # 棚卸調整は「数量＝棚卸後の実在庫」として扱う
        if process_code == "AD":
            new_stock = quantity
        elif process_code in ("IN", "RT"):
            new_stock = product["stock"] + quantity
        else:  # 消費・廃棄・破損
            new_stock = product["stock"] - quantity

        if new_stock < 0:
            conn.close()
            flash("在庫数がマイナスになるため登録できません。", "error")
            return redirect(url_for("stock", product_id=product_id))

        if not confirmed:
            visible_processes = conn.execute(
                "SELECT * FROM process_types WHERE is_visible = 1 ORDER BY rowid"
            ).fetchall()
            hidden_processes = conn.execute(
                "SELECT * FROM process_types WHERE is_visible = 0 ORDER BY rowid"
            ).fetchall()
            products = conn.execute("SELECT * FROM products ORDER BY product_id").fetchall()
            conn.close()
            return render_template(
                "stock.html",
                products=products,
                visible_processes=visible_processes,
                hidden_processes=hidden_processes,
                selected_product_id=int(product_id),
                confirmation={
                    "product_id": product_id,
                    "product_name": product["product_name"],
                    "process_code": process_code,
                    "process_name": process["process_name"],
                    "quantity": quantity,
                    "unit": product["unit"],
                    "employee_name": session["employee_name"],
                }
            )

        created_at = datetime.now().strftime("%Y/%m/%d %H:%M")
        conn.execute(
            "UPDATE products SET stock = ? WHERE product_id = ?",
            (new_stock, product_id)
        )
        conn.execute(
            """INSERT INTO transactions
               (created_at, product_id, process_type, quantity, employee_id)
               VALUES (?, ?, ?, ?, ?)""",
            (created_at, product_id, process["process_name"], quantity, session["employee_id"])
        )
        conn.commit()
        conn.close()

        flash(
            f'✓ {product["product_name"]} {quantity}{product["unit"]}を{process["process_name"]}として登録しました。',
            "success"
        )
        return redirect(url_for("home"))

    selected_product_id = request.args.get("product_id", type=int)
    products = conn.execute("SELECT * FROM products ORDER BY product_id").fetchall()
    visible_processes = conn.execute(
        "SELECT * FROM process_types WHERE is_visible = 1 ORDER BY rowid"
    ).fetchall()
    hidden_processes = conn.execute(
        "SELECT * FROM process_types WHERE is_visible = 0 ORDER BY rowid"
    ).fetchall()
    conn.close()

    return render_template(
        "stock.html",
        products=products,
        visible_processes=visible_processes,
        hidden_processes=hidden_processes,
        selected_product_id=selected_product_id
    )


@app.route("/settings/process-types")
@admin_required
def process_settings():
    conn = get_db()
    process_types = conn.execute(
        "SELECT * FROM process_types ORDER BY rowid"
    ).fetchall()
    conn.close()
    return render_template("process_settings.html", process_types=process_types)


@app.route("/process-types/<process_code>/toggle", methods=["POST"])
@admin_required
def toggle_process_type(process_code):
    if process_code in ("IN", "CO", "DI"):
        flash("入荷・消費・廃棄は常時表示します。", "error")
        return redirect(url_for("process_settings"))

    conn = get_db()
    process = conn.execute(
        "SELECT * FROM process_types WHERE process_code = ?",
        (process_code,)
    ).fetchone()

    if process:
        conn.execute(
            "UPDATE process_types SET is_visible = ? WHERE process_code = ?",
            (0 if process["is_visible"] else 1, process_code)
        )
        conn.commit()

    conn.close()
    return redirect(url_for("process_settings"))


@app.route("/history")
@login_required
def history():
    date_from = request.args.get("date_from", "").strip()
    date_to = request.args.get("date_to", "").strip()
    product_id = request.args.get("product_id", "").strip()
    process_type = request.args.get("process_type", "").strip()
    employee_id = request.args.get("employee_id", "").strip()

    sql = """
        SELECT t.transaction_id, t.created_at, p.product_name,
               t.process_type, t.quantity, p.unit,
               COALESCE(e.employee_name, '旧データ') AS employee_name
        FROM transactions t
        JOIN products p ON t.product_id = p.product_id
        LEFT JOIN employees e ON t.employee_id = e.employee_id
        WHERE 1 = 1
    """
    params = []

    if date_from:
        sql += " AND substr(t.created_at, 1, 10) >= ?"
        params.append(date_from.replace("-", "/"))
    if date_to:
        sql += " AND substr(t.created_at, 1, 10) <= ?"
        params.append(date_to.replace("-", "/"))
    if product_id:
        sql += " AND t.product_id = ?"
        params.append(product_id)
    if process_type:
        sql += " AND t.process_type = ?"
        params.append(process_type)
    if employee_id:
        sql += " AND t.employee_id = ?"
        params.append(employee_id)

    sql += " ORDER BY t.transaction_id DESC"

    conn = get_db()
    transactions = conn.execute(sql, params).fetchall()
    products = conn.execute("SELECT * FROM products ORDER BY product_name").fetchall()
    process_types = conn.execute("SELECT * FROM process_types ORDER BY rowid").fetchall()
    employees = conn.execute("SELECT employee_id, employee_name FROM employees ORDER BY employee_id").fetchall()
    conn.close()

    return render_template(
        "history.html",
        transactions=transactions,
        products=products,
        process_types=process_types,
        employees=employees,
        filters={
            "date_from": date_from,
            "date_to": date_to,
            "product_id": product_id,
            "process_type": process_type,
            "employee_id": employee_id,
        }
    )


@app.route("/history/<int:transaction_id>")
@login_required
def history_detail(transaction_id):
    conn = get_db()
    transaction = conn.execute(
        """
        SELECT t.*, p.product_name, p.unit,
               COALESCE(e.employee_name, '旧データ') AS employee_name
        FROM transactions t
        JOIN products p ON t.product_id = p.product_id
        LEFT JOIN employees e ON t.employee_id = e.employee_id
        WHERE t.transaction_id = ?
        """,
        (transaction_id,)
    ).fetchone()
    corrections = conn.execute(
        """
        SELECT c.*, e.employee_name
        FROM transaction_corrections c
        LEFT JOIN employees e ON c.corrected_by = e.employee_id
        WHERE c.transaction_id = ?
        ORDER BY c.correction_id DESC
        """,
        (transaction_id,)
    ).fetchall()
    conn.close()

    if transaction is None:
        flash("履歴が見つかりません。", "error")
        return redirect(url_for("history"))

    return render_template(
        "history_detail.html",
        transaction=transaction,
        corrections=corrections
    )


@app.route("/history/<int:transaction_id>/edit", methods=["GET", "POST"])
@login_required
def history_edit(transaction_id):
    conn = get_db()
    transaction = conn.execute(
        """
        SELECT t.*, p.product_name, p.unit
        FROM transactions t
        JOIN products p ON t.product_id = p.product_id
        WHERE t.transaction_id = ?
        """,
        (transaction_id,)
    ).fetchone()

    if transaction is None:
        conn.close()
        flash("履歴が見つかりません。", "error")
        return redirect(url_for("history"))

    if request.method == "POST":
        new_quantity = int(request.form["quantity"])
        reason = request.form["reason"].strip()

        if new_quantity < 1 or not reason:
            conn.close()
            flash("訂正数量と訂正理由を入力してください。", "error")
            return redirect(url_for("history_edit", transaction_id=transaction_id))

        difference = new_quantity - transaction["quantity"]
        product = conn.execute(
            "SELECT * FROM products WHERE product_id = ?",
            (transaction["product_id"],)
        ).fetchone()

        # 元処理が在庫を増やすものなら差分を加算、減らすものなら差分を減算。
        # 棚卸調整は過去の実在庫値なので自動再計算せず、訂正記録のみ残す。
        if transaction["process_type"] in ("入荷", "返品"):
            new_stock = product["stock"] + difference
        elif transaction["process_type"] in ("消費", "廃棄", "破損"):
            new_stock = product["stock"] - difference
        else:
            new_stock = product["stock"]

        if new_stock < 0:
            conn.close()
            flash("訂正すると在庫数がマイナスになるため確定できません。", "error")
            return redirect(url_for("history_edit", transaction_id=transaction_id))

        corrected_at = datetime.now().strftime("%Y/%m/%d %H:%M")

        conn.execute(
            """
            INSERT INTO transaction_corrections
            (transaction_id, old_quantity, new_quantity, reason, corrected_at, corrected_by)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                transaction_id,
                transaction["quantity"],
                new_quantity,
                reason,
                corrected_at,
                session["employee_id"],
            )
        )
        conn.execute(
            "UPDATE transactions SET quantity = ? WHERE transaction_id = ?",
            (new_quantity, transaction_id)
        )
        if transaction["process_type"] != "棚卸調整":
            conn.execute(
                "UPDATE products SET stock = ? WHERE product_id = ?",
                (new_stock, transaction["product_id"])
            )

        conn.commit()
        conn.close()
        flash("✓ 履歴を訂正しました。訂正前の内容も記録されています。", "success")
        return redirect(url_for("history_detail", transaction_id=transaction_id))

    conn.close()
    return render_template("history_edit.html", transaction=transaction)


@app.route("/employees/new", methods=["GET", "POST"])
@admin_required
def employee_new():
    if request.method == "POST":
        employee_id = request.form["employee_id"].strip().upper()
        employee_name = request.form["employee_name"].strip()
        password = request.form["password"]
        role = request.form.get("role", "staff")

        if not re.fullmatch(r"[A-Za-z0-9]+", employee_id):
            flash("従業員IDは半角英数字で入力してください。", "error")
            return render_template("employee_new.html")
        if not re.fullmatch(r"[A-Za-z0-9]+", password):
            flash("パスワードは半角英数字で入力してください。", "error")
            return render_template("employee_new.html")
        if not employee_name:
            flash("氏名を入力してください。", "error")
            return render_template("employee_new.html")
        if role not in ("admin", "staff"):
            role = "staff"

        conn = get_db()
        exists = conn.execute(
            "SELECT 1 FROM employees WHERE employee_id = ?",
            (employee_id,)
        ).fetchone()
        if exists:
            conn.close()
            flash("この従業員IDはすでに登録されています。", "error")
            return render_template("employee_new.html")

        conn.execute(
            "INSERT INTO employees (employee_id, employee_name, password_hash, role) VALUES (?, ?, ?, ?)",
            (employee_id, employee_name, generate_password_hash(password), role)
        )
        conn.commit()
        conn.close()
        flash(f"✓ {employee_id} {employee_name} を登録しました。", "success")
        return redirect(url_for("home"))

    return render_template("employee_new.html")


@app.route("/products/new", methods=["GET", "POST"])
@admin_required
def product_new():
    if request.method == "POST":
        product_name = request.form["product_name"].strip()
        unit = request.form["unit"].strip()
        ideal_stock = int(request.form["ideal_stock"])
        stock_value = int(request.form["stock"])

        conn = get_db()
        conn.execute(
            """INSERT INTO products (product_name, stock, unit, ideal_stock)
               VALUES (?, ?, ?, ?)""",
            (product_name, stock_value, unit, ideal_stock)
        )
        conn.commit()
        conn.close()
        flash("✓ 商品を登録しました。", "success")
        return redirect(url_for("home"))

    return render_template("product_new.html")


if __name__ == "__main__":
    app.run(debug=True)

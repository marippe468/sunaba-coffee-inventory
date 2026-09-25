from flask import Flask, render_template, request, redirect, url_for
import sqlite3
from datetime import datetime

app = Flask(__name__)


def get_db():
    conn = sqlite3.connect("sunaba_coffee.db")
    return conn


# P1 商品在庫状況
@app.route("/")
def home():
    conn = get_db()
    cursor = conn.cursor()

    cursor.execute("SELECT * FROM products")
    products = cursor.fetchall()

    conn.close()

    return render_template("index.html", products=products)


# P2 入出荷管理
@app.route("/stock", methods=["GET", "POST"])
def stock():
    conn = get_db()
    cursor = conn.cursor()

    if request.method == "POST":

        product_id = request.form["product_id"]
        process_type = request.form["type"]
        quantity = int(request.form["quantity"])

        if process_type == "入荷":
            cursor.execute(
                "UPDATE products SET stock = stock + ? WHERE product_id = ?",
                (quantity, product_id)
            )

        elif process_type in ["消費", "廃棄"]:
            cursor.execute(
                "UPDATE products SET stock = stock - ? WHERE product_id = ?",
                (quantity, product_id)
            )

        created_at = datetime.now().strftime("%Y/%m/%d %H:%M")

        cursor.execute(
            """
            INSERT INTO transactions
            (created_at, product_id, process_type, quantity)
            VALUES (?, ?, ?, ?)
            """,
            (created_at, product_id, process_type, quantity)
        )

        conn.commit()
        conn.close()

        return redirect(url_for("home"))

    cursor.execute("SELECT * FROM products")
    products = cursor.fetchall()

    conn.close()

    return render_template("stock.html", products=products)


# P3 処理履歴
@app.route("/history")
def history():
    conn = get_db()
    cursor = conn.cursor()

    cursor.execute(
        """
        SELECT
            transactions.transaction_id,
            transactions.created_at,
            products.product_name,
            transactions.process_type,
            transactions.quantity,
            products.unit
        FROM transactions
        JOIN products
            ON transactions.product_id = products.product_id
        ORDER BY transactions.transaction_id DESC
        """
    )

    transactions = cursor.fetchall()

    conn.close()

    return render_template(
        "history.html",
        transactions=transactions
    )


# P4 コード登録
@app.route("/products/new", methods=["GET", "POST"])
def product_new():
    if request.method == "POST":

        product_name = request.form["product_name"]
        unit = request.form["unit"]
        ideal_stock = int(request.form["ideal_stock"])
        stock = int(request.form["stock"])

        conn = get_db()
        cursor = conn.cursor()

        cursor.execute(
            """
            INSERT INTO products
            (product_name, stock, unit, ideal_stock)
            VALUES (?, ?, ?, ?)
            """,
            (product_name, stock, unit, ideal_stock)
        )

        conn.commit()
        conn.close()

        return redirect(url_for("home"))

    return render_template("product_new.html")


if __name__ == "__main__":
    app.run(debug=True)
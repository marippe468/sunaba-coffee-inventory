import sqlite3
from werkzeug.security import generate_password_hash

DB_NAME = "sunaba_coffee.db"


def column_exists(cursor, table_name, column_name):
    columns = cursor.execute(f"PRAGMA table_info({table_name})").fetchall()
    return any(column[1] == column_name for column in columns)


def setup_database():
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS employees (
            employee_id TEXT PRIMARY KEY,
            employee_name TEXT NOT NULL,
            password_hash TEXT NOT NULL,
            role TEXT NOT NULL DEFAULT 'staff'
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS process_types (
            process_code TEXT PRIMARY KEY,
            process_name TEXT NOT NULL UNIQUE,
            is_visible INTEGER NOT NULL DEFAULT 0
        )
    """)

    process_types = [
        ("IN", "入荷", 1),
        ("CO", "消費", 1),
        ("DI", "廃棄", 1),
        ("RT", "返品", 0),
        ("AD", "棚卸調整", 0),
        ("DM", "破損", 0),
    ]
    cursor.executemany("""
        INSERT OR IGNORE INTO process_types
        (process_code, process_name, is_visible)
        VALUES (?, ?, ?)
    """, process_types)

    cursor.execute(
        "SELECT employee_id FROM employees WHERE employee_id = ?",
        ("E001",)
    )
    if cursor.fetchone() is None:
        cursor.execute("""
            INSERT INTO employees
            (employee_id, employee_name, password_hash, role)
            VALUES (?, ?, ?, ?)
        """, (
            "E001",
            "山田店長",
            generate_password_hash("sunaba123"),
            "admin"
        ))

    # 既存履歴を壊さず、登録者列だけ追加
    if not column_exists(cursor, "transactions", "employee_id"):
        cursor.execute("ALTER TABLE transactions ADD COLUMN employee_id TEXT")

    # 訂正履歴は別テーブルに保存
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS transaction_corrections (
            correction_id INTEGER PRIMARY KEY AUTOINCREMENT,
            transaction_id INTEGER NOT NULL,
            old_quantity INTEGER NOT NULL,
            new_quantity INTEGER NOT NULL,
            reason TEXT NOT NULL,
            corrected_at TEXT NOT NULL,
            corrected_by TEXT,
            FOREIGN KEY (transaction_id) REFERENCES transactions(transaction_id),
            FOREIGN KEY (corrected_by) REFERENCES employees(employee_id)
        )
    """)

    conn.commit()
    conn.close()
    print("データベースの設定が完了しました。")


if __name__ == "__main__":
    setup_database()

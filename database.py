import sqlite3
from werkzeug.security import generate_password_hash

DB_NAME = "sunaba_coffee.db"

def column_exists(cursor, table_name, column_name):
    return any(c[1] == column_name for c in cursor.execute(f"PRAGMA table_info({table_name})").fetchall())

def setup_database():
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("""CREATE TABLE IF NOT EXISTS employees (employee_id TEXT PRIMARY KEY, employee_name TEXT NOT NULL, password_hash TEXT NOT NULL, role TEXT NOT NULL DEFAULT 'staff')""")
    cursor.execute("""CREATE TABLE IF NOT EXISTS process_types (process_code TEXT PRIMARY KEY, process_name TEXT NOT NULL UNIQUE, is_visible INTEGER NOT NULL DEFAULT 0)""")
    cursor.executemany("INSERT OR IGNORE INTO process_types (process_code, process_name, is_visible) VALUES (?, ?, ?)", [("IN","入荷",1),("CO","消費",1),("DI","廃棄",1),("RT","返品",0),("AD","棚卸調整",0),("DM","破損",0)])

    # E001 は既存パスワードを維持したまま、氏名・権限だけ更新
    e001 = cursor.execute("SELECT 1 FROM employees WHERE employee_id='E001'").fetchone()
    if e001:
        cursor.execute("UPDATE employees SET employee_name='山田', role='admin' WHERE employee_id='E001'")
    else:
        cursor.execute("INSERT INTO employees VALUES (?, ?, ?, ?)", ("E001", "山田", generate_password_hash("sunaba123"), "admin"))

    # デモ用一般ユーザー。初期パスワードは sunaba123
    cursor.execute("INSERT OR IGNORE INTO employees VALUES (?, ?, ?, ?)", ("E002", "越智", generate_password_hash("sunaba123"), "staff"))
    cursor.execute("UPDATE employees SET employee_name='越智', role='staff' WHERE employee_id='E002'")

    if not column_exists(cursor, "transactions", "employee_id"):
        cursor.execute("ALTER TABLE transactions ADD COLUMN employee_id TEXT")
    cursor.execute("""CREATE TABLE IF NOT EXISTS transaction_corrections (correction_id INTEGER PRIMARY KEY AUTOINCREMENT, transaction_id INTEGER NOT NULL, old_quantity INTEGER NOT NULL, new_quantity INTEGER NOT NULL, reason TEXT NOT NULL, corrected_at TEXT NOT NULL, corrected_by TEXT)""")
    conn.commit(); conn.close()
    print("データベースの設定が完了しました。E001 山田（管理者）/ E002 越智（一般）")

if __name__ == "__main__": setup_database()

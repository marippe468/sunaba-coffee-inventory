import sqlite3

DB_NAME = "sunaba_coffee.db"

conn = sqlite3.connect(DB_NAME)

cursor = conn.cursor()
cursor.execute("""
CREATE TABLE IF NOT EXISTS products (
    product_id INTEGER PRIMARY KEY,
    product_name TEXT NOT NULL,
    stock INTEGER NOT NULL DEFAULT 0
)
""")
cursor.execute(
    "INSERT INTO products (product_id, product_name, stock) VALUES (?, ?, ?)",
    (1, "コーヒー豆", 10)
)
conn.commit()
conn.close()

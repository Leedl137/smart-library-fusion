import pymysql
from pathlib import Path

TMP_DIR = Path(r'C:\Users\think\Desktop\软著\smart_library_fusion\scripts\tmp_csv')

DB_CONFIG = {
    'host': '127.0.0.1', 'port': 3306, 'user': 'root',
    'password': '123456', 'database': 'smart_library_v2', 'local_infile': True,
}

def get_conn():
    return pymysql.connect(**DB_CONFIG)

# Step 1: Truncate
print("[1] Truncate...")
conn = get_conn()
with conn.cursor() as cur:
    cur.execute("SET FOREIGN_KEY_CHECKS = 0")
    cur.execute("TRUNCATE TABLE book_inventory")
    cur.execute("TRUNCATE TABLE books")
    cur.execute("SET FOREIGN_KEY_CHECKS = 1")
conn.commit()
conn.close()
print("  Done")

# Step 2: Import books (full CSV at once)
print("[2] Importing books...")
books_csv = str(TMP_DIR / 'books.csv')
conn = get_conn()
with conn.cursor() as cur:
    cur.execute("SET FOREIGN_KEY_CHECKS=0")
    cur.execute(f"""
    LOAD DATA LOCAL INFILE '{books_csv.replace(chr(92), chr(47))}'
    INTO TABLE books CHARACTER SET utf8mb4
    FIELDS TERMINATED BY ',' OPTIONALLY ENCLOSED BY '"'
    LINES TERMINATED BY '\r\n' IGNORE 1 LINES
    (isbn,barcode,title,authors,publisher,publish_year,category_code,call_no,language,doc_type,total_copies,available_copies,location,status)
    """)
    conn.commit()
    cur.execute("SELECT COUNT(*) FROM books")
    print(f"  Books: {cur.fetchone()[0]}")
conn.close()

# Step 3: Import inventory
print("[3] Importing inventory...")
inv_csv = str(TMP_DIR / 'inventory.csv')
conn = get_conn()
with conn.cursor() as cur:
    cur.execute(f"""
    LOAD DATA LOCAL INFILE '{inv_csv.replace(chr(92), chr(47))}'
    INTO TABLE book_inventory CHARACTER SET utf8mb4
    FIELDS TERMINATED BY ',' OPTIONALLY ENCLOSED BY '"'
    LINES TERMINATED BY '\r\n' IGNORE 1 LINES
    (isbn,stock)
    """)
    conn.commit()
    cur.execute("SELECT COUNT(*) FROM book_inventory")
    print(f"  Inventory: {cur.fetchone()[0]}")
conn.close()

print("Done!")

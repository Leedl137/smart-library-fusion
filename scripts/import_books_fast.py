import pymysql
from pathlib import Path

TMP_DIR = Path(r'C:\Users\think\Desktop\软著\smart_library_fusion\scripts\tmp_csv')
DB_CONFIG = {
    'host': '127.0.0.1', 'port': 3306, 'user': 'root',
    'password': '123456', 'database': 'smart_library_v2', 'local_infile': True,
}

def get_conn():
    return pymysql.connect(**DB_CONFIG)

print("[1/5] Truncate & drop indexes...")
conn = get_conn()
with conn.cursor() as cur:
    cur.execute("TRUNCATE TABLE books")
    cur.execute("ALTER TABLE books DROP INDEX uk_barcode")
    cur.execute("ALTER TABLE books DROP INDEX idx_title")
    cur.execute("ALTER TABLE books DROP INDEX idx_category")
    cur.execute("ALTER TABLE books DROP INDEX idx_status")
    cur.execute("ALTER TABLE books DROP INDEX ft_title_authors")
    print("  Indexes dropped")
conn.commit()
conn.close()

print("[2/5] LOAD DATA INFILE books...")
books_csv = str(TMP_DIR / 'books.csv')
conn = get_conn()
with conn.cursor() as cur:
    cur.execute(f"""
    LOAD DATA LOCAL INFILE '{books_csv.replace(chr(92), chr(47))}'
    INTO TABLE books
    CHARACTER SET utf8mb4
    FIELDS TERMINATED BY ','
    OPTIONALLY ENCLOSED BY '"'
    LINES TERMINATED BY '\r\n'
    IGNORE 1 LINES
    (isbn,barcode,title,authors,publisher,publish_year,category_code,call_no,language,doc_type,total_copies,available_copies,location,status)
    """)
    print(f"  Affected: {cur.rowcount}")
conn.commit()
with conn.cursor() as cur:
    cur.execute("SELECT COUNT(*) FROM books")
    print(f"  Books count: {cur.fetchone()[0]}")
conn.close()

print("[3/5] Rebuild indexes...")
conn = get_conn()
with conn.cursor() as cur:
    cur.execute("ALTER TABLE books ADD UNIQUE KEY uk_barcode (barcode)")
    cur.execute("ALTER TABLE books ADD KEY idx_title (title)")
    cur.execute("ALTER TABLE books ADD KEY idx_category (category_code)")
    cur.execute("ALTER TABLE books ADD KEY idx_status (status)")
    cur.execute("ALTER TABLE books ADD FULLTEXT KEY ft_title_authors (title, authors)")
    print("  Indexes rebuilt")
conn.commit()
conn.close()

print("[4/5] Truncate & reload inventory...")
inv_csv = str(TMP_DIR / 'inventory.csv')
conn = get_conn()
with conn.cursor() as cur:
    cur.execute("TRUNCATE TABLE book_inventory")
    cur.execute(f"""
    LOAD DATA LOCAL INFILE '{inv_csv.replace(chr(92), chr(47))}'
    INTO TABLE book_inventory
    CHARACTER SET utf8mb4
    FIELDS TERMINATED BY ','
    OPTIONALLY ENCLOSED BY '"'
    LINES TERMINATED BY '\r\n'
    IGNORE 1 LINES
    (isbn,stock)
    """)
    print(f"  Affected: {cur.rowcount}")
conn.commit()
with conn.cursor() as cur:
    cur.execute("SELECT COUNT(*) FROM book_inventory")
    print(f"  Inventory count: {cur.fetchone()[0]}")
conn.close()

print("[5/5] Done!")

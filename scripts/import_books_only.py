import pandas as pd
import pymysql
from pathlib import Path
import csv

RAW_ROOT = Path(r'C:\Users\think\Desktop\软著\raw_data\图书馆原始数据')
TMP_DIR = Path(r'C:\Users\think\Desktop\软著\smart_library_fusion\scripts\tmp_csv')
TMP_DIR.mkdir(exist_ok=True)

DB_CONFIG = {
    'host': '127.0.0.1', 'port': 3306, 'user': 'root',
    'password': '123456', 'database': 'smart_library_v2', 'local_infile': True,
}

def get_conn():
    return pymysql.connect(**DB_CONFIG)

print("[1/3] Truncate books & inventory...")
conn = get_conn()
with conn.cursor() as cur:
    cur.execute("SET FOREIGN_KEY_CHECKS = 0")
    cur.execute("TRUNCATE TABLE book_inventory")
    cur.execute("TRUNCATE TABLE books")
    cur.execute("SET FOREIGN_KEY_CHECKS = 1")
conn.commit()
conn.close()

print("[2/3] Read book CSV...")
books = pd.read_csv(RAW_ROOT / '借阅数据' / '借阅数据' / '图书数据.csv', encoding='utf-8', dtype=str)
print(f"  Rows: {len(books)}")
books = books.rename(columns={
    'ID': 'isbn', 'TITLE': 'title', 'AUTHOR': 'authors',
    'PUBLISHER': 'publisher', 'YEAR': 'publish_year',
    'CALLNO': 'call_no', 'LANGUAGE': 'language', 'DOCTYPE': 'doc_type'
})
books['barcode'] = books['isbn']
books['title'] = books['title'].str[:255]
books['authors'] = books['authors'].str[:100]
books['publisher'] = books['publisher'].str[:100]
books['publish_year'] = books['publish_year'].str.extract(r'(\d{4})')
books['call_no'] = books['call_no'].str[:100]
books['language'] = books['language'].fillna('Chinese').str[:20]
books['doc_type'] = books['doc_type'].fillna('Book').str[:50]
books['category_code'] = books['call_no'].str[0].str.upper()
books.loc[~books['category_code'].isin(list('ABCDEFGHIJKLMNOPQRSTUVWXYZ')), 'category_code'] = 'Z'
books['total_copies'] = 1
books['available_copies'] = 1
books['location'] = '3F-A-01-A'
books['status'] = 'onshelf'

bcols = ['isbn','barcode','title','authors','publisher','publish_year','category_code',
         'call_no','language','doc_type','total_copies','available_copies','location','status']
books_csv = str(TMP_DIR / 'books.csv')
books[bcols].to_csv(books_csv, index=False, encoding='utf-8-sig', quoting=csv.QUOTE_ALL)
print(f"  CSV saved: {books_csv}")

print("[3/3] LOAD DATA INFILE...")
conn = get_conn()
with conn.cursor() as cur:
    cur.execute(f"""
    LOAD DATA LOCAL INFILE '{books_csv.replace('\\', '/')}'
    INTO TABLE books
    CHARACTER SET utf8mb4
    FIELDS TERMINATED BY ','
    OPTIONALLY ENCLOSED BY '"'
    LINES TERMINATED BY '\r\n'
    IGNORE 1 LINES
    ({','.join(bcols)})
    """)
conn.commit()
with conn.cursor() as cur:
    cur.execute("SELECT COUNT(*) FROM books")
    print(f"  Books count: {cur.fetchone()[0]}")
conn.close()

# inventory
inv = books[['isbn']].copy()
inv['stock'] = 1
inv_csv = str(TMP_DIR / 'inventory.csv')
inv.to_csv(inv_csv, index=False, encoding='utf-8-sig', quoting=csv.QUOTE_ALL)
conn = get_conn()
with conn.cursor() as cur:
    cur.execute(f"""
    LOAD DATA LOCAL INFILE '{inv_csv.replace('\\', '/')}'
    INTO TABLE book_inventory
    CHARACTER SET utf8mb4
    FIELDS TERMINATED BY ','
    OPTIONALLY ENCLOSED BY '"'
    LINES TERMINATED BY '\r\n'
    IGNORE 1 LINES
    (isbn,stock)
    """)
conn.commit()
with conn.cursor() as cur:
    cur.execute("SELECT COUNT(*) FROM book_inventory")
    print(f"  Inventory count: {cur.fetchone()[0]}")
conn.close()

print("Done!")

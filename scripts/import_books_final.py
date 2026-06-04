import pandas as pd
import pymysql
from pathlib import Path
import csv
import time

RAW_ROOT = Path(r'C:\Users\think\Desktop\软著\raw_data\图书馆原始数据')
TMP_DIR = Path(r'C:\Users\think\Desktop\软著\smart_library_fusion\scripts\tmp_csv')
TMP_DIR.mkdir(exist_ok=True)

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

# Step 2: Generate CSVs if not exists
books_csv = str(TMP_DIR / 'books.csv')
if not Path(books_csv).exists():
    print("[2] Generating books CSV...")
    books = pd.read_csv(RAW_ROOT / '借阅数据' / '借阅数据' / '图书数据.csv', encoding='utf-8', dtype=str)
    books = books.rename(columns={
        'ID':'isbn','TITLE':'title','AUTHOR':'authors','PUBLISHER':'publisher',
        'YEAR':'publish_year','CALLNO':'call_no','LANGUAGE':'language','DOCTYPE':'doc_type'
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
    bcols = ['isbn','barcode','title','authors','publisher','publish_year','category_code','call_no','language','doc_type','total_copies','available_copies','location','status']
    books[bcols].to_csv(books_csv, index=False, encoding='utf-8-sig', quoting=csv.QUOTE_ALL)
    print(f"  CSV ready: {len(books)} rows")

inv_csv = str(TMP_DIR / 'inventory.csv')
if not Path(inv_csv).exists():
    print("[3] Generating inventory CSV...")
    inv = pd.read_csv(RAW_ROOT / '借阅数据' / '借阅数据' / '图书数据.csv', encoding='utf-8', dtype=str, usecols=['ID'])
    inv = inv.rename(columns={'ID':'isbn'})
    inv['stock'] = 1
    inv.to_csv(inv_csv, index=False, encoding='utf-8-sig', quoting=csv.QUOTE_ALL)
    print(f"  CSV ready: {len(inv)} rows")

# Step 3: Import books in chunks
print("[4] Importing books...")
total = 0
chunk_idx = 0
chunk_size = 50000

for chunk in pd.read_csv(books_csv, encoding='utf-8-sig', dtype=str, chunksize=chunk_size):
    chunk_idx += 1
    chunk_csv = str(TMP_DIR / f'books_{chunk_idx}.csv')
    chunk.to_csv(chunk_csv, index=False, encoding='utf-8-sig', quoting=csv.QUOTE_ALL)
    
    conn = get_conn()
    with conn.cursor() as cur:
        cur.execute("SET GLOBAL local_infile = 1")
        cur.execute("SET FOREIGN_KEY_CHECKS=0")
        cur.execute(f"""
        LOAD DATA LOCAL INFILE '{chunk_csv.replace(chr(92), chr(47))}'
        INTO TABLE books CHARACTER SET utf8mb4
        FIELDS TERMINATED BY ',' OPTIONALLY ENCLOSED BY '"'
        LINES TERMINATED BY '\r\n' IGNORE 1 LINES
        (isbn,barcode,title,authors,publisher,publish_year,category_code,call_no,language,doc_type,total_copies,available_copies,location,status)
        """)
        conn.commit()
    conn.close()
    
    total += len(chunk)
    print(f"  Chunk {chunk_idx}: +{len(chunk)} => total {total}")

print(f"  Books total: {total}")

# Step 4: Import inventory
print("[5] Importing inventory...")
conn = get_conn()
with conn.cursor() as cur:
    cur.execute("SET GLOBAL local_infile = 1")
    cur.execute("SET FOREIGN_KEY_CHECKS=0")
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

print("\nBooks & Inventory done!")

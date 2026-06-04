"""
Fast bulk import using LOAD DATA LOCAL INFILE.
Books: ~453k rows | Borrows: ~1.9M rows
"""
import pandas as pd
import pymysql
from pathlib import Path
import csv
import time

RAW_ROOT = Path(r'C:\Users\think\Desktop\软著\raw_data\图书馆原始数据')
TMP_DIR = Path(r'C:\Users\think\Desktop\软著\smart_library_fusion\scripts\tmp_csv')
TMP_DIR.mkdir(exist_ok=True)

DB_CONFIG = {
    'host': '127.0.0.1',
    'port': 3306,
    'user': 'root',
    'password': '123456',
    'database': 'smart_library_v2',
    'local_infile': True,
}

def get_conn():
    return pymysql.connect(**DB_CONFIG)

# ==================== PHASE 1: BOOKS (truncate + full reload) ====================
print("[PHASE 1] Books: truncate + full reload...")
conn = get_conn()
with conn.cursor() as cur:
    cur.execute("SET FOREIGN_KEY_CHECKS = 0")
    cur.execute("TRUNCATE TABLE book_inventory")
    cur.execute("TRUNCATE TABLE books")
    cur.execute("SET FOREIGN_KEY_CHECKS = 1")
conn.commit()
conn.close()

print("  Reading book CSV...")
books = pd.read_csv(RAW_ROOT / '借阅数据' / '借阅数据' / '图书数据.csv', encoding='utf-8', dtype=str)
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

print("  LOAD DATA INFILE books...")
conn = get_conn()
with conn.cursor() as cur:
    cur.execute(f"""
    LOAD DATA LOCAL INFILE '{books_csv.replace('\\', '/')}'
    INTO TABLE books
    CHARACTER SET utf8mb4
    FIELDS TERMINATED BY ','
    OPTIONALLY ENCLOSED BY '"'
    LINES TERMINATED BY '\\r\\n'
    IGNORE 1 LINES
    ({','.join(bcols)})
    """)
conn.commit()
conn.close()
print(f"  Books loaded: {len(books)}")

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
    LINES TERMINATED BY '\\r\\n'
    IGNORE 1 LINES
    (isbn,stock)
    """)
conn.commit()
conn.close()
print(f"  Inventory loaded: {len(inv)}")

del books, inv

# ==================== PHASE 2: BORROW RECORDS (chunked) ====================
print("\n[PHASE 2] Borrow records: chunked import...")
conn = get_conn()
with conn.cursor() as cur:
    cur.execute("SELECT id, uid FROM users")
    uid_to_id = {row[1]: row[0] for row in cur.fetchall()}
conn.close()
print(f"  User map ready: {len(uid_to_id)} entries")

# Clear existing borrow records if any
conn = get_conn()
with conn.cursor() as cur:
    cur.execute("TRUNCATE TABLE borrow_records")
conn.commit()
conn.close()

total_borrows = 0
chunk_size = 300000
chunk_idx = 0
borrow_file = RAW_ROOT / '借阅数据' / '借阅数据' / '借阅数据_guid.csv'

for chunk in pd.read_csv(borrow_file, encoding='utf-8', dtype=str, chunksize=chunk_size):
    chunk_idx += 1
    chunk = chunk.rename(columns={
        'ID': 'borrow_id', 'READERID': 'user_uid', 'BOOKID': 'isbn',
        'BORROWDATE': 'borrow_time', 'RETURNDATE': 'return_time',
        'RENEWCOUNTS': 'renew_count', 'STATUS': 'status'
    })
    chunk['user_id'] = chunk['user_uid'].map(uid_to_id)
    chunk = chunk[chunk['user_id'].notna()].copy()
    if len(chunk) == 0:
        continue
    
    chunk['borrow_id'] = chunk['borrow_id'].fillna('').str[:64]
    chunk['borrow_time'] = pd.to_datetime(chunk['borrow_time'], errors='coerce').fillna(pd.Timestamp('2023-01-01'))
    chunk['return_time'] = pd.to_datetime(chunk['return_time'], errors='coerce')
    chunk['due_date'] = chunk['borrow_time'] + pd.Timedelta(days=30)
    chunk['renew_count'] = pd.to_numeric(chunk['renew_count'], errors='coerce').fillna(0).astype(int)
    chunk['status'] = chunk['status'].fillna('borrowed').str[:20]
    chunk['returned'] = chunk['status'].apply(lambda x: 1 if str(x).lower() in ('returned','return','已还') else 0)
    chunk['fine_amount'] = 0.00
    chunk['operator_id'] = 1
    
    brcols = ['borrow_id','user_id','isbn','borrow_time','due_date','return_time',
              'renew_count','status','returned','fine_amount','operator_id']
    br_csv = str(TMP_DIR / f'borrow_records_{chunk_idx}.csv')
    chunk[brcols].to_csv(br_csv, index=False, encoding='utf-8-sig', quoting=csv.QUOTE_ALL)
    
    conn = get_conn()
    with conn.cursor() as cur:
        cur.execute(f"""
        LOAD DATA LOCAL INFILE '{br_csv.replace('\\', '/')}'
        INTO TABLE borrow_records
        CHARACTER SET utf8mb4
        FIELDS TERMINATED BY ','
        OPTIONALLY ENCLOSED BY '"'
        LINES TERMINATED BY '\\r\\n'
        IGNORE 1 LINES
        ({','.join(brcols)})
        """)
    conn.commit()
    conn.close()
    
    total_borrows += len(chunk)
    print(f"  Chunk {chunk_idx}: +{len(chunk)} => total {total_borrows}")

print(f"\nBorrow records total: {total_borrows}")

# ==================== VERIFY ====================
print("\n[VERIFY] Final counts:")
conn = get_conn()
with conn.cursor() as cur:
    for t in ['categories','users','books','book_inventory','borrow_records','access_logs','seat_logs']:
        cur.execute(f'SELECT COUNT(*) FROM {t}')
        print(f"  {t}: {cur.fetchone()[0]}")
conn.close()
print("\nAll done!")

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

# Check current count
conn = get_conn()
with conn.cursor() as cur:
    cur.execute("SELECT COUNT(*) FROM borrow_records")
    existing = cur.fetchone()[0]
conn.close()

if existing > 0:
    print(f"Borrow records already exist ({existing}), skip")
    exit(0)

# Build uid->id map
print("Building user map...")
conn = get_conn()
with conn.cursor() as cur:
    cur.execute("SELECT id, uid FROM users")
    uid_to_id = {row[1]: row[0] for row in cur.fetchall()}
conn.close()
print(f"  Mapped {len(uid_to_id)} users")

# Process borrow records in chunks
print("Importing borrow records...")
total = 0
chunk_idx = 0
chunk_size = 100000
borrow_file = RAW_ROOT / '借阅数据' / '借阅数据' / '借阅数据_guid.csv'

t0 = time.time()
for chunk in pd.read_csv(borrow_file, encoding='utf-8', dtype=str, chunksize=chunk_size):
    chunk_idx += 1
    chunk = chunk.rename(columns={
        'NO': 'borrow_no', 'READERID': 'user_uid', 'BOOKID': 'isbn',
        'LENDDATE': 'borrow_time', 'RETURNDATE': 'return_time',
        'RENEWCOUNTS': 'renew_count'
    })
    chunk['user_id'] = chunk['user_uid'].map(uid_to_id)
    chunk = chunk[chunk['user_id'].notna()].copy()
    if len(chunk) == 0:
        continue
    
    chunk['borrow_id'] = 'BR' + chunk['borrow_no'].astype(str).str.zfill(10)
    chunk['borrow_time'] = pd.to_datetime(chunk['borrow_time'], errors='coerce').fillna(pd.Timestamp('2023-01-01'))
    chunk['return_time'] = pd.to_datetime(chunk['return_time'], errors='coerce')
    chunk['due_time'] = chunk['borrow_time'] + pd.Timedelta(days=30)
    chunk['renew_count'] = pd.to_numeric(chunk['renew_count'], errors='coerce').fillna(0).astype(int)
    chunk['status'] = chunk['return_time'].apply(lambda x: 'returned' if pd.notna(x) else 'borrowed')
    chunk['overdue_days'] = 0
    chunk['is_deleted'] = 0
    chunk['operator_id'] = 1
    
    brcols = ['borrow_id','user_id','isbn','borrow_time','due_time','return_time','operator_id','status','overdue_days','renew_count','is_deleted']
    br_csv = str(TMP_DIR / f'borrow_{chunk_idx}.csv')
    chunk[brcols].to_csv(br_csv, index=False, encoding='utf-8-sig', quoting=csv.QUOTE_ALL)
    
    conn = get_conn()
    with conn.cursor() as cur:
        cur.execute("SET GLOBAL local_infile = 1")
        cur.execute("SET FOREIGN_KEY_CHECKS=0")
        cur.execute(f"""
        LOAD DATA LOCAL INFILE '{br_csv.replace(chr(92), chr(47))}'
        INTO TABLE borrow_records CHARACTER SET utf8mb4
        FIELDS TERMINATED BY ',' OPTIONALLY ENCLOSED BY '"'
        LINES TERMINATED BY '\r\n' IGNORE 1 LINES
        ({','.join(brcols)})
        """)
        conn.commit()
    conn.close()
    
    total += len(chunk)
    elapsed = time.time() - t0
    print(f"  Chunk {chunk_idx}: +{len(chunk)} => total {total} ({elapsed:.1f}s)")

print(f"\nBorrow records total: {total}")

# Rebuild indexes
print("Rebuilding indexes...")
conn = get_conn()
with conn.cursor() as cur:
    cur.execute("ALTER TABLE borrow_records ADD KEY idx_br_status (status)")
    cur.execute("ALTER TABLE borrow_records ADD KEY idx_br_return (return_time)")
    cur.execute("ALTER TABLE borrow_records ADD KEY idx_br_borrow_time (borrow_time)")
    conn.commit()
    print("  Done")
conn.close()

print("\nAll done!")

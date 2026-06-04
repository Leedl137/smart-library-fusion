import pandas as pd
from sqlalchemy import create_engine
import time
import pymysql
from pathlib import Path

TMP_DIR = Path(r'C:\Users\think\Desktop\软著\smart_library_fusion\scripts\tmp_csv')

# Test 1: LOAD DATA INFILE with 50k rows
print("Test 1: LOAD DATA INFILE 50k rows...")
books_csv = str(TMP_DIR / 'books_1.csv')
conn = pymysql.connect(host='127.0.0.1', port=3306, user='root', password='123456', database='smart_library_v2', local_infile=True)
t0 = time.time()
with conn.cursor() as cur:
    cur.execute("SET GLOBAL local_infile = 1")
    cur.execute("SET FOREIGN_KEY_CHECKS=0")
    cur.execute(f"""
    LOAD DATA LOCAL INFILE '{books_csv.replace(chr(92), chr(47))}'
    INTO TABLE books CHARACTER SET utf8mb4
    FIELDS TERMINATED BY ',' OPTIONALLY ENCLOSED BY '"'
    LINES TERMINATED BY '\r\n' IGNORE 1 LINES
    (isbn,barcode,title,authors,publisher,publish_year,category_code,call_no,language,doc_type,total_copies,available_copies,location,status)
    """)
    conn.commit()
t1 = time.time()
print(f"  Done in {t1-t0:.2f}s")

with conn.cursor() as cur:
    cur.execute("SELECT COUNT(*) FROM books")
    print(f"  Books: {cur.fetchone()[0]}")
conn.close()

# Clean up test data
conn = pymysql.connect(host='127.0.0.1', port=3306, user='root', password='123456', database='smart_library_v2')
with conn.cursor() as cur:
    cur.execute("TRUNCATE TABLE books")
conn.commit()
conn.close()

# Test 2: pandas to_sql with 5000 rows
print("\nTest 2: pandas to_sql 5000 rows...")
engine = create_engine('mysql+pymysql://root:123456@127.0.0.1:3306/smart_library_v2?charset=utf8mb4')
df = pd.read_csv(str(TMP_DIR / 'books.csv'), nrows=5000, encoding='utf-8-sig', dtype=str)
t0 = time.time()
df.to_sql('books', engine, if_exists='append', index=False, method='multi', chunksize=1000)
t1 = time.time()
print(f"  Done in {t1-t0:.2f}s")

with engine.connect() as conn:
    r = conn.execute('SELECT COUNT(*) FROM books')
    print(f"  Books: {r.scalar()}")
engine.dispose()

# Clean up
conn = pymysql.connect(host='127.0.0.1', port=3306, user='root', password='123456', database='smart_library_v2')
with conn.cursor() as cur:
    cur.execute("TRUNCATE TABLE books")
conn.commit()
conn.close()

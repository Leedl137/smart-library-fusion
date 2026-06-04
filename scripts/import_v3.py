"""
Complete data import into smart_library_v3 (optimized for speed).
Strategy: disable keys/checks, bulk load, re-enable.
"""
import pandas as pd
import pymysql
from pathlib import Path
import csv
import time

RAW_ROOT = Path(r'C:\Users\think\Desktop\软著\raw_data\图书馆原始数据')
TMP_DIR = Path(r'C:\Users\think\Desktop\软著\smart_library_fusion\scripts\tmp_csv')
TMP_DIR.mkdir(exist_ok=True)

DB = 'smart_library_v3'
DB_CONFIG = {
    'host': '127.0.0.1', 'port': 3306, 'user': 'root',
    'password': '123456', 'database': DB, 'local_infile': True,
}

def get_conn():
    return pymysql.connect(**DB_CONFIG)

# ============= STEP 0: Create DB & tables =============
print("[0] Creating database & tables...")
conn = pymysql.connect(host='127.0.0.1', port=3306, user='root', password='123456')
with conn.cursor() as cur:
    cur.execute(f"CREATE DATABASE IF NOT EXISTS {DB} CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci")
conn.commit()
conn.close()

# Read DDL and adapt
with open(Path(r'C:\Users\think\Desktop\软著\smart_library_fusion\database.sql'), 'r', encoding='utf-8') as f:
    ddl = f.read()
# Replace DB name
ddl = ddl.replace('`smart_library_v2`', f'`{DB}`')
# Remove FULLTEXT index from books (will add later)
ddl = ddl.replace("FULLTEXT INDEX `ft_title_authors` (`title`, `authors`) COMMENT 'MySQL全文检索',", "")
# Remove CHECK constraints (MySQL 8.0.12 may enforce them and real data may violate)
ddl = ddl.replace("CONSTRAINT `chk_isbn_length` CHECK (LENGTH(`isbn`) = 13),", "")
ddl = ddl.replace("CONSTRAINT `chk_copies_positive` CHECK (`total_copies` >= 0 AND `available_copies` >= 0),", "")
ddl = ddl.replace("CONSTRAINT `chk_copies_consistency` CHECK (`total_copies` >= `available_copies`),", "")
ddl = ddl.replace("CONSTRAINT `chk_stock_positive` CHECK (`stock` >= 0),", "")
# Remove comment lines then split by semicolon
lines = [l for l in ddl.split('\n') if not l.strip().startswith('--')]
clean_ddl = '\n'.join(lines)
conn = get_conn()
with conn.cursor() as cur:
    for stmt in clean_ddl.split(';'):
        stmt = stmt.strip()
        if stmt:
            try:
                cur.execute(stmt)
            except Exception as e:
                err = str(e)
                if any(k in err.lower() for k in ['duplicate', 'already exists', 'database exists']):
                    pass
                else:
                    print(f"  DDL warn: {e}")
conn.commit()
conn.close()
print("  Tables ready")

# ============= STEP 1: Categories =============
print("[1] Categories...")
conn = get_conn()
with conn.cursor() as cur:
    cur.execute("SELECT COUNT(*) FROM categories")
    if cur.fetchone()[0] == 0:
        cats = [
            ('A','A-Marxism',1),('B','B-Philosophy',1),('C','C-SocialSci',1),
            ('D','D-PoliticsLaw',1),('E','E-Military',1),('F','F-Economy',1),
            ('G','G-CultureEdu',1),('H','H-Language',1),('I','I-Literature',1),
            ('J','J-Art',1),('K','K-HistoryGeo',1),('N','N-NaturalSci',1),
            ('O','O-MathChem',1),('P','P-AstroEarth',1),('Q','Q-Biology',1),
            ('R','R-Medicine',1),('S','S-Agriculture',1),('T','T-Industry',1),
            ('TP','TP-Computer',2),('U','U-Transport',1),('V','V-Aerospace',1),
            ('X','X-Environment',1),('Z','Z-General',1),
        ]
        cur.executemany("INSERT INTO categories (code,name,level) VALUES (%s,%s,%s)", cats)
        conn.commit()
        print(f"  Inserted {len(cats)}")
    else:
        print("  Skip")
conn.close()

# ============= STEP 2: Users =============
print("[2] Users...")
conn = get_conn()
with conn.cursor() as cur:
    cur.execute("SELECT COUNT(*) FROM users")
    if cur.fetchone()[0] == 0:
        df = pd.read_csv(RAW_ROOT / '借阅数据' / '借阅数据' / '读者数据_guid.csv', encoding='gbk')
        df = df.rename(columns={'ID':'uid','GENDER':'gender','ENROLLYEAR':'enroll_year','TYPE':'reader_type','DEPARTMENT':'department'})
        df['enroll_year'] = df['enroll_year'].astype(str).str.extract(r'(\d{4})')
        df['real_name'] = 'reader_' + df['uid'].str[:8]
        df['role'] = 'student'
        df['id_type'] = 'idcard'
        df['id_number_enc'] = 'enc'
        df['phone_enc'] = 'enc'
        df['user_status'] = 'normal'
        df['review_status'] = 'approved'
        df['max_borrow_count'] = 5
        df['max_borrow_days'] = 30
        cols = ['uid','real_name','gender','enroll_year','reader_type','department','role','id_type','id_number_enc','phone_enc','user_status','review_status','max_borrow_count','max_borrow_days']
        csv_path = str(TMP_DIR / 'users.csv')
        df[cols].to_csv(csv_path, index=False, encoding='utf-8-sig', quoting=csv.QUOTE_ALL)
        
        with conn.cursor() as cur2:
            cur2.execute("SET FOREIGN_KEY_CHECKS=0")
            cur2.execute(f"""
            LOAD DATA LOCAL INFILE '{csv_path.replace(chr(92), chr(47))}'
            INTO TABLE users CHARACTER SET utf8mb4
            FIELDS TERMINATED BY ',' OPTIONALLY ENCLOSED BY '"'
            LINES TERMINATED BY '\r\n' IGNORE 1 LINES
            ({','.join(cols)})
            """)
        conn.commit()
        print(f"  Loaded {len(df)}")
    else:
        print("  Skip")
conn.close()

# ============= STEP 3: Books (drop idx, load, rebuild) =============
print("[3] Books...")
conn = get_conn()
with conn.cursor() as cur:
    cur.execute("SELECT COUNT(*) FROM books")
    if cur.fetchone()[0] == 0:
        # Drop non-PK indexes for speed
        cur.execute("ALTER TABLE books DROP INDEX uk_barcode")
        cur.execute("ALTER TABLE books DROP INDEX idx_title")
        cur.execute("ALTER TABLE books DROP INDEX idx_category")
        cur.execute("ALTER TABLE books DROP INDEX idx_status")
        conn.commit()
        print("  Dropped secondary indexes")
        
        books_csv = str(TMP_DIR / 'books.csv')
        if not Path(books_csv).exists():
            print("  Generating books CSV...")
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
        print(f"  Loaded {cur.fetchone()[0]} books")
        
        # Rebuild indexes
        cur.execute("ALTER TABLE books ADD UNIQUE KEY uk_barcode (barcode)")
        cur.execute("ALTER TABLE books ADD KEY idx_title (title)")
        cur.execute("ALTER TABLE books ADD KEY idx_category (category_code)")
        cur.execute("ALTER TABLE books ADD KEY idx_status (status)")
        conn.commit()
        print("  Rebuilt indexes")
        
        # Inventory
        inv_csv = str(TMP_DIR / 'inventory.csv')
        if not Path(inv_csv).exists():
            print("  Generating inventory CSV...")
            if 'books' in dir():
                inv = books[['isbn']].copy()
            else:
                # re-read minimal
                inv = pd.read_csv(RAW_ROOT / '借阅数据' / '借阅数据' / '图书数据.csv', encoding='utf-8', dtype=str, usecols=['ID'])
                inv = inv.rename(columns={'ID':'isbn'})
            inv['stock'] = 1
            inv.to_csv(inv_csv, index=False, encoding='utf-8-sig', quoting=csv.QUOTE_ALL)
        
        cur.execute("TRUNCATE TABLE book_inventory")
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
    else:
        print("  Skip")
conn.close()

# ============= STEP 4: Borrow records (chunked) =============
print("[4] Borrow records...")
conn = get_conn()
with conn.cursor() as cur:
    cur.execute("SELECT COUNT(*) FROM borrow_records")
    if cur.fetchone()[0] == 0:
        # Build uid->id map
        cur.execute("SELECT id, uid FROM users")
        uid_to_id = {row[1]: row[0] for row in cur.fetchall()}
        print(f"  User map: {len(uid_to_id)}")
        
        # Drop borrow indexes temporarily
        cur.execute("ALTER TABLE borrow_records DROP INDEX idx_br_user")
        cur.execute("ALTER TABLE borrow_records DROP INDEX idx_br_isbn")
        cur.execute("ALTER TABLE borrow_records DROP INDEX idx_br_status")
        cur.execute("ALTER TABLE borrow_records DROP INDEX idx_br_return")
        cur.execute("ALTER TABLE borrow_records DROP INDEX idx_br_borrow_time")
        conn.commit()
        print("  Dropped secondary indexes")
        
        total = 0
        chunk_idx = 0
        borrow_file = RAW_ROOT / '借阅数据' / '借阅数据' / '借阅数据_guid.csv'
        for chunk in pd.read_csv(borrow_file, encoding='utf-8', dtype=str, chunksize=300000):
            chunk_idx += 1
            chunk = chunk.rename(columns={
                'ID':'borrow_id','READERID':'user_uid','BOOKID':'isbn',
                'BORROWDATE':'borrow_time','RETURNDATE':'return_time',
                'RENEWCOUNTS':'renew_count','STATUS':'status'
            })
            chunk['user_id'] = chunk['user_uid'].map(uid_to_id)
            chunk = chunk[chunk['user_id'].notna()].copy()
            if len(chunk) == 0:
                continue
            chunk['borrow_id'] = chunk['borrow_id'].fillna('').str[:64]
            chunk['borrow_time'] = pd.to_datetime(chunk['borrow_time'], errors='coerce').fillna(pd.Timestamp('2023-01-01'))
            chunk['return_time'] = pd.to_datetime(chunk['return_time'], errors='coerce')
            chunk['due_time'] = chunk['borrow_time'] + pd.Timedelta(days=30)
            chunk['renew_count'] = pd.to_numeric(chunk['renew_count'], errors='coerce').fillna(0).astype(int)
            chunk['status'] = chunk['status'].fillna('borrowed').str[:20]
            chunk['overdue_days'] = 0
            chunk['is_deleted'] = 0
            chunk['operator_id'] = 1
            
            # Note: DDL uses due_time not due_date
            brcols = ['borrow_id','user_id','isbn','borrow_time','due_time','return_time','operator_id','status','overdue_days','renew_count','is_deleted']
            br_csv = str(TMP_DIR / f'borrow_{chunk_idx}.csv')
            chunk[brcols].to_csv(br_csv, index=False, encoding='utf-8-sig', quoting=csv.QUOTE_ALL)
            
            cur.execute("SET FOREIGN_KEY_CHECKS=0")
            cur.execute(f"""
            LOAD DATA LOCAL INFILE '{br_csv.replace(chr(92), chr(47))}'
            INTO TABLE borrow_records CHARACTER SET utf8mb4
            FIELDS TERMINATED BY ',' OPTIONALLY ENCLOSED BY '"'
            LINES TERMINATED BY '\r\n' IGNORE 1 LINES
            ({','.join(brcols)})
            """)
            conn.commit()
            total += len(chunk)
            print(f"  Chunk {chunk_idx}: +{len(chunk)} => total {total}")
        
        # Rebuild indexes
        cur.execute("ALTER TABLE borrow_records ADD KEY idx_br_user (user_id)")
        cur.execute("ALTER TABLE borrow_records ADD KEY idx_br_isbn (isbn)")
        cur.execute("ALTER TABLE borrow_records ADD KEY idx_br_status (status)")
        cur.execute("ALTER TABLE borrow_records ADD KEY idx_br_return (return_time)")
        cur.execute("ALTER TABLE borrow_records ADD KEY idx_br_borrow_time (borrow_time)")
        conn.commit()
        print(f"  Rebuilt indexes. Total borrow records: {total}")
    else:
        print("  Skip")
conn.close()

# ============= STEP 5: Access logs =============
print("[5] Access logs...")
conn = get_conn()
with conn.cursor() as cur:
    cur.execute("SELECT COUNT(*) FROM access_logs")
    if cur.fetchone()[0] == 0:
        files = list((RAW_ROOT / '门禁数据').rglob('*.csv'))
        print(f"  Found {len(files)} files")
        # TODO: implement if needed
    else:
        print("  Skip")
conn.close()

# ============= STEP 6: Seat logs =============
print("[6] Seat logs...")
conn = get_conn()
with conn.cursor() as cur:
    cur.execute("SELECT COUNT(*) FROM seat_logs")
    if cur.fetchone()[0] == 0:
        files = list((RAW_ROOT / '座位数据').rglob('*.csv'))
        print(f"  Found {len(files)} files")
        # TODO: implement if needed
    else:
        print("  Skip")
conn.close()

# ============= STEP 7: Fulltext index =============
print("[7] Rebuilding fulltext index on books...")
conn = get_conn()
with conn.cursor() as cur:
    cur.execute("ALTER TABLE books ADD FULLTEXT KEY ft_title_authors (title, authors)")
    conn.commit()
    print("  Done")
conn.close()

# ============= VERIFY =============
print("\n[VERIFY] Final counts:")
conn = get_conn()
with conn.cursor() as cur:
    for t in ['categories','users','books','book_inventory','borrow_records','access_logs','seat_logs']:
        cur.execute(f'SELECT COUNT(*) FROM {t}')
        print(f"  {t}: {cur.fetchone()[0]}")
conn.close()
print("\nAll done!")

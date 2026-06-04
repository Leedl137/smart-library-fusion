"""
Fast bulk import using LOAD DATA LOCAL INFILE.
Requires: MySQL local_infile=ON
"""
import pandas as pd
import pymysql
from pathlib import Path
import csv
import os

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

def truncate_tables(conn, tables):
    with conn.cursor() as cur:
        cur.execute("SET FOREIGN_KEY_CHECKS = 0")
        for t in tables:
            cur.execute(f"TRUNCATE TABLE {t}")
            print(f"  TRUNCATED {t}")
        cur.execute("SET FOREIGN_KEY_CHECKS = 1")
    conn.commit()

def load_csv(conn, table, csv_path, columns):
    sql = f"""
    LOAD DATA LOCAL INFILE '{csv_path.replace('\\', '/')}')
    INTO TABLE {table}
    CHARACTER SET utf8mb4
    FIELDS TERMINATED BY ','
    OPTIONALLY ENCLOSED BY '"'
    ESCAPED BY '\\\\'
    LINES TERMINATED BY '\\r\\n'
    IGNORE 1 LINES
    ({','.join(columns)})
    """
    with conn.cursor() as cur:
        cur.execute(sql)
    conn.commit()
    print(f"  LOADED {table} from {csv_path}")

# ==================== 1. CATEGORIES (skip if exists) ====================
print("[1/6] Categories (skip if already loaded)...")
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
        print("  Inserted 23 categories")
    else:
        print("  Already exists, skip")
conn.close()

# ==================== 2. READERS -> users ====================
print("[2/6] Readers -> users...")
conn = get_conn()
with conn.cursor() as cur:
    cur.execute("SELECT COUNT(*) FROM users")
    user_cnt = cur.fetchone()[0]
conn.close()

if user_cnt == 0:
    print("  Loading readers CSV...")
    df = pd.read_csv(RAW_ROOT / '借阅数据' / '借阅数据' / '读者数据_guid.csv', encoding='gbk')
    df = df.rename(columns={
        'ID': 'uid', 'GENDER': 'gender', 'ENROLLYEAR': 'enroll_year',
        'TYPE': 'reader_type', 'DEPARTMENT': 'department'
    })
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
    cols = ['uid','real_name','gender','enroll_year','reader_type','department',
            'role','id_type','id_number_enc','phone_enc','user_status','review_status',
            'max_borrow_count','max_borrow_days']
    csv_path = str(TMP_DIR / 'users.csv')
    df[cols].to_csv(csv_path, index=False, encoding='utf-8-sig', quoting=csv.QUOTE_ALL)
    
    conn = get_conn()
    with conn.cursor() as cur:
        cur.execute(f"""
        LOAD DATA LOCAL INFILE '{csv_path.replace('\\', '/')}')
        INTO TABLE users
        CHARACTER SET utf8mb4
        FIELDS TERMINATED BY ','
        OPTIONALLY ENCLOSED BY '"'
        LINES TERMINATED BY '\\r\\n'
        IGNORE 1 LINES
        ({','.join(cols)})
        """)
    conn.commit()
    conn.close()
    print(f"  Done: {len(df)} users")
else:
    print(f"  Already exists ({user_cnt}), skip")

# ==================== 3. BOOKS + INVENTORY ====================
print("[3/6] Books + inventory...")
conn = get_conn()
with conn.cursor() as cur:
    cur.execute("SELECT COUNT(*) FROM books")
    book_cnt = cur.fetchone()[0]
conn.close()

if book_cnt == 0:
    truncate_tables(get_conn(), ['book_inventory', 'books'])
    
    print("  Reading full book CSV...")
    df = pd.read_csv(RAW_ROOT / '借阅数据' / '借阅数据' / '图书数据.csv', encoding='utf-8')
    df = df.rename(columns={
        'ID': 'isbn', 'TITLE': 'title', 'AUTHOR': 'authors',
        'PUBLISHER': 'publisher', 'YEAR': 'publish_year',
        'CALLNO': 'call_no', 'LANGUAGE': 'language', 'DOCTYPE': 'doc_type'
    })
    df['barcode'] = df['isbn']
    df['title'] = df['title'].astype(str).str[:255]
    df['authors'] = df['authors'].astype(str).str[:100]
    df['publisher'] = df['publisher'].astype(str).str[:100]
    df['publish_year'] = df['publish_year'].astype(str).str.extract(r'(\d{4})')
    df['call_no'] = df['call_no'].astype(str).str[:100]
    df['language'] = df['language'].fillna('Chinese').astype(str).str[:20]
    df['doc_type'] = df['doc_type'].fillna('Book').astype(str).str[:50]
    df['category_code'] = df['call_no'].astype(str).str[0].str.upper()
    df.loc[~df['category_code'].isin(list('ABCDEFGHIJKLMNOPQRSTUVWXYZ')), 'category_code'] = 'Z'
    df['total_copies'] = 1
    df['available_copies'] = 1
    df['location'] = '3F-A-01-A'
    df['status'] = 'onshelf'
    
    bcols = ['isbn','barcode','title','authors','publisher','publish_year','category_code',
             'call_no','language','doc_type','total_copies','available_copies','location','status']
    books_csv = str(TMP_DIR / 'books.csv')
    df[bcols].to_csv(books_csv, index=False, encoding='utf-8-sig', quoting=csv.QUOTE_ALL)
    
    conn = get_conn()
    with conn.cursor() as cur:
        cur.execute(f"""
        LOAD DATA LOCAL INFILE '{books_csv.replace('\\', '/')}')
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
    print(f"  Books loaded: {len(df)}")
    
    # inventory
    inv = df[['isbn']].copy()
    inv['stock'] = 1
    inv_csv = str(TMP_DIR / 'inventory.csv')
    inv.to_csv(inv_csv, index=False, encoding='utf-8-sig', quoting=csv.QUOTE_ALL)
    
    conn = get_conn()
    with conn.cursor() as cur:
        cur.execute(f"""
        LOAD DATA LOCAL INFILE '{inv_csv.replace('\\', '/')}')
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
else:
    print(f"  Already exists ({book_cnt}), skip")

# ==================== 4. BORROW RECORDS ====================
print("[4/6] Borrow records...")
conn = get_conn()
with conn.cursor() as cur:
    cur.execute("SELECT COUNT(*) FROM borrow_records")
    br_cnt = cur.fetchone()[0]
conn.close()

if br_cnt == 0:
    print("  Building uid->id map...")
    conn = get_conn()
    with conn.cursor() as cur:
        cur.execute("SELECT id, uid FROM users")
        uid_to_id = {row[1]: row[0] for row in cur.fetchall()}
    conn.close()
    print(f"  Mapped {len(uid_to_id)} users")
    
    print("  Reading borrow CSV...")
    df = pd.read_csv(RAW_ROOT / '借阅数据' / '借阅数据' / '借阅数据.csv', encoding='utf-8')
    df = df.rename(columns={
        'ID': 'borrow_id', 'READERID': 'user_uid', 'BOOKID': 'isbn',
        'BORROWDATE': 'borrow_time', 'RETURNDATE': 'return_time',
        'RENEWCOUNTS': 'renew_count', 'STATUS': 'status'
    })
    # map uid -> user_id
    df['user_id'] = df['user_uid'].map(uid_to_id)
    df = df[df['user_id'].notna()].copy()
    print(f"  Valid records after mapping: {len(df)}")
    
    # fill defaults
    df['borrow_id'] = df['borrow_id'].fillna('').astype(str).str[:64]
    df['borrow_time'] = pd.to_datetime(df['borrow_time'], errors='coerce').fillna(pd.Timestamp('2023-01-01'))
    df['return_time'] = pd.to_datetime(df['return_time'], errors='coerce')
    df['due_date'] = df['borrow_time'] + pd.Timedelta(days=30)
    df['renew_count'] = pd.to_numeric(df['renew_count'], errors='coerce').fillna(0).astype(int)
    df['status'] = df['status'].fillna('borrowed').astype(str).str[:20]
    df['returned'] = df['status'].apply(lambda x: 1 if str(x).lower() in ('returned','return','已还') else 0)
    df['fine_amount'] = 0.00
    df['operator_id'] = 1
    
    brcols = ['borrow_id','user_id','isbn','borrow_time','due_date','return_time',
              'renew_count','status','returned','fine_amount','operator_id']
    br_csv = str(TMP_DIR / 'borrow_records.csv')
    df[brcols].to_csv(br_csv, index=False, encoding='utf-8-sig', quoting=csv.QUOTE_ALL)
    
    conn = get_conn()
    with conn.cursor() as cur:
        cur.execute(f"""
        LOAD DATA LOCAL INFILE '{br_csv.replace('\\', '/')}')
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
    print(f"  Loaded {len(df)} borrow records")
else:
    print(f"  Already exists ({br_cnt}), skip")

# ==================== 5. ACCESS LOGS ====================
print("[5/6] Access logs...")
conn = get_conn()
with conn.cursor() as cur:
    cur.execute("SELECT COUNT(*) FROM access_logs")
    al_cnt = cur.fetchone()[0]
conn.close()

if al_cnt == 0:
    files = list((RAW_ROOT / '门禁数据').rglob('*.csv'))
    print(f"  Found {len(files)} access CSV files")
    # concatenate and import
    all_dfs = []
    for f in files:
        try:
            d = pd.read_csv(f, encoding='gbk')
            all_dfs.append(d)
        except Exception as e:
            print(f"    skip {f.name}: {e}")
    if all_dfs:
        df = pd.concat(all_dfs, ignore_index=True)
        # rename based on typical columns
        cols = {c.upper(): c for c in df.columns}
        rename_map = {}
        for c in df.columns:
            u = c.upper()
            if 'ID' in u or 'USER' in u or 'READER' in u:
                rename_map[c] = 'uid'
            elif 'TIME' in u or 'DATE' in u:
                rename_map[c] = 'access_time'
            elif 'DOOR' in u or 'GATE' in u or 'DEVICE' in u:
                rename_map[c] = 'gate_id'
            elif 'DIREC' in u or 'INOUT' in u or 'TYPE' in u:
                rename_map[c] = 'direction'
            elif 'ROOM' in u or 'AREA' in u:
                rename_map[c] = 'room_id'
        df = df.rename(columns=rename_map)
        # map uid -> user_id if possible
        conn = get_conn()
        with conn.cursor() as cur:
            cur.execute("SELECT id, uid FROM users")
            uid_to_id = {row[1]: row[0] for row in cur.fetchall()}
        conn.close()
        if 'uid' in df.columns:
            df['user_id'] = df['uid'].map(uid_to_id)
            df = df[df['user_id'].notna()].copy()
        else:
            df['user_id'] = 1
        df['access_time'] = pd.to_datetime(df.get('access_time', pd.Timestamp('2023-01-01')), errors='coerce').fillna(pd.Timestamp('2023-01-01'))
        df['gate_id'] = df.get('gate_id', 'G01').astype(str).str[:20]
        df['direction'] = df.get('direction', 'in').astype(str).str[:10]
        df['room_id'] = df.get('room_id', 'R01').astype(str).str[:20]
        
        acols = ['user_id','access_time','gate_id','direction','room_id']
        acsv = str(TMP_DIR / 'access_logs.csv')
        df[acols].to_csv(acsv, index=False, encoding='utf-8-sig', quoting=csv.QUOTE_ALL)
        
        conn = get_conn()
        with conn.cursor() as cur:
            cur.execute(f"""
            LOAD DATA LOCAL INFILE '{acsv.replace('\\', '/')}')
            INTO TABLE access_logs
            CHARACTER SET utf8mb4
            FIELDS TERMINATED BY ','
            OPTIONALLY ENCLOSED BY '"'
            LINES TERMINATED BY '\\r\\n'
            IGNORE 1 LINES
            ({','.join(acols)})
            """)
        conn.commit()
        conn.close()
        print(f"  Loaded {len(df)} access logs")
    else:
        print("  No access data found")
else:
    print(f"  Already exists ({al_cnt}), skip")

# ==================== 6. SEAT LOGS ====================
print("[6/6] Seat logs...")
conn = get_conn()
with conn.cursor() as cur:
    cur.execute("SELECT COUNT(*) FROM seat_logs")
    sl_cnt = cur.fetchone()[0]
conn.close()

if sl_cnt == 0:
    files = list((RAW_ROOT / '座位数据').rglob('*.csv'))
    print(f"  Found {len(files)} seat CSV files")
    all_dfs = []
    for f in files:
        try:
            d = pd.read_csv(f, encoding='gbk')
            all_dfs.append(d)
        except Exception as e:
            print(f"    skip {f.name}: {e}")
    if all_dfs:
        df = pd.concat(all_dfs, ignore_index=True)
        rename_map = {}
        for c in df.columns:
            u = c.upper()
            if 'ID' in u or 'USER' in u or 'READER' in u:
                rename_map[c] = 'uid'
            elif 'START' in u or 'BEGIN' in u:
                rename_map[c] = 'start_time'
            elif 'END' in u or 'LEAVE' in u or 'FINISH' in u:
                rename_map[c] = 'end_time'
            elif 'SEAT' in u or 'NO' in u:
                rename_map[c] = 'seat_no'
            elif 'ROOM' in u or 'AREA' in u:
                rename_map[c] = 'room_id'
            elif 'STATUS' in u or 'STATE' in u:
                rename_map[c] = 'status'
        df = df.rename(columns=rename_map)
        conn = get_conn()
        with conn.cursor() as cur:
            cur.execute("SELECT id, uid FROM users")
            uid_to_id = {row[1]: row[0] for row in cur.fetchall()}
        conn.close()
        if 'uid' in df.columns:
            df['user_id'] = df['uid'].map(uid_to_id)
            df = df[df['user_id'].notna()].copy()
        else:
            df['user_id'] = 1
        df['start_time'] = pd.to_datetime(df.get('start_time', pd.Timestamp('2023-01-01')), errors='coerce').fillna(pd.Timestamp('2023-01-01'))
        df['end_time'] = pd.to_datetime(df.get('end_time'), errors='coerce')
        df['seat_no'] = df.get('seat_no', 'S001').astype(str).str[:20]
        df['room_id'] = df.get('room_id', 'R01').astype(str).str[:20]
        df['status'] = df.get('status', 'used').astype(str).str[:20]
        
        scols = ['user_id','start_time','end_time','seat_no','room_id','status']
        scsv = str(TMP_DIR / 'seat_logs.csv')
        df[scols].to_csv(scsv, index=False, encoding='utf-8-sig', quoting=csv.QUOTE_ALL)
        
        conn = get_conn()
        with conn.cursor() as cur:
            cur.execute(f"""
            LOAD DATA LOCAL INFILE '{scsv.replace('\\', '/')}')
            INTO TABLE seat_logs
            CHARACTER SET utf8mb4
            FIELDS TERMINATED BY ','
            OPTIONALLY ENCLOSED BY '"'
            LINES TERMINATED BY '\\r\\n'
            IGNORE 1 LINES
            ({','.join(scols)})
            """)
        conn.commit()
        conn.close()
        print(f"  Loaded {len(df)} seat logs")
    else:
        print("  No seat data found")
else:
    print(f"  Already exists ({sl_cnt}), skip")

print("\nAll done!")

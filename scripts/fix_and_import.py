"""
Fix books table structure and continue importing data into smart_library_v3.
"""
import pandas as pd
import pymysql
from pathlib import Path
import csv

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

# ============= FIX books table =============
print("[FIX] Dropping and recreating books & inventory...")
conn = get_conn()
with conn.cursor() as cur:
    cur.execute("SET FOREIGN_KEY_CHECKS = 0")
    cur.execute("DROP TABLE IF EXISTS book_inventory")
    cur.execute("DROP TABLE IF EXISTS books")
    cur.execute("""
    CREATE TABLE `books` (
        `isbn`              VARCHAR(13)     NOT NULL    COMMENT 'ISBN-13',
        `barcode`           VARCHAR(50)     NOT NULL    COMMENT '图书馆内部条码',
        `title`             VARCHAR(255)    NOT NULL    COMMENT '书名',
        `authors`           VARCHAR(500)    NOT NULL    COMMENT '作者列表',
        `publisher`         VARCHAR(255)    NOT NULL    COMMENT '出版社',
        `publish_year`      INT             NULL        COMMENT '出版年份',
        `category_code`     VARCHAR(10)     NOT NULL    COMMENT '分类编码',
        `call_no`           VARCHAR(100)    NULL        COMMENT '索书号',
        `language`          VARCHAR(20)     DEFAULT '中文' COMMENT '图书语言',
        `doc_type`          VARCHAR(50)     DEFAULT '普通图书' COMMENT '文献类型',
        `total_copies`      INT             NOT NULL    DEFAULT 1 COMMENT '馆藏总册数',
        `available_copies`  INT             NOT NULL    DEFAULT 1 COMMENT '当前可借册数',
        `location`          VARCHAR(50)     NOT NULL    COMMENT '馆藏位置',
        `status`            VARCHAR(10)     NOT NULL    DEFAULT '在库' COMMENT '在库/借出/下架/遗失/编目中',
        `created_at`        DATETIME        DEFAULT CURRENT_TIMESTAMP COMMENT '录入时间',
        `updated_at`        DATETIME        DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '最后更新时间',
        PRIMARY KEY (`isbn`),
        UNIQUE KEY `uk_barcode` (`barcode`),
        KEY `idx_title` (`title`),
        KEY `idx_category` (`category_code`),
        KEY `idx_status` (`status`),
        CONSTRAINT `fk_book_category` FOREIGN KEY (`category_code`) REFERENCES `categories`(`code`)
            ON DELETE RESTRICT ON UPDATE CASCADE
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='图书主信息表';
    """)
    cur.execute("""
    CREATE TABLE `book_inventory` (
        `isbn`      VARCHAR(13) NOT NULL    COMMENT 'ISBN',
        `stock`     INT         NOT NULL    DEFAULT 0 COMMENT '实时库存',
        `updated_at` DATETIME   DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
        PRIMARY KEY (`isbn`),
        CONSTRAINT `fk_inv_book` FOREIGN KEY (`isbn`) REFERENCES `books`(`isbn`)
            ON DELETE CASCADE ON UPDATE CASCADE
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='图书库存实时表';
    """)
    cur.execute("SET FOREIGN_KEY_CHECKS = 1")
conn.commit()
conn.close()
print("  Recreated.")

# ============= IMPORT BOOKS =============
print("[3] Importing books...")
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
    print(f"  Books loaded: {cur.fetchone()[0]}")
conn.close()

# Inventory
inv_csv = str(TMP_DIR / 'inventory.csv')
if not Path(inv_csv).exists():
    print("  Generating inventory CSV...")
    inv = pd.read_csv(RAW_ROOT / '借阅数据' / '借阅数据' / '图书数据.csv', encoding='utf-8', dtype=str, usecols=['ID'])
    inv = inv.rename(columns={'ID':'isbn'})
    inv['stock'] = 1
    inv.to_csv(inv_csv, index=False, encoding='utf-8-sig', quoting=csv.QUOTE_ALL)

conn = get_conn()
with conn.cursor() as cur:
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
    print(f"  Inventory loaded: {cur.fetchone()[0]}")
conn.close()

# ============= IMPORT BORROW RECORDS =============
print("[4] Importing borrow records...")
conn = get_conn()
with conn.cursor() as cur:
    cur.execute("SELECT COUNT(*) FROM borrow_records")
    br_cnt = cur.fetchone()[0]
conn.close()

if br_cnt == 0:
    # Build uid->id map
    conn = get_conn()
    with conn.cursor() as cur:
        cur.execute("SELECT id, uid FROM users")
        uid_to_id = {row[1]: row[0] for row in cur.fetchall()}
    conn.close()
    print(f"  User map: {len(uid_to_id)}")
    
    # Temporarily drop secondary indexes on borrow_records for speed
    conn = get_conn()
    with conn.cursor() as cur:
        cur.execute("ALTER TABLE borrow_records DROP INDEX idx_br_user")
        cur.execute("ALTER TABLE borrow_records DROP INDEX idx_br_isbn")
        cur.execute("ALTER TABLE borrow_records DROP INDEX idx_br_status")
        cur.execute("ALTER TABLE borrow_records DROP INDEX idx_br_return")
        cur.execute("ALTER TABLE borrow_records DROP INDEX idx_br_borrow_time")
        conn.commit()
        print("  Dropped secondary indexes")
    conn.close()
    
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
        
        brcols = ['borrow_id','user_id','isbn','borrow_time','due_time','return_time','operator_id','status','overdue_days','renew_count','is_deleted']
        br_csv = str(TMP_DIR / f'borrow_{chunk_idx}.csv')
        chunk[brcols].to_csv(br_csv, index=False, encoding='utf-8-sig', quoting=csv.QUOTE_ALL)
        
        conn = get_conn()
        with conn.cursor() as cur:
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
        print(f"  Chunk {chunk_idx}: +{len(chunk)} => total {total}")
    
    # Rebuild indexes
    conn = get_conn()
    with conn.cursor() as cur:
        cur.execute("ALTER TABLE borrow_records ADD KEY idx_br_user (user_id)")
        cur.execute("ALTER TABLE borrow_records ADD KEY idx_br_isbn (isbn)")
        cur.execute("ALTER TABLE borrow_records ADD KEY idx_br_status (status)")
        cur.execute("ALTER TABLE borrow_records ADD KEY idx_br_return (return_time)")
        cur.execute("ALTER TABLE borrow_records ADD KEY idx_br_borrow_time (borrow_time)")
        conn.commit()
        print(f"  Rebuilt indexes. Total: {total}")
    conn.close()
else:
    print(f"  Already exists ({br_cnt}), skip")

# ============= FULLTEXT INDEX =============
print("[5] Adding fulltext index on books...")
conn = get_conn()
with conn.cursor() as cur:
    try:
        cur.execute("ALTER TABLE books ADD FULLTEXT KEY ft_title_authors (title, authors)")
        conn.commit()
        print("  Done")
    except Exception as e:
        print(f"  Warn: {e}")
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

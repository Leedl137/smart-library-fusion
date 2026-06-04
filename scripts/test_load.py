import pymysql
conn = pymysql.connect(
    host='127.0.0.1', port=3306, user='root',
    password='123456', database='smart_library_v2',
    local_infile=True,
)
with conn.cursor() as cur:
    cur.execute("SET SESSION local_infile = 1")
    cur.execute("SHOW VARIABLES LIKE 'local_infile'")
    print(cur.fetchone())
    
    # Test with a tiny CSV
    csv_path = r'C:\Users\think\Desktop\软著\smart_library_fusion\scripts\tmp_csv\books.csv'
    print(f"Testing LOAD DATA with: {csv_path}")
    sql = f"""
    LOAD DATA LOCAL INFILE '{csv_path.replace(chr(92), chr(47))}'
    INTO TABLE books
    CHARACTER SET utf8mb4
    FIELDS TERMINATED BY ','
    OPTIONALLY ENCLOSED BY '"'
    LINES TERMINATED BY '\r\n'
    IGNORE 1 LINES
    (isbn,barcode,title,authors,publisher,publish_year,category_code,call_no,language,doc_type,total_copies,available_copies,location,status)
    """
    cur.execute(sql)
    print(f"Affected rows: {cur.rowcount}")
conn.commit()
with conn.cursor() as cur:
    cur.execute("SELECT COUNT(*) FROM books")
    print(f"Total books: {cur.fetchone()[0]}")
conn.close()

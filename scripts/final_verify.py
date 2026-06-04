import pymysql

conn = pymysql.connect(host='127.0.0.1', port=3306, user='root', password='123456', database='smart_library_v2')

print("[FINAL VERIFY] Table counts:")
with conn.cursor() as cur:
    tables = ['categories', 'users', 'books', 'book_inventory', 'borrow_records', 'access_logs', 'seat_logs', 'reading_rooms']
    for t in tables:
        cur.execute(f'SELECT COUNT(*) FROM {t}')
        count = cur.fetchone()[0]
        print(f"  {t}: {count}")
    
    # Check views
    cur.execute("SHOW TABLES LIKE 'v_%'")
    views = cur.fetchall()
    print(f"\n  Views: {len(views)}")
    for v in views:
        print(f"    {v[0]}")

conn.close()

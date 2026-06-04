import pymysql
conn = pymysql.connect(host='127.0.0.1', port=3306, user='root', password='123456', database='smart_library_v2', charset='utf8mb4')
cursor = conn.cursor()

tables = ['users', 'books', 'borrow_records', 'access_logs', 'seat_logs', 'reading_rooms']
for t in tables:
    cursor.execute(f"SHOW INDEX FROM {t}")
    indexes = cursor.fetchall()
    print(f"\n{t}:")
    for idx in indexes:
        print(f"  {idx[2]}: {idx[4]} ({'UNIQUE' if idx[1]==0 else ''})")
conn.close()

import pymysql
import time

conn = pymysql.connect(host='127.0.0.1', port=3306, user='root', password='123456', database='smart_library_v2')

queries = [
    ("SELECT COUNT(*) FROM users", "users count"),
    ("SELECT COUNT(*) FROM books", "books count"),
    ("SELECT COUNT(*) FROM borrow_records WHERE is_deleted=0", "borrow count"),
    ("SELECT COUNT(*) FROM access_logs", "access_logs count"),
    ("SELECT reader_type, COUNT(*) FROM users GROUP BY reader_type", "reader types"),
    ("""SELECT u.department AS `学院`, COUNT(*) AS `总借阅次数`
        FROM borrow_records br
        JOIN users u ON br.user_id = u.id
        WHERE br.is_deleted = 0
        GROUP BY u.department
        ORDER BY `总借阅次数` DESC
        LIMIT 10""", "dept stats"),
    ("""SELECT DATE_FORMAT(`borrow_time`, '%Y-%m') AS `月份`, COUNT(*) AS `借阅次数`
        FROM borrow_records
        WHERE is_deleted = 0
        GROUP BY DATE_FORMAT(`borrow_time`, '%Y-%m')
        ORDER BY `月份`
        LIMIT 24""", "monthly trend"),
]

for sql, desc in queries:
    t0 = time.time()
    with conn.cursor() as cur:
        cur.execute(sql)
        cur.fetchall()
    t1 = time.time()
    print(f"{desc}: {t1-t0:.2f}s")

conn.close()

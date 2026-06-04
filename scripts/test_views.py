import pymysql
import time

conn = pymysql.connect(host='127.0.0.1', port=3306, user='root', password='123456', database='smart_library_v2')

queries = [
    ("SELECT COUNT(*) FROM borrow_records", "Count borrow_records"),
    ("SELECT COUNT(*) FROM users", "Count users"),
    ("SELECT * FROM v_department_borrow_stats LIMIT 5", "Department stats"),
    ("SELECT * FROM v_monthly_borrow_trend LIMIT 5", "Monthly trend"),
]

for sql, desc in queries:
    t0 = time.time()
    with conn.cursor() as cur:
        cur.execute(sql)
        rows = cur.fetchall()
    t1 = time.time()
    print(f"{desc}: {t1-t0:.2f}s, rows: {len(rows)}")
    for r in rows[:3]:
        print(f"  {r}")

conn.close()

import pymysql
import time

conn = pymysql.connect(host='127.0.0.1', port=3306, user='root', password='123456', database='smart_library_v2')

# Original view query
sql1 = """
SELECT `学院`, `总借阅次数` FROM `v_department_borrow_stats` LIMIT 10
"""

# Simplified query
sql2 = """
SELECT u.department, COUNT(*) as total
FROM borrow_records br
JOIN users u ON br.user_id = u.id
WHERE br.is_deleted = 0
GROUP BY u.department
ORDER BY total DESC
LIMIT 10
"""

for sql, desc in [(sql1, "Original view"), (sql2, "Simplified")]:
    t0 = time.time()
    with conn.cursor() as cur:
        cur.execute(sql)
        rows = cur.fetchall()
    t1 = time.time()
    print(f"{desc}: {t1-t0:.2f}s, rows: {len(rows)}")
    for r in rows[:3]:
        print(f"  {r}")

conn.close()

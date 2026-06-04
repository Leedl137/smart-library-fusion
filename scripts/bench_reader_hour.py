import time, pymysql

conn = pymysql.connect(host='127.0.0.1', port=3306, user='root', password='123456', database='smart_library_v2', charset='utf8mb4')

def bench(sql, label):
    print(f"\n--- {label} ---")
    t0 = time.time()
    with conn.cursor() as c:
        c.execute(sql)
        rows = c.fetchall()
        t1 = time.time()
        print(f"  OK: {len(rows)} rows in {t1-t0:.2f}s")

# Original (from dashboard_data.py)
bench("""
SELECT u.reader_type AS `读者类型`, HOUR(g.visit_time) AS `24小时时段`,
       COUNT(g.log_id) AS `入馆总人次`
FROM access_logs g
JOIN users u ON g.user_id = u.id
WHERE HOUR(g.visit_time) BETWEEN 6 AND 23
  AND u.reader_type IS NOT NULL AND u.reader_type != ''
GROUP BY u.reader_type, HOUR(g.visit_time)
ORDER BY u.reader_type, `24小时时段`
""", "original reader_hour")

# Optimized: subquery first then SUM
bench("""
SELECT u.reader_type, h.hr AS `24小时时段`, SUM(h.cnt) AS `入馆总人次`
FROM (
    SELECT user_id, HOUR(visit_time) AS hr, COUNT(*) AS cnt
    FROM access_logs
    WHERE HOUR(visit_time) BETWEEN 6 AND 23
    GROUP BY user_id, HOUR(visit_time)
) h
JOIN users u ON h.user_id = u.id
WHERE u.reader_type IS NOT NULL AND u.reader_type != ''
GROUP BY u.reader_type, h.hr
ORDER BY u.reader_type, h.hr
""", "subquery-first reader_hour")

# Optimized v2: only join needed columns
bench("""
SELECT u.reader_type, h.hr AS `24小时时段`, SUM(h.cnt) AS `入馆总人次`
FROM (
    SELECT user_id, HOUR(visit_time) AS hr, COUNT(*) AS cnt
    FROM access_logs
    WHERE HOUR(visit_time) BETWEEN 6 AND 23
    GROUP BY user_id, HOUR(visit_time)
) h
JOIN (SELECT id, reader_type FROM users WHERE reader_type IS NOT NULL AND reader_type != '') u
  ON h.user_id = u.id
GROUP BY u.reader_type, h.hr
ORDER BY u.reader_type, h.hr
""", "filtered users join")

conn.close()

import time, pymysql

conn = pymysql.connect(host='127.0.0.1', port=3306, user='root', password='123456', database='smart_library_v2', charset='utf8mb4')

def bench(sql, label, timeout=60):
    print(f"\n--- {label} ---")
    t0 = time.time()
    try:
        with conn.cursor() as c:
            c.execute(sql)
            rows = c.fetchall()
            t1 = time.time()
            print(f"  OK: {len(rows)} rows in {t1-t0:.2f}s")
    except Exception as e:
        t1 = time.time()
        print(f"  ERROR after {t1-t0:.2f}s: {e}")

bench("SELECT COUNT(*) FROM users", "users count")
bench("SELECT COUNT(*) FROM books", "books count")
bench("SELECT COUNT(*) FROM borrow_records WHERE is_deleted=0", "borrow count")
bench("SHOW TABLE STATUS LIKE 'access_logs'", "access_logs approx")

bench("""
SELECT DATE(visit_time) AS d, COUNT(*) AS c
FROM access_logs
WHERE visit_time >= DATE_SUB(CURDATE(), INTERVAL 365 DAY)
GROUP BY DATE(visit_time)
ORDER BY d
""", "daily access (365d)")

bench("""
SELECT rm.room_name, COUNT(s.log_id) AS c
FROM reading_rooms rm
LEFT JOIN seat_logs s ON rm.room_no = s.room_no
GROUP BY rm.room_no, rm.room_name
ORDER BY c DESC
""", "room heat")

bench("""
SELECT u.department, COUNT(*) AS c
FROM borrow_records br
JOIN users u ON br.user_id = u.id
WHERE br.is_deleted = 0
GROUP BY u.department
ORDER BY c DESC LIMIT 10
""", "dept borrow")

bench("""
SELECT reader_type, COUNT(*) AS value
FROM users
WHERE reader_type IS NOT NULL AND reader_type != ''
GROUP BY reader_type
ORDER BY value DESC LIMIT 8
""", "reader types")

bench("""
SELECT DATE_FORMAT(borrow_time, '%Y-%m') AS m, COUNT(*) AS c
FROM borrow_records WHERE is_deleted = 0
GROUP BY DATE_FORMAT(borrow_time, '%Y-%m')
ORDER BY m LIMIT 24
""", "monthly borrow")

bench("""
SELECT bk.doc_type, COUNT(DISTINCT bk.isbn) AS a, COUNT(DISTINCT br.isbn) AS b,
       ROUND(COUNT(DISTINCT br.isbn)/COUNT(DISTINCT bk.isbn)*100,2)
FROM books bk
LEFT JOIN borrow_records br ON bk.isbn = br.isbn AND br.is_deleted = 0
GROUP BY bk.doc_type
HAVING a > 100
ORDER BY 4 DESC
""", "circulation")

bench("""
SELECT u.reader_type, COUNT(*) AS c, ROUND(AVG(access_cnt),1), ROUND(AVG(borrow_cnt),1)
FROM users u
LEFT JOIN (SELECT user_id, COUNT(*) AS access_cnt FROM access_logs WHERE visit_time >= DATE_SUB(CURDATE(), INTERVAL 365 DAY) GROUP BY user_id) ac ON u.id = ac.user_id
LEFT JOIN (SELECT user_id, COUNT(*) AS borrow_cnt FROM borrow_records WHERE is_deleted = 0 GROUP BY user_id) bc ON u.id = bc.user_id
WHERE u.reader_type IS NOT NULL AND u.reader_type != ''
GROUP BY u.reader_type
HAVING c > 50
ORDER BY c DESC
""", "reader profile (365d)")

bench("""
SELECT u.reader_type, HOUR(g.visit_time) AS h, COUNT(g.log_id) AS c
FROM access_logs g
JOIN users u ON g.user_id = u.id
WHERE g.visit_time >= DATE_SUB(CURDATE(), INTERVAL 90 DAY)
  AND HOUR(g.visit_time) BETWEEN 6 AND 23
  AND u.reader_type IS NOT NULL AND u.reader_type != ''
GROUP BY u.reader_type, HOUR(g.visit_time)
ORDER BY u.reader_type, h
""", "reader hour (90d)")

conn.close()
print("\nDone.")

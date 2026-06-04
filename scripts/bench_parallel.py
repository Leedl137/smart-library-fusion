import time, pymysql
from concurrent.futures import ThreadPoolExecutor

def run_query(args):
    label, sql = args
    conn = pymysql.connect(host='127.0.0.1', port=3306, user='root', password='123456', database='smart_library_v2', charset='utf8mb4')
    t0 = time.time()
    with conn.cursor() as c:
        c.execute(sql)
        rows = c.fetchall()
        cols = [d[0] for d in c.description] if c.description else []
    conn.close()
    t1 = time.time()
    return label, t1-t0, len(rows), cols, rows

queries = [
    ("books_count", "SELECT COUNT(*) FROM books"),
    ("borrow_count", "SELECT COUNT(*) FROM borrow_records WHERE is_deleted=0"),
    ("access_approx", "SHOW TABLE STATUS LIKE 'access_logs'"),
    ("daily_access", """
        SELECT DATE(visit_time) AS `日期`, COUNT(*) AS `日入馆人次`
        FROM access_logs
        WHERE visit_time >= '2018-01-01'
        GROUP BY DATE(visit_time)
        ORDER BY `日期`
    """),
    ("room_heat", """
        SELECT rm.room_name AS `阅览室名称`, COUNT(s.log_id) AS `累计使用人次`
        FROM reading_rooms rm
        LEFT JOIN seat_logs s ON rm.room_no = s.room_no
        GROUP BY rm.room_no, rm.room_name
        ORDER BY `累计使用人次` DESC
    """),
    ("dept_borrow", """
        SELECT u.department AS `学院`, COUNT(*) AS `学院总借阅册数`
        FROM borrow_records br
        JOIN users u ON br.user_id = u.id
        WHERE br.is_deleted = 0
        GROUP BY u.department
        ORDER BY `学院总借阅册数` DESC LIMIT 10
    """),
    ("reader_types", """
        SELECT reader_type AS `name`, COUNT(*) AS `value`
        FROM users WHERE reader_type IS NOT NULL AND reader_type != ''
        GROUP BY reader_type ORDER BY `value` DESC LIMIT 8
    """),
    ("monthly", """
        SELECT DATE_FORMAT(borrow_time, '%Y-%m') AS `月份`, COUNT(*) AS `借阅次数`
        FROM borrow_records WHERE is_deleted = 0
        GROUP BY DATE_FORMAT(borrow_time, '%Y-%m') ORDER BY `月份` LIMIT 24
    """),
    ("circulation", """
        SELECT b.doc_type AS `图书类型`, COUNT(*) AS `馆藏总册数`,
               COUNT(br.isbn) AS `曾被借阅册数`,
               ROUND(COUNT(br.isbn)/COUNT(*)*100,2) AS `流通率(%)`
        FROM books b
        LEFT JOIN (
            SELECT DISTINCT isbn FROM borrow_records WHERE is_deleted = 0
        ) br ON b.isbn = br.isbn
        GROUP BY b.doc_type
        HAVING `馆藏总册数` > 100
        ORDER BY `流通率(%)` DESC
    """),
    ("reader_profile", """
        SELECT u.reader_type AS `读者类型`, COUNT(*) AS `群体总人数`,
               ROUND(AVG(access_cnt), 1) AS `人均入馆次数`,
               ROUND(AVG(borrow_cnt), 1) AS `人均借阅量`
        FROM users u
        LEFT JOIN (
            SELECT user_id, COUNT(*) AS access_cnt FROM access_logs GROUP BY user_id
        ) ac ON u.id = ac.user_id
        LEFT JOIN (
            SELECT user_id, COUNT(*) AS borrow_cnt FROM borrow_records WHERE is_deleted = 0 GROUP BY user_id
        ) bc ON u.id = bc.user_id
        WHERE u.reader_type IS NOT NULL AND u.reader_type != ''
        GROUP BY u.reader_type
        HAVING `群体总人数` > 50
        ORDER BY `群体总人数` DESC
    """),
    ("reader_hour", """
        SELECT u.reader_type AS `读者类型`, HOUR(g.visit_time) AS `24小时时段`,
               COUNT(g.log_id) AS `入馆总人次`
        FROM access_logs g
        JOIN users u ON g.user_id = u.id
        WHERE HOUR(g.visit_time) BETWEEN 6 AND 23
          AND u.reader_type IS NOT NULL AND u.reader_type != ''
        GROUP BY u.reader_type, HOUR(g.visit_time)
        ORDER BY u.reader_type, `24小时时段`
    """),
]

t0 = time.time()
with ThreadPoolExecutor(max_workers=6) as pool:
    results = list(pool.map(run_query, queries))
t1 = time.time()

for label, elapsed, nrows, cols, rows in results:
    print(f"{label}: {nrows} rows in {elapsed:.2f}s")

print(f"\nTotal parallel time: {t1-t0:.2f}s")

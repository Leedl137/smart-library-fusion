import time, pymysql
from concurrent.futures import ThreadPoolExecutor, as_completed

def run_query(args):
    label, sql = args
    conn = pymysql.connect(host='127.0.0.1', port=3306, user='root', password='123456',
                           database='smart_library_v2', charset='utf8mb4',
                           cursorclass=pymysql.cursors.DictCursor)
    t0 = time.time()
    with conn.cursor() as c:
        c.execute(sql)
        rows = c.fetchall()
    conn.close()
    t1 = time.time()
    return label, t1-t0, len(rows)

queries = {
    "daily_access": """
        SELECT DATE(visit_time) AS `日期`, COUNT(*) AS `日入馆人次`
        FROM access_logs
        WHERE visit_time >= '2018-01-01'
        GROUP BY DATE(visit_time)
        ORDER BY `日期`
    """,
    "room_heat": """
        SELECT rm.room_name AS `阅览室名称`, COUNT(s.log_id) AS `累计使用人次`
        FROM reading_rooms rm
        LEFT JOIN seat_logs s ON rm.room_no = s.room_no
        GROUP BY rm.room_no, rm.room_name
        ORDER BY `累计使用人次` DESC
    """,
    "dept_borrow": """
        SELECT u.department AS `学院`, COUNT(*) AS `学院总借阅册数`
        FROM borrow_records br
        JOIN users u ON br.user_id = u.id
        WHERE br.is_deleted = 0
        GROUP BY u.department
        ORDER BY `学院总借阅册数` DESC
        LIMIT 10
    """,
    "reader_types": """
        SELECT reader_type AS `name`, COUNT(*) AS `value`
        FROM users
        WHERE reader_type IS NOT NULL AND reader_type != ''
        GROUP BY reader_type
        ORDER BY `value` DESC
        LIMIT 8
    """,
    "monthly": """
        SELECT DATE_FORMAT(borrow_time, '%Y-%m') AS `月份`, COUNT(*) AS `借阅次数`
        FROM borrow_records
        WHERE is_deleted = 0
        GROUP BY DATE_FORMAT(borrow_time, '%Y-%m')
        ORDER BY `月份`
        LIMIT 24
    """,
    "circulation": """
        SELECT b.doc_type AS `图书类型`, COUNT(*) AS `馆藏总册数`,
               COUNT(br.isbn) AS `曾被借阅册数`,
               ROUND(COUNT(br.isbn) / COUNT(*) * 100, 2) AS `流通率(%)`
        FROM books b
        LEFT JOIN (
            SELECT DISTINCT isbn FROM borrow_records WHERE is_deleted = 0
        ) br ON b.isbn = br.isbn
        GROUP BY b.doc_type
        HAVING COUNT(*) > 100
        ORDER BY `流通率(%)` DESC
    """,
}

t0 = time.time()
with ThreadPoolExecutor(max_workers=6) as pool:
    futures = {pool.submit(run_query, (label, sql)): label for label, sql in queries.items()}
    for fut in as_completed(futures):
        label, elapsed, nrows = fut.result()
        print(f"{label}: {nrows} rows in {elapsed:.2f}s")
t1 = time.time()
print(f"Total parallel: {t1-t0:.2f}s")

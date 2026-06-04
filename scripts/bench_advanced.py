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
    "circulation": """
        SELECT b.doc_type AS `图书类型`, COUNT(*) AS `馆藏总册数`,
               COUNT(br.isbn) AS `曾被借阅册数`,
               ROUND(COUNT(br.isbn)/COUNT(*)*100,2) AS `流通率(%)`
        FROM books b
        LEFT JOIN (SELECT DISTINCT isbn FROM borrow_records WHERE is_deleted = 0) br ON b.isbn = br.isbn
        GROUP BY b.doc_type
        HAVING COUNT(*) > 100
        ORDER BY `流通率(%)` DESC
    """,
    "study_only": """
        SELECT u.uid AS `学号`, ac.access_cnt AS `入馆次数`, bc.borrow_cnt AS `总借阅量`
        FROM users u
        LEFT JOIN (SELECT user_id, COUNT(*) AS access_cnt FROM access_logs GROUP BY user_id) ac ON u.id = ac.user_id
        LEFT JOIN (SELECT user_id, COUNT(*) AS borrow_cnt FROM borrow_records WHERE is_deleted = 0 GROUP BY user_id) bc ON u.id = bc.user_id
        WHERE ac.access_cnt > 100 AND (bc.borrow_cnt IS NULL OR bc.borrow_cnt < 3)
    """,
    "super_reader": """
        SELECT r.uid AS `学号`, r.department AS `学院`, bc.borrow_cnt AS `总借阅量`,
               ROUND(avg_dept.avg_borrows, 2) AS `本院平均借阅量`
        FROM users r
        JOIN (SELECT department, AVG(borrow_cnt) AS avg_borrows FROM users u2
              LEFT JOIN (SELECT user_id, COUNT(*) AS borrow_cnt FROM borrow_records WHERE is_deleted = 0 GROUP BY user_id) b2 ON u2.id = b2.user_id
              GROUP BY department) avg_dept ON r.department = avg_dept.department
        LEFT JOIN (SELECT user_id, COUNT(*) AS borrow_cnt FROM borrow_records WHERE is_deleted = 0 GROUP BY user_id) bc ON r.id = bc.user_id
        WHERE bc.borrow_cnt > avg_dept.avg_borrows * 2
        ORDER BY (bc.borrow_cnt - avg_dept.avg_borrows) DESC LIMIT 50
    """,
    "branch_fan": """
        SELECT r.uid AS `学号`, r.department AS `学院`
        FROM users r
        WHERE NOT EXISTS (
            SELECT 1 FROM reading_rooms rm
            WHERE rm.room_name LIKE '%分馆%'
              AND NOT EXISTS (
                  SELECT 1 FROM seat_logs s WHERE s.user_id = r.id AND s.room_no = rm.room_no
              )
        )
    """,
    "streak": """
        WITH Target_Month_Visits AS (
            SELECT user_id, DATE(visit_time) AS `访问日期`
            FROM access_logs WHERE visit_time >= '2018-06-01' AND visit_time < '2018-07-01'
            GROUP BY user_id, DATE(visit_time)
        ),
        Ranked_Visits AS (
            SELECT user_id, `访问日期`, ROW_NUMBER() OVER(PARTITION BY user_id ORDER BY `访问日期`) AS rn
            FROM Target_Month_Visits
        ),
        Streak_Groups AS (
            SELECT user_id, `访问日期`, DATE_SUB(`访问日期`, INTERVAL rn DAY) AS `基准日期`
            FROM Ranked_Visits
        )
        SELECT u.uid AS `学号`, MIN(`访问日期`) AS `连续起始日`, MAX(`访问日期`) AS `连续结束日`, COUNT(*) AS `连续打卡天数`
        FROM Streak_Groups sg
        JOIN users u ON sg.user_id = u.id
        GROUP BY sg.user_id, `基准日期`
        HAVING COUNT(*) >= 7
        ORDER BY `连续打卡天数` DESC
    """,
    "peak_room": """
        WITH Event_Stream AS (
            SELECT room_no, start_time AS event_time, 1 AS change_val FROM seat_logs
            WHERE start_time >= '2018-06-01' AND start_time < '2018-07-01' AND end_time IS NOT NULL
            UNION ALL
            SELECT room_no, end_time AS event_time, -1 AS change_val FROM seat_logs
            WHERE end_time >= '2018-06-01' AND end_time < '2018-07-01' AND start_time IS NOT NULL
        ),
        Running_Total AS (
            SELECT room_no, event_time,
                   SUM(change_val) OVER(PARTITION BY room_no ORDER BY event_time ASC) AS current_occupancy
            FROM Event_Stream
        )
        SELECT room_no AS `阅览室编号`, event_time AS `达到峰值的精确时间`, current_occupancy AS `最高并发人数`
        FROM (
            SELECT room_no, event_time, current_occupancy,
                   RANK() OVER(PARTITION BY room_no ORDER BY current_occupancy DESC) AS rnk
            FROM Running_Total
        ) t
        WHERE rnk = 1
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

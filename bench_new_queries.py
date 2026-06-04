import pymysql, time
conn = pymysql.connect(host='127.0.0.1', port=3306, user='root', password='123456', charset='utf8mb4', read_timeout=300)
c = conn.cursor()
c.execute('USE smart_library_v2')

queries = {
    "borrow_funnel": """
        SELECT '在库' AS `阶段`, COUNT(*) AS `数量` FROM books WHERE status='在库'
        UNION ALL
        SELECT '被借出', COUNT(DISTINCT isbn) FROM borrow_records WHERE status='borrowed' AND is_deleted=0
        UNION ALL
        SELECT '已归还', COUNT(DISTINCT isbn) FROM borrow_records WHERE status='returned' AND is_deleted=0
        UNION ALL
        SELECT '已逾期', COUNT(DISTINCT isbn) FROM borrow_records WHERE status='overdue' AND is_deleted=0
    """,
    "overdue_trend": """
        SELECT DATE_FORMAT(borrow_time, '%Y-%m') AS `月份`,
            ROUND(SUM(CASE WHEN status='overdue' THEN 1 ELSE 0 END) * 100.0 / COUNT(*), 2) AS `逾期率(%)`,
            COUNT(*) AS `总借阅数`
        FROM borrow_records
        WHERE is_deleted = 0 AND borrow_time >= '2018-01-01'
        GROUP BY DATE_FORMAT(borrow_time, '%Y-%m')
        ORDER BY `月份` LIMIT 24
    """,
    "borrow_turnover": """
        SELECT CASE 
            WHEN turnover_days <= 7 THEN '7天内归还'
            WHEN turnover_days <= 14 THEN '8-14天'
            WHEN turnover_days <= 30 THEN '15-30天'
            WHEN turnover_days <= 60 THEN '31-60天'
            ELSE '60天以上'
        END AS `周转周期`, COUNT(*) AS `图书次数`
        FROM (
            SELECT DATEDIFF(return_time, borrow_time) AS turnover_days
            FROM borrow_records
            WHERE is_deleted = 0 AND return_time IS NOT NULL AND borrow_time >= '2018-01-01'
        ) t
        GROUP BY `周转周期`
        ORDER BY `图书次数` DESC
    """,
    "top_books": """
        SELECT b.title AS `书名`, b.authors AS `作者`, COUNT(*) AS `被借次数`
        FROM borrow_records br
        JOIN books b ON br.isbn = b.isbn
        WHERE br.is_deleted = 0
        GROUP BY b.isbn, b.title, b.authors
        ORDER BY `被借次数` DESC LIMIT 10
    """,
    "renew_analysis": """
        SELECT renew_count AS `续借次数`, COUNT(*) AS `记录数`
        FROM borrow_records WHERE is_deleted = 0
        GROUP BY renew_count
        ORDER BY renew_count LIMIT 10
    """,
    "seat_utilization": """
        SELECT rm.room_name AS `阅览室`,
            ROUND(COUNT(s.log_id) * 100.0 / (rm.capacity * 30), 2) AS `月利用率(%)`
        FROM reading_rooms rm
        LEFT JOIN seat_logs s ON rm.room_no = s.room_no
            AND s.start_time >= '2018-06-01' AND s.start_time < '2018-07-01'
        WHERE rm.capacity > 0
        GROUP BY rm.room_no, rm.room_name, rm.capacity
        ORDER BY `月利用率(%)` DESC
    """,
    "dept_access_borrow": """
        SELECT u.department AS `学院`,
            COUNT(DISTINCT a.log_id) AS `入馆人次`,
            COUNT(DISTINCT br.borrow_id) AS `借阅次数`
        FROM users u
        LEFT JOIN access_logs a ON u.id = a.user_id
            AND a.visit_time >= '2018-06-01' AND a.visit_time < '2018-07-01'
        LEFT JOIN borrow_records br ON u.id = br.user_id
            AND br.borrow_time >= '2018-06-01' AND br.borrow_time < '2018-07-01' AND br.is_deleted = 0
        WHERE u.department IS NOT NULL AND u.department != ''
        GROUP BY u.department
        ORDER BY `借阅次数` DESC LIMIT 10
    """,
    "hourly_borrow": """
        SELECT HOUR(borrow_time) AS `时段`, COUNT(*) AS `借阅次数`
        FROM borrow_records
        WHERE is_deleted = 0 AND borrow_time >= '2018-01-01'
        GROUP BY HOUR(borrow_time)
        ORDER BY `时段`
    """,
}

for name, sql in queries.items():
    t0 = time.time()
    try:
        c.execute(sql)
        rows = c.fetchall()
        print(f'OK {name}: {len(rows)} rows in {time.time()-t0:.1f}s')
    except Exception as e:
        print(f'ERR {name}: {str(e)[:80]} in {time.time()-t0:.1f}s')

conn.close()

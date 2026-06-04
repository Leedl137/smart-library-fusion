import pymysql, time
conn = pymysql.connect(host='127.0.0.1', port=3306, user='root', password='123456', charset='utf8mb4', read_timeout=300)
c = conn.cursor()
c.execute('USE smart_library_v2')

queries = [
    ("borrow_funnel", "SELECT '在库' AS s, COUNT(*) AS v FROM books WHERE status='在库' UNION ALL SELECT '被借出', COUNT(DISTINCT isbn) FROM borrow_records WHERE status='borrowed' AND is_deleted=0 UNION ALL SELECT '已归还', COUNT(DISTINCT isbn) FROM borrow_records WHERE status='returned' AND is_deleted=0 UNION ALL SELECT '已逾期', COUNT(DISTINCT isbn) FROM borrow_records WHERE status='overdue' AND is_deleted=0"),
    ("overdue_trend", "SELECT DATE_FORMAT(borrow_time,'%Y-%m') AS m, ROUND(SUM(CASE WHEN status='overdue' THEN 1 ELSE 0 END)*100.0/COUNT(*),2) AS r, COUNT(*) AS c FROM borrow_records WHERE is_deleted=0 AND borrow_time >= '2018-06-01' GROUP BY m ORDER BY m LIMIT 12"),
    ("borrow_turnover", "SELECT CASE WHEN turnover_days<=7 THEN '7天内' WHEN turnover_days<=14 THEN '8-14天' WHEN turnover_days<=30 THEN '15-30天' ELSE '30天以上' END AS t, COUNT(*) AS c FROM (SELECT DATEDIFF(return_time,borrow_time) AS turnover_days FROM borrow_records WHERE is_deleted=0 AND return_time IS NOT NULL AND borrow_time >= '2018-06-01') t GROUP BY t ORDER BY c DESC"),
    ("top_books", "SELECT b.title, COUNT(*) AS c FROM borrow_records br JOIN books b ON br.isbn=b.isbn WHERE br.is_deleted=0 AND br.borrow_time >= '2018-06-01' GROUP BY b.isbn, b.title ORDER BY c DESC LIMIT 10"),
    ("renew_analysis", "SELECT renew_count, COUNT(*) FROM borrow_records WHERE is_deleted=0 GROUP BY renew_count ORDER BY renew_count LIMIT 10"),
    ("seat_utilization", "SELECT rm.room_name, ROUND(COUNT(s.log_id)*100.0/(rm.capacity*30),2) AS r FROM reading_rooms rm LEFT JOIN seat_logs s ON rm.room_no=s.room_no AND s.start_time >= '2018-06-01' AND s.start_time < '2018-07-01' WHERE rm.capacity>0 GROUP BY rm.room_no, rm.room_name, rm.capacity ORDER BY r DESC"),
    ("dept_access_borrow", "SELECT department, SUM(access_count) AS a, SUM(borrow_count) AS b FROM users WHERE department IS NOT NULL AND department != '' GROUP BY department ORDER BY b DESC LIMIT 10"),
    ("hourly_borrow", "SELECT HOUR(borrow_time), COUNT(*) FROM borrow_records WHERE is_deleted=0 AND borrow_time >= '2018-06-01' GROUP BY HOUR(borrow_time) ORDER BY HOUR(borrow_time)"),
]

for name, sql in queries:
    t0 = time.time()
    try:
        c.execute(sql)
        rows = c.fetchall()
        print(f'OK {name}: {len(rows)} rows in {time.time()-t0:.1f}s')
    except Exception as e:
        print(f'ERR {name}: {str(e)[:60]} in {time.time()-t0:.1f}s')

conn.close()

import pymysql, time
conn = pymysql.connect(host='127.0.0.1', port=3306, user='root', password='123456', charset='utf8mb4')
c = conn.cursor()
c.execute("USE smart_library_v2")

sql = """
    SELECT b.doc_type, COUNT(*) AS total,
           COUNT(br.isbn) AS borrowed,
           ROUND(COUNT(br.isbn) / COUNT(*) * 100, 2) AS rate
    FROM books b
    LEFT JOIN (
        SELECT DISTINCT isbn FROM borrow_records WHERE is_deleted = 0
    ) br ON b.isbn = br.isbn
    GROUP BY b.doc_type
    HAVING COUNT(*) > 100
    ORDER BY rate DESC
"""

t0 = time.time()
c.execute(sql)
rows = c.fetchall()
print(f'circulation_with_index: {len(rows)} rows in {time.time()-t0:.1f}s')
for r in rows:
    print(' ', r)

conn.close()

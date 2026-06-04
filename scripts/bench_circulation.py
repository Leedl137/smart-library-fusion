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
        for r in rows[:3]:
            print(f"    {r}")

# Original
bench("""
SELECT bk.doc_type, COUNT(DISTINCT bk.isbn) AS a, COUNT(DISTINCT br.isbn) AS b,
       ROUND(COUNT(DISTINCT br.isbn)/COUNT(DISTINCT bk.isbn)*100,2)
FROM books bk
LEFT JOIN borrow_records br ON bk.isbn = br.isbn AND br.is_deleted = 0
GROUP BY bk.doc_type
HAVING a > 100
ORDER BY 4 DESC
""", "original circulation")

# Optimized: pre-compute borrowed isbns per doc_type
bench("""
SELECT b.doc_type, COUNT(*) AS total,
       COUNT(br.isbn) AS borrowed,
       ROUND(COUNT(br.isbn)/COUNT(*)*100,2) AS rate
FROM books b
LEFT JOIN (
    SELECT DISTINCT isbn FROM borrow_records WHERE is_deleted = 0
) br ON b.isbn = br.isbn
GROUP BY b.doc_type
HAVING total > 100
ORDER BY rate DESC
""", "optimized circulation v1")

# Optimized v2: use a temp approach with separate counts
bench("""
SELECT doc_type, total, borrowed, ROUND(borrowed/total*100,2) AS rate
FROM (
    SELECT doc_type, COUNT(*) AS total FROM books GROUP BY doc_type
) t1
LEFT JOIN (
    SELECT b.doc_type, COUNT(DISTINCT br.isbn) AS borrowed
    FROM borrow_records br
    JOIN books b ON br.isbn = b.isbn
    WHERE br.is_deleted = 0
    GROUP BY b.doc_type
) t2 ON t1.doc_type = t2.doc_type
WHERE total > 100
ORDER BY rate DESC
""", "optimized circulation v2")

conn.close()

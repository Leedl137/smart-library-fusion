import pymysql, time
conn = pymysql.connect(host='127.0.0.1', port=3306, user='root', password='123456', charset='utf8mb4', read_timeout=300)
c = conn.cursor()
c.execute('USE smart_library_v2')

t0 = time.time()
c.execute("SELECT status, COUNT(*) FROM books GROUP BY status")
print('books by status:', c.fetchall(), f'in {time.time()-t0:.1f}s')

t0 = time.time()
c.execute("SELECT b.title, br.cnt FROM (SELECT isbn, COUNT(*) AS cnt FROM borrow_records WHERE is_deleted=0 AND borrow_time >= '2018-06-01' GROUP BY isbn ORDER BY cnt DESC LIMIT 10) br JOIN books b ON br.isbn=b.isbn")
print('top books v2:', len(c.fetchall()), f'in {time.time()-t0:.1f}s')

conn.close()

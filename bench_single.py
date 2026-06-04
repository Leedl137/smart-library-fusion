import pymysql, time
conn = pymysql.connect(host='127.0.0.1', port=3306, user='root', password='123456', charset='utf8mb4')
c = conn.cursor()
c.execute('USE smart_library_v2')

t0 = time.time()
c.execute("SELECT COUNT(*) FROM books WHERE status='在库'")
print('COUNT 在库:', c.fetchone()[0], f'in {time.time()-t0:.1f}s')

t0 = time.time()
c.execute("SELECT COUNT(DISTINCT isbn) FROM borrow_records WHERE status='borrowed' AND is_deleted=0")
print('COUNT 被借出:', c.fetchone()[0], f'in {time.time()-t0:.1f}s')

conn.close()

import pymysql
conn = pymysql.connect(host='127.0.0.1', port=3306, user='root', password='123456', charset='utf8mb4')
c = conn.cursor()
c.execute('USE smart_library_v2')
c.execute("SELECT status, COUNT(*) FROM books GROUP BY status LIMIT 10")
print('books status:')
for r in c.fetchall():
    print(' ', r)
c.execute("SELECT status, COUNT(*) FROM borrow_records WHERE is_deleted=0 GROUP BY status LIMIT 10")
print('borrow status:')
for r in c.fetchall():
    print(' ', r)
conn.close()

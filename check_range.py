import pymysql
conn = pymysql.connect(host='127.0.0.1', port=3306, user='root', password='123456', charset='utf8mb4', read_timeout=300, write_timeout=300)
c = conn.cursor()
c.execute('USE smart_library_v2')
c.execute('SELECT MIN(visit_time), MAX(visit_time) FROM access_logs')
print('range:', c.fetchone())
c.execute("SELECT COUNT(DISTINCT reader_type) FROM users WHERE reader_type IS NOT NULL AND reader_type != ''")
print('reader_types:', c.fetchone()[0])
conn.close()

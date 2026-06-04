import pymysql, time
conn = pymysql.connect(
    host='127.0.0.1', port=3306, user='root', password='123456',
    charset='utf8mb4', read_timeout=600, write_timeout=600
)
c = conn.cursor()
c.execute('USE smart_library_v2')
c.execute('TRUNCATE TABLE user_hour_stats')
print('Truncated, inserting...')
t0 = time.time()
c.execute('''
    INSERT INTO user_hour_stats (reader_type, hour, access_count)
    SELECT u.reader_type, HOUR(a.visit_time), COUNT(*)
    FROM access_logs a
    JOIN users u ON a.user_id = u.id
    WHERE u.reader_type IS NOT NULL AND u.reader_type != ''
      AND a.visit_time >= '2017-01-01'
    GROUP BY u.reader_type, HOUR(a.visit_time)
''')
conn.commit()
print(f'Inserted in {time.time()-t0:.1f}s')
c.execute('SELECT COUNT(*) FROM user_hour_stats')
print('rows:', c.fetchone()[0])
conn.close()

import pymysql
conn = pymysql.connect(host='127.0.0.1', port=3306, user='root', password='123456')
with conn.cursor() as cur:
    for var in ['innodb_buffer_pool_size', 'innodb_flush_log_at_trx_commit']:
        cur.execute("SHOW VARIABLES LIKE '%s'" % var)
        print(cur.fetchone())
conn.close()

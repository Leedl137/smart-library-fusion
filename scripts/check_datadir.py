import pymysql
conn = pymysql.connect(host='127.0.0.1', port=3306, user='root', password='123456')
with conn.cursor() as cur:
    cur.execute("SHOW VARIABLES LIKE 'datadir'")
    print(cur.fetchone())
conn.close()

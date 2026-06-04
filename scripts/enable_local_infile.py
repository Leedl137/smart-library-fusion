import pymysql
conn = pymysql.connect(host='127.0.0.1', port=3306, user='root', password='123456', database='smart_library_v2')
with conn.cursor() as cur:
    cur.execute("SET GLOBAL local_infile = 1")
    cur.execute("SHOW VARIABLES LIKE 'local_infile'")
    print(cur.fetchone())
conn.close()

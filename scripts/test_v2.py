import pymysql
conn = pymysql.connect(host='127.0.0.1', port=3306, user='root', password='123456', database='smart_library_v2', connect_timeout=5)
with conn.cursor() as cur:
    cur.execute('SELECT COUNT(*) FROM books')
    print('books:', cur.fetchone()[0])
    cur.execute('SELECT COUNT(*) FROM users')
    print('users:', cur.fetchone()[0])
    cur.execute("INSERT INTO books (isbn, barcode, title, authors, publisher, category_code, location, status) VALUES ('TEST123', 'TEST123', 'Test', 'Author', 'Pub', 'A', '3F', 'onshelf') ON DUPLICATE KEY UPDATE title='Test'")
    conn.commit()
    print('Insert test: OK')
    cur.execute('SELECT COUNT(*) FROM books')
    print('books after insert:', cur.fetchone()[0])
conn.close()

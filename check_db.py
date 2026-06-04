import pymysql
conn = pymysql.connect(host='127.0.0.1', port=3306, user='root', password='123456', charset='utf8mb4')
c = conn.cursor()
c.execute("USE smart_library_v2")

# Check users columns
c.execute("DESCRIBE users")
users_cols = [row[0] for row in c.fetchall()]
print('USERS_COLS:', ','.join(users_cols))

has_access = 'access_count' in users_cols
has_borrow = 'borrow_count' in users_cols
print('HAS_ACCESS_COUNT:', has_access)
print('HAS_BORROW_COUNT:', has_borrow)

c.execute("SHOW TABLES LIKE 'user_hour_stats'")
has_hour = c.fetchone() is not None
print('HAS_USER_HOUR_STATS:', has_hour)
if has_hour:
    c.execute("SELECT COUNT(*) FROM user_hour_stats")
    print('HOUR_STATS_ROWS:', c.fetchone()[0])

c.execute("SELECT COUNT(*) FROM users")
print('USERS:', c.fetchone()[0])
c.execute("SELECT COUNT(*) FROM books")
print('BOOKS:', c.fetchone()[0])
c.execute("SELECT COUNT(*) FROM borrow_records")
print('BORROWS:', c.fetchone()[0])
c.execute("SELECT COUNT(*) FROM access_logs")
print('ACCESS:', c.fetchone()[0])
c.execute("SELECT COUNT(*) FROM seat_logs")
print('SEATS:', c.fetchone()[0])

conn.close()

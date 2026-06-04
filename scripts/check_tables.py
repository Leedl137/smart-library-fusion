import pymysql
conn = pymysql.connect(host='127.0.0.1', port=3306, user='root', password='123456', database='smart_library_v2', charset='utf8mb4')
cursor = conn.cursor()
cursor.execute("SHOW TABLES")
tables = [t[0] for t in cursor.fetchall()]

chinese_names = ['读者', '图书', '借阅记录', '门禁日志', '座位日志', '阅览室']
english_names = ['users', 'books', 'borrow_records', 'access_logs', 'seat_logs', 'reading_rooms']

print("Chinese-named tables/views:", [t for t in tables if t in chinese_names])
print("English tables:", [t for t in tables if t in english_names])

# Show create for any Chinese ones
for cn in chinese_names:
    if cn in tables:
        cursor.execute(f"SHOW CREATE TABLE `{cn}`")
        row = cursor.fetchone()
        print(f"\n{cn}: {row[1][:200]}...")

conn.close()

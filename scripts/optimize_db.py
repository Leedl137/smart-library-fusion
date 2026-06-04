"""
Create pre-computed summary tables to speed up dashboard queries.
"""
import pymysql
import time

conn = pymysql.connect(
    host='127.0.0.1', port=3306, user='root', password='123456',
    database='smart_library_v2', charset='utf8mb4', autocommit=True
)

def run(sql, label):
    t0 = time.time()
    with conn.cursor() as c:
        c.execute(sql)
    t1 = time.time()
    print(f"  {label}: {t1-t0:.2f}s")

print("=== Step 1: Add access_count & borrow_count to users ===")
with conn.cursor() as c:
    try:
        c.execute("ALTER TABLE users ADD COLUMN access_count INT DEFAULT 0")
        print("  Added access_count")
    except Exception as e:
        print(f"  access_count already exists: {e}")
    try:
        c.execute("ALTER TABLE users ADD COLUMN borrow_count INT DEFAULT 0")
        print("  Added borrow_count")
    except Exception as e:
        print(f"  borrow_count already exists: {e}")

print("\n=== Step 2: Update access_count ===")
run("""
UPDATE users u
JOIN (SELECT user_id, COUNT(*) AS cnt FROM access_logs GROUP BY user_id) ac
  ON u.id = ac.user_id
SET u.access_count = ac.cnt
""", "Update access_count")

print("\n=== Step 3: Update borrow_count ===")
run("""
UPDATE users u
JOIN (SELECT user_id, COUNT(*) AS cnt FROM borrow_records WHERE is_deleted = 0 GROUP BY user_id) bc
  ON u.id = bc.user_id
SET u.borrow_count = bc.cnt
""", "Update borrow_count")

print("\n=== Step 4: Create user_hour_stats table ===")
with conn.cursor() as c:
    c.execute("DROP TABLE IF EXISTS user_hour_stats")
    c.execute("""
        CREATE TABLE user_hour_stats (
            reader_type VARCHAR(50) NOT NULL,
            hour INT NOT NULL,
            access_count INT DEFAULT 0,
            PRIMARY KEY (reader_type, hour)
        )
    """)

run("""
INSERT INTO user_hour_stats (reader_type, hour, access_count)
SELECT u.reader_type, HOUR(g.visit_time) AS hr, COUNT(*) AS cnt
FROM access_logs g
JOIN users u ON g.user_id = u.id
WHERE u.reader_type IS NOT NULL AND u.reader_type != ''
GROUP BY u.reader_type, HOUR(g.visit_time)
""", "Populate user_hour_stats")

print("\n=== Step 5: Create indexes ===")
with conn.cursor() as c:
    c.execute("CREATE INDEX idx_users_access ON users(access_count)")
    c.execute("CREATE INDEX idx_users_borrow ON users(borrow_count)")
    print("  Created indexes")

print("\n=== Done ===")
conn.close()

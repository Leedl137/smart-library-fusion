import pymysql

conn = pymysql.connect(host='127.0.0.1', port=3306, user='root', password='123456', database='smart_library_v2')

print("[VERIFY] Table counts:")
with conn.cursor() as cur:
    for t in ['categories', 'users', 'books', 'book_inventory', 'borrow_records', 'access_logs', 'seat_logs']:
        cur.execute(f'SELECT COUNT(*) FROM {t}')
        print(f"  {t}: {cur.fetchone()[0]}")

print("\n[INDEX] Rebuilding fulltext index on books...")
with conn.cursor() as cur:
    try:
        cur.execute("ALTER TABLE books ADD FULLTEXT KEY ft_title_authors (title, authors)")
        conn.commit()
        print("  Fulltext index added")
    except Exception as e:
        print(f"  Warn: {e}")

print("\n[INDEX] Rebuilding borrow_records indexes...")
with conn.cursor() as cur:
    for idx_sql in [
        "ALTER TABLE borrow_records ADD KEY idx_br_status (status)",
        "ALTER TABLE borrow_records ADD KEY idx_br_return (return_time)",
        "ALTER TABLE borrow_records ADD KEY idx_br_borrow_time (borrow_time)"
    ]:
        try:
            cur.execute(idx_sql)
            conn.commit()
            print(f"  {idx_sql.split('ADD KEY')[1].split('(')[0].strip()}: OK")
        except Exception as e:
            err = str(e)
            if 'Duplicate' in err or 'already exists' in err.lower():
                print(f"  Already exists, skip")
            else:
                print(f"  Error: {e}")

conn.close()
print("\nAll done!")

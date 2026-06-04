import pymysql

DB_CONFIG = {
    'host': '127.0.0.1', 'port': 3306, 'user': 'root',
    'password': '123456', 'database': 'smart_library_v2', 'local_infile': True,
}
conn = pymysql.connect(**DB_CONFIG)
with conn.cursor() as cur:
    # Drop fulltext index on books
    try:
        cur.execute("ALTER TABLE books DROP INDEX ft_title_authors")
        print("Dropped ft_title_authors")
    except Exception as e:
        print(f"ft_title_authors: {e}")
    
    # Truncate tables
    cur.execute("SET FOREIGN_KEY_CHECKS = 0")
    cur.execute("TRUNCATE TABLE book_inventory")
    cur.execute("TRUNCATE TABLE books")
    cur.execute("TRUNCATE TABLE borrow_records")
    cur.execute("SET FOREIGN_KEY_CHECKS = 1")
    print("Truncated books, inventory, borrow_records")
    
    # Drop borrow_records secondary indexes that are NOT used by FK
    # fk_br_user uses idx_br_user, fk_br_book uses idx_br_isbn -> keep these
    for idx in ['idx_br_status', 'idx_br_return', 'idx_br_borrow_time']:
        try:
            cur.execute(f"ALTER TABLE borrow_records DROP INDEX {idx}")
            print(f"Dropped {idx}")
        except Exception as e:
            print(f"{idx}: {e}")
    
conn.commit()
conn.close()
print("Prep done")

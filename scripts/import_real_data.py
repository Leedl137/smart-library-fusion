#!/usr/bin/env python
# coding: utf-8
import os
import re
import pandas as pd
import pymysql
from pathlib import Path

RAW_ROOT = Path(r"C:\Users\think\Desktop\软著\raw_data\图书馆原始数据")
DB_CONFIG = {
    "host": os.getenv("DB_HOST", "127.0.0.1"),
    "port": int(os.getenv("DB_PORT", "3306")),
    "user": os.getenv("DB_USER", "root"),
    "password": os.getenv("DB_PASSWORD", "123456"),
    "database": os.getenv("DB_NAME", "smart_library_v2"),
    "charset": "utf8mb4",
    "autocommit": True,
}

def get_conn():
    return pymysql.connect(**DB_CONFIG)

def batch_insert(conn, sql, rows, batch_size=5000):
    total = 0
    batch = []
    with conn.cursor() as cursor:
        for row in rows:
            batch.append(row)
            if len(batch) >= batch_size:
                cursor.executemany(sql, batch)
                total += len(batch)
                batch.clear()
                print(f"  ... inserted {total}")
        if batch:
            cursor.executemany(sql, batch)
            total += len(batch)
    return total

def import_categories(conn):
    print("[1/6] import categories...")
    cats = [
        ("A", "A-Marxism", 1), ("B", "B-Philosophy", 1), ("C", "C-SocialSci", 1),
        ("D", "D-PoliticsLaw", 1), ("E", "E-Military", 1), ("F", "F-Economy", 1),
        ("G", "G-CultureEdu", 1), ("H", "H-Language", 1), ("I", "I-Literature", 1),
        ("J", "J-Art", 1), ("K", "K-HistoryGeo", 1), ("N", "N-NaturalSci", 1),
        ("O", "O-MathChem", 1), ("P", "P-AstroEarth", 1), ("Q", "Q-Biology", 1),
        ("R", "R-Medicine", 1), ("S", "S-Agriculture", 1), ("T", "T-Industry", 1),
        ("TP", "TP-Computer", 2), ("U", "U-Transport", 1), ("V", "V-Aerospace", 1),
        ("X", "X-Environment", 1), ("Z", "Z-General", 1),
    ]
    sql = "INSERT IGNORE INTO categories(code, name, level) VALUES (%s, %s, %s)"
    batch_insert(conn, sql, cats)
    print("  done")

def import_readers(conn, limit=None):
    print("[2/6] import readers...")
    path = RAW_ROOT / "借阅数据" / "借阅数据" / "读者数据_guid.csv"
    df_iter = pd.read_csv(path, encoding="gbk", chunksize=20000)
    sql = "INSERT IGNORE INTO users(uid, real_name, gender, enroll_year, reader_type, department, role, id_type, id_number_enc, phone_enc, user_status, review_status, max_borrow_count, max_borrow_days) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)"
    total = 0
    for df in df_iter:
        if limit and total >= limit:
            break
        rows = []
        for row in df.itertuples(index=False):
            gender = str(row.GENDER).strip() if pd.notna(row.GENDER) else "unknown"
            enroll = None
            if pd.notna(row.ENROLLYEAR):
                m = re.search(r"\d{4}", str(row.ENROLLYEAR))
                if m:
                    enroll = m.group(0)
            rtype = str(row.TYPE).strip() if pd.notna(row.TYPE) else "unknown"
            dept = str(row.DEPARTMENT).strip() if pd.notna(row.DEPARTMENT) else "unknown"
            name = f"reader_{str(row.ID)[:8]}"
            rows.append((str(row.ID), name, gender, enroll, rtype, dept, "student", "idcard", "enc", "enc", "normal", "approved", 5, 30))
        n = batch_insert(conn, sql, rows)
        total += n
        if limit and total >= limit:
            break
    print(f"  done: {total}")

def import_books(conn, limit=None):
    print("[3/6] import books...")
    path = RAW_ROOT / "借阅数据" / "借阅数据" / "图书数据.csv"
    df_iter = pd.read_csv(path, encoding="utf-8", chunksize=20000)
    sql_book = "INSERT IGNORE INTO books(isbn, barcode, title, authors, publisher, publish_year, category_code, call_no, language, doc_type, total_copies, available_copies, location, status) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)"
    sql_inv = "INSERT IGNORE INTO book_inventory(isbn, stock) VALUES (%s, %s)"
    total = 0
    for df in df_iter:
        if limit and total >= limit:
            break
        rows_book = []
        rows_inv = []
        for row in df.itertuples(index=False):
            bid = str(row.ID).strip()
            title = str(row.TITLE)[:255] if pd.notna(row.TITLE) else "unknown"
            author = str(row.AUTHOR)[:100] if pd.notna(row.AUTHOR) else None
            publisher = str(row.PUBLISHER)[:100] if pd.notna(row.PUBLISHER) else None
            year = None
            if pd.notna(row.YEAR):
                m = re.search(r"\d{4}", str(row.YEAR))
                if m:
                    year = int(m.group(0))
            callno = str(row.CALLNO)[:100] if pd.notna(row.CALLNO) else None
            lang = str(row.LANGUAGE)[:20] if pd.notna(row.LANGUAGE) else "Chinese"
            doctype = str(row.DOCTYPE)[:50] if pd.notna(row.DOCTYPE) else "Book"
            cat_code = "TP" if "computer" in title.lower() or "program" in title.lower() else "Z"
            if callno and len(callno) > 0:
                cat_code = callno[0].upper() if callno[0].upper() in "ABCDEFGHIJKLMNOPQRSTUVWXYZ" else "Z"
            rows_book.append((bid, bid, title, author, publisher, year, cat_code, callno, lang, doctype, 1, 1, "3F-A-01-A", "onshelf"))
            rows_inv.append((bid, 1))
        n = batch_insert(conn, sql_book, rows_book)
        batch_insert(conn, sql_inv, rows_inv)
        total += n
        if limit and total >= limit:
            break
    print(f"  done: {total}")

def import_borrows(conn, limit=None):
    print("[4/6] import borrow records...")
    path = RAW_ROOT / "借阅数据" / "借阅数据" / "借阅数据_guid.csv"
    df_iter = pd.read_csv(path, encoding="gbk", chunksize=50000)
    sql = "INSERT IGNORE INTO borrow_records(borrow_id, user_id, isbn, borrow_time, due_time, return_time, status, overdue_days, renew_count) VALUES (%s, (SELECT id FROM users WHERE uid = %s LIMIT 1), %s, %s, DATE_ADD(%s, INTERVAL 30 DAY), %s, %s, %s, %s)"
    total = 0
    for df in df_iter:
        if limit and total >= limit:
            break
        rows = []
        for row in df.itertuples(index=False):
            lend = str(row.LENDDATE).strip() if pd.notna(row.LENDDATE) else None
            ret = str(row.RETURNDATE).strip() if pd.notna(row.RETURNDATE) else None
            if not lend:
                continue
            renew = int(row.RENEWCOUNTS) if pd.notna(row.RENEWCOUNTS) else 0
            bid = f"B{row.NO}"
            status = "returned" if ret else "borrowed"
            rows.append((bid, str(row.READERID), str(row.BOOKID), lend, lend, ret, status, 0, renew))
        n = batch_insert(conn, sql, rows)
        total += n
        if limit and total >= limit:
            break
    print(f"  done: {total}")

def import_access_logs(conn, limit=50000):
    print("[5/6] import access logs (sample)...")
    folder = RAW_ROOT / "门禁数据"
    files = sorted(folder.glob("20*.txt"))
    sql = "INSERT IGNORE INTO access_logs(user_id, visit_time, location, access_type) VALUES ((SELECT id FROM users WHERE uid = %s LIMIT 1), %s, %s, %s)"
    total = 0
    for path in files[:2]:
        if limit and total >= limit:
            break
        df = pd.read_csv(path, sep="\t", encoding="utf-8", nrows=(limit - total) if limit else None)
        rows = []
        for row in df.itertuples(index=False):
            vt = str(row.VisitTime).strip() if hasattr(row, "VisitTime") and pd.notna(row.VisitTime) else None
            loc = str(row.Location)[:20] if hasattr(row, "Location") and pd.notna(row.Location) else "main_gate"
            uid = str(row.ID).strip() if hasattr(row, "ID") and pd.notna(row.ID) else None
            if not uid or not vt:
                continue
            rows.append((uid, vt, loc, "in"))
        n = batch_insert(conn, sql, rows)
        total += n
    print(f"  done: {total}")

def import_seat_logs(conn, limit=50000):
    print("[6/6] import seat logs (sample)...")
    room_path = RAW_ROOT / "座位系统数据" / "ReadingRoom.txt"
    try:
        df_room = pd.read_csv(room_path, sep="\t", encoding="utf-8")
        sql_room = "INSERT IGNORE INTO reading_rooms(room_no, room_name) VALUES (%s, %s)"
        rows_room = [(str(r.ReadingRoomNo), str(r.ReadingRoomName)) for r in df_room.itertuples(index=False) if hasattr(r, "ReadingRoomNo") and hasattr(r, "ReadingRoomName")]
        batch_insert(conn, sql_room, rows_room)
        print(f"  rooms done: {len(rows_room)}")
    except Exception as e:
        print(f"  rooms skip: {e}")

    folder = RAW_ROOT / "座位系统数据"
    files = sorted(folder.glob("20*.txt"))
    sql = "INSERT IGNORE INTO seat_logs(user_id, room_no, seat_no, start_time, end_time) VALUES ((SELECT id FROM users WHERE uid = %s LIMIT 1), %s, %s, %s, %s)"
    total = 0
    for path in files[:2]:
        if limit and total >= limit:
            break
        try:
            df = pd.read_csv(path, sep="\t", encoding="gbk", nrows=(limit - total) if limit else None)
        except:
            df = pd.read_csv(path, sep="\t", encoding="utf-8", nrows=(limit - total) if limit else None)
        rows = []
        for row in df.itertuples(index=False):
            uid = str(row.ID).strip() if hasattr(row, "ID") and pd.notna(row.ID) else None
            room = str(row.ReadingRoomNo).strip() if hasattr(row, "ReadingRoomNo") and pd.notna(row.ReadingRoomNo) else None
            seat = str(row.SeatNo).strip() if hasattr(row, "SeatNo") and pd.notna(row.SeatNo) else None
            st = str(row.SelectSeatTime).strip() if hasattr(row, "SelectSeatTime") and pd.notna(row.SelectSeatTime) else None
            et = str(row.LeaveSeatTime).strip() if hasattr(row, "LeaveSeatTime") and pd.notna(row.LeaveSeatTime) else None
            if not uid or not room or not seat or not st:
                continue
            rows.append((uid, room, seat, st, et))
        n = batch_insert(conn, sql, rows)
        total += n
    print(f"  done: {total}")

def main():
    print("========================================")
    print("  Real Library Data Import")
    print("========================================")
    conn = get_conn()
    try:
        import_categories(conn)
        import_readers(conn)
        import_books(conn)
        import_borrows(conn)
        import_access_logs(conn)
        import_seat_logs(conn)
        print("\nAll done!")
    except Exception as e:
        import traceback
        traceback.print_exc()
    finally:
        conn.close()

if __name__ == "__main__":
    main()

#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
智慧校园图书借阅信息管理系统 V2.0 —— 真实数据 ETL 导入脚本
功能: 将 raw_data/ 下的真实高校图书馆数据清洗、转换后导入 MySQL

用法示例:
    python etl_import_realdata.py --host localhost --port 3306 --user root --password xxx --database smart_library_v2
"""

import argparse
import csv
import datetime
import hashlib
import logging
import os
import re
import sys
import time
from collections import defaultdict
from pathlib import Path

import pymysql

# ---------- 路径配置 ----------
BASE_DIR = Path(__file__).resolve().parent.parent
RAW_DIR = BASE_DIR.parent / "raw_data" / "图书馆原始数据"
TMP_DIR = BASE_DIR / "scripts" / "tmp_csv"
TMP_DIR.mkdir(parents=True, exist_ok=True)

FILE_PATHS = {
    "readers": RAW_DIR / "借阅数据" / "借阅数据" / "读者数据_guid.csv",
    "books": RAW_DIR / "借阅数据" / "借阅数据" / "图书数据.csv",
    "borrows": RAW_DIR / "借阅数据" / "借阅数据" / "借阅数据_guid.csv",
    "reading_rooms": RAW_DIR / "座位系统数据" / "ReadingRoom.txt",
    "seat_students": RAW_DIR / "座位系统数据" / "Student.txt",
    "gate_students": RAW_DIR / "门禁数据" / "Student.txt",
    "articles_cn": RAW_DIR / "学者库数据" / "ArticleCn.xlsx",
    "articles_en": RAW_DIR / "学者库数据" / "ArticleEn.xls",
}

SEAT_LOGS_DIR = RAW_DIR / "座位系统数据"
GATE_LOGS_DIR = RAW_DIR / "门禁数据"

# ---------- 日志 ----------
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
)
logger = logging.getLogger("ETL")

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

# ---------- 中图法大类映射 ----------
CATEGORY_MAP = {
    "A": "马克思主义",
    "B": "哲学",
    "C": "社会科学总论",
    "D": "政治法律",
    "E": "军事",
    "F": "经济",
    "G": "文化教育体育",
    "H": "语言文字",
    "I": "文学",
    "J": "艺术",
    "K": "历史地理",
    "N": "自然科学总论",
    "O": "数理科学",
    "P": "天文地球",
    "Q": "生物",
    "R": "医药",
    "S": "农业",
    "T": "工业技术",
    "U": "交通",
    "V": "航空航天",
    "X": "环境",
    "Z": "综合性图书",
}

# ---------- 命令行参数 ----------
def parse_args():
    parser = argparse.ArgumentParser(description="智慧校园图书系统 V2 ETL 导入脚本")
    parser.add_argument("--host", default="localhost", help="MySQL 主机地址")
    parser.add_argument("--port", type=int, default=3306, help="MySQL 端口")
    parser.add_argument("--user", default="root", help="MySQL 用户名")
    parser.add_argument("--password", default="", help="MySQL 密码")
    parser.add_argument("--database", default="smart_library_v2", help="目标数据库名")
    return parser.parse_args()


# ---------- MySQL 连接 ----------
def get_connection(args):
    conn = pymysql.connect(
        host=args.host,
        port=args.port,
        user=args.user,
        password=args.password,
        database=args.database,
        charset="utf8mb4",
        local_infile=True,
        autocommit=False,
    )
    return conn


# ---------- 辅助函数 ----------
def timed_step(step_name):
    """装饰器：记录步骤耗时"""
    def decorator(func):
        def wrapper(*args, **kwargs):
            logger.info(f"【开始】{step_name}")
            t0 = time.time()
            result = func(*args, **kwargs)
            elapsed = time.time() - t0
            logger.info(f"【完成】{step_name}，耗时 {elapsed:.2f}s")
            return result
        return wrapper
    return decorator


def safe_str(val, default="", max_len=None):
    """安全字符串处理"""
    if val is None:
        return default
    s = str(val).strip()
    if s in ("", "NULL", "None"):
        return default
    if max_len and len(s) > max_len:
        s = s[:max_len]
    return s


def safe_int(val, default=None):
    """安全整数转换"""
    try:
        return int(float(val))
    except Exception:
        return default


def parse_datetime(val):
    """解析日期时间字符串"""
    val = safe_str(val)
    if not val:
        return None
    for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%d %H:%M:%S.%f", "%Y-%m-%d", "%Y/%m/%d"):
        try:
            return datetime.datetime.strptime(val, fmt)
        except ValueError:
            continue
    return None


def callno_to_category(call_no):
    """从索书号提取中图法大类"""
    call_no = safe_str(call_no)
    if not call_no:
        return "Z"
    first = call_no[0].upper()
    return first if first in CATEGORY_MAP else "Z"


def md5_borrow_id(reader_id, book_id, lend_date):
    """生成借阅记录唯一ID"""
    raw = f"{reader_id}|{book_id}|{lend_date}"
    return hashlib.md5(raw.encode("utf-8")).hexdigest()


# ---------- 建表/清理 ----------
def ensure_articles_table(cursor):
    """确保 articles 表存在（schema.sql 中未包含）"""
    sql = """
    CREATE TABLE IF NOT EXISTS articles (
        article_id INT AUTO_INCREMENT PRIMARY KEY COMMENT '文章自增ID',
        article_type VARCHAR(50) NULL COMMENT '文献类型',
        title VARCHAR(500) NOT NULL COMMENT '文章标题',
        authors VARCHAR(500) NULL COMMENT '作者',
        author_affiliation VARCHAR(1000) NULL COMMENT '作者单位',
        journal_name VARCHAR(200) NULL COMMENT '期刊名称',
        issn VARCHAR(20) NULL COMMENT '期刊刊号',
        publish_date VARCHAR(20) NULL COMMENT '发表时间',
        created_at DATETIME DEFAULT CURRENT_TIMESTAMP
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='学者库文章数据';
    """
    cursor.execute(sql)
    logger.info("articles 表已确认存在")


def truncate_tables(cursor):
    """清空所有目标表（保留结构），按依赖顺序"""
    tables = [
        "borrow_records",
        "book_inventory",
        "access_logs",
        "seat_logs",
        "articles",
        "users",
        "books",
        "reading_rooms",
        "categories",
    ]
    cursor.execute("SET FOREIGN_KEY_CHECKS = 0")
    for tbl in tables:
        cursor.execute(f"TRUNCATE TABLE {tbl}")
        logger.info(f"  已清空表: {tbl}")
    cursor.execute("SET FOREIGN_KEY_CHECKS = 1")
    logger.info("所有目标表已 TRUNCATE")


# ---------- 小表导入：executemany ----------
@timed_step("导入 categories（中图法分类）")
def import_categories(cursor):
    rows = []
    for code, name in CATEGORY_MAP.items():
        rows.append((code, name, 1, None))
    sql = "INSERT INTO categories (code, name, level, parent_code) VALUES (%s, %s, %s, %s)"
    cursor.executemany(sql, rows)
    logger.info(f"  导入 {len(rows)} 条分类记录")
    return len(rows)


@timed_step("导入 reading_rooms")
def import_reading_rooms(cursor):
    path = FILE_PATHS["reading_rooms"]
    rows = []
    seen = set()
    with open(path, "r", encoding="utf-8", errors="replace") as f:
        next(f)  # skip header
        for line in f:
            line = line.strip()
            if not line:
                continue
            parts = line.split("\t")
            if len(parts) < 2:
                continue
            room_no = safe_str(parts[0], max_len=20)
            room_name = safe_str(parts[1], max_len=100)
            if room_no in seen:
                continue
            seen.add(room_no)
            rows.append((room_no, room_name, "总馆", 100, "open"))
    sql = "INSERT INTO reading_rooms (room_no, room_name, location, capacity, status) VALUES (%s, %s, %s, %s, %s)"
    cursor.executemany(sql, rows)
    logger.info(f"  导入 {len(rows)} 条阅览室记录")
    return len(rows)


@timed_step("导入 users（合并3个来源读者数据并去重）")
def import_users(cursor, conn):
    """
    合并借阅读者、座位学生、门禁学生，去重后导入 users 表。
    返回: (reader_guid -> uid 映射, uid -> user_id 映射)
    """
    users_raw = {}  # guid -> dict

    # 1) 借阅读者
    logger.info("  读取借阅读者数据 ...")
    with open(FILE_PATHS["readers"], "r", encoding="gb2312", errors="replace") as f:
        reader = csv.reader(f)
        next(reader)
        for row in reader:
            if len(row) < 6:
                continue
            guid = safe_str(row[1])
            if not guid or guid in users_raw:
                continue
            users_raw[guid] = {
                "gender": safe_str(row[2]),
                "enroll_year": safe_str(row[3]),
                "reader_type": safe_str(row[4], "本科生"),
                "department": safe_str(row[5], "未知院系"),
            }
    logger.info(f"  借阅读者: {len(users_raw)} 条")

    # 2) 座位学生
    logger.info("  读取座位学生数据 ...")
    with open(FILE_PATHS["seat_students"], "r", encoding="utf-8", errors="replace") as f:
        next(f)
        for line in f:
            line = line.strip()
            if not line:
                continue
            parts = line.split("\t")
            if len(parts) < 5:
                continue
            guid = safe_str(parts[0])
            if not guid or guid in users_raw:
                continue
            users_raw[guid] = {
                "gender": safe_str(parts[1]),
                "enroll_year": safe_str(parts[3]),
                "reader_type": safe_str(parts[2], "本科生"),
                "department": safe_str(parts[4], "未知院系"),
            }
    logger.info(f"  合并座位学生后: {len(users_raw)} 条")

    # 3) 门禁学生
    logger.info("  读取门禁学生数据 ...")
    with open(FILE_PATHS["gate_students"], "r", encoding="utf-8", errors="replace") as f:
        next(f)
        for line in f:
            line = line.strip()
            if not line:
                continue
            parts = line.split("\t")
            if len(parts) < 5:
                continue
            guid = safe_str(parts[0])
            if not guid or guid in users_raw:
                continue
            users_raw[guid] = {
                "gender": safe_str(parts[2]),
                "enroll_year": safe_str(parts[4]),
                "reader_type": safe_str(parts[3], "本科生"),
                "department": safe_str(parts[1], "未知院系"),
            }
    logger.info(f"  合并门禁学生后: {len(users_raw)} 条")

    # 生成 uid
    year_counter = defaultdict(int)
    guid_to_uid = {}
    for guid, info in users_raw.items():
        year = info["enroll_year"] if info["enroll_year"] else "0000"
        year_counter[year] += 1
        seq = year_counter[year]
        uid = f"U{year}{seq:05d}"
        guid_to_uid[guid] = uid

    # 批量插入 users（每批 5000）
    batch = []
    total = 0
    sql = """
        INSERT INTO users (
            uid, real_name, gender, enroll_year, department, role, reader_type,
            id_number_enc, phone_enc, password_hash, access_count, borrow_count
        ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
    """
    for guid, info in users_raw.items():
        uid = guid_to_uid[guid]
        batch.append((
            uid,
            f"读者{uid}",
            info["gender"] if info["gender"] else None,
            info["enroll_year"] if info["enroll_year"] else None,
            info["department"],
            "student",
            info["reader_type"],
            "ENCRYPTED",
            "ENCRYPTED",
            "PLACEHOLDER",
            0,
            0,
        ))
        if len(batch) >= 5000:
            cursor.executemany(sql, batch)
            total += len(batch)
            batch = []
    if batch:
        cursor.executemany(sql, batch)
        total += len(batch)
    conn.commit()
    logger.info(f"  已插入 users: {total} 条")

    # 建立 uid -> user_id 映射
    cursor.execute("SELECT id, uid FROM users ORDER BY id")
    uid_to_id = {uid: uid_id for uid_id, uid in cursor.fetchall()}
    logger.info(f"  已建立 uid->user_id 映射: {len(uid_to_id)} 条")
    return guid_to_uid, uid_to_id


@timed_step("导入 books + book_inventory")
def import_books(cursor, conn):
    """导入图书数据，返回 book_guid -> isbn 映射"""
    path = FILE_PATHS["books"]
    book_guid_to_isbn = {}
    seen_isbn = set()
    seen_barcode = set()
    barcode_dup_counter = {}
    batch_books = []
    batch_inv = []
    total = 0

    sql_book = """
        INSERT INTO books (
            isbn, barcode, title, authors, publisher, publish_year,
            category_code, call_no, language, doc_type,
            total_copies, available_copies, location, status
        ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
    """
    sql_inv = "INSERT INTO book_inventory (isbn, stock) VALUES (%s, %s)"

    with open(path, "r", encoding="utf-8-sig", errors="replace") as f:
        reader = csv.reader(f)
        next(reader)
        for row in reader:
            if len(row) < 9:
                continue
            isbn = safe_str(row[1])
            if not isbn or isbn in seen_isbn:
                continue
            seen_isbn.add(isbn)
            book_guid_to_isbn[isbn] = isbn

            title = safe_str(row[2], "未知书名", 255)
            authors = safe_str(row[3], "未知作者", 500)
            publisher = safe_str(row[4], "未知出版社", 255)
            publish_year = safe_int(row[5])
            call_no = safe_str(row[6], "", 100)
            category_code = callno_to_category(call_no)
            language = safe_str(row[7], "中文", 20)
            doc_type = safe_str(row[8], "普通图书", 50)

            # barcode 去重处理
            barcode = call_no if call_no else isbn
            if barcode in seen_barcode:
                barcode_dup_counter[barcode] = barcode_dup_counter.get(barcode, 1) + 1
                barcode = f"{barcode}_{barcode_dup_counter[barcode]}"
            seen_barcode.add(barcode)

            batch_books.append((
                isbn, barcode, title, authors, publisher, publish_year,
                category_code, call_no, language, doc_type,
                1, 1, "总馆", "在库",
            ))
            batch_inv.append((isbn, 1))

            if len(batch_books) >= 5000:
                cursor.executemany(sql_book, batch_books)
                cursor.executemany(sql_inv, batch_inv)
                total += len(batch_books)
                batch_books = []
                batch_inv = []

    if batch_books:
        cursor.executemany(sql_book, batch_books)
        cursor.executemany(sql_inv, batch_inv)
        total += len(batch_books)

    conn.commit()
    logger.info(f"  已插入 books + book_inventory: {total} 条")
    return book_guid_to_isbn


# ---------- 大表导入：临时 CSV + LOAD DATA INFILE ----------
def write_borrow_csv(reader_to_user, book_to_isbn, csv_path):
    """清洗借阅数据并写入临时 CSV"""
    path = FILE_PATHS["borrows"]
    total = 0
    skipped = 0
    seen_ids = set()

    with open(csv_path, "w", newline="", encoding="utf-8") as outf:
        writer = csv.writer(outf, quoting=csv.QUOTE_MINIMAL)
        writer.writerow([
            "borrow_id", "user_id", "isbn", "borrow_time", "due_time",
            "return_time", "status", "overdue_days", "renew_count",
        ])

        with open(path, "r", encoding="ascii", errors="replace") as inf:
            reader = csv.reader(inf)
            next(reader)
            for row in reader:
                if len(row) < 6:
                    continue
                reader_guid = safe_str(row[1])
                book_guid = safe_str(row[2])
                lend_date_str = safe_str(row[3])
                return_date_str = safe_str(row[4])
                renew_counts = safe_int(row[5], 0)

                user_id = reader_to_user.get(reader_guid)
                isbn = book_to_isbn.get(book_guid)
                if not user_id or not isbn or not lend_date_str:
                    skipped += 1
                    continue

                borrow_id = md5_borrow_id(reader_guid, book_guid, lend_date_str)
                if borrow_id in seen_ids:
                    # 极小概率 MD5 冲突，追加计数重新生成
                    borrow_id = hashlib.md5(
                        f"{borrow_id}|{total}".encode()
                    ).hexdigest()
                seen_ids.add(borrow_id)

                borrow_dt = parse_datetime(lend_date_str)
                if not borrow_dt:
                    skipped += 1
                    continue
                due_dt = borrow_dt + datetime.timedelta(days=30)

                return_dt = parse_datetime(return_date_str) if return_date_str else None
                status = "returned" if return_dt else "borrowed"
                overdue_days = 0
                if return_dt:
                    overdue_days = max(0, (return_dt - due_dt).days)

                writer.writerow([
                    borrow_id,
                    user_id,
                    isbn,
                    borrow_dt.strftime("%Y-%m-%d %H:%M:%S"),
                    due_dt.strftime("%Y-%m-%d %H:%M:%S"),
                    return_dt.strftime("%Y-%m-%d %H:%M:%S") if return_dt else "",
                    status,
                    overdue_days,
                    renew_counts,
                ])
                total += 1
                if total % 200000 == 0:
                    logger.info(f"    已处理 borrow 记录: {total}")

    logger.info(f"  borrow 有效记录: {total}, 跳过: {skipped}")
    return total


@timed_step("导入 borrow_records（LOAD DATA INFILE）")
def import_borrow_records(cursor, conn, reader_to_user, book_to_isbn):
    csv_path = TMP_DIR / "borrow_records.csv"
    total = write_borrow_csv(reader_to_user, book_to_isbn, csv_path)

    sql = f"""
    LOAD DATA LOCAL INFILE '{str(csv_path).replace(chr(92), "/")}'
    INTO TABLE borrow_records
    CHARACTER SET utf8mb4
    FIELDS TERMINATED BY ','
    OPTIONALLY ENCLOSED BY '"'
    LINES TERMINATED BY '\\n'
    IGNORE 1 LINES
    (@borrow_id, @user_id, @isbn, @borrow_time, @due_time, @return_time, @status, @overdue_days, @renew_count)
    SET
        borrow_id = @borrow_id,
        user_id = @user_id,
        isbn = @isbn,
        borrow_time = @borrow_time,
        due_time = @due_time,
        return_time = NULLIF(@return_time, ''),
        status = @status,
        overdue_days = @overdue_days,
        renew_count = @renew_count
    """
    cursor.execute(sql)
    conn.commit()
    logger.info(f"  LOAD DATA 完成: {total} 条")
    return total


def write_seat_csv(reader_to_user, csv_path):
    """清洗座位日志并写入临时 CSV（4 个文件合并）"""
    files = sorted(
        [f for f in os.listdir(SEAT_LOGS_DIR) if f.endswith(".txt") and f[0].isdigit()]
    )
    total = 0
    skipped = 0

    with open(csv_path, "w", newline="", encoding="utf-8") as outf:
        writer = csv.writer(outf, quoting=csv.QUOTE_MINIMAL)
        writer.writerow(["user_id", "room_no", "seat_no", "start_time", "end_time"])

        for fname in files:
            fpath = os.path.join(SEAT_LOGS_DIR, fname)
            logger.info(f"    处理座位日志文件: {fname}")
            with open(fpath, "r", encoding="utf-8", errors="replace") as inf:
                next(inf)
                for line in inf:
                    line = line.strip()
                    if not line:
                        continue
                    parts = line.split("\t")
                    if len(parts) < 5:
                        continue
                    guid = safe_str(parts[0])
                    room_no = safe_str(parts[1])
                    seat_no = safe_str(parts[2])
                    start_str = safe_str(parts[3])
                    end_str = safe_str(parts[4])

                    user_id = reader_to_user.get(guid)
                    if not user_id or not room_no or not start_str:
                        skipped += 1
                        continue

                    start_dt = parse_datetime(start_str)
                    end_dt = parse_datetime(end_str) if end_str else None
                    if not start_dt:
                        skipped += 1
                        continue

                    writer.writerow([
                        user_id,
                        room_no,
                        seat_no,
                        start_dt.strftime("%Y-%m-%d %H:%M:%S"),
                        end_dt.strftime("%Y-%m-%d %H:%M:%S") if end_dt else "",
                    ])
                    total += 1
                    if total % 500000 == 0:
                        logger.info(f"    累计处理 seat 记录: {total}")

    logger.info(f"  seat 有效记录: {total}, 跳过: {skipped}")
    return total


@timed_step("导入 seat_logs（LOAD DATA INFILE）")
def import_seat_logs(cursor, conn, reader_to_user):
    csv_path = TMP_DIR / "seat_logs.csv"
    total = write_seat_csv(reader_to_user, csv_path)

    sql = f"""
    LOAD DATA LOCAL INFILE '{str(csv_path).replace(chr(92), "/")}'
    INTO TABLE seat_logs
    CHARACTER SET utf8mb4
    FIELDS TERMINATED BY ','
    OPTIONALLY ENCLOSED BY '"'
    LINES TERMINATED BY '\\n'
    IGNORE 1 LINES
    (@user_id, @room_no, @seat_no, @start_time, @end_time)
    SET
        user_id = @user_id,
        room_no = @room_no,
        seat_no = @seat_no,
        start_time = @start_time,
        end_time = NULLIF(@end_time, '')
    """
    cursor.execute(sql)
    conn.commit()
    logger.info(f"  LOAD DATA 完成: {total} 条")
    return total


def write_access_csv(reader_to_user, csv_path):
    """清洗门禁日志并写入临时 CSV（4 个文件合并）"""
    files = sorted(
        [f for f in os.listdir(GATE_LOGS_DIR) if f.endswith(".txt") and f[0].isdigit()]
    )
    total = 0
    skipped = 0

    with open(csv_path, "w", newline="", encoding="utf-8") as outf:
        writer = csv.writer(outf, quoting=csv.QUOTE_MINIMAL)
        writer.writerow(["user_id", "visit_time", "location", "access_type"])

        for fname in files:
            fpath = os.path.join(GATE_LOGS_DIR, fname)
            logger.info(f"    处理门禁日志文件: {fname}")
            with open(fpath, "r", encoding="utf-8", errors="replace") as inf:
                next(inf)
                for line in inf:
                    line = line.strip()
                    if not line:
                        continue
                    parts = line.split("\t")
                    if len(parts) < 3:
                        continue
                    guid = safe_str(parts[0])
                    visit_str = safe_str(parts[1])
                    location = safe_str(parts[2])

                    user_id = reader_to_user.get(guid)
                    if not user_id or not visit_str:
                        skipped += 1
                        continue

                    visit_dt = parse_datetime(visit_str)
                    if not visit_dt:
                        skipped += 1
                        continue

                    writer.writerow([
                        user_id,
                        visit_dt.strftime("%Y-%m-%d %H:%M:%S"),
                        location,
                        "in",
                    ])
                    total += 1
                    if total % 1000000 == 0:
                        logger.info(f"    累计处理 access 记录: {total}")

    logger.info(f"  access 有效记录: {total}, 跳过: {skipped}")
    return total


@timed_step("导入 access_logs（LOAD DATA INFILE）")
def import_access_logs(cursor, conn, reader_to_user):
    csv_path = TMP_DIR / "access_logs.csv"
    total = write_access_csv(reader_to_user, csv_path)

    sql = f"""
    LOAD DATA LOCAL INFILE '{str(csv_path).replace(chr(92), "/")}'
    INTO TABLE access_logs
    CHARACTER SET utf8mb4
    FIELDS TERMINATED BY ','
    OPTIONALLY ENCLOSED BY '"'
    LINES TERMINATED BY '\\n'
    IGNORE 1 LINES
    (@user_id, @visit_time, @location, @access_type)
    SET
        user_id = @user_id,
        visit_time = @visit_time,
        location = @location,
        access_type = @access_type
    """
    cursor.execute(sql)
    conn.commit()
    logger.info(f"  LOAD DATA 完成: {total} 条")
    return total


# ---------- articles（pandas -> CSV -> LOAD DATA） ----------
def write_articles_csv(csv_path):
    """读取学者库 Excel 并写入临时 CSV"""
    try:
        import pandas as pd
    except ImportError as e:
        logger.error("缺少 pandas 库，无法导入学者库数据。请执行: pip install pandas openpyxl xlrd")
        raise

    total = 0

    with open(csv_path, "w", newline="", encoding="utf-8") as outf:
        writer = csv.writer(outf, quoting=csv.QUOTE_MINIMAL)
        writer.writerow([
            "article_type", "title", "authors", "author_affiliation",
            "journal_name", "issn", "publish_date",
        ])

        for label, path in [("中文", FILE_PATHS["articles_cn"]), ("英文", FILE_PATHS["articles_en"])]:
            logger.info(f"    读取学者库 {label}: {path}")
            if not path.exists():
                logger.warning(f"    文件不存在，跳过: {path}")
                continue
            df = pd.read_excel(path, engine=None)
            for _, row in df.iterrows():
                article_type = safe_str(row.get("论文分类"), "", 50)
                title = safe_str(row.get("论文题名"), "未知标题", 500)
                authors = safe_str(row.get("作者"), "", 500)
                affil = safe_str(row.get("作者单位"), "", 1000)
                journal = safe_str(row.get("期刊名称"), "", 200)
                issn = safe_str(row.get("期刊代码"), "", 20)
                pub_date = safe_str(row.get("发表日期"), "", 20)

                writer.writerow([article_type, title, authors, affil, journal, issn, pub_date])
                total += 1
                if total % 20000 == 0:
                    logger.info(f"    累计处理 articles: {total}")

    logger.info(f"  articles 有效记录: {total}")
    return total


@timed_step("导入 articles（LOAD DATA INFILE）")
def import_articles(cursor, conn):
    csv_path = TMP_DIR / "articles.csv"
    total = write_articles_csv(csv_path)

    sql = f"""
    LOAD DATA LOCAL INFILE '{str(csv_path).replace(chr(92), "/")}'
    INTO TABLE articles
    CHARACTER SET utf8mb4
    FIELDS TERMINATED BY ','
    OPTIONALLY ENCLOSED BY '"'
    LINES TERMINATED BY '\\n'
    IGNORE 1 LINES
    (@article_type, @title, @authors, @author_affiliation, @journal_name, @issn, @publish_date)
    SET
        article_type = @article_type,
        title = @title,
        authors = @authors,
        author_affiliation = @author_affiliation,
        journal_name = @journal_name,
        issn = @issn,
        publish_date = @publish_date
    """
    cursor.execute(sql)
    conn.commit()
    logger.info(f"  LOAD DATA 完成: {total} 条")
    return total


# ---------- 统计更新 ----------
def update_user_counts(cursor, conn):
    """更新 users 的 access_count 和 borrow_count（可选）"""
    logger.info("【开始】更新用户统计计数")
    t0 = time.time()

    # borrow_count
    cursor.execute("""
        UPDATE users u
        JOIN (
            SELECT user_id, COUNT(*) AS cnt FROM borrow_records GROUP BY user_id
        ) b ON u.id = b.user_id
        SET u.borrow_count = b.cnt
    """)
    logger.info(f"  更新 borrow_count: {cursor.rowcount} 条")

    # access_count
    cursor.execute("""
        UPDATE users u
        JOIN (
            SELECT user_id, COUNT(*) AS cnt FROM access_logs GROUP BY user_id
        ) a ON u.id = a.user_id
        SET u.access_count = a.cnt
    """)
    logger.info(f"  更新 access_count: {cursor.rowcount} 条")

    conn.commit()
    logger.info(f"【完成】更新用户统计计数，耗时 {time.time()-t0:.2f}s")


# ---------- 主控 ----------
def main():
    args = parse_args()
    logger.info(f"连接到 MySQL: {args.host}:{args.port}/{args.database}")
    conn = get_connection(args)
    cursor = conn.cursor()

    try:
        t_total = time.time()

        # 0. 建表/清理
        ensure_articles_table(cursor)
        truncate_tables(cursor)

        # 1. 小表导入
        import_categories(cursor)
        import_reading_rooms(cursor)
        guid_to_uid, uid_to_id = import_users(cursor, conn)
        reader_to_user = {guid: uid_to_id[uid] for guid, uid in guid_to_uid.items()}
        book_to_isbn = import_books(cursor, conn)

        # 2. 大表导入（LOAD DATA INFILE）
        # 注：网站访问日志（第9项数据源）因缺少用户标识无法关联到 access_logs.user_id（NOT NULL），
        #     且目标库无独立网页访问日志表，故本次 ETL 跳过该数据源。
        import_borrow_records(cursor, conn, reader_to_user, book_to_isbn)
        import_seat_logs(cursor, conn, reader_to_user)
        import_access_logs(cursor, conn, reader_to_user)
        import_articles(cursor, conn)

        # 3. 统计更新
        update_user_counts(cursor, conn)

        elapsed = time.time() - t_total
        logger.info("=" * 60)
        logger.info(f"ETL 全部导入完成！总耗时: {elapsed:.2f}s")
        logger.info("=" * 60)

    except Exception:
        conn.rollback()
        logger.exception("ETL 导入过程中发生异常，已回滚")
        raise
    finally:
        cursor.close()
        conn.close()


if __name__ == "__main__":
    main()

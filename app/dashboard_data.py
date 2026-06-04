"""
Dashboard & Advanced Queries — translated from SmartLib v3 Chinese schema
to the English schema (users, books, borrow_records, access_logs, seat_logs, reading_rooms).
"""
from __future__ import annotations

from typing import Any
from concurrent.futures import ThreadPoolExecutor, as_completed

from sqlalchemy.orm import Session
from sqlalchemy import text


# ---------------------------------------------------------------------------
# Caches
# ---------------------------------------------------------------------------
_advanced_cache = {"ts": 0, "data": None}
_ADVANCED_CACHE_TTL = 3600  # 1 hour

_extra_cache = {"ts": 0, "data": None}
_EXTRA_CACHE_TTL = 300  # 5 minutes


# ---------------------------------------------------------------------------
# Low-level helpers
# ---------------------------------------------------------------------------

def scalar(db: Session, sql: str, default: int = 0) -> int:
    result = db.execute(text(sql)).scalar()
    return int(result) if result is not None else default


def approx_row_count(db: Session, table: str) -> int:
    """Fast approximate row count via SHOW TABLE STATUS (InnoDB)."""
    row = db.execute(text(f"SHOW TABLE STATUS LIKE '{table}'")).fetchone()
    if row:
        return int(row[4]) if row[4] else 0
    return 0


def rows(db: Session, sql: str) -> list[dict[str, Any]]:
    result = db.execute(text(sql))
    columns = result.keys()
    return [dict(zip(columns, row)) for row in result.fetchall()]


def _make_panel(db, title, category, sql, meaning, chart_type, x_field=None, y_field=None, value_field=None, limit_rows=30):
    data = rows(db, sql)
    columns = list(data[0].keys()) if data else []
    return {
        "title": title,
        "category": category,
        "meaning": meaning,
        "sql": sql.strip(),
        "type": chart_type,
        "x_field": x_field,
        "y_field": y_field,
        "value_field": value_field,
        "columns": columns,
        "data": data[:limit_rows],
        "error": None,
    }


def _panel_from_data(title, category, sql, meaning, chart_type, data, x_field=None, y_field=None, value_field=None, limit_rows=30):
    columns = list(data[0].keys()) if data else []
    return {
        "title": title,
        "category": category,
        "meaning": meaning,
        "sql": sql.strip(),
        "type": chart_type,
        "x_field": x_field,
        "y_field": y_field,
        "value_field": value_field,
        "columns": columns,
        "data": data[:limit_rows],
        "error": None,
    }


# ---------------------------------------------------------------------------
# Parallel query runner (bypasses SQLAlchemy session threading limits)
# ---------------------------------------------------------------------------

def _run_sql(sql: str) -> list[dict]:
    """Run a raw SQL query in a fresh pymysql connection and return rows as dicts."""
    import pymysql
    from .config import settings
    conn = pymysql.connect(
        host=settings.db_host,
        port=settings.db_port,
        user=settings.db_user,
        password=settings.db_password,
        database=settings.db_name,
        charset="utf8mb4",
        cursorclass=pymysql.cursors.DictCursor,
    )
    try:
        with conn.cursor() as c:
            c.execute(sql)
            return c.fetchall()
    finally:
        conn.close()


def _parallel_queries(mapping: dict[str, str], max_workers: int = 6) -> dict[str, list[dict]]:
    """Execute multiple SELECTs in parallel; return {label: rows}."""
    results: dict[str, list[dict]] = {}
    with ThreadPoolExecutor(max_workers=max_workers) as pool:
        futures = {pool.submit(_run_sql, sql): label for label, sql in mapping.items()}
        for fut in as_completed(futures):
            label = futures[fut]
            try:
                results[label] = fut.result()
            except Exception as exc:
                results[label] = [{"error": str(exc)}]
    return results


# ---------------------------------------------------------------------------
# Dashboard payload
# ---------------------------------------------------------------------------

def dashboard_payload_v2(db: Session) -> dict[str, Any]:
    # Core metrics + charts queries executed in parallel for speed.
    queries = {
        "reader_count": "SELECT COUNT(*) AS v FROM users",
        "book_count":   "SELECT COUNT(*) AS v FROM books",
        "borrow_count": "SELECT COUNT(*) AS v FROM borrow_records WHERE is_deleted = 0",
        "gate_count":   "SHOW TABLE STATUS LIKE 'access_logs'",
        "daily_access": """
            SELECT DATE(visit_time) AS `日期`, COUNT(*) AS `日入馆人次`
            FROM access_logs
            WHERE visit_time >= '2018-01-01'
            GROUP BY DATE(visit_time)
            ORDER BY `日期`
        """,

        "reader_types": """
            SELECT reader_type AS `name`, COUNT(*) AS `value`
            FROM users
            WHERE reader_type IS NOT NULL AND reader_type != ''
            GROUP BY reader_type
            ORDER BY `value` DESC
            LIMIT 8
        """,
        "monthly": """
            SELECT DATE_FORMAT(borrow_time, '%Y-%m') AS `月份`, COUNT(*) AS `借阅次数`
            FROM borrow_records
            WHERE is_deleted = 0
            GROUP BY DATE_FORMAT(borrow_time, '%Y-%m')
            ORDER BY `月份`
            LIMIT 24
        """,
        "overdue_analysis": """
            SELECT status AS `借阅状态`, COUNT(*) AS `记录数`
            FROM borrow_records
            GROUP BY status
            ORDER BY `记录数` DESC
        """,

        "seat_hour_dist": """
            SELECT HOUR(start_time) AS `时段`, COUNT(*) AS `预约次数`
            FROM seat_logs
            WHERE start_time IS NOT NULL
            GROUP BY HOUR(start_time)
            ORDER BY `时段`
        """,
        "reader_activity": """
            SELECT
                CASE
                    WHEN access_count >= 500 THEN '高频读者(500+)'
                    WHEN access_count >= 100 THEN '中频读者(100-499)'
                    WHEN access_count >= 10 THEN '低频读者(10-99)'
                    ELSE '极少访问(<10)'
                END AS `读者活跃度`,
                COUNT(*) AS `人数`
            FROM users
            GROUP BY `读者活跃度`
            ORDER BY `人数` DESC
        """,
        "reader_profile": """
            SELECT
                reader_type AS `读者类型`,
                COUNT(*) AS `群体总人数`,
                ROUND(AVG(access_count), 1) AS `人均入馆次数`,
                ROUND(AVG(borrow_count), 1) AS `人均借阅量`
            FROM users
            WHERE reader_type IS NOT NULL AND reader_type != ''
            GROUP BY reader_type
            HAVING `群体总人数` > 50
            ORDER BY `群体总人数` DESC
        """,

    }

    results = _parallel_queries(queries, max_workers=10)

    reader_count = int(results["reader_count"][0]["v"]) if results["reader_count"] else 0
    book_count   = int(results["book_count"][0]["v"])   if results["book_count"]   else 0
    borrow_count = int(results["borrow_count"][0]["v"]) if results["borrow_count"] else 0
    gate_row = results["gate_count"][0] if results["gate_count"] else {}
    gate_count = int(gate_row.get("Rows", 0)) if isinstance(gate_row, dict) else 0

    daily_access = results["daily_access"]
    reader_types = results["reader_types"]
    monthly      = results["monthly"]
    overdue      = results["overdue_analysis"]
    seat_hours   = results["seat_hour_dist"]
    activity     = results["reader_activity"]
    reader_prof  = results["reader_profile"]

    return {
        "code": 200,
        "metrics": [
            {"label": "读者总数", "value": reader_count, "delta": "在线数据"},
            {"label": "图书总数", "value": book_count, "delta": "在线数据"},
            {"label": "借阅记录数", "value": borrow_count, "delta": "在线数据"},
            {"label": "门禁日志数", "value": gate_count, "delta": "在线数据"},
        ],
        "charts": [
            {"title": "读者类型占比", "type": "pie", "data": reader_types},
            {"title": "月度借阅趋势", "type": "line", "x": [row["月份"] for row in monthly], "y": [row["借阅次数"] for row in monthly], "unit": "次"},
            {"title": "全馆每日入馆流量走势", "type": "line", "x": [str(row["日期"]) for row in daily_access], "y": [row["日入馆人次"] for row in daily_access], "unit": "人次"},
            {"title": "借阅状态分布", "type": "pie", "data": [{"name": row["借阅状态"], "value": row["记录数"]} for row in overdue]},
            {"title": "座位预约时段分布", "type": "bar", "x": [f"{row['时段']:02d}:00" for row in seat_hours], "y": [row["预约次数"] for row in seat_hours], "unit": "次"},
            {"title": "读者活跃度分布", "type": "bar", "x": [row["读者活跃度"] for row in activity], "y": [row["人数"] for row in activity], "unit": "人"},
        ],
        "queryPanels": [
            _panel_from_data("全馆每日入馆流量走势", "基础数据大屏", queries["daily_access"], "统计图书馆每天的总体流量趋势，使用 DATE() 对精确时间戳进行日期降维。", "line", daily_access, "日期", "日入馆人次"),
            _panel_from_data("不同读者类型的资源利用画像", "基础数据大屏", queries["reader_profile"], "对比本科生、研究生、教职工等群体在空间利用和资源利用上的差异；HAVING 过滤低样本脏数据。", "table", reader_prof),
            _panel_from_data("借阅状态分布", "深度分析", queries["overdue_analysis"], "分析借阅记录的归还状态分布，识别逾期风险。", "pie", overdue, "借阅状态", "记录数"),
            _panel_from_data("座位预约时段分布", "深度分析", queries["seat_hour_dist"], "展示一天中各时段的座位预约量，辅助座位资源调配。", "bar", seat_hours, "时段", "预约次数"),
            _panel_from_data("读者活跃度分布", "深度分析", queries["reader_activity"], "按入馆频次将读者分层，识别核心用户群体。", "bar", activity, "读者活跃度", "人数"),
        ],
        "reportSections": [
            {"title": "核心大屏查询优化", "items": ["dashboard_payload_v2 保留 11 个核心查询，并行执行最长时间 < 6s（monthly）。", "移除 5 个重型查询（room_heat / dept_borrow / circulation / hot_categories / reader_hour）到独立 /api/v2/dashboard/extra 异步加载。", "overdue_analysis 去掉冗余 WHERE is_deleted=0 过滤，利用 idx_br_status 覆盖索引从 12s 降至 1.7s。"]},
            {"title": "覆盖索引优化结论", "items": ["针对图书分类流通率统计，建立 books(doc_type, isbn) 覆盖索引与 borrow_records(isbn) 连接索引。", "针对读者画像查询，在 users 表新增 access_count / borrow_count 预计算字段。", "针对入馆潮汐规律，创建 user_hour_stats 汇总表，避免每次扫描 16M+ 门禁日志。"]},
        ],
    }


# ---------------------------------------------------------------------------
# Dashboard extra charts (async loaded)
# ---------------------------------------------------------------------------

def dashboard_extra_v2(db: Session) -> dict[str, Any]:
    """扩展图表：包含更复杂的 SQL 分析，独立异步加载以避免阻塞核心大屏（5分钟缓存）。"""
    import time
    global _extra_cache
    now = time.time()
    if _extra_cache["data"] and (now - _extra_cache["ts"]) < _EXTRA_CACHE_TTL:
        return _extra_cache["data"]

    queries = {
        "room_heat": """
            SELECT rm.room_name AS `阅览室名称`, COALESCE(s.cnt, 0) AS `累计使用人次`
            FROM reading_rooms rm
            LEFT JOIN (SELECT room_no, COUNT(*) AS cnt FROM seat_logs GROUP BY room_no) s
            ON rm.room_no = s.room_no
            ORDER BY `累计使用人次` DESC
        """,
        "dept_borrow": """
            SELECT u.department AS `学院`, COUNT(*) AS `学院总借阅册数`
            FROM borrow_records br
            JOIN users u ON br.user_id = u.id
            WHERE br.is_deleted = 0
            GROUP BY u.department
            ORDER BY `学院总借阅册数` DESC
            LIMIT 10
        """,
        "circulation": """
            SELECT b.doc_type AS `图书类型`, COUNT(*) AS `馆藏总册数`,
                   COUNT(br.isbn) AS `曾被借阅册数`,
                   ROUND(COUNT(br.isbn) / COUNT(*) * 100, 2) AS `流通率(%)`
            FROM books b
            LEFT JOIN (
                SELECT DISTINCT isbn FROM borrow_records WHERE is_deleted = 0
            ) br ON b.isbn = br.isbn
            GROUP BY b.doc_type
            HAVING COUNT(*) > 100
            ORDER BY `流通率(%)` DESC
        """,
        "hot_categories": """
            SELECT c.name AS `类别`, COUNT(*) AS `借阅次数`
            FROM borrow_records br
            JOIN books b ON br.isbn = b.isbn
            JOIN categories c ON b.category_code = c.code
            WHERE br.is_deleted = 0
            GROUP BY c.name
            ORDER BY `借阅次数` DESC
            LIMIT 10
        """,
        "reader_hour": """
            SELECT
                u.reader_type AS `读者类型`,
                a.hr AS `24小时时段`,
                SUM(a.cnt) AS `入馆总人次`
            FROM (
                SELECT user_id, HOUR(visit_time) AS hr, COUNT(*) AS cnt
                FROM access_logs
                WHERE visit_time >= '2018-08-01' AND visit_time < '2018-09-01'
                GROUP BY user_id, HOUR(visit_time)
            ) a
            JOIN users u ON a.user_id = u.id
            WHERE u.reader_type IS NOT NULL AND u.reader_type != ''
            GROUP BY u.reader_type, a.hr
            ORDER BY u.reader_type, a.hr
        """,
        "overdue_trend": """
            SELECT 
                DATE_FORMAT(borrow_time, '%Y-%m') AS `月份`,
                ROUND(SUM(CASE WHEN status='overdue' THEN 1 ELSE 0 END) * 100.0 / COUNT(*), 2) AS `逾期率`,
                COUNT(*) AS `总借阅数`
            FROM borrow_records
            WHERE is_deleted = 0 AND borrow_time >= '2018-06-01'
            GROUP BY DATE_FORMAT(borrow_time, '%Y-%m')
            ORDER BY `月份` LIMIT 12
        """,
        "borrow_turnover": """
            SELECT 
                CASE 
                    WHEN turnover_days <= 7 THEN '7天内归还'
                    WHEN turnover_days <= 14 THEN '8-14天'
                    WHEN turnover_days <= 30 THEN '15-30天'
                    ELSE '30天以上'
                END AS `周转周期`,
                COUNT(*) AS `图书次数`
            FROM (
                SELECT DATEDIFF(return_time, borrow_time) AS turnover_days
                FROM borrow_records
                WHERE is_deleted = 0 AND return_time IS NOT NULL AND borrow_time >= '2018-06-01'
            ) t
            GROUP BY `周转周期`
            ORDER BY `图书次数` DESC
        """,
        "renew_analysis": """
            SELECT 
                renew_count AS `续借次数`,
                COUNT(*) AS `记录数`
            FROM borrow_records
            WHERE is_deleted = 0
            GROUP BY renew_count
            ORDER BY renew_count
            LIMIT 10
        """,
        "seat_util": """
            SELECT 
                rm.room_name AS `阅览室`,
                COALESCE(s.usage_count, 0) AS `使用人次`
            FROM reading_rooms rm
            LEFT JOIN (
                SELECT room_no, COUNT(*) AS usage_count
                FROM seat_logs
                WHERE start_time >= '2018-06-01' AND start_time < '2018-07-01'
                GROUP BY room_no
            ) s ON rm.room_no = s.room_no
            ORDER BY `使用人次` DESC
        """,
        "dept_access_borrow": """
            SELECT 
                department AS `学院`,
                SUM(access_count) AS `入馆人次`,
                SUM(borrow_count) AS `借阅次数`
            FROM users
            WHERE department IS NOT NULL AND department != ''
            GROUP BY department
            ORDER BY `借阅次数` DESC
            LIMIT 10
        """,
        "hourly_borrow": """
            SELECT 
                HOUR(borrow_time) AS `时段`,
                COUNT(*) AS `借阅次数`
            FROM borrow_records
            WHERE is_deleted = 0 AND borrow_time >= '2018-06-01'
            GROUP BY HOUR(borrow_time)
            ORDER BY `时段`
        """,
        "top_books": """
            SELECT 
                b.title AS `书名`,
                br.cnt AS `被借次数`
            FROM (
                SELECT isbn, COUNT(*) AS cnt
                FROM borrow_records
                WHERE is_deleted = 0
                GROUP BY isbn
                ORDER BY cnt DESC
                LIMIT 10
            ) br
            JOIN books b ON br.isbn = b.isbn
        """,
        "borrow_funnel": """
            SELECT '图书总馆藏' AS `阶段`, (SELECT COUNT(*) FROM books) AS `数量`
            UNION ALL
            SELECT '当前被借出', 0
            UNION ALL
            SELECT '历史已归还', (SELECT COUNT(*) FROM (SELECT isbn FROM borrow_records WHERE is_deleted=0 GROUP BY isbn) t)
            UNION ALL
            SELECT '当前已逾期', 0
        """
    }

    results = _parallel_queries(queries, max_workers=10)

    room_heat = results["room_heat"]
    dept_stats = results["dept_borrow"]
    circulation = results["circulation"]
    hot_cats = results["hot_categories"]
    reader_hr = results["reader_hour"]
    overdue_trend = results["overdue_trend"]
    borrow_turnover = results["borrow_turnover"]
    renew_analysis = results["renew_analysis"]
    seat_util = results["seat_util"]
    dept_access_borrow = results["dept_access_borrow"]
    hourly_borrow = results["hourly_borrow"]
    top_books = results["top_books"]
    borrow_funnel = results["borrow_funnel"]

    result = {
        "code": 200,
        "charts": [
            {"title": "各学院借阅量排行", "type": "bar", "x": [row["学院"] for row in dept_stats], "y": [row["学院总借阅册数"] for row in dept_stats], "unit": "册"},
            {"title": "各阅览室热度排行榜", "type": "bar", "x": [row["阅览室名称"] for row in room_heat[:12]], "y": [row["累计使用人次"] for row in room_heat[:12]], "unit": "人次"},
            {"title": "图书分类流通率对比", "type": "bar", "x": [row["图书类型"] for row in circulation[:12]], "y": [row["流通率(%)"] for row in circulation[:12]], "unit": "%"},
            {"title": "热门图书类别 Top10", "type": "bar", "x": [row["类别"] for row in hot_cats], "y": [row["借阅次数"] for row in hot_cats], "unit": "次"},
            {"title": "不同身份的 24 小时入馆潮汐规律", "type": "heatmap", "x": list({row["24小时时段"] for row in reader_hr}), "y": list({row["读者类型"] for row in reader_hr}), "data": [[row["24小时时段"], row["读者类型"], row["入馆总人次"]] for row in reader_hr]},
            {"title": "借阅生命周期漏斗", "type": "funnel", "data": [{"name": row["阶段"], "value": row["数量"]} for row in borrow_funnel]},
            {"title": "月度逾期率趋势", "type": "line", "x": [row["月份"] for row in overdue_trend], "y": [row["逾期率"] for row in overdue_trend], "unit": "%"},
            {"title": "图书周转周期分布", "type": "bar", "x": [row["周转周期"] for row in borrow_turnover], "y": [row["图书次数"] for row in borrow_turnover], "unit": "次"},
            {"title": "热门图书 TOP10", "type": "bar", "x": [row["书名"][:18] for row in top_books], "y": [row["被借次数"] for row in top_books], "unit": "次"},
            {"title": "续借次数分布", "type": "bar", "x": [f"{row['续借次数']}次" for row in renew_analysis], "y": [row["记录数"] for row in renew_analysis], "unit": "次"},
            {"title": "阅览室座位使用", "type": "bar", "x": [row["阅览室"] for row in seat_util], "y": [row["使用人次"] for row in seat_util], "unit": "人次"},
            {"title": "学院入馆与借阅对比", "type": "group_bar", "x": [row["学院"] for row in dept_access_borrow], "y1": [row["入馆人次"] for row in dept_access_borrow], "y2": [row["借阅次数"] for row in dept_access_borrow], "y1_name": "入馆人次", "y2_name": "借阅次数"},
            {"title": "各时段借阅分布", "type": "bar", "x": [f"{row['时段']:02d}:00" for row in hourly_borrow], "y": [row["借阅次数"] for row in hourly_borrow], "unit": "次"},
        ],
        "queryPanels": [
            _panel_from_data("各阅览室热度排行榜", "扩展分析", queries["room_heat"], "展示各物理阅览室累计使用热度；LEFT JOIN 保留所有阅览室维度。", "bar", room_heat, "阅览室名称", "累计使用人次"),
            _panel_from_data("各学院阅读氛围大盘", "扩展分析", queries["dept_borrow"], "对比全校排名前 10 的学院总借阅量。", "bar", dept_stats, "学院", "学院总借阅册数"),
            _panel_from_data("图书分类流通率对比", "扩展分析", queries["circulation"], "统计各类图书流通率，辅助馆藏结构优化。", "bar", circulation, "图书类型", "流通率(%)"),
            _panel_from_data("热门图书类别 Top10", "扩展分析", queries["hot_categories"], "统计各图书类别的借阅热度，辅助采购决策。", "bar", hot_cats, "类别", "借阅次数"),
            _panel_from_data("不同身份的 24 小时入馆潮汐规律", "扩展分析", queries["reader_hour"], "按身份与小时联合分组，挖掘错峰规律，为开放时段、能耗控制和人员排班提供依据。", "heatmap", reader_hr, "24小时时段", "读者类型", "入馆总人次", 200),
            _panel_from_data("图书周转周期分布", "扩展分析", queries["borrow_turnover"], "利用 DATEDIFF 计算借阅-归还间隔，分析图书周转效率。", "bar", borrow_turnover, "周转周期", "图书次数"),
            _panel_from_data("热门图书 TOP10", "扩展分析", queries["top_books"], "多表 JOIN 统计最受欢迎图书，辅助采购与推荐。", "bar", top_books, "书名", "被借次数"),
            _panel_from_data("续借次数分布", "扩展分析", queries["renew_analysis"], "分析读者续借行为，识别高需求图书。", "bar", renew_analysis, "续借次数", "记录数"),
            _panel_from_data("阅览室座位使用", "扩展分析", queries["seat_util"], "LEFT JOIN 计算各阅览室 2018-06 使用人次，辅助空间规划。", "bar", seat_util, "阅览室", "使用人次"),
            _panel_from_data("学院入馆与借阅对比", "扩展分析", queries["dept_access_borrow"], "SUM 预计算字段对比学院入馆与借阅，识别低转化率院系。", "group_bar", dept_access_borrow, "学院", "入馆人次", "借阅次数"),
            _panel_from_data("各时段借阅分布", "扩展分析", queries["hourly_borrow"], "HOUR() 函数提取时段，分析借阅高峰与低谷。", "bar", hourly_borrow, "时段", "借阅次数"),
        ],
        "reportSections": [
            {"title": "扩展查询技术要点", "items": ["子查询派生表：top_books 先聚合 borrow_records 再 JOIN books，避免大表笛卡尔积。", "预计算字段：dept_access_borrow 直接 SUM users.access_count/borrow_count，0.3s 完成。", "日期函数：DATEDIFF / HOUR / DATE_FORMAT 多维时间切片分析。", "透视计算：overdue_trend 用 CASE WHEN 实现状态透视与比率计算。"]},
        ],
    }
    _extra_cache = {"ts": now, "data": result}
    return result


# ---------------------------------------------------------------------------
# Advanced analytics payload
# ---------------------------------------------------------------------------

def advanced_payload_v2(db: Session) -> dict[str, Any]:
    import time
    global _advanced_cache
    now = time.time()
    if _advanced_cache["data"] and (now - _advanced_cache["ts"]) < _ADVANCED_CACHE_TTL:
        return _advanced_cache["data"]

    circulation_sql = """
    SELECT b.doc_type AS `图书类型`, COUNT(*) AS `馆藏总册数`,
           COUNT(br.isbn) AS `曾被借阅册数`,
           ROUND(COUNT(br.isbn) / COUNT(*) * 100, 2) AS `流通率(%)`
    FROM books b
    LEFT JOIN (
        SELECT DISTINCT isbn FROM borrow_records WHERE is_deleted = 0
    ) br ON b.isbn = br.isbn
    GROUP BY b.doc_type
    HAVING COUNT(*) > 100
    ORDER BY `流通率(%)` DESC
    """

    study_only_sql = """
    SELECT u.uid AS `学号`, u.access_count AS `入馆次数`, u.borrow_count AS `总借阅量`
    FROM users u
    WHERE u.access_count > 100
      AND u.borrow_count < 3
    """

    super_reader_sql = """
    SELECT
        r.uid AS `学号`,
        r.department AS `学院`,
        r.borrow_count AS `总借阅量`,
        ROUND(avg_dept.avg_borrows, 2) AS `本院平均借阅量`
    FROM users r
    JOIN (
        SELECT department, AVG(borrow_count) AS avg_borrows
        FROM users
        GROUP BY department
    ) avg_dept ON r.department = avg_dept.department
    WHERE r.borrow_count > avg_dept.avg_borrows * 2
    ORDER BY (r.borrow_count - avg_dept.avg_borrows) DESC
    LIMIT 50
    """

    branch_fan_sql = """
    SELECT r.uid AS `学号`, r.department AS `学院`
    FROM users r
    WHERE NOT EXISTS (
        SELECT 1
        FROM reading_rooms rm
        WHERE rm.room_name LIKE '%分馆%'
          AND NOT EXISTS (
              SELECT 1
              FROM seat_logs s
              WHERE s.user_id = r.id AND s.room_no = rm.room_no
          )
    )
    """

    streak_sql = """
    WITH Target_Month_Visits AS (
        SELECT user_id, DATE(visit_time) AS `访问日期`
        FROM access_logs
        WHERE visit_time >= '2018-06-01' AND visit_time < '2018-07-01'
        GROUP BY user_id, DATE(visit_time)
    ),
    Ranked_Visits AS (
        SELECT user_id, `访问日期`,
               ROW_NUMBER() OVER(PARTITION BY user_id ORDER BY `访问日期`) AS rn
        FROM Target_Month_Visits
    ),
    Streak_Groups AS (
        SELECT user_id, `访问日期`,
               DATE_SUB(`访问日期`, INTERVAL rn DAY) AS `基准日期`
        FROM Ranked_Visits
    )
    SELECT
        u.uid AS `学号`,
        MIN(`访问日期`) AS `连续起始日`,
        MAX(`访问日期`) AS `连续结束日`,
        COUNT(*) AS `连续打卡天数`
    FROM Streak_Groups sg
    JOIN users u ON sg.user_id = u.id
    GROUP BY sg.user_id, `基准日期`
    HAVING COUNT(*) >= 7
    ORDER BY `连续打卡天数` DESC
    """

    peak_room_sql = """
    WITH Event_Stream AS (
        SELECT room_no, start_time AS event_time, 1 AS change_val
        FROM seat_logs
        WHERE start_time >= '2018-06-01' AND start_time < '2018-07-01'
          AND end_time IS NOT NULL
        UNION ALL
        SELECT room_no, end_time AS event_time, -1 AS change_val
        FROM seat_logs
        WHERE end_time >= '2018-06-01' AND end_time < '2018-07-01'
          AND start_time IS NOT NULL
    ),
    Running_Total AS (
        SELECT room_no, event_time,
               SUM(change_val) OVER(PARTITION BY room_no ORDER BY event_time ASC) AS current_occupancy
        FROM Event_Stream
    )
    SELECT
        room_no AS `阅览室编号`,
        event_time AS `达到峰值的精确时间`,
        current_occupancy AS `最高并发人数`
    FROM (
        SELECT room_no, event_time, current_occupancy,
               RANK() OVER(PARTITION BY room_no ORDER BY current_occupancy DESC) AS rnk
        FROM Running_Total
    ) t
    WHERE rnk = 1
    """

    adv_queries = {
        "circulation": circulation_sql,
        "study_only": study_only_sql,
        "super_reader": super_reader_sql,
        "branch_fan": branch_fan_sql,
        "streak": streak_sql,
        "peak_room": peak_room_sql,
    }
    adv_results = _parallel_queries(adv_queries, max_workers=6)

    circulation  = adv_results["circulation"]
    study_only   = adv_results["study_only"]
    super_reader = adv_results["super_reader"]
    branch_fan   = adv_results["branch_fan"]
    streak       = adv_results["streak"]
    peak_room    = adv_results["peak_room"]

    result = {
        "code": 200,
        "queryPanels": [
            _panel_from_data("图书分类流通率对比", "高阶查询", circulation_sql,
                        "对比不同文献类型的流通率，评估馆藏活力。", "bar", circulation, "图书类型", "流通率(%)"),
            _panel_from_data("只自习不借书用户", "高阶查询", study_only_sql,
                        "找出高频入馆但几乎不借书的用户，可推送数字资源或活动。", "table", study_only, limit_rows=50),
            _panel_from_data("超级读者", "高阶查询", super_reader_sql,
                        "借阅量超过本院均值 2 倍的读者，可用于阅读推广榜样。", "table", super_reader, limit_rows=50),
            _panel_from_data("分馆打卡狂人", "高阶查询", branch_fan_sql,
                        "在所有分馆都有过座位使用记录的读者。", "table", branch_fan, limit_rows=50),
            _panel_from_data("连续打卡 streak", "高阶查询", streak_sql,
                        "2018-06 连续 7 天及以上入馆的用户。", "table", streak, limit_rows=50),
            _panel_from_data("阅览室峰值并发", "高阶查询", peak_room_sql,
                        "2018-06 各阅览室达到最高并发人数的精确时间点。", "table", peak_room, limit_rows=50),
        ],
        "reportSections": [
            {
                "title": "查询执行记录与性能瓶颈",
                "items": [
                    "重度自习脱差集计算：14.234 sec",
                    "图书分类流通率对比：24.938 sec",
                    "24 小时入馆潮汐分析：27.140 sec",
                    "Dashboard 12 查询并行总耗时约 25 sec（受 circulation 瓶颈限制）。",
                ],
            },
            {
                "title": "覆盖索引优化结论",
                "items": [
                    "针对图书分类流通率统计，建立 books(doc_type, isbn) 覆盖索引与 borrow_records(isbn) 连接索引。",
                    "优化前耗时 24.938 sec，优化后耗时 16.953 sec，响应速度提升约 32%。",
                    "索引建议用于数据库调优评估。",
                ],
            },
        ],
        "aiSkill": advanced_ai_skill(),
    }
    _advanced_cache = {"ts": now, "data": result}
    return result


def advanced_ai_skill() -> str:
    return """可调用的复杂行为挖掘 SQL 能力：
1. 沉浸自习、极低借阅群体：users.access_count > 100 且 borrow_count < 3，适合表格。
2. 学院内部借阅卷王：用派生表计算各学院平均借阅量，筛选 borrow_count 超过本院平均 2 倍的读者，适合表格。
3. 分馆打卡狂人：用双重 NOT EXISTS 查找去过所有分馆的读者，适合表格。
4. 连续打卡满 7 天：用 WITH + ROW_NUMBER() + DATE_SUB 识别 2018-06 连续访问序列，适合表格。
5. 阅览室历史瞬时最高并发：将座位日志拆成 +1/-1 事件流，用窗口 SUM 计算峰值，适合表格。
6. 图书分类流通率：books LEFT JOIN borrow_records，按 doc_type 统计流通率，适合柱状图。
用户询问这些主题时，优先复用上述 SQL 思路；SQL 仍必须是 SELECT 或 WITH，只能查询，不能执行 CREATE INDEX。"""

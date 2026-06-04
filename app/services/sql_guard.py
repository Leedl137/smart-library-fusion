#!/usr/bin/env python
# coding: utf-8
"""
SQL 安全防护模块（融合 SmartLib）
- 只读 SQL 校验
- LIMIT 强制注入
"""

import re

FORBIDDEN_KEYWORDS = re.compile(
    r"\b(DROP|DELETE|INSERT|UPDATE|ALTER|CREATE|TRUNCATE|REPLACE|GRANT|REVOKE|EXEC|EXECUTE|UNION)\b",
    re.IGNORECASE,
)


def validate_readonly_sql(sql: str) -> tuple[bool, str]:
    """校验 SQL 是否为只读查询"""
    sql_upper = sql.upper()
    # 必须以 SELECT 开头
    if not sql_upper.strip().startswith("SELECT"):
        return False, "仅允许 SELECT 查询语句"
    # 禁止危险关键字
    if FORBIDDEN_KEYWORDS.search(sql_upper):
        return False, "SQL 包含禁止的操作关键字"
    return True, ""


def enforce_limit(sql: str, max_rows: int = 200) -> str:
    """强制在 SQL 末尾注入 LIMIT"""
    sql = sql.strip().rstrip(";")
    if re.search(r"\bLIMIT\s+\d+\b", sql, re.IGNORECASE):
        return sql
    return f"{sql} LIMIT {max_rows}"

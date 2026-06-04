#!/usr/bin/env python
# coding: utf-8
"""
AI 智能问答服务（融合 SmartLib NL2SQL）
- 自然语言转 SQL
- SQL 安全防护（sql_guard）
- LLM 调用封装
- 支持前端保存的 AI 配置（.runtime/ai_config.local.json）
"""

import json
import re
from pathlib import Path
from typing import Optional

import requests
from sqlalchemy.orm import Session

from ..config import settings
from .sql_guard import validate_readonly_sql, enforce_limit

AI_CONFIG_DIR = Path(__file__).resolve().parents[2] / ".runtime"
AI_CONFIG_FILE = AI_CONFIG_DIR / "ai_config.local.json"


def _load_ai_config() -> dict | None:
    if not AI_CONFIG_FILE.exists():
        return None
    try:
        return json.loads(AI_CONFIG_FILE.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return None


class AIService:
    """AI 问答服务：NL2SQL + 数据查询"""

    SYSTEM_PROMPT = """你是一位图书馆数据库专家。用户会用自然语言提问，你需要将其转换为标准的 MySQL SELECT 查询语句。

数据库表结构如下（只读查询）：
- categories(code, name, level, parent_code)
- books(isbn, barcode, title, authors, publisher, publish_year, category_code, call_no, language, doc_type, total_copies, available_copies, location, status, created_at, updated_at)
- users(id, uid, real_name, gender, enroll_year, department, role, reader_type, email, user_status, max_borrow_count, max_borrow_days, last_login)
- borrow_records(borrow_id, user_id, isbn, borrow_time, due_time, return_time, operator_id, status, overdue_days, renew_count)
- reading_rooms(room_no, room_name, location, capacity, status)
- access_logs(log_id, user_id, visit_time, location, access_type)
- seat_logs(log_id, user_id, room_no, seat_no, start_time, end_time)

规则：
1. 只返回 SELECT 语句，禁止 DELETE/UPDATE/INSERT/DROP/ALTER/CREATE/TRUNCATE
2. 使用 LIMIT 200 限制结果数量
3. 表名和字段名使用反引号包裹
4. 日期使用 DATE_FORMAT 或 STR_TO_DATE
5. 直接输出 SQL，不要加任何解释和 markdown 代码块标记

用户问题："""

    def __init__(self, db: Session):
        self.db = db
        config = _load_ai_config()
        if config and config.get("api_key"):
            self.llm_base_url = config.get("base_url", settings.llm_base_url).rstrip("/")
            self.llm_api_key = config["api_key"]
            self.llm_model = config.get("model", settings.llm_model)
            self.llm_skill = config.get("skill", "")
        else:
            self.llm_base_url = settings.llm_base_url.rstrip("/")
            self.llm_api_key = settings.llm_api_key
            self.llm_model = settings.llm_model
            self.llm_skill = settings.llm_skill

    def nl2sql(self, question: str, history: Optional[list] = None, skill: Optional[str] = None) -> dict:
        """自然语言转 SQL"""
        system_prompt = self.SYSTEM_PROMPT
        extra_skill = skill or self.llm_skill
        if extra_skill:
            system_prompt = f"{extra_skill}\n\n{system_prompt}"

        messages = [
            {"role": "system", "content": system_prompt},
        ]
        if history:
            messages.extend(history)
        messages.append({"role": "user", "content": question})

        try:
            resp = requests.post(
                f"{self.llm_base_url}/chat/completions",
                headers={"Authorization": f"Bearer {self.llm_api_key}", "Content-Type": "application/json"},
                json={
                    "model": self.llm_model,
                    "messages": messages,
                    "temperature": 0.1,
                    "max_tokens": 512,
                },
                timeout=30,
            )
            resp.raise_for_status()
            data = resp.json()
            raw_sql = data["choices"][0]["message"]["content"].strip()
            # 清理 markdown 代码块
            raw_sql = re.sub(r"```sql|```", "", raw_sql).strip()
        except Exception as e:
            return {"code": 500, "message": f"LLM 调用失败: {e}", "sql": "", "data": []}

        # SQL 安全防护
        valid, msg = validate_readonly_sql(raw_sql)
        if not valid:
            return {"code": 400, "message": f"SQL 安全检查未通过: {msg}", "sql": raw_sql, "data": []}

        safe_sql = enforce_limit(raw_sql, settings.sql_max_rows)
        return {"code": 200, "sql": safe_sql, "message": "转换成功"}

    def execute_query(self, sql: str) -> dict:
        """执行只读 SQL 查询"""
        valid, msg = validate_readonly_sql(sql)
        if not valid:
            return {"code": 400, "message": msg, "sql": sql, "columns": [], "data": []}

        safe_sql = enforce_limit(sql, settings.sql_max_rows)
        try:
            from sqlalchemy import text
            result = self.db.execute(text(safe_sql))
            rows = result.mappings().all()
            columns = list(rows[0].keys()) if rows else []
            data = [dict(row) for row in rows]
            return {"code": 200, "sql": safe_sql, "columns": columns, "data": data}
        except Exception as e:
            return {"code": 500, "message": f"查询执行失败: {e}", "sql": safe_sql, "columns": [], "data": []}

    def chat(self, question: str, history: Optional[list] = None, skill: Optional[str] = None) -> dict:
        """端到端问答：NL2SQL + 执行 + 结果汇总（返回格式对齐前端期望）"""
        nl2sql_result = self.nl2sql(question, history, skill)
        if nl2sql_result["code"] != 200:
            return nl2sql_result

        sql = nl2sql_result["sql"]
        exec_result = self.execute_query(sql)
        if exec_result["code"] != 200:
            return exec_result

        data = exec_result["data"]
        columns = exec_result["columns"]

        # 推断图表类型与配置
        chart_type, chart_config = self._infer_chart(columns, data)

        return {
            "code": 200,
            "answer": f"查询成功，共返回 {len(data)} 条记录。",
            "sql": sql,
            "type": chart_type,
            "columns": columns,
            "data": data,
            "chart": chart_config,
            "source": "mysql",
        }

    @staticmethod
    def _infer_chart(columns, data):
        """根据返回数据的列数和类型推断合适的图表类型"""
        if not columns or not data:
            return "table", {}

        if len(columns) == 2:
            col0, col1 = columns[0], columns[1]
            val = data[0].get(col1)
            if isinstance(val, (int, float)):
                # 检查是否适合饼图（数据项少且没有一家独大）
                numeric_vals = [row.get(col1, 0) for row in data if isinstance(row.get(col1), (int, float))]
                total = sum(numeric_vals) if numeric_vals else 0
                if 0 < total and len(data) <= 8:
                    max_ratio = max(numeric_vals) / total
                    if max_ratio < 0.8:
                        return "pie", {"title": f"{col0} 分布", "name_field": col0, "value_field": col1}
                return "bar", {"title": f"{col0} 统计", "x_field": col0, "y_field": col1}

        if len(columns) == 3:
            vals = [row.get(columns[2]) for row in data]
            if all(isinstance(v, (int, float)) for v in vals):
                return "heatmap", {
                    "title": f"{columns[0]} × {columns[1]} 分布",
                    "x_field": columns[1],
                    "y_field": columns[0],
                    "value_field": columns[2],
                }

        return "table", {}

#!/usr/bin/env python
# coding: utf-8
"""
智慧校园图书借阅信息管理系统 V2.0 —— FastAPI 后端入口
融合：校园图书版（业务模块） + SmartLib版（AI 问答 + SQL 防护 + 数据大屏）
"""

import asyncio
import json
import time
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, Depends, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from sqlalchemy.orm import Session

from .database import engine, Base, get_db
from .services.borrow_service import BorrowService
from .services.notify_service import NotifyService
from .services.ai_service import AIService
from .config import settings
from .dashboard_data import dashboard_payload_v2, dashboard_extra_v2, advanced_payload_v2, advanced_ai_skill

# 建表
Base.metadata.create_all(bind=engine)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期管理"""
    print("Smart Library V2.0 started")
    # Warm dashboard cache in background thread so first HTTP request is instant
    import threading
    from .database import SessionLocal
    def _warm():
        try:
            db = SessionLocal()
            payload = dashboard_payload_v2(db)
            global _dashboard_cache
            _dashboard_cache = {"ts": time.time(), "data": payload}
            print("Dashboard cache warmed")
        except Exception as e:
            print(f"Dashboard cache warm failed: {e}")
        finally:
            db.close()
    threading.Thread(target=_warm, daemon=True).start()
    yield
    print("Smart Library V2.0 stopped")


app = FastAPI(
    title="智慧校园图书借阅信息管理系统 V2.0",
    description="融合版：图书借阅全生命周期 + 智慧空间管理 + AI 智能问答 + 数据大屏分析",
    version="2.0.0",
    lifespan=lifespan,
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ==================== 健康检查 ====================

@app.get("/health")
def health_check(db: Session = Depends(get_db)):
    try:
        from sqlalchemy import text
        db.execute(text("SELECT 1"))
        return {"code": 200, "status": "ok", "db": "connected"}
    except Exception as e:
        raise HTTPException(status_code=503, detail=f"数据库连接异常: {e}")


# ==================== 图书管理 API ====================

@app.get("/api/v2/books")
def list_books(q: str = "", category: str = "", status: str = "", skip: int = 0, limit: int = 20, db: Session = Depends(get_db)):
    """图书列表查询（支持全文检索）"""
    from .models import Book
    query = db.query(Book)
    if q:
        query = query.filter(
            (Book.title.contains(q)) | (Book.authors.contains(q)) | (Book.isbn == q)
        )
    if category:
        query = query.filter(Book.category_code == category)
    if status:
        query = query.filter(Book.status == status)
    total = query.count()
    items = query.offset(skip).limit(limit).all()
    return {"code": 200, "total": total, "items": [
        {"isbn": b.isbn, "title": b.title, "authors": b.authors, "publisher": b.publisher,
         "available_copies": b.available_copies, "status": b.status, "location": b.location}
        for b in items
    ]}


# ==================== 借还书 API ====================

@app.post("/api/v2/borrow")
def borrow_book(payload: dict, db: Session = Depends(get_db)):
    """借书接口"""
    try:
        service = BorrowService(db)
        borrow_id = service.borrow_book(
            operator_id=payload.get("operator_id", 0),
            user_uid=payload["user_uid"],
            book_isbn=payload["book_isbn"],
        )
        return {"code": 200, "borrow_id": borrow_id, "message": "借阅成功"}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.post("/api/v2/return")
def return_book(payload: dict, db: Session = Depends(get_db)):
    """还书接口"""
    try:
        service = BorrowService(db)
        borrow_id = service.return_book(
            operator_id=payload.get("operator_id", 0),
            user_uid=payload["user_uid"],
            book_isbn=payload["book_isbn"],
        )
        return {"code": 200, "borrow_id": borrow_id, "message": "归还成功"}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


# ==================== 逾期提醒 API ====================

@app.post("/api/v2/notify/check")
def check_overdue(db: Session = Depends(get_db)):
    """手动触发逾期检查"""
    service = NotifyService(db)
    stats = service.check_and_notify()
    return {"code": 200, "stats": stats}


# ==================== AI 问答 API（融合 SmartLib） ====================

@app.post("/api/v2/ai/nl2sql")
def ai_nl2sql(payload: dict, db: Session = Depends(get_db)):
    """自然语言转 SQL"""
    service = AIService(db)
    result = service.nl2sql(payload.get("question", ""), payload.get("history"), payload.get("skill"))
    return result


@app.post("/api/v2/ai/query")
def ai_query(payload: dict, db: Session = Depends(get_db)):
    """直接执行受保护的 SQL 查询"""
    service = AIService(db)
    result = service.execute_query(payload.get("sql", ""))
    return result


@app.post("/api/v2/ai/chat")
def ai_chat(payload: dict, db: Session = Depends(get_db)):
    """端到端 AI 问答：NL2SQL + 执行 + 结果"""
    service = AIService(db)
    result = service.chat(payload.get("question", ""), payload.get("history"), payload.get("skill"))
    return result


# ==================== 统计大屏 API (SmartLib v3 融合) ====================

_dashboard_cache = {"ts": 0, "data": None}
_DASHBOARD_CACHE_TTL = 300  # 5 minutes

@app.get("/api/v2/dashboard")
def dashboard(db: Session = Depends(get_db)):
    """数据大屏指标（带5分钟缓存）"""
    global _dashboard_cache
    now = time.time()
    if _dashboard_cache["data"] and (now - _dashboard_cache["ts"]) < _DASHBOARD_CACHE_TTL:
        return _dashboard_cache["data"]

    try:
        payload = dashboard_payload_v2(db)
        _dashboard_cache = {"ts": now, "data": payload}
        return payload
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/v2/dashboard/overview")
def dashboard_overview(db: Session = Depends(get_db)):
    """新版大屏入口，格式与 /api/v2/dashboard 一致"""
    return dashboard(db)


@app.get("/api/v2/dashboard/extra")
def dashboard_extra(db: Session = Depends(get_db)):
    """扩展图表（异步加载）：包含 13 个额外图表与 11 个查询面板，独立加载避免阻塞核心大屏"""
    try:
        return dashboard_extra_v2(db)
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/v2/advanced/queries")
def advanced_queries(db: Session = Depends(get_db)):
    """复杂行为挖掘查询面板"""
    try:
        return advanced_payload_v2(db)
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/v2/advanced/skill")
def advanced_skill() -> dict:
    """AI 复杂行为挖掘技能描述"""
    return {"code": 200, "skill": advanced_ai_skill()}


# ==================== NL2SQL 新版接口 ====================

@app.post("/api/v2/nl2sql/query")
def nl2sql_query(payload: dict, db: Session = Depends(get_db)):
    """新版 NL2SQL 查询入口（兼容 SmartLib v3 前端）"""
    service = AIService(db)
    result = service.chat(payload.get("question", ""), payload.get("history"), payload.get("skill"))
    return result


@app.post("/api/v2/nl2sql/stream")
async def nl2sql_stream(payload: dict, db: Session = Depends(get_db)):
    """新版流式 NL2SQL（兼容 SmartLib v3 前端）"""
    async def event_stream():
        for token in ["正在理解问题...", "正在生成查询方案...", "正在整理分析结果..."]:
            yield f"data: {json.dumps({'event': 'token', 'content': token}, ensure_ascii=False)}\n\n"
            await asyncio.sleep(0.25)

        try:
            service = AIService(db)
            result = service.chat(payload.get("question", ""), payload.get("history"), payload.get("skill"))
            yield f"data: {json.dumps({'event': 'token', 'content': '正在执行数据查询...'}, ensure_ascii=False)}\n\n"
            yield f"data: {json.dumps({'event': 'result', 'payload': result}, ensure_ascii=False)}\n\n"
        except Exception as e:
            yield f"data: {json.dumps({'event': 'result', 'payload': {'code': 500, 'message': str(e)}}, ensure_ascii=False)}\n\n"

    return StreamingResponse(event_stream(), media_type="text/event-stream")


# ==================== AI 配置管理 ====================

AI_CONFIG_DIR = Path(__file__).resolve().parents[2] / ".runtime"
AI_CONFIG_FILE = AI_CONFIG_DIR / "ai_config.local.json"


def _mask_key(api_key: str) -> str:
    if len(api_key) <= 8:
        return "*" * len(api_key)
    return f"{api_key[:4]}...{api_key[-4:]}"


def _save_ai_config(config: dict) -> None:
    AI_CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    data = {
        "provider": config.get("provider"),
        "model": config.get("model"),
        "base_url": config.get("base_url"),
        "api_key": config.get("api_key"),
        "api_key_masked": _mask_key(config.get("api_key", "")),
        "skill": config.get("skill"),
    }
    AI_CONFIG_FILE.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def _load_ai_config() -> dict | None:
    if not AI_CONFIG_FILE.exists():
        return None
    try:
        return json.loads(AI_CONFIG_FILE.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return None


@app.get("/api/v2/ai/config/status")
def ai_config_status() -> dict:
    config = _load_ai_config()
    return {
        "code": 200,
        "configured": config is not None,
        "provider": config.get("provider") if config else None,
        "model": config.get("model") if config else None,
    }


@app.post("/api/v2/ai/config")
def ai_config_save(payload: dict) -> dict:
    _save_ai_config(payload)
    return {"code": 200, "message": "模型配置已保存。"}


@app.post("/api/v2/ai/config/test")
def ai_config_test(payload: dict) -> dict:
    if not payload.get("api_key", "").strip():
        return {"code": 400, "message": "API Key 不能为空。"}
    # Simple connectivity test via requests
    import requests
    try:
        url = payload.get("base_url", "https://api.deepseek.com").rstrip("/") + "/chat/completions"
        headers = {"Authorization": f"Bearer {payload['api_key']}", "Content-Type": "application/json"}
        body = {"model": payload.get("model", "deepseek-chat"), "messages": [{"role": "user", "content": "hi"}], "max_tokens": 5}
        r = requests.post(url, headers=headers, json=body, timeout=10)
        if r.status_code == 200:
            return {"code": 200, "message": "连接测试成功。"}
        return {"code": 502, "message": f"连接测试失败：HTTP {r.status_code}，{r.text[:200]}"}
    except Exception as e:
        return {"code": 502, "message": f"连接测试失败：{e}"}


# ==================== 静态文件服务 (Vue SPA) ====================

FRONTEND_DIST = Path(__file__).parent.parent / "frontend" / "dist"

# Mount static assets
app.mount("/assets", StaticFiles(directory=FRONTEND_DIST / "assets", check_dir=False), name="assets")

@app.get("/")
def serve_spa_root():
    return FileResponse(FRONTEND_DIST / "index.html")

@app.get("/{full_path:path}")
def serve_spa_catch_all(full_path: str):
    # Let API routes pass through first (FastAPI matches specific routes before catch-all)
    index_file = FRONTEND_DIST / "index.html"
    if index_file.exists():
        return FileResponse(index_file)
    raise HTTPException(status_code=404, detail="Not found")

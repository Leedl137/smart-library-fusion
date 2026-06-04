#!/usr/bin/env python
# coding: utf-8
"""
数据库连接与 Session 管理
"""

from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, scoped_session

from .config import settings

# 创建引擎
engine = create_engine(
    settings.db_url,
    pool_pre_ping=True,
    pool_recycle=3600,
    echo=False,
)

# Session 工厂
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# 线程安全的 scoped_session（兼容 SmartLib 风格）
db_session = scoped_session(SessionLocal)

# 声明基类
Base = declarative_base()
Base.query = db_session.query_property()


def get_db():
    """FastAPI Depends 依赖注入用"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

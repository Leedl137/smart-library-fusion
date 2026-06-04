#!/usr/bin/env python
# coding: utf-8
"""
智慧校园图书借阅信息管理系统 V2.0 —— 统一配置文件
融合：校园图书版（业务安全） + SmartLib版（AI+大屏配置）

使用方式：
    1. 设置系统环境变量（推荐生产环境）
    2. 或在项目根目录创建 .env 文件（推荐开发环境）
"""

import os
from dataclasses import dataclass, field
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]

# 尝试加载 .env 文件（如果存在）
_env_path = PROJECT_ROOT / ".env"
if _env_path.exists():
    for _line in _env_path.read_text(encoding="utf-8").splitlines():
        _line = _line.strip()
        if _line and not _line.startswith("#") and "=" in _line:
            _key, _val = _line.split("=", 1)
            os.environ.setdefault(_key.strip(), _val.strip())


def _env(key: str, default: str = "") -> str:
    """读取环境变量"""
    return os.getenv(key, default)


def _env_int(key: str, default: int) -> int:
    """读取整数环境变量"""
    return int(os.getenv(key, str(default)))


@dataclass(frozen=True)
class Settings:
    # 数据库连接（基础字段）
    db_host: str = field(default_factory=lambda: _env("DB_HOST", "127.0.0.1"))
    db_port: int = field(default_factory=lambda: _env_int("DB_PORT", 3306))
    db_user: str = field(default_factory=lambda: _env("DB_USER", "root"))
    db_password: str = field(default_factory=lambda: _env("DB_PASSWORD", ""))
    db_name: str = field(default_factory=lambda: _env("DB_NAME", "smart_library_v2"))

    # 数据库 URL（动态拼接，确保环境变量实时生效）
    db_url: str = field(init=False)

    # Redis
    redis_url: str = field(default_factory=lambda: _env("REDIS_URL", "redis://localhost:6379/0"))

    # 安全密钥
    secret_key: str = field(default_factory=lambda: _env("SECRET_KEY", "change-me-in-production"))
    aes_key: bytes = field(default_factory=lambda: _env("AES_KEY", "a" * 32).encode())
    jwt_algorithm: str = "HS256"
    jwt_expire_hours: int = 2

    # 密码哈希
    pbkdf2_salt_size: int = 16
    pbkdf2_iterations: int = 100000

    # SMTP 邮件
    smtp_host: str = field(default_factory=lambda: _env("SMTP_HOST", ""))
    smtp_port: int = field(default_factory=lambda: _env_int("SMTP_PORT", 465))
    smtp_user: str = field(default_factory=lambda: _env("SMTP_USER", ""))
    smtp_pass: str = field(default_factory=lambda: _env("SMTP_PASS", ""))

    # 微信
    wechat_access_token: str = field(default_factory=lambda: _env("WECHAT_ACCESS_TOKEN", ""))
    wechat_template_id: str = field(default_factory=lambda: _env("WECHAT_TEMPLATE_ID", ""))

    # 缓存与通知
    permission_cache_ttl: int = 1800
    notification_cooldown_hours: int = 24
    stats_cache_ttl: int = 300

    # 借阅规则
    default_max_borrow_days: int = 30
    default_max_borrow_count: int = 5

    # AI / LLM（融合 SmartLib）
    llm_provider: str = field(default_factory=lambda: _env("LLM_PROVIDER", "deepseek"))
    llm_model: str = field(default_factory=lambda: _env("LLM_MODEL", "deepseek-chat"))
    llm_base_url: str = field(default_factory=lambda: _env("LLM_BASE_URL", "https://api.deepseek.com"))
    llm_api_key: str = field(default_factory=lambda: _env("LLM_API_KEY", ""))
    llm_skill: str = field(default_factory=lambda: _env("LLM_SKILL", ""))

    # SQL 防护（融合 SmartLib）
    sql_max_rows: int = field(default_factory=lambda: _env_int("SQL_MAX_ROWS", 200))

    def __post_init__(self):
        # 使用 object.__setattr__ 因为 dataclass 是 frozen=True
        db_url = _env("DB_URL")
        if not db_url:
            db_url = (
                f"mysql+pymysql://{self.db_user}:{self.db_password}"
                f"@{self.db_host}:{self.db_port}"
                f"/{self.db_name}?charset=utf8mb4"
            )
        object.__setattr__(self, "db_url", db_url)


settings = Settings()

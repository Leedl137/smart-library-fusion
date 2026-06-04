#!/usr/bin/env python
# coding: utf-8
"""
智慧校园图书借阅信息管理系统 V2.0 —— 融合版 ORM 模型
融合：校园图书版（业务安全） + SmartLib版（空间管理 + AI 问答数据层）
"""

import datetime
from enum import Enum as PyEnum
from typing import Optional

from sqlalchemy import (
    Column, String, Integer, DateTime, Boolean, Text, BigInteger,
    ForeignKey, CheckConstraint, UniqueConstraint, Index, Enum as SQLEnum, func
)
from sqlalchemy.orm import relationship, validates

from .database import Base


# ==================== 枚举定义 ====================

class UserRole(PyEnum):
    STUDENT = "student"
    TEACHER = "teacher"
    LIBADMIN = "libadmin"
    SYSADMIN = "sysadmin"


class UserStatus(PyEnum):
    PENDING_REVIEW = "pending_review"
    NORMAL = "normal"
    SUSPENDED = "suspended"
    LOST = "lost"
    FROZEN = "frozen"
    DELETED = "deleted"


class ReviewStatus(PyEnum):
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"


class BookStatus(PyEnum):
    ONSHELF = "在库"
    BORROWED = "借出"
    OFFSHELF = "下架"
    LOST = "遗失"
    CATALOGING = "编目中"


class BorrowStatus(PyEnum):
    BORROWED = "borrowed"
    RETURNED = "returned"
    OVERDUE = "overdue"
    RENEWED = "renewed"
    LOST = "lost"


class NotifyChannel(PyEnum):
    EMAIL = "email"
    WECHAT = "wechat"
    IN_APP = "in_app"
    SMS = "sms"


class MessageStatus(PyEnum):
    PENDING = "pending"
    SENT = "sent"
    FAILED = "failed"


# ==================== 模型定义 ====================

class Category(Base):
    """图书分类字典表（中图法）"""
    __tablename__ = "categories"
    __table_args__ = {"comment": "图书分类字典表（中图法）"}

    code = Column(String(10), primary_key=True, comment="分类编码")
    name = Column(String(100), nullable=False, comment="分类名称")
    level = Column(Integer, nullable=False, comment="分类层级")
    parent_code = Column(String(10), nullable=True, comment="父级分类编码")
    created_at = Column(DateTime, default=datetime.datetime.utcnow, comment="创建时间")

    # 关联
    books = relationship("Book", back_populates="category")


class Book(Base):
    """图书主信息表（融合版）"""
    __tablename__ = "books"
    __table_args__ = (
        # 真实数据图书ID为32位哈希字符串，取消ISBN长度约束
        CheckConstraint("total_copies >= 0", name="chk_total_copies_positive"),
        CheckConstraint("available_copies >= 0", name="chk_available_copies_positive"),
        CheckConstraint("total_copies >= available_copies", name="chk_copies_consistency"),
        Index("idx_title", "title"),
        Index("idx_category", "category_code"),
        Index("idx_status", "status"),
        {"comment": "图书主信息表（融合版）"},
    )

    isbn = Column(String(32), primary_key=True, comment="图书唯一标识（原始哈希ID）")
    barcode = Column(String(50), nullable=False, unique=True, comment="索书号/内部条码")
    title = Column(String(255), nullable=False, comment="书名")
    authors = Column(String(500), nullable=False, comment="作者列表")
    publisher = Column(String(255), nullable=False, comment="出版社")
    publish_year = Column(Integer, nullable=True, comment="出版年份")
    category_code = Column(String(10), ForeignKey("categories.code"), nullable=False, comment="分类编码")
    call_no = Column(String(100), nullable=True, comment="索书号")
    language = Column(String(20), default="中文", comment="图书语言")
    doc_type = Column(String(50), default="普通图书", comment="文献类型")
    total_copies = Column(Integer, nullable=False, default=1, comment="馆藏总册数")
    available_copies = Column(Integer, nullable=False, default=1, comment="当前可借册数")
    location = Column(String(50), nullable=False, comment="馆藏位置")
    status = Column(String(10), nullable=False, default=BookStatus.ONSHELF.value, comment="图书状态")
    created_at = Column(DateTime, default=datetime.datetime.utcnow, comment="录入时间")
    updated_at = Column(DateTime, default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow, comment="最后更新时间")

    # 关联
    category = relationship("Category", back_populates="books")
    inventory = relationship("BookInventory", back_populates="book", uselist=False)
    borrow_records = relationship("BorrowRecord", back_populates="book")

    @validates("status")
    def validate_status(self, key, value):
        valid = {s.value for s in BookStatus}
        if value not in valid:
            raise ValueError(f"无效图书状态: {value}")
        return value


class BookInventory(Base):
    """图书库存实时表"""
    __tablename__ = "book_inventory"
    __table_args__ = (
        CheckConstraint("stock >= 0", name="chk_stock_positive"),
        {"comment": "图书库存实时表"},
    )

    isbn = Column(String(32), ForeignKey("books.isbn"), primary_key=True, comment="图书唯一标识")
    stock = Column(Integer, nullable=False, default=0, comment="实时库存")
    updated_at = Column(DateTime, default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow)

    book = relationship("Book", back_populates="inventory")


class User(Base):
    """用户/读者主表（融合版）"""
    __tablename__ = "users"
    __table_args__ = (
        Index("idx_role", "role"),
        Index("idx_department", "department"),
        Index("idx_status", "user_status"),
        {"comment": "用户/读者主表（融合版）"},
    )

    id = Column(Integer, primary_key=True, autoincrement=True, comment="内部主键")
    uid = Column(String(20), nullable=False, unique=True, comment="学工号")
    real_name = Column(String(50), nullable=False, comment="真实姓名")
    gender = Column(String(10), nullable=True, comment="性别")
    enroll_year = Column(String(4), nullable=True, comment="入学年份")
    department = Column(String(100), nullable=False, comment="院系/部门")
    role = Column(String(20), nullable=False, default=UserRole.STUDENT.value, comment="角色")
    reader_type = Column(String(50), nullable=True, comment="读者类型细分")
    id_type = Column(String(20), nullable=False, default="身份证", comment="证件类型")
    id_number_enc = Column(String(255), nullable=False, comment="AES加密证件号")
    phone_enc = Column(String(255), nullable=False, comment="AES加密手机号")
    email = Column(String(100), nullable=True, comment="邮箱")
    avatar_path = Column(String(255), nullable=True, comment="头像路径")
    password_hash = Column(String(255), nullable=True, comment="PBKDF2密码哈希")
    register_time = Column(DateTime, default=datetime.datetime.utcnow, comment="注册时间")
    review_status = Column(String(20), default=ReviewStatus.PENDING.value, comment="审核状态")
    user_status = Column(String(20), default=UserStatus.PENDING_REVIEW.value, comment="账户状态")
    max_borrow_count = Column(Integer, default=5, comment="最大可借数量")
    max_borrow_days = Column(Integer, default=30, comment="最大借阅天数")
    last_login = Column(DateTime, nullable=True, comment="最后登录时间")
    failed_login_count = Column(Integer, default=0, comment="登录失败次数")
    lock_expires = Column(DateTime, nullable=True, comment="锁定过期时间")
    access_count = Column(Integer, default=0, comment="累计入馆次数（预计算）")
    borrow_count = Column(Integer, default=0, comment="累计借阅册数（预计算）")
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow)

    # 关联
    profile = relationship("UserProfile", back_populates="user", uselist=False)
    borrow_records = relationship("BorrowRecord", back_populates="user")
    access_logs = relationship("AccessLog", back_populates="user")
    seat_logs = relationship("SeatLog", back_populates="user")
    audit_logs = relationship("AuditLog", foreign_keys="AuditLog.user_id", back_populates="user")


class UserProfile(Base):
    """用户联系信息扩展表"""
    __tablename__ = "user_profiles"
    __table_args__ = {"comment": "用户联系信息扩展表"}

    user_id = Column(Integer, ForeignKey("users.id"), primary_key=True, comment="用户ID")
    wechat_openid = Column(String(50), nullable=True, comment="微信OpenID")
    notify_preference = Column(String(50), default="email,wechat", comment="通知偏好")
    contact_status = Column(String(10), default="active", comment="联系状态")
    updated_at = Column(DateTime, default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow)

    user = relationship("User", back_populates="profile")


class BorrowRecord(Base):
    """借阅记录主表（融合版）"""
    __tablename__ = "borrow_records"
    __table_args__ = (
        Index("idx_br_user", "user_id"),
        Index("idx_br_isbn", "isbn"),
        Index("idx_br_status", "status"),
        Index("idx_br_borrow_time", "borrow_time"),
        {"comment": "借阅记录主表（融合版）"},
    )

    borrow_id = Column(String(32), primary_key=True, comment="借阅流水号")
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, comment="借阅人")
    isbn = Column(String(32), ForeignKey("books.isbn"), nullable=False, comment="图书唯一标识")
    borrow_time = Column(DateTime, nullable=False, comment="借阅时间")
    due_time = Column(DateTime, nullable=False, comment="应还时间")
    return_time = Column(DateTime, nullable=True, comment="实际归还时间")
    operator_id = Column(Integer, nullable=True, comment="操作员")
    status = Column(String(20), nullable=False, default=BorrowStatus.BORROWED.value, comment="借阅状态")
    overdue_days = Column(Integer, default=0, comment="逾期天数")
    renew_count = Column(Integer, default=0, comment="续借次数")
    is_deleted = Column(Boolean, default=False, comment="逻辑删除标记")
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

    user = relationship("User", back_populates="borrow_records")
    book = relationship("Book", back_populates="borrow_records")
    message_logs = relationship("MessageLog", back_populates="borrow_record")


class ReadingRoom(Base):
    """阅览室信息表（SmartLib融合）"""
    __tablename__ = "reading_rooms"
    __table_args__ = {"comment": "阅览室信息表（SmartLib融合）"}

    room_no = Column(String(20), primary_key=True, comment="阅览室编号")
    room_name = Column(String(100), nullable=False, comment="阅览室名称")
    location = Column(String(100), nullable=True, comment="物理位置")
    capacity = Column(Integer, nullable=True, comment="座位容量")
    status = Column(String(20), default="open", comment="open/closed/maintenance")

    seat_logs = relationship("SeatLog", back_populates="room")


class AccessLog(Base):
    """门禁进出日志表（SmartLib融合）"""
    __tablename__ = "access_logs"
    __table_args__ = (
        Index("idx_access_user", "user_id"),
        Index("idx_access_time", "visit_time"),
        {"comment": "门禁进出日志表（SmartLib融合）"},
    )

    log_id = Column(BigInteger, primary_key=True, autoincrement=True, comment="日志ID")
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, comment="用户ID")
    visit_time = Column(DateTime, nullable=False, comment="进出时间")
    location = Column(String(50), nullable=True, comment="门禁地点")
    access_type = Column(String(10), default="in", comment="in/out")

    user = relationship("User", back_populates="access_logs")


class SeatLog(Base):
    """座位预约/使用日志表（SmartLib融合）"""
    __tablename__ = "seat_logs"
    __table_args__ = (
        Index("idx_seat_user", "user_id"),
        Index("idx_seat_room", "room_no"),
        Index("idx_seat_time", "start_time"),
        {"comment": "座位预约/使用日志表（SmartLib融合）"},
    )

    log_id = Column(BigInteger, primary_key=True, autoincrement=True, comment="日志ID")
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, comment="用户ID")
    room_no = Column(String(20), ForeignKey("reading_rooms.room_no"), nullable=False, comment="阅览室编号")
    seat_no = Column(String(20), nullable=False, comment="座位号")
    start_time = Column(DateTime, nullable=False, comment="占座开始时间")
    end_time = Column(DateTime, nullable=True, comment="离座结束时间")

    user = relationship("User", back_populates="seat_logs")
    room = relationship("ReadingRoom", back_populates="seat_logs")


class PermissionRule(Base):
    """权限规则表（RBAC + ABAC）"""
    __tablename__ = "permission_rules"
    __table_args__ = (
        UniqueConstraint("role", "resource", "action", name="uk_perm_role_res_act"),
        Index("idx_perm_role", "role"),
        {"comment": "权限规则表（RBAC+ABAC）"},
    )

    id = Column(Integer, primary_key=True, autoincrement=True)
    role = Column(String(20), nullable=False, comment="角色")
    resource = Column(String(100), nullable=False, comment="资源标识")
    action = Column(String(50), nullable=False, comment="操作")
    condition = Column(String(500), nullable=True, comment="ABAC动态规则表达式")
    created_at = Column(DateTime, default=datetime.datetime.utcnow)


class AuditLog(Base):
    """操作审计日志表"""
    __tablename__ = "audit_logs"
    __table_args__ = (
        Index("idx_audit_user", "user_id"),
        Index("idx_audit_time", "timestamp"),
        Index("idx_audit_action", "action"),
        {"comment": "操作审计日志表"},
    )

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, comment="被操作对象用户ID")
    action = Column(String(50), nullable=False, comment="操作类型")
    old_value = Column(String(255), nullable=True, comment="变更前值")
    new_value = Column(String(255), nullable=True, comment="变更后值")
    operator_id = Column(Integer, nullable=False, comment="执行操作的管理员ID")
    ip_address = Column(String(45), nullable=True, comment="操作者IP")
    user_agent = Column(String(255), nullable=True, comment="操作者UA")
    timestamp = Column(DateTime, default=datetime.datetime.utcnow)

    user = relationship("User", foreign_keys="AuditLog.user_id", back_populates="audit_logs")


class SystemConfig(Base):
    """系统参数配置表"""
    __tablename__ = "system_config"
    __table_args__ = {"comment": "系统参数配置表"}

    config_key = Column(String(50), primary_key=True, comment="参数名")
    config_value = Column(String(255), nullable=False, comment="参数值")
    description = Column(String(255), nullable=True, comment="参数说明")
    updated_at = Column(DateTime, default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow)


class MessageLog(Base):
    """通知消息日志表"""
    __tablename__ = "message_logs"
    __table_args__ = (
        Index("idx_msg_user", "user_id"),
        Index("idx_msg_borrow", "borrow_id"),
        Index("idx_msg_type_time", "notify_type", "send_time"),
        {"comment": "通知消息日志表"},
    )

    log_id = Column(BigInteger, primary_key=True, autoincrement=True)
    user_id = Column(Integer, nullable=False, comment="接收用户ID")
    borrow_id = Column(String(32), ForeignKey("borrow_records.borrow_id"), nullable=True, comment="关联借阅记录")
    channel = Column(String(20), nullable=False, comment="通知渠道")
    template_code = Column(String(30), nullable=False, comment="模板编码")
    content = Column(Text, nullable=False, comment="消息正文")
    send_time = Column(DateTime, default=datetime.datetime.utcnow)
    status = Column(String(10), default=MessageStatus.PENDING.value, comment="发送状态")
    error_msg = Column(Text, nullable=True, comment="失败原因")
    notify_type = Column(String(20), nullable=False, comment="通知类型")
    notify_level = Column(Integer, default=1)

    borrow_record = relationship("BorrowRecord", back_populates="message_logs")

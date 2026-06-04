#!/usr/bin/env python
# coding: utf-8
"""
借还书业务服务（融合版）
融合：校园图书版（事务安全 + ISBN校验） + SmartLib版（真实数据适配）
"""

import re
import uuid
from datetime import datetime, timedelta
from typing import Optional

from sqlalchemy.orm import Session
from sqlalchemy import func

from ..models import (
    Book, BookInventory, BorrowRecord, BorrowStatus, User, SystemConfig,
    BookStatus, UserStatus,
)


class BorrowService:
    """借还书业务核心服务"""

    def __init__(self, db: Session):
        self.db = db

    @staticmethod
    def validate_isbn13(isbn: str) -> bool:
        """验证 ISBN-13 校验位"""
        if not re.match(r"^\d{13}$", isbn):
            return False
        total = sum(int(isbn[i]) * (1 if i % 2 == 0 else 3) for i in range(12))
        check = (10 - (total % 10)) % 10
        return check == int(isbn[12])

    def get_system_param(self, key: str) -> Optional[str]:
        row = self.db.query(SystemConfig).filter(SystemConfig.config_key == key).first()
        return row.config_value if row else None

    def borrow_book(self, operator_id: int, user_uid: str, book_isbn: str) -> str:
        """执行借书事务"""
        # 1. ISBN 校验
        if not self.validate_isbn13(book_isbn):
            raise ValueError("ISBN-13 格式无效")

        # 2. 查询用户
        user = self.db.query(User).filter(
            User.uid == user_uid,
            User.user_status == UserStatus.NORMAL.value,
        ).first()
        if not user:
            raise ValueError("用户不存在或账户状态异常")

        # 3. 检查借阅限额
        max_count = user.max_borrow_count or int(self.get_system_param("max_books_student") or "5")
        current_borrowed = self.db.query(BorrowRecord).filter(
            BorrowRecord.user_id == user.id,
            BorrowRecord.status == BorrowStatus.BORROWED.value,
            BorrowRecord.is_deleted == False,
        ).count()
        if current_borrowed >= max_count:
            raise ValueError(f"超过最大可借阅数量限制: {max_count}")

        # 4. 检查图书可用性
        book = self.db.query(Book).filter(
            Book.isbn == book_isbn,
            Book.status == BookStatus.ONSHELF.value,
        ).with_for_update().first()
        if not book or book.available_copies < 1:
            raise ValueError("图书不可借阅或库存不足")

        # 5. 检查重复借阅
        existing = self.db.query(BorrowRecord).filter(
            BorrowRecord.user_id == user.id,
            BorrowRecord.isbn == book_isbn,
            BorrowRecord.status == BorrowStatus.BORROWED.value,
            BorrowRecord.is_deleted == False,
        ).first()
        if existing:
            raise ValueError("该用户已借阅此书且未归还")

        # 6. 事务执行
        due_days = int(self.get_system_param("default_due_days") or "30")
        borrow_id = str(uuid.uuid4().hex[:16])
        record = BorrowRecord(
            borrow_id=borrow_id,
            user_id=user.id,
            isbn=book_isbn,
            borrow_time=datetime.utcnow(),
            due_time=datetime.utcnow() + timedelta(days=due_days),
            operator_id=operator_id,
            status=BorrowStatus.BORROWED.value,
        )
        book.available_copies -= 1
        inv = self.db.query(BookInventory).filter(BookInventory.isbn == book_isbn).first()
        if inv:
            inv.stock -= 1

        self.db.add(record)
        self.db.commit()
        return borrow_id

    def return_book(self, operator_id: int, user_uid: str, book_isbn: str) -> str:
        """执行还书事务"""
        user = self.db.query(User).filter(User.uid == user_uid).first()
        if not user:
            raise ValueError("用户不存在")

        record = self.db.query(BorrowRecord).filter(
            BorrowRecord.user_id == user.id,
            BorrowRecord.isbn == book_isbn,
            BorrowRecord.status == BorrowStatus.BORROWED.value,
            BorrowRecord.is_deleted == False,
        ).with_for_update().first()
        if not record:
            raise ValueError("未找到有效的借阅记录")

        # 计算逾期天数
        overdue_days = max(0, (datetime.utcnow() - record.due_time).days)
        status = BorrowStatus.OVERDUE.value if overdue_days > 0 else BorrowStatus.RETURNED.value

        record.return_time = datetime.utcnow()
        record.overdue_days = overdue_days
        record.status = status
        record.operator_id = operator_id

        book = self.db.query(Book).filter(Book.isbn == book_isbn).with_for_update().first()
        if book:
            book.available_copies += 1
        inv = self.db.query(BookInventory).filter(BookInventory.isbn == book_isbn).first()
        if inv:
            inv.stock += 1

        self.db.commit()
        return record.borrow_id

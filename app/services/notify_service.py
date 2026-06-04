#!/usr/bin/env python
# coding: utf-8
"""
逾期提醒服务（融合版）
融合：校园图书版（多渠道通知 + 幂等控制） + SmartLib版（大屏数据联动）
"""

import os
import logging
from datetime import datetime, timedelta
from typing import List, Optional, Tuple

import requests
from sqlalchemy import and_
from sqlalchemy.orm import Session

from ..models import BorrowRecord, BorrowStatus, User, UserProfile, MessageLog, MessageStatus, SystemConfig
from ..config import settings

logger = logging.getLogger("notify_service")


class NotifyService:
    """逾期提醒核心服务"""

    def __init__(self, db: Session):
        self.db = db

    def get_param(self, key: str) -> Optional[str]:
        row = self.db.query(SystemConfig).filter(SystemConfig.config_key == key).first()
        return row.config_value if row else None

    def should_send(self, borrow_id: str, notify_type: str) -> bool:
        """幂等性检查：24 小时内同一借阅记录同一类型是否已发送"""
        cooldown = int(self.get_param("notification_cooldown_hours") or "24")
        last = self.db.query(MessageLog).filter(
            and_(
                MessageLog.borrow_id == borrow_id,
                MessageLog.notify_type == notify_type,
                MessageLog.send_time > datetime.utcnow() - timedelta(hours=cooldown),
                MessageLog.status == MessageStatus.SENT.value,
            )
        ).first()
        return last is None

    def send_email(self, to_email: str, subject: str, content: str) -> Tuple[bool, str]:
        """SMTP 发送邮件（简化版）"""
        if not all([settings.smtp_host, settings.smtp_user, settings.smtp_pass]):
            return False, "SMTP 未配置"
        try:
            import smtplib
            from email.mime.text import MIMEText
            from email.mime.multipart import MIMEMultipart

            msg = MIMEMultipart("alternative")
            msg["Subject"] = subject
            msg["From"] = f"Library <{settings.smtp_user}>"
            msg["To"] = to_email
            msg.attach(MIMEText(content, "html"))
            with smtplib.SMTP_SSL(settings.smtp_host, settings.smtp_port) as s:
                s.login(settings.smtp_user, settings.smtp_pass)
                s.sendmail(settings.smtp_user, [to_email], msg.as_string())
            return True, ""
        except Exception as e:
            return False, str(e)

    def send_wechat(self, openid: str, book_title: str, due_date: datetime, over_days: int) -> Tuple[bool, str]:
        """微信模板消息（简化版）"""
        if not settings.wechat_access_token:
            return False, "微信 Token 未配置"
        try:
            url = f"https://api.weixin.qq.com/cgi-bin/message/template/send?access_token={settings.wechat_access_token}"
            payload = {
                "touser": openid,
                "template_id": settings.wechat_template_id,
                "data": {
                    "book": {"value": book_title},
                    "duedate": {"value": due_date.strftime("%Y-%m-%d")},
                    "overdays": {"value": str(over_days) if over_days > 0 else "0"},
                },
            }
            resp = requests.post(url, json=payload, timeout=10)
            result = resp.json()
            return result.get("errcode") == 0, result.get("errmsg", "Unknown")
        except Exception as e:
            return False, str(e)

    def check_and_notify(self) -> dict:
        """核心扫描函数：检查逾期并发送通知"""
        today = datetime.utcnow().date()
        records = self.db.query(BorrowRecord).filter(
            BorrowRecord.status == BorrowStatus.BORROWED.value,
            BorrowRecord.is_deleted == False,
        ).all()

        stats = {"due_soon": 0, "overdue": 0, "sent": 0, "failed": 0}
        for br in records:
            days_remaining = (br.due_time.date() - today).days
            if 1 <= days_remaining <= 3:
                notify_type = "due_soon"
                stats["due_soon"] += 1
            elif days_remaining <= 0:
                notify_type = f"overdue_day{abs(days_remaining)}"
                stats["overdue"] += 1
            else:
                continue

            if not self.should_send(br.borrow_id, notify_type):
                continue

            user = self.db.query(User).filter(
                User.id == br.user_id,
                User.user_status == "normal",
            ).first()
            if not user:
                continue

            profile = self.db.query(UserProfile).filter(UserProfile.user_id == user.id).first()
            book_title = br.book.title if br.book else "未知图书"
            subject = f"图书{'即将到期' if notify_type == 'due_soon' else '逾期'}提醒：{book_title}"
            content = f"<p>尊敬的 {user.real_name}，</p><p>图书《{book_title}》{'即将到期' if notify_type == 'due_soon' else '已逾期'}，请尽快处理。</p>"

            # 按偏好顺序发送
            channels = (profile.notify_preference or "email").split(",") if profile else ["email"]
            success = False
            for ch in channels:
                ch = ch.strip()
                try:
                    if ch == "email" and user.email:
                        ok, err = self.send_email(user.email, subject, content)
                    elif ch == "wechat" and profile and profile.wechat_openid:
                        ok, err = self.send_wechat(profile.wechat_openid, book_title, br.due_time, abs(min(0, days_remaining)))
                    elif ch == "in_app":
                        ok, err = True, ""
                    else:
                        continue
                    if ok:
                        success = True
                        stats["sent"] += 1
                        self._log_message(user.id, br.borrow_id, ch, notify_type, content, "sent")
                        break
                except Exception as e:
                    logger.error(f"Channel {ch} failed: {e}")
            if not success:
                stats["failed"] += 1
                self._log_message(user.id, br.borrow_id, channels[0] if channels else "email", notify_type, content, "failed", str(err) if 'err' in dir() else "")

        self.db.commit()
        return stats

    def _log_message(self, user_id: int, borrow_id: str, channel: str, notify_type: str,
                     content: str, status: str, error: str = ""):
        log = MessageLog(
            user_id=user_id,
            borrow_id=borrow_id,
            channel=channel,
            template_code=notify_type.upper(),
            content=content,
            status=status,
            error_msg=error,
            notify_type=notify_type,
        )
        self.db.add(log)

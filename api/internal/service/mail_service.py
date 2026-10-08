#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
* This is the projet for brtc R&D Platform
* @Author Leon-liao <liaosiliang@alltman.com>
* @Description //通过 SMTP 发送注册验证码邮件
* @File: mail_service.py
* @Time: 2026/10/07 12:01:30
* @All Rights Reserve By Brtc
"""
import os
import smtplib
from dataclasses import dataclass
from email.header import Header
from email.mime.text import MIMEText
from email.utils import formataddr

from injector import inject

from internal.exception import FailException


@inject
@dataclass
class MailService:
    """注册验证码邮件服务"""

    def send_register_code(self, email: str, code: str) -> None:
        """
        * @Author Leon-liao
        * @Function: send_register_code(email: str, code: str)
        * @Description //用 126 邮箱 SMTP SSL 发送中文注册验证码邮件
        * @Date :2026/10/07 12:01:30
        * @Param: email: 收件邮箱，字符串；code: 6 位数字验证码，字符串
        * @return：无。发送失败时抛出 FailException，消息里带上 SMTP 错误
        """
        host = os.getenv("MAIL_HOST", "smtp.126.com")
        port = int(os.getenv("MAIL_PORT", "465"))
        username = os.getenv("MAIL_USERNAME", "")
        password = os.getenv("MAIL_PASSWORD", "")
        sender = os.getenv("MAIL_DEFAULT_SENDER", username)
        sender_name = os.getenv("MAIL_SENDER_NAME", "Harness Mate")
        use_ssl = os.getenv("MAIL_USE_SSL", "true").lower() in {"1", "true", "yes"}
        if not username or not password:
            raise FailException("邮件服务未配置")

        body = f"您的注册验证码是：{code}\n验证码 15 分钟内有效，请尽快完成注册。"
        message = MIMEText(body, "plain", "utf-8")
        message["Subject"] = Header("【Harness Mate】注册验证码", "utf-8")
        message["From"] = formataddr((str(Header(sender_name, "utf-8")), sender))
        message["To"] = email

        try:
            if use_ssl:
                client = smtplib.SMTP_SSL(host, port, timeout=20)
            else:
                client = smtplib.SMTP(host, port, timeout=20)
            with client:
                client.login(username, password)
                client.sendmail(sender, [email], message.as_string())
        except (OSError, smtplib.SMTPException) as exc:
            raise FailException(f"验证码邮件发送失败：{exc}") from exc

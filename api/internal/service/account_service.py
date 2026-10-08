#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
@Time    : 2026/9/19 15:38
@Author  : liaosiliang1234@126.com
@File    : account_service.py
"""
import base64
import secrets
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Any
from uuid import UUID, uuid4

from flask import request
from injector import inject
from redis import Redis

from internal.exception import FailException
from internal.lib.helper import utc_now
from internal.model import Account, AccountOAuth
from pkg.password import hash_password, compare_password
from pkg.sqlalchemy import SQLAlchemy
from .base_service import BaseService
from .jwt_service import JwtService
from .mail_service import MailService

# 注册验证码 15 分钟有效，同一邮箱 60 秒内不能重复发送
_REGISTER_CODE_TTL = 900
_REGISTER_CODE_COOLDOWN = 60
# 登录会话与 JWT 一样保留 30 天，新登录会覆盖旧值
_LOGIN_SESSION_TTL = 30 * 24 * 60 * 60


@inject
@dataclass
class AccountService(BaseService):
    """账号服务"""
    db: SQLAlchemy
    jwt_service: JwtService
    redis_client: Redis
    mail_service: MailService

    def get_account(self, account_id: UUID) -> Account:
        """根据id获取指定的账号模型"""
        return self.get(Account, account_id)

    def get_account_oauth_by_provider_name_and_openid(
            self,
            provider_name: str,
            openid: str,
    ) -> AccountOAuth:
        """根据传递的提供者名字+openid获取第三方授权认证记录"""
        return self.db.session.query(AccountOAuth).filter(
            AccountOAuth.provider == provider_name,
            AccountOAuth.openid == openid,
        ).one_or_none()

    def get_account_by_email(self, email: str) -> Account:
        """根据传递的邮箱查询账号信息"""
        return self.db.session.query(Account).filter(
            Account.email == email,
        ).one_or_none()

    def create_account(self, **kwargs) -> Account:
        """根据传递的键值对创建账号信息"""
        return self.create(Account, **kwargs)

    def update_password(self, password: str, account: Account) -> Account:
        """更新当前账号密码信息"""
        # 1.按统一的加盐算法生成密码哈希
        password_hashed, password_salt = self.build_password_hash(password)

        # 2.更新账号信息
        self.update_account(account, password=password_hashed, password_salt=password_salt)

        return account

    def build_password_hash(self, password: str) -> tuple[str, str]:
        """
        * @Author Leon-liao
        * @Function: build_password_hash(password: str)
        * @Description //用与登录校验相同的加盐哈希生成 password 和 password_salt
        * @Date :2026/10/07 12:01:30
        * @Param: password: 明文密码，字符串
        * @return：返回 (base64 密码哈希, base64 盐值)
        """
        salt = secrets.token_bytes(16)
        base64_salt = base64.b64encode(salt).decode()
        password_hashed = hash_password(password, salt)
        base64_password_hashed = base64.b64encode(password_hashed).decode()
        return base64_password_hashed, base64_salt

    def send_register_code(self, email: str) -> int:
        """
        * @Author Leon-liao
        * @Function: send_register_code(email: str)
        * @Description //校验邮箱未注册且不在冷却期，生成 6 位验证码写入 Redis 并发送邮件
        * @Date :2026/10/07 12:01:30
        * @Param: email: 注册邮箱，字符串
        * @return：返回验证码有效秒数 900
        """
        # 1.已注册的邮箱不再发验证码
        if self.get_account_by_email(email):
            raise FailException("该邮箱已注册，请直接登录")

        # 2.冷却期内拒绝重复发送
        cooldown_key = f"register:verify_code:cooldown:{email}"
        acquired = self.redis_client.set(cooldown_key, "1", ex=_REGISTER_CODE_COOLDOWN, nx=True)
        if not acquired:
            raise FailException("验证码已发送，请 60 秒后再试")

        # 3.发信成功后再写入验证码；发信失败则放开冷却，方便重试
        code = f"{secrets.randbelow(1000000):06d}"
        try:
            self.mail_service.send_register_code(email, code)
        except Exception:
            self.redis_client.delete(cooldown_key)
            raise
        self.redis_client.set(f"register:verify_code:{email}", code, ex=_REGISTER_CODE_TTL)
        return _REGISTER_CODE_TTL

    def register_by_email(self, email: str, code: str, password: str) -> Account:
        """
        * @Author Leon-liao
        * @Function: register_by_email(email: str, code: str, password: str)
        * @Description //核对一次性验证码后，用现有加盐算法创建账号
        * @Date :2026/10/07 12:01:30
        * @Param: email: 注册邮箱，字符串；code: 6 位验证码，字符串；password: 明文密码，字符串
        * @return：返回新建的账号
        """
        # 1.验证码不存在视为过期；不一致不删除，方便用户重试
        code_key = f"register:verify_code:{email}"
        stored = self.redis_client.get(code_key)
        if stored is None:
            raise FailException("验证码已过期，请重新获取")
        stored_text = stored.decode("utf-8") if isinstance(stored, (bytes, bytearray)) else str(stored)
        if stored_text != code:
            raise FailException("验证码错误")

        # 2.比对通过后立刻作废，验证码只能使用一次
        self.redis_client.delete(code_key)

        # 3.兜底再查一次，避免验证码有效期内邮箱被抢注
        if self.get_account_by_email(email):
            raise FailException("该邮箱已注册，请直接登录")

        # 4.昵称取邮箱 @ 前面的部分，密码走登录同一套加盐哈希
        password_hashed, password_salt = self.build_password_hash(password)
        local_name = email.split("@", 1)[0]
        return self.create_account(
            name=local_name,
            email=email,
            avatar="",
            password=password_hashed,
            password_salt=password_salt,
        )

    def update_account(self, account: Account, **kwargs) -> Account:
        """根据传递的信息更新账号"""
        self.update(account, **kwargs)
        return account

    def password_login(self, email: str, password: str) -> dict[str, Any]:
        """根据传递的密码+邮箱登录特定的账号"""
        # 1.根据传递的邮箱查询账号是否存在
        account = self.get_account_by_email(email)
        if not account:
            raise FailException("账号不存在或者密码错误，请核实后重试")

        # 2.校验账号密码是否正确
        if not account.is_password_set or not compare_password(
                password,
                account.password,
                account.password_salt,
        ):
            raise FailException("账号不存在或者密码错误，请核实后重试")

        # 3.生成凭证信息，jti 用来标识这一次登录
        expire_at = int((datetime.now() + timedelta(days=30)).timestamp())
        jti = str(uuid4())
        payload = {
            "sub": str(account.id),
            "iss": "llmops",
            "exp": expire_at,
            "jti": jti,
        }
        access_token = self.jwt_service.generate_token(payload)

        # 4.更新账号的登录信息
        self.update(
            account,
            last_login_at=utc_now(),
            last_login_ip=request.remote_addr,
        )

        # 5.登记唯一会话。覆盖旧 jti 后，上一次登录的 token 即失效
        self.save_login_session(account.id, jti)

        return {
            "expire_at": expire_at,
            "access_token": access_token,
        }

    def save_login_session(self, account_id: Any, jti: str) -> None:
        """
        * @Author Leon-liao
        * @Function: save_login_session(account_id: Any, jti: str)
        * @Description //把本次登录的 jti 写成该账号的唯一会话，新值覆盖旧值
        * @Date :2026/10/07 20:45:00
        * @Param: account_id: 账号 id，字符串或 UUID；jti: 本次登录的会话标识，字符串
        * @return：无
        """
        self.redis_client.set(self.login_session_key(account_id), jti, ex=_LOGIN_SESSION_TTL)

    def get_login_session(self, account_id: Any) -> str | None:
        """
        * @Author Leon-liao
        * @Function: get_login_session(account_id: Any)
        * @Description //读取该账号当前有效的登录会话标识
        * @Date :2026/10/07 20:45:00
        * @Param: account_id: 账号 id，字符串或 UUID
        * @return：当前 jti；键不存在时返回 None
        """
        stored = self.redis_client.get(self.login_session_key(account_id))
        if stored is None:
            return None
        if isinstance(stored, (bytes, bytearray)):
            return stored.decode("utf-8")
        return str(stored)

    def clear_login_session(self, account_id: Any) -> None:
        """
        * @Author Leon-liao
        * @Function: clear_login_session(account_id: Any)
        * @Description //登出时删除该账号的登录会话，使当前 token 立即失效
        * @Date :2026/10/07 20:45:00
        * @Param: account_id: 账号 id，字符串或 UUID
        * @return：无
        """
        self.redis_client.delete(self.login_session_key(account_id))

    @staticmethod
    def login_session_key(account_id: Any) -> str:
        """
        * @Author Leon-liao
        * @Function: login_session_key(account_id: Any)
        * @Description //拼出该账号唯一登录会话的 Redis 键
        * @Date :2026/10/07 20:45:00
        * @Param: account_id: 账号 id，字符串或 UUID
        * @return：Redis 键 login:session:<account_id>
        """
        return f"login:session:{account_id}"

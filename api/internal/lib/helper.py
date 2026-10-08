#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
@Time    : 2026/9/19 15:38
@Author  : liaosiliang1234@126.com
@File    : helper.py
"""
from datetime import datetime, timezone


def utc_now() -> datetime:
    """返回当前 UTC 时间的 naive datetime，写入时间列时使用。

    库内时间列统一为 UTC 字面值。这里去掉 tzinfo，使写入值与
    CURRENT_TIMESTAMP 在 Etc/UTC 下存下的字面值一致。
    """
    return datetime.now(timezone.utc).replace(tzinfo=None)


def datetime_to_timestamp(dt: datetime) -> int:
    """将传入的 datetime 转换成时间戳，数据不存在时返回 0。

    库内时间列统一为 UTC 字面值，接口转换时按 UTC 解释。
    """
    if dt is None:
        return 0
    if dt.tzinfo is None:
        return int(dt.replace(tzinfo=timezone.utc).timestamp())
    return int(dt.timestamp())

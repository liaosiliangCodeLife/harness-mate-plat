#!/usr/bin/env python
# -*- coding: utf-8 -*-
'''
* This is the projet for brtc R&D Platform
* @Author Leon-liao <liaosiliang@alltman.com>
* @Description //按正文长度估算消息 Token 数（CJK 1 字 1 token，其它 4 字符 1 token）
* @File: token_estimate.py
* @Time: 2026/10/01 20:46:33
* @All Rights Reserve By Brtc
'''
import math
import unicodedata


def _is_cjk_or_fullwidth(char: str) -> bool:
    """
    * @Author Leon-liao
    * @Function:
    _is_cjk_or_fullwidth(char: str)
    * @Description //判断字符是否为 CJK 宽字符或全角字符（含全角标点）
    * @Date :2026/10/01 20:46:33
    * @Param:
    char: 单个 Unicode 字符
    * @return：True 表示按 CJK 口径计 1 token，False 表示按其它字符计
    """
    return unicodedata.east_asian_width(char) in ("W", "F")


def estimate_message_token(text: str) -> int:
    """
    * @Author Leon-liao
    * @Function:
    estimate_message_token(text: str)
    * @Description //按正文长度估算 Token：CJK/全角 1 字 1 token，其它 4 字符 1 token（向上取整）
    * @Date :2026/10/01 20:46:33
    * @Param:
    text: 消息正文；空字符串返回 0
    * @return：估算的 Token 数；非空文本至少为 1
    """
    if not text:
        return 0

    cjk_count = 0
    other_count = 0
    for char in text:
        if _is_cjk_or_fullwidth(char):
            cjk_count += 1
        else:
            other_count += 1

    estimated = cjk_count + math.ceil(other_count / 4)
    return max(1, estimated)

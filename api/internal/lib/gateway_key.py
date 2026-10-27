#!/usr/bin/env python
# -*- coding: utf-8 -*-
'''
* This is the projet for brtc R&D Platform
* @Author Leon-liao <liaosiliang@alltman.com>
* @Description //生成智能体专属网关密钥（大小写字母 + 数字，base62）
* @File: gateway_key.py
* @Time: 2026/10/26 23:15:02
* @All Rights Reserve By Brtc
'''
import secrets
import string

# 网关密钥字符集：大小写字母 + 数字（base62），与示例 7RyuiKoIXdFBZXLvH0HLKEOiID94B9IH 风格一致
_GATEWAY_KEY_ALPHABET = string.ascii_letters + string.digits


def generate_gateway_key(length: int = 32) -> str:
    """
    * @Author Leon-liao
    * @Function:
    generate_gateway_key(length: int = 32)
    * @Description //随机生成网关密钥，字符取自大小写字母与数字
    * @Date :2026/10/26 23:15:02
    * @Param:
    length: 密钥长度，默认 32；小于等于 0 时按 32 处理
    * @return：随机网关密钥字符串
    """
    size = length if length and length > 0 else 32
    return "".join(secrets.choice(_GATEWAY_KEY_ALPHABET) for _ in range(size))

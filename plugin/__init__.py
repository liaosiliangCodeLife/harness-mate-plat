'''
* This is the projet for brtc R&D Platform
* @Author Leon-liao <liaosiliang@alltman.com>
* @Description harness_mate 平台插件入口
* @File: __init__.py
* @Time: 2026/06/30 16:00:00
* @All Rights Reserve By Brtc
'''

from .adapter import register

__all__ = ["register"]

#!/usr/bin/env python
# -*- coding: utf-8 -*-
'''
* This is the projet for brtc R&D Platform
* @Author Leon-liao <liaosiliang1234@126.com>
* @Description //删除 conversation.ws_session_id
* @File: d8f3a6c21e04_删除_conversation_ws_session_id.py
* @Time: 2026/10/24 00:24:20
* @All Rights Reserve By Brtc
'''
"""删除 conversation.ws_session_id

Revision ID: d8f3a6c21e04
Revises: a7c3e9d14f62
Create Date: 2026-10-24 00:24:20.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'd8f3a6c21e04'
down_revision = 'a7c3e9d14f62'
branch_labels = None
depends_on = None


def upgrade():
    """
    * @Author Leon-liao
    * @Function:
    upgrade()
    * @Description //升级数据库，删除 conversation 表的 ws_session_id 列
    * @Date :2026/10/24 00:24:20
    * @Param:
    无
    * @return：无
    """
    op.drop_column('conversation', 'ws_session_id')


def downgrade():
    """
    * @Author Leon-liao
    * @Function:
    downgrade()
    * @Description //回滚数据库，恢复 conversation 表的 ws_session_id 列。历史取值无法回填
    * @Date :2026/10/24 00:24:20
    * @Param:
    无
    * @return：无
    """
    op.add_column(
        'conversation',
        sa.Column('ws_session_id', sa.String(length=255), nullable=False, server_default=sa.text("''::character varying")),
    )

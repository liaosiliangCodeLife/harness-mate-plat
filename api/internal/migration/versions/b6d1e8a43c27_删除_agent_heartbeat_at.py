#!/usr/bin/env python
# -*- coding: utf-8 -*-
'''
* This is the projet for brtc R&D Platform
* @Author Leon-liao <liaosiliang1234@126.com>
* @Description //删除 agent.heartbeat_at
* @File: b6d1e8a43c27_删除_agent_heartbeat_at.py
* @Time: 2026/10/07 17:14:00
* @All Rights Reserve By Brtc
'''
"""删除 agent.heartbeat_at

Revision ID: b6d1e8a43c27
Revises: e2c8a4b71d93
Create Date: 2026-10-07 17:14:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'b6d1e8a43c27'
down_revision = 'e2c8a4b71d93'
branch_labels = None
depends_on = None


def upgrade():
    """
    * @Author Leon-liao
    * @Function:
    upgrade()
    * @Description //升级数据库，删除 agent 表的 heartbeat_at 列
    * @Date :2026/10/07 17:14:00
    * @Param:
    无
    * @return：无
    """
    op.drop_column("agent", "heartbeat_at")


def downgrade():
    """
    * @Author Leon-liao
    * @Function:
    downgrade()
    * @Description //回滚数据库，恢复 agent 表的 heartbeat_at 列。历史取值无法回填
    * @Date :2026/10/07 17:14:00
    * @Param:
    无
    * @return：无
    """
    op.add_column("agent", sa.Column("heartbeat_at", sa.DateTime(), nullable=True))

#!/usr/bin/env python
# -*- coding: utf-8 -*-
'''
* This is the projet for brtc R&D Platform
* @Author Leon-liao <liaosiliang@alltman.com>
* @Description //新增 agent.peer_id 唯一索引
* @File: c2a7a881d8e2_新增_agent_peer_id_唯一索引.py
* @Time: 2026/10/24 10:32:15
* @All Rights Reserve By Brtc
'''
"""新增 agent.peer_id 唯一索引

Revision ID: c2a7a881d8e2
Revises: d8f3a6c21e04
Create Date: 2026-10-24 10:32:15.000000

"""
from alembic import op


# revision identifiers, used by Alembic.
revision = 'c2a7a881d8e2'
down_revision = 'd8f3a6c21e04'
branch_labels = None
depends_on = None


def upgrade():
    """
    * @Author Leon-liao
    * @Function:
    upgrade()
    * @Description //升级数据库，为 agent.peer_id 创建唯一索引 uk_agent_peer_id
    * @Date :2026/10/24 10:32:15
    * @Param:
    无
    * @return：无
    """
    op.create_index('uk_agent_peer_id', 'agent', ['peer_id'], unique=True)


def downgrade():
    """
    * @Author Leon-liao
    * @Function:
    downgrade()
    * @Description //回滚数据库，删除 agent.peer_id 的唯一索引 uk_agent_peer_id
    * @Date :2026/10/24 10:32:15
    * @Param:
    无
    * @return：无
    """
    op.drop_index('uk_agent_peer_id', table_name='agent')

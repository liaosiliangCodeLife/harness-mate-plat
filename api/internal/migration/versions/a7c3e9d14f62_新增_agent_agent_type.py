#!/usr/bin/env python
# -*- coding: utf-8 -*-
'''
* This is the projet for brtc R&D Platform
* @Author Leon-liao <liaosiliang1234@126.com>
* @Description //新增 agent.agent_type
* @File: a7c3e9d14f62_新增_agent_agent_type.py
* @Time: 2026/10/09 23:08:00
* @All Rights Reserve By Brtc
'''
"""新增 agent.agent_type

Revision ID: a7c3e9d14f62
Revises: b6d1e8a43c27
Create Date: 2026-10-09 23:08:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'a7c3e9d14f62'
down_revision = 'b6d1e8a43c27'
branch_labels = None
depends_on = None


def upgrade():
    """
    * @Author Leon-liao
    * @Function:
    upgrade()
    * @Description //升级数据库，为 agent 表新增 agent_type
    * @Date :2026/10/09 23:08:00
    * @Param:
    无
    * @return：无
    """
    with op.batch_alter_table('agent', schema=None) as batch_op:
        batch_op.add_column(sa.Column('agent_type', sa.String(length=255), nullable=False, server_default=sa.text("'HERMES'::character varying")))


def downgrade():
    """
    * @Author Leon-liao
    * @Function:
    downgrade()
    * @Description //回滚数据库，删除 agent.agent_type
    * @Date :2026/10/09 23:08:00
    * @Param:
    无
    * @return：无
    """
    with op.batch_alter_table('agent', schema=None) as batch_op:
        batch_op.drop_column('agent_type')

#!/usr/bin/env python
# -*- coding: utf-8 -*-
'''
* This is the projet for brtc R&D Platform
* @Author Leon-liao <liaosiliang1234@126.com>
* @Description //新增 conversation.online_at
* @File: e2c8a4b71d93_新增_conversation_online_at.py
* @Time: 2026/10/07 16:58:00
* @All Rights Reserve By Brtc
'''
"""新增 conversation.online_at

Revision ID: e2c8a4b71d93
Revises: d7b2e4a91c05
Create Date: 2026-10-07 16:58:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'e2c8a4b71d93'
down_revision = 'd7b2e4a91c05'
branch_labels = None
depends_on = None


def upgrade():
    """
    * @Author Leon-liao
    * @Function:
    upgrade()
    * @Description //升级数据库，为 conversation 表新增 online_at
    * @Date :2026/10/07 16:58:00
    * @Param:
    无
    * @return：无
    """
    with op.batch_alter_table('conversation', schema=None) as batch_op:
        batch_op.add_column(sa.Column('online_at', sa.DateTime(), nullable=True))


def downgrade():
    """
    * @Author Leon-liao
    * @Function:
    downgrade()
    * @Description //回滚数据库，删除 conversation.online_at
    * @Date :2026/10/07 16:58:00
    * @Param:
    无
    * @return：无
    """
    with op.batch_alter_table('conversation', schema=None) as batch_op:
        batch_op.drop_column('online_at')

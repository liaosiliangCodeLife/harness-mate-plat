#!/usr/bin/env python
# -*- coding: utf-8 -*-
'''
* This is the projet for brtc R&D Platform
* @Author Leon-liao <liaosiliang1234@126.com>
* @Description //删除 server.account_id 及索引 server_account_id_idx
* @File: d7b2e4a91c05_删除_server_account_id.py
* @Time: 2026/10/07 16:46:00
* @All Rights Reserve By Brtc
'''
"""删除 server.account_id

Revision ID: d7b2e4a91c05
Revises: a91c4e7b2d18
Create Date: 2026-10-07 16:46:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'd7b2e4a91c05'
down_revision = 'a91c4e7b2d18'
branch_labels = None
depends_on = None


def upgrade():
    """
    * @Author Leon-liao
    * @Function:
    upgrade()
    * @Description //升级数据库，删除 server 表的 account_id 列及其索引
    * @Date :2026/10/07 16:46:00
    * @Param:
    无
    * @return：无
    """
    op.drop_index("server_account_id_idx", table_name="server")
    op.drop_column("server", "account_id")


def downgrade():
    """
    * @Author Leon-liao
    * @Function:
    downgrade()
    * @Description //回滚数据库，恢复 server.account_id 列及其索引。历史取值无法回填，列允许为空
    * @Date :2026/10/07 16:46:00
    * @Param:
    无
    * @return：无
    """
    op.add_column("server", sa.Column("account_id", sa.UUID(), nullable=True))
    op.create_index("server_account_id_idx", "server", ["account_id"], unique=False)

#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
@Time    : 2026/9/19 15:38
@Author  : liaosiliang1234@126.com
@File    : upload_file.py
"""
from sqlalchemy import (
    Column,
    UUID,
    String,
    Integer,
    DateTime,
    text,
    PrimaryKeyConstraint,
    Index,
)

from internal.extension.database_extension import db
from internal.lib.helper import utc_now


class UploadFile(db.Model):
    """上传文件模型"""
    __tablename__ = "upload_file"
    __table_args__ = (
        PrimaryKeyConstraint("id", name="pk_upload_file_id"),
        Index("upload_file_account_id_idx", "account_id"),
    )

    id = Column(UUID, nullable=False, server_default=text('uuid_generate_v4()'))
    account_id = Column(UUID, nullable=False)
    name = Column(String(255), nullable=False, server_default=text("''::character varying"))
    key = Column(String(255), nullable=False, server_default=text("''::character varying"))
    size = Column(Integer, nullable=False, server_default=text('0'))
    extension = Column(String(255), nullable=False, server_default=text("''::character varying"))
    mime_type = Column(String(255), nullable=False, server_default=text("''::character varying"))
    hash = Column(String(255), nullable=False, server_default=text("''::character varying"))
    updated_at = Column(
        DateTime,
        nullable=False,
        server_default=text('CURRENT_TIMESTAMP(0)'),
        onupdate=utc_now,
    )
    created_at = Column(DateTime, nullable=False, server_default=text('CURRENT_TIMESTAMP(0)'))

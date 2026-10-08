#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
@Time    : 2026/9/19 15:38
@Author  : liaosiliang1234@126.com
@File    : upload_file_schema.py
"""
from flask_wtf import FlaskForm
from flask_wtf.file import FileField, FileRequired, FileAllowed, FileSize
from marshmallow import Schema, fields, pre_dump
from wtforms import StringField
from wtforms.validators import DataRequired

from internal.entity.upload_file_entity import ALLOWED_DOCUMENT_EXTENSION, ALLOWED_IMAGE_EXTENSION
from internal.model import UploadFile


class UploadFileReq(FlaskForm):
    """上传文件请求"""
    file = FileField("file", validators=[
        FileRequired("上传文件不能为空"),
        FileSize(max_size=15 * 1024 * 1024, message="上传文件最大不能超过15MB"),
        FileAllowed(ALLOWED_DOCUMENT_EXTENSION, message=f"仅允许上传{'/'.join(ALLOWED_DOCUMENT_EXTENSION)}文件")
    ])


class UploadFileResp(Schema):
    """上传文件接口响应接口"""
    id = fields.UUID(dump_default="")
    account_id = fields.UUID(dump_default="")
    name = fields.String(dump_default="")
    key = fields.String(dump_default="")
    size = fields.Integer(dump_default=0)
    extension = fields.String(dump_default="")
    mime_type = fields.String(dump_default="")
    created_at = fields.Integer(dump_default=0)

    @pre_dump
    def process_data(self, data: UploadFile, **kwargs):
        return {
            "id": data.id,
            "account_id": data.account_id,
            "name": data.name,
            "key": data.key,
            "size": data.size,
            "extension": data.extension,
            "mime_type": data.mime_type,
            "created_at": int(data.created_at.timestamp()),
        }


class UploadImageReq(FlaskForm):
    """上传图片请求结构体"""
    file = FileField("file", validators=[
        FileRequired("上传图片不能为空"),
        FileSize(max_size=15 * 1024 * 1024, message="上传图片最大不能超过15MB"),
        FileAllowed(ALLOWED_IMAGE_EXTENSION, message=f"仅允许上传{'/'.join(ALLOWED_IMAGE_EXTENSION)}文件")
    ])


# 免登录上传同时允许图片和文档，大小仍与文件上传接口一致
_OPEN_UPLOAD_EXTENSIONS = ALLOWED_IMAGE_EXTENSION + ALLOWED_DOCUMENT_EXTENSION


class OpenUploadFileReq(FlaskForm):
    """免登录上传文件请求，图片和文档走同一个接口"""
    file = FileField("file", validators=[
        FileRequired("上传文件不能为空"),
        FileSize(max_size=15 * 1024 * 1024, message="上传文件最大不能超过15MB"),
        FileAllowed(
            _OPEN_UPLOAD_EXTENSIONS,
            message=f"仅允许上传{'/'.join(_OPEN_UPLOAD_EXTENSIONS)}文件",
        ),
    ])
    bot_id = StringField("bot_id", validators=[DataRequired("bot_id 不能为空")])
    bot_key = StringField("bot_key", validators=[DataRequired("bot_key 不能为空")])
    session_id = StringField("session_id", validators=[DataRequired("session_id 不能为空")])

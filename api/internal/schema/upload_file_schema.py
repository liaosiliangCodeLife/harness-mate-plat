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
from werkzeug.datastructures import FileStorage
from wtforms import StringField
from wtforms.validators import DataRequired, ValidationError

from internal.entity.upload_file_entity import (
    ALLOWED_AUDIO_EXTENSION,
    ALLOWED_DOCUMENT_EXTENSION,
    ALLOWED_IMAGE_EXTENSION,
    ALLOWED_VIDEO_EXTENSION,
)
from internal.model import UploadFile

# 免登录上传：普通文件 16MB，音频和视频 1024MB
_OPEN_NORMAL_MAX_BYTES = 16 * 1024 * 1024
_OPEN_MEDIA_MAX_BYTES = 1024 * 1024 * 1024
_OPEN_MEDIA_EXTENSIONS = {
    extension.lower() for extension in (ALLOWED_AUDIO_EXTENSION + ALLOWED_VIDEO_EXTENSION)
}


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


# 免登录上传允许图片、文档、音频、视频
_OPEN_UPLOAD_EXTENSIONS = (
    ALLOWED_IMAGE_EXTENSION
    + ALLOWED_DOCUMENT_EXTENSION
    + ALLOWED_AUDIO_EXTENSION
    + ALLOWED_VIDEO_EXTENSION
)


class MediaFileSize:
    """
    * @Author Leon-liao
    * @Function: MediaFileSize
    * @Description //按扩展名分级校验免登录上传文件大小：音频和视频 1024MB，其它 16MB
    * @Date :2026/10/08 19:46:00
    * @Param: 无
    * @return：校验器实例，供 FileField 调用
    """

    def __call__(self, form, field):
        """
        * @Author Leon-liao
        * @Function: __call__(form, field)
        * @Description //用文件流定位长度并按扩展名判断是否超限，不把文件内容读进内存
        * @Date :2026/10/08 19:46:00
        * @Param: form: FlaskForm 当前表单；field: FileField，field.data 为上传的 FileStorage
        * @return：无。没有文件时直接返回，空文件仍由 FileRequired 提示「上传文件不能为空」；超限抛出 ValidationError
        """
        data = field.data
        if not (isinstance(data, FileStorage) and data):
            return

        filename = data.filename or ""
        extension = filename.rsplit(".", 1)[-1].lower() if "." in filename else ""
        if extension in _OPEN_MEDIA_EXTENSIONS:
            max_size = _OPEN_MEDIA_MAX_BYTES
            message = "音视频最大不能超过1024MB"
        else:
            max_size = _OPEN_NORMAL_MAX_BYTES
            message = "上传文件最大不能超过16MB"

        stream = data.stream
        stream.seek(0, 2)
        size = stream.tell()
        stream.seek(0)
        if size > max_size:
            raise ValidationError(message)


class OpenUploadFileReq(FlaskForm):
    """免登录上传文件请求，图片、文档、音频和视频走同一个接口"""
    file = FileField("file", validators=[
        FileRequired("上传文件不能为空"),
        MediaFileSize(),
        FileAllowed(
            _OPEN_UPLOAD_EXTENSIONS,
            message=f"仅允许上传{'/'.join(_OPEN_UPLOAD_EXTENSIONS)}文件",
        ),
    ])
    bot_id = StringField("bot_id", validators=[DataRequired("bot_id 不能为空")])
    bot_key = StringField("bot_key", validators=[DataRequired("bot_key 不能为空")])
    session_id = StringField("session_id", validators=[DataRequired("session_id 不能为空")])

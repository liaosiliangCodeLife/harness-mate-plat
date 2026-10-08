'''
* This is the projet for brtc R&D Platform
* @Author Leon-liao <liaosiliang@alltman.com>
* @Description 免授权上传客户端：POST /open-api/upload-file
* @File: file_upload.py
* @Time: 2026/10/07 20:12:00
* @All Rights Reserve By Brtc
'''

import json
import mimetypes
import os
import uuid
from pathlib import Path
from typing import Optional, Tuple
from urllib import error as urlerror
from urllib import request as urlrequest


MAX_UPLOAD_BYTES = 15 * 1024 * 1024
IMAGE_EXTENSIONS = frozenset({"jpg", "jpeg", "png", "webp", "gif", "svg"})
DOCUMENT_EXTENSIONS = frozenset(
    {"txt", "markdown", "md", "pdf", "html", "htm", "xlsx", "xls", "doc", "docx", "csv"}
)
ALLOWED_EXTENSIONS = IMAGE_EXTENSIONS | DOCUMENT_EXTENSIONS
OPEN_API_UPLOAD_PATH = "/api/open-api/upload-file"
DEFAULT_OPEN_API_UPLOAD_URL = "https://harness.alltman.com" + OPEN_API_UPLOAD_PATH
UPLOAD_TIMEOUT_SECONDS = 60.0


class OpenApiUploadError(Exception):
    """免授权上传失败。"""

    def __init__(self, message: str, *, retryable: bool = False):
        """
        * @Author Leon-liao
        * @Function: OpenApiUploadError.__init__(message, retryable)
        * @Description //记录上传失败原因，以及是否适合重试
        * @Date :2026/10/07 20:12:00
        * @Param: message: 失败提示；retryable: 网络类错误为 True
        * @return：无
        """
        super().__init__(message)
        self.message = message
        self.retryable = retryable


def extension_of(filename: str) -> str:
    """
    * @Author Leon-liao
    * @Function: extension_of(filename)
    * @Description //取文件扩展名，不含点，并转为小写
    * @Date :2026/10/07 20:12:00
    * @Param: filename: 文件名或路径
    * @return：扩展名；没有扩展名时返回空字符串
    """
    name = str(filename or "").rsplit("/", 1)[-1].rsplit("\\", 1)[-1]
    if "." not in name:
        return ""
    return name.rsplit(".", 1)[-1].lower()


def media_kind_for_name(filename: str) -> str:
    """
    * @Author Leon-liao
    * @Function: media_kind_for_name(filename)
    * @Description //按扩展名区分图片和普通文件
    * @Date :2026/10/07 20:12:00
    * @Param: filename: 文件名或路径
    * @return：图片返回 image，其余返回 file
    """
    if extension_of(filename) in IMAGE_EXTENSIONS:
        return "image"
    return "file"


def mime_type_for_name(filename: str) -> str:
    """
    * @Author Leon-liao
    * @Function: mime_type_for_name(filename)
    * @Description //根据文件名推测 MIME 类型
    * @Date :2026/10/07 20:12:00
    * @Param: filename: 文件名或路径
    * @return：MIME 字符串
    """
    guessed, _encoding = mimetypes.guess_type(str(filename or ""))
    if guessed:
        return guessed
    if extension_of(filename) in IMAGE_EXTENSIONS:
        return "image/jpeg"
    return "application/octet-stream"


def resolve_upload_url(explicit: str = "") -> str:
    """
    * @Author Leon-liao
    * @Function: resolve_upload_url(explicit)
    * @Description //解析免授权上传地址，主机只写域名时补上 /api/open-api/upload-file
    * @Date :2026/10/07 20:45:00
    * @Param: explicit: 配置项中的上传地址或主机，可为空
    * @return：完整的 POST 地址
    """
    candidate = str(explicit or "").strip()
    if not candidate:
        candidate = os.getenv("HARNESS_MATE_UPLOAD_URL", "").strip()
    if not candidate:
        candidate = DEFAULT_OPEN_API_UPLOAD_URL
    candidate = candidate.rstrip("/")
    legacy_suffix = "/open-api/upload-file"
    if candidate.endswith(OPEN_API_UPLOAD_PATH):
        return candidate
    if candidate.endswith(legacy_suffix):
        return candidate[: -len(legacy_suffix)] + OPEN_API_UPLOAD_PATH
    return candidate + OPEN_API_UPLOAD_PATH


def _safe_filename(filename: str) -> str:
    """
    * @Author Leon-liao
    * @Function: _safe_filename(filename)
    * @Description //去掉会破坏 multipart 头的字符，只保留文件名
    * @Date :2026/10/07 20:12:00
    * @Param: filename: 原始文件名
    * @return：可用于 Content-Disposition 的文件名
    """
    name = Path(str(filename or "")).name.replace('"', "").replace("\r", "").replace("\n", "")
    name = name.strip() or "upload.bin"
    return name


def prepare_upload_file(file_path: str) -> Tuple[str, bytes, str]:
    """
    * @Author Leon-liao
    * @Function: prepare_upload_file(file_path)
    * @Description //读取本地文件并校验扩展名与 15 MB 大小上限
    * @Date :2026/10/07 20:12:00
    * @Param: file_path: 本地文件路径
    * @return：(安全文件名, 文件字节, MIME)
    """
    path = Path(str(file_path or "")).expanduser()
    if not path.is_file():
        raise OpenApiUploadError("文件不存在")
    extension = extension_of(path.name)
    if extension not in ALLOWED_EXTENSIONS:
        shown = extension or "未知"
        raise OpenApiUploadError(f"该.{shown}扩展的文件不允许上传")
    content = path.read_bytes()
    if len(content) > MAX_UPLOAD_BYTES:
        raise OpenApiUploadError("文件大小不能超过 15 MB")
    if not content:
        raise OpenApiUploadError("文件内容不能为空")
    return _safe_filename(path.name), content, mime_type_for_name(path.name)


def _encode_multipart(
    fields: dict,
    filename: str,
    content: bytes,
    content_type: str,
) -> Tuple[bytes, str]:
    """
    * @Author Leon-liao
    * @Function: _encode_multipart(fields, filename, content, content_type)
    * @Description //组装 multipart/form-data，文件字段名为 file
    * @Date :2026/10/07 20:12:00
    * @Param: fields: 文本表单字段；filename: 文件名；content: 文件字节；content_type: MIME
    * @return：(请求体, boundary)
    """
    boundary = uuid.uuid4().hex
    chunks = []
    for key, value in fields.items():
        chunks.append(
            (
                f"--{boundary}\r\n"
                f'Content-Disposition: form-data; name="{key}"\r\n\r\n'
                f"{value}\r\n"
            ).encode("utf-8")
        )
    chunks.append(
        (
            f"--{boundary}\r\n"
            f'Content-Disposition: form-data; name="file"; filename="{filename}"\r\n'
            f"Content-Type: {content_type}\r\n\r\n"
        ).encode("utf-8")
    )
    chunks.append(content)
    chunks.append(f"\r\n--{boundary}--\r\n".encode("utf-8"))
    return b"".join(chunks), boundary


def parse_upload_response(raw: bytes) -> str:
    """
    * @Author Leon-liao
    * @Function: parse_upload_response(raw)
    * @Description //解析上传接口 JSON，成功时取出 data.url
    * @Date :2026/10/07 20:12:00
    * @Param: raw: 接口响应字节
    * @return：可访问的文件 URL
    """
    text = raw.decode("utf-8", errors="replace").lstrip()
    if text.startswith("<"):
        raise OpenApiUploadError("上传接口返回了网页而不是 JSON，请检查上传地址", retryable=False)
    try:
        payload = json.loads(text)
    except json.JSONDecodeError as exc:
        raise OpenApiUploadError("上传文件失败，请稍后重试", retryable=True) from exc
    if not isinstance(payload, dict):
        raise OpenApiUploadError("上传文件失败，请稍后重试", retryable=True)
    code = str(payload.get("code") or "").strip()
    message = str(payload.get("message") or "").strip() or "上传文件失败，请稍后重试"
    if code != "success":
        raise OpenApiUploadError(message, retryable=code not in {"validate_error", "not_found", "forbidden"})
    data = payload.get("data")
    url = ""
    if isinstance(data, dict):
        url = str(data.get("url") or "").strip()
    if not url:
        raise OpenApiUploadError("上传成功但未返回文件地址")
    return url


def _post_multipart(upload_url: str, body: bytes, boundary: str, timeout: float) -> bytes:
    """
    * @Author Leon-liao
    * @Function: _post_multipart(upload_url, body, boundary, timeout)
    * @Description //向免授权上传接口发送 multipart 请求，不附带 Authorization
    * @Date :2026/10/07 20:12:00
    * @Param: upload_url: 接口地址；body: 请求体；boundary: 分隔符；timeout: 超时秒数
    * @return：响应字节
    """
    req = urlrequest.Request(
        upload_url,
        data=body,
        method="POST",
        headers={
            "Content-Type": f"multipart/form-data; boundary={boundary}",
            "Accept": "application/json",
        },
    )
    try:
        with urlrequest.urlopen(req, timeout=timeout) as response:
            return response.read()
    except urlerror.HTTPError as exc:
        detail = exc.read()
        if detail:
            return detail
        raise OpenApiUploadError("上传文件失败，请稍后重试", retryable=True) from exc
    except urlerror.URLError as exc:
        raise OpenApiUploadError("上传文件失败，请稍后重试", retryable=True) from exc
    except TimeoutError as exc:
        raise OpenApiUploadError("上传文件失败，请稍后重试", retryable=True) from exc


def upload_open_api_file(
    file_path: str,
    bot_id: str,
    bot_key: str,
    session_id: str,
    upload_url: str = "",
    timeout: Optional[float] = None,
) -> str:
    """
    * @Author Leon-liao
    * @Function: upload_open_api_file(file_path, bot_id, bot_key, session_id, upload_url, timeout)
    * @Description //用智能体标识、网关密钥和会话标识把本地文件上传到对象存储
    * @Date :2026/10/07 20:12:00
    * @Param: file_path: 本地文件；bot_id: 智能体业务标识；bot_key: 网关密钥；session_id: 会话 ws_session_id；upload_url: 上传地址；timeout: 超时秒数
    * @return：上传后的可访问 URL
    """
    bot_id = str(bot_id or "").strip()
    bot_key = str(bot_key or "").strip()
    session_id = str(session_id or "").strip()
    if not bot_id:
        raise OpenApiUploadError("bot_id 不能为空")
    if not bot_key:
        raise OpenApiUploadError("bot_key 不能为空")
    if not session_id:
        raise OpenApiUploadError("session_id 不能为空")

    filename, content, content_type = prepare_upload_file(file_path)
    body, boundary = _encode_multipart(
        {"bot_id": bot_id, "bot_key": bot_key, "session_id": session_id},
        filename,
        content,
        content_type,
    )
    raw = _post_multipart(
        resolve_upload_url(upload_url),
        body,
        boundary,
        UPLOAD_TIMEOUT_SECONDS if timeout is None else timeout,
    )
    return parse_upload_response(raw)

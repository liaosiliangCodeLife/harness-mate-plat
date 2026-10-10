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
import tempfile
import time
import uuid
from pathlib import Path
from typing import Optional, Tuple
from urllib import error as urlerror
from urllib import request as urlrequest


MAX_UPLOAD_BYTES = 16 * 1024 * 1024
MAX_MEDIA_UPLOAD_BYTES = 1024 * 1024 * 1024
MAX_ARCHIVE_UPLOAD_BYTES = 100 * 1024 * 1024
IMAGE_EXTENSIONS = frozenset({"jpg", "jpeg", "png", "webp", "gif", "svg"})
DOCUMENT_EXTENSIONS = frozenset(
    {"txt", "markdown", "md", "pdf", "html", "htm", "xlsx", "xls", "doc", "docx", "csv"}
)
AUDIO_EXTENSIONS = {"mp3", "wav", "m4a", "aac", "flac", "ogg", "oga", "opus", "amr", "wma", "aiff", "mka"}
VIDEO_EXTENSIONS = {"mp4", "mov", "m4v", "avi", "mkv", "webm", "flv", "wmv", "mpeg", "mpg", "ts", "3gp"}
ARCHIVE_EXTENSIONS = {
    "zip", "rar", "7z", "tar", "gz", "tgz", "bz2", "tbz", "tbz2", "xz", "txz", "zst", "zipx", "cab", "jar", "war",
}
ALLOWED_EXTENSIONS = IMAGE_EXTENSIONS | DOCUMENT_EXTENSIONS | AUDIO_EXTENSIONS | VIDEO_EXTENSIONS | ARCHIVE_EXTENSIONS
OPEN_API_UPLOAD_PATH = "/api/open-api/upload-file"
DEFAULT_OPEN_API_UPLOAD_URL = "https://harness.alltman.com" + OPEN_API_UPLOAD_PATH
UPLOAD_TIMEOUT_SECONDS = 60.0
UPLOAD_MEDIA_TIMEOUT_SECONDS = 1800.0
_UPLOAD_COPY_CHUNK_BYTES = 1024 * 1024
_UPLOAD_MAX_ATTEMPTS = 4
_UPLOAD_RETRY_DELAYS = (0.5, 1.5, 3.0)


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
    * @Description //按扩展名区分图片、视频、音频和普通文件
    * @Date :2026/10/08 20:31:00
    * @Param: filename: 文件名或路径
    * @return：image、video、audio 或 file。图片优先，其次视频，再次音频
    """
    extension = extension_of(filename)
    if extension in IMAGE_EXTENSIONS:
        return "image"
    if extension in VIDEO_EXTENSIONS:
        return "video"
    if extension in AUDIO_EXTENSIONS:
        return "audio"
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
    kind = media_kind_for_name(filename)
    if kind == "image":
        return "image/jpeg"
    if kind == "audio":
        return "audio/mpeg"
    if kind == "video":
        return "video/mp4"
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


def prepare_upload_file(file_path: str) -> Tuple[str, str, int, str]:
    """
    * @Author Leon-liao
    * @Function: prepare_upload_file(file_path)
    * @Description //校验本地文件的扩展名与分级大小上限，不把内容读进内存
    * @Date :2026/10/08 20:31:00
    * @Param: file_path: 本地文件路径
    * @return：(安全文件名, 本地路径, 字节大小, MIME)
    """
    path = Path(str(file_path or "")).expanduser()
    if not path.is_file():
        raise OpenApiUploadError("文件不存在")
    extension = extension_of(path.name)
    if extension not in ALLOWED_EXTENSIONS:
        shown = extension or "未知"
        raise OpenApiUploadError(f"该.{shown}扩展的文件不允许上传")
    size = os.path.getsize(path)
    if size <= 0:
        raise OpenApiUploadError("文件内容不能为空")
    kind = media_kind_for_name(path.name)
    if kind in {"audio", "video"}:
        if size > MAX_MEDIA_UPLOAD_BYTES:
            raise OpenApiUploadError("音视频大小不能超过 1024 MB")
    elif extension in ARCHIVE_EXTENSIONS:
        if size > MAX_ARCHIVE_UPLOAD_BYTES:
            raise OpenApiUploadError("压缩包最大不能超过100MB")
    elif size > MAX_UPLOAD_BYTES:
        raise OpenApiUploadError("文件大小不能超过 16 MB")
    return _safe_filename(path.name), str(path), size, mime_type_for_name(path.name)


def _write_multipart_file(
    fields: dict,
    filename: str,
    source_path: str,
    content_type: str,
) -> Tuple[str, str, int]:
    """
    * @Author Leon-liao
    * @Function: _write_multipart_file(fields, filename, source_path, content_type)
    * @Description //把 multipart 写到临时文件，文件内容按块拷贝，避免整段进内存
    * @Date :2026/10/08 20:31:00
    * @Param: fields: 文本表单字段；filename: 文件名；source_path: 本地文件路径；content_type: MIME
    * @return：(临时文件路径, boundary, 请求体字节长度)。调用方负责删除临时文件
    """
    boundary = uuid.uuid4().hex
    temp = tempfile.NamedTemporaryFile(delete=False)
    temp_path = temp.name
    try:
        for key, value in fields.items():
            temp.write(
                (
                    f"--{boundary}\r\n"
                    f'Content-Disposition: form-data; name="{key}"\r\n\r\n'
                    f"{value}\r\n"
                ).encode("utf-8")
            )
        temp.write(
            (
                f"--{boundary}\r\n"
                f'Content-Disposition: form-data; name="file"; filename="{filename}"\r\n'
                f"Content-Type: {content_type}\r\n\r\n"
            ).encode("utf-8")
        )
        with open(source_path, "rb") as source:
            while True:
                chunk = source.read(_UPLOAD_COPY_CHUNK_BYTES)
                if not chunk:
                    break
                temp.write(chunk)
        temp.write(f"\r\n--{boundary}--\r\n".encode("utf-8"))
        temp.flush()
        content_length = temp.tell()
    except Exception:
        temp.close()
        try:
            os.remove(temp_path)
        except OSError:
            pass
        raise
    temp.close()
    return temp_path, boundary, content_length


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


def _post_multipart(
    upload_url: str,
    body_path: str,
    boundary: str,
    content_length: int,
    timeout: float,
) -> bytes:
    """
    * @Author Leon-liao
    * @Function: _post_multipart(upload_url, body_path, boundary, content_length, timeout)
    * @Description //把临时文件当作请求体发给免授权上传接口，并带上 Content-Length
    * @Date :2026/10/08 20:31:00
    * @Param: upload_url: 接口地址；body_path: multipart 临时文件；boundary: 分隔符；content_length: 请求体长度；timeout: 超时秒数
    * @return：响应字节
    """
    with open(body_path, "rb") as body:
        req = urlrequest.Request(
            upload_url,
            data=body,
            method="POST",
            headers={
                "Content-Type": f"multipart/form-data; boundary={boundary}",
                "Content-Length": str(content_length),
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


def _resolve_timeout(filename: str, timeout: Optional[float]) -> float:
    """
    * @Author Leon-liao
    * @Function: _resolve_timeout(filename, timeout)
    * @Description //未指定超时时，音视频用 1800 秒，其它文件用 60 秒
    * @Date :2026/10/08 20:31:00
    * @Param: filename: 上传文件名；timeout: 调用方指定的秒数，None 表示按类型选择
    * @return：实际使用的超时秒数
    """
    if timeout is not None:
        return timeout
    if media_kind_for_name(filename) in {"audio", "video"}:
        return UPLOAD_MEDIA_TIMEOUT_SECONDS
    return UPLOAD_TIMEOUT_SECONDS


def _upload_error_reason(exc: BaseException) -> str:
    """
    * @Author Leon-liao
    * @Function: _upload_error_reason(exc)
    * @Description //取出最后一次上传失败的底层原因，供重试耗尽后的提示使用
    * @Date :2026/10/08 22:08:00
    * @Param: exc: 最后一次失败的异常，可能是 URLError、TimeoutError 或 OpenApiUploadError
    * @return：可读的原因字符串
    """
    current = exc.__cause__ if isinstance(exc, OpenApiUploadError) and exc.__cause__ is not None else exc
    if isinstance(current, urlerror.URLError) and current.reason is not None:
        return str(current.reason)
    if isinstance(current, OpenApiUploadError):
        return current.message
    return str(current)


def _read_http_error_body(exc: urlerror.HTTPError) -> bytes:
    """
    * @Author Leon-liao
    * @Function: _read_http_error_body(exc)
    * @Description //读取 HTTP 错误响应体；读不到或为空时返回空字节，表示这次请求没有业务 JSON
    * @Date :2026/10/08 22:08:00
    * @Param: exc: urllib 抛出的 HTTPError
    * @return：响应体字节；没有内容时为空字节串
    """
    try:
        detail = exc.read()
    except Exception:
        return b""
    if not detail:
        return b""
    return detail


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
    * @Description //用智能体标识、网关密钥和会话标识把本地文件上传到对象存储。连接被对端断开这类网络失败会自动重试，服务端业务错误不重试
    * @Date :2026/10/08 22:08:00
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

    filename, local_path, _size, content_type = prepare_upload_file(file_path)
    body_path = ""
    try:
        body_path, boundary, content_length = _write_multipart_file(
            {"bot_id": bot_id, "bot_key": bot_key, "session_id": session_id},
            filename,
            local_path,
            content_type,
        )
        request_timeout = _resolve_timeout(filename, timeout)
        resolved_url = resolve_upload_url(upload_url)
        last_error: Optional[BaseException] = None
        for attempt in range(_UPLOAD_MAX_ATTEMPTS):
            try:
                raw = _post_multipart(
                    resolved_url,
                    body_path,
                    boundary,
                    content_length,
                    request_timeout,
                )
                return parse_upload_response(raw)
            except urlerror.HTTPError as exc:
                detail = _read_http_error_body(exc)
                if detail:
                    try:
                        return parse_upload_response(detail)
                    except OpenApiUploadError as parsed:
                        if not parsed.retryable:
                            raise
                        last_error = parsed
                else:
                    last_error = exc
            except urlerror.URLError as exc:
                last_error = exc
            except TimeoutError as exc:
                last_error = exc
            except OpenApiUploadError as exc:
                if not exc.retryable:
                    raise
                last_error = exc
            if attempt < _UPLOAD_MAX_ATTEMPTS - 1:
                time.sleep(_UPLOAD_RETRY_DELAYS[attempt])
        reason = _upload_error_reason(last_error) if last_error is not None else ""
        raise OpenApiUploadError(
            f"上传文件失败，请稍后重试（已重试 {_UPLOAD_MAX_ATTEMPTS - 1} 次，最后错误：{reason}）",
            retryable=True,
        ) from last_error
    finally:
        if body_path:
            try:
                os.remove(body_path)
            except OSError:
                pass

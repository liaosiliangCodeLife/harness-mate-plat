# HermesMate - API 文档

应用 API 接口统一以 JSON 格式返回，并且包含 3 个字段：`code`、`data` 和 `message`，分别代表`业务状态码`、`业务数据`和`接口附加信息`。

`业务状态码`共有 6 种，其中只有 `success(成功)` 代表业务操作成功，其他 5 种状态均代表失败，并且失败时会附加相关的信息：`fail(通用失败)`、`not_found(未找到)`、`unauthorized(未授权)`、`forbidden(无权限)`和`validate_error(数据验证失败)`。

接口示例：

```json
{
    "code": "success",
    "data": {
        "redirect_url": "https://github.com/login/oauth/authorize?client_id=f69102c6b97d90d69768&redirect_uri=http%3A%2F%2Flocalhost%3A5001%2Foauth%2Fauthorize%2Fgithub&scope=user%3Aemail"
    },
    "message": ""
}
```

带有分页数据的接口会在 `data` 内固定传递 `list` 和 `paginator` 字段，其中 `list` 代表分页后的列表数据，`paginator` 代表分页的数据。

`paginator` 内存在 4 个字段：`current_page(当前页数)` 、`page_size(每页数据条数)`、`total_page(总页数)`、`total_record(总记录条数)`，示例数据如下：

```json
{
    "code": "success",
    "data": {
        "list": [
            {
                "app_count": 0,
                "created_at": 1713105994,
                "description": "这是专门用来存储博睿LLMOps课程信息的知识库",
                "document_count": 13,
                "icon": "https://imooc-llmops-1257184990.cos.ap-guangzhou.myqcloud.com/2024/04/07/96b5e270-c54a-4424-aece-ff8a2b7e4331.png",
                "id": "c0759ca8-2d35-4480-83a8-1f41f29d1401",
                "name": "博睿LLMOps课程知识库",
                "updated_at": 1713106758,
                "word_count": 8850
            }
        ],
        "paginator": {
            "current_page": 1,
            "page_size": 20,
            "total_page": 1,
            "total_record": 2
        }
    },
    "message": ""
}
```

如果接口需要授权，需要在 `headers` 中添加 `Authorization` ，并附加 `access_token` 即可完成授权登录，示例：

```json
Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJleHAiOjE3MTY0NTY3OTgsImlzcyI6ImxsbW9wcyIsInN1YiI6ImM5MDljMWRiLWIyMmUtNGZlNi04OGIyLWIyZTkxZWFiMWE3YiJ9.JDAtWDBBGiXa_XFihfopRe4Cz-RQ9_TAcno9w81tNbE
```

## 01. 文件上传模块

### 1.1 将文件上传到腾讯云cos

- **接口说明**：将文件上传到腾讯云对象存储中，该接口主要用于上传文件，调用接口后返回对应的文件 id、名字、云端位置等信息。

- **接口信息**：`授权`+`POST:/upload-files/file`

- **接口参数**：

  - 请求参数：
    - `file -> File`：需要上传的文件，最多支持上传一个文件，最大支持的文件不能超过 15 MB。
  - 响应参数：
    - `id -> uuid`：上传文件的引用 id，类型为 uuid，后续业务接口会使用该引用文件 id。
    - `account_id -> uuid`：该文件所归属的账号 id，用于标记是哪个账号上传了该文件。
    - `name -> str`：原始文件名字。
    - `key -> str`：云端文件对应的 key 或者路径。
    - `size -> int`：文件大小，单位为字节。
    - `extension -> str`：文件的扩展名，例如 `.md`。
    - `mime_type -> str`：文件 mime-type 类型推断。
    - `created_at -> str`：文件的创建时间戳。
    - `url -> str`：上传文件对应的可访问 URL 链接。

- **响应示例**：

  ```json
  {
      "code": "success",
      "data": {
          "id": "46db30d1-3199-4e79-a0cd-abf12fa6858f",
          "account_id": "e1baf52a-1be2-4b93-ad62-6fad72f1ec37",
          "name": "项目API文档.md",
          "key": "2024/05/14/218e5217-ab10-4634-9681-022867955f1b.md",
          "size": 30241,
          "extension": ".md",
          "mime_type": "txt",
          "created_at": 1721460914,
          "url": "https://cdn.imooc.com/2024/05/14/218e5217-ab10-4634-9681-022867955f1b.md"
      },
      "message": ""
  }
  ```

### 1.2 将图片上传到腾讯云cos

- **接口说明**：将图片上传到腾讯云 cos 对象存储中，该接口用于需要上传图片的模块，接口会返回图片的 URL 地址。

- **接口信息**：`授权`+`POST:/upload-files/image`

- **接口参数**：

  - 请求参数：
    - `file -> File`：需要上传的图片文件，支持上传 jpg、jpeg、png、gif，最大不能超过 15 MB。
  - 响应参数：
    - `image_url -> str`：上传图片对应的 URL 链接。

- **响应示例**：

  ```json
  {
      "code": "success",
      "data": {
          "image_url": "https://cdn.imooc.com/2024/05/14/218e5217-ab10-4634-9681-022867955f1b.png"
      },
      "message": ""
  }
  ```

### 1.3 通过 bot_id/bot_key/session_id 上传文件（免授权）

- **接口说明**：免登录把文件上传到腾讯云对象存储。图片和其它允许的文件走同一个接口，不需要 `Authorization`。调用方用智能体业务标识、网关密钥和会话标识证明文件属于该智能体的当前会话，上传记录挂到该智能体所属账号。

- **接口信息**：`免授权`+`POST:/open-api/upload-file`

- **接口参数**：

  - 请求参数（`multipart/form-data`）：
    - `file -> File`：需要上传的文件，图片也可以，最多支持上传一个文件。支持的文件类型为图片（jpg、jpeg、png、webp、gif、svg）、文档（txt、markdown、md、pdf、html、htm、xlsx、xls、doc、docx、csv）、音频（mp3、wav、m4a、aac、flac、ogg、oga、opus、amr、wma、aiff、mka）、视频（mp4、mov、m4v、avi、mkv、webm、flv、wmv、mpeg、mpg、ts、3gp）。大小限制：普通文件 16MB，音视频 1024MB。
    - `bot_id -> str`：智能体业务标识，不能为空。
    - `bot_key -> str`：网关密钥，必须与该智能体所属网关的 `gateway_key` 完全一致，不能为空。
    - `session_id -> str`：会话标识，必须与该智能体下未删除会话的 `ws_session_id` 完全一致，不能为空。
  - 响应参数：
    - `url -> str`：上传文件对应的可访问 URL 链接。

- **失败提示**：

  - `bot_id`、`bot_key`、`session_id` 任一为空：参数校验失败（`validate_error`），分别提示「bot_id 不能为空」「bot_key 不能为空」「session_id 不能为空」。
  - 按 `bot_id` 查不到未删除智能体：「bot_id 对应的智能体不存在」。
  - 智能体没有关联网关，或网关 `gateway_key` 与传入 `bot_key` 不一致：「bot_key 校验失败」。
  - 按 `session_id` 查不到未删除会话，或会话不属于该智能体：「session_id 对应的会话不存在或不属于该智能体」。

- **响应示例**：

  ```json
  {
      "code": "success",
      "data": {
          "url": "https://cdn.imooc.com/2024/05/14/218e5217-ab10-4634-9681-022867955f1b.md"
      },
      "message": ""
  }
  ```

## 02. 授权认证模块

### 2.1 获取指定第三方授权服务的重定向地址

- **接口说明**：用于获取指定的第三方授权方案的重定向地址，例如 Github、Google 等。

- **接口信息**：`无需授权`+`GET:/oauth/:provider_name`

- **接口参数**：

  - 请求参数：
    - `provider_name -> str`：第三方授权服务提供商名字，例如 `github`、`google`。
  - 响应参数：
    - `redirect_url -> str`：指定第三方授权服务重定向地址。

- **请求示例**：

  ```bash
  GET:/oauth/github
  ```

- **响应示例**：

  ```json
  {
      "code": "success",
      "data": {
          "redirect_url": "http://github.com/oauth/xxx"
      },
      "message": ""
  }
  ```

### 2.2 指定第三方授权服务的授权地址

- **接口说明**：用于第三方授权服务确认后的回调地址，例如 `github` 授权登录后，会跳转回 LLMOps 平台，并携带相关的 `code` 标识，用于在后端获取对应用户的授权凭证。

- **接口信息**：`无需授权`+`POST:/oauth/authorize/:provider_name`

- **接口参数**：

  - 请求参数：
    - `provider_name -> str`：路由参数，指定的第三方授权服务提供商名字，例如 `github`、`google` 等。
    - `code -> str`：第三方授权服务提供的 `code` 编码，用于后端获取该平台的授权信息（邮箱、OpenID等）。
  - 响应参数：
    - `access_token -> str`：jwt 授权令牌信息。
    - `expire_at -> int`：授权令牌的过期时间，单位为秒。

- **请求示例**：

  ```bash
  POST:/oauth/callback/github
  
  {
  	"code": "XKq425OjBETb6GAN"
  }
  ```

- **响应示例**：

  ```json
  {
      "code": "success",
      "data": {
          "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiIxMjM0NTY3ODkwIiwibmFtZSI6IkpvaG4gRG9lIiwiaWF0IjoxNTE2MjM5MDIyfQ.SflKxwRJSMeKKF2QT4fwpMeJf36POk6yJV_adQssw5c",
          "expire_at": 1730712246
      },
      "message": ""
  }
  ```

### 2.3 账号密码登录

- **接口说明**：使用账号/邮箱+密码登录 LLMOps 平台 API 接口。

- **接口信息**：`无需授权`+`POST:/auth/password-login`

- **接口参数**：

  - 请求参数：
    - `email -> str`：登录的账号邮箱，类型为字符串，邮箱长度在 254 个字符内。
    - `password -> str`：登录的账号密码，类型为字符串，密码长度在 8-16 位，最少包含一个字母、一个数字。
  - 响应参数：
    - `access_token -> str`：jwt 授权令牌信息。
    - `expire_at -> int`：授权令牌的过期时间，单位为秒。

- **请求示例**：

  ```bash
  POST:/auth/password-login
  
  {
  	"email": "zehuiya@163.com",
  	"password": "imooc.com@zehuiya"
  }
  ```

- **响应示例**：

  ```json
  {
      "code": "success",
      "data": {
          "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiIxMjM0NTY3ODkwIiwibmFtZSI6IkpvaG4gRG9lIiwiaWF0IjoxNTE2MjM5MDIyfQ.SflKxwRJSMeKKF2QT4fwpMeJf36POk6yJV_adQssw5c",
          "expire_at": 1730712246
      },
      "message": ""
  }
  ```

### 2.4 退出当前登录账号

- **接口说明**：用于退出当前登录的账号信息，退出账号后，在后端可以选择性执行多种方案，例如将该 token 添加到 redis 缓存中并设置过期时间（黑名单），亦或者是什么都不处理，单纯在前端清空授权凭证。

- **接口信息**：`授权`+`POST:/auth/logout`

- **接口参数**：无

- **请求示例**：

  ```bash
  POST:/auth/logout
  ```

- **响应示例**：

  ```json
  {
      "code": "success",
      "data": {},
      "message": "退出当前账号成功"
  }
  ```

### 2.5 发送注册验证码

- **接口说明**：向未注册邮箱发送 6 位数字注册验证码。验证码写入 Redis，15 分钟内有效；同一邮箱 60 秒内不能重复发送。不需要登录。

- **接口信息**：`无需授权`+`POST:/auth/register-code`

- **接口参数**：

  - 请求参数：
    - `email -> str`：注册邮箱，类型为字符串，不能为空，格式必须合法，长度在 5-254 个字符。
  - 响应参数：
    - `expire_in -> int`：验证码有效时间，单位为秒，固定为 900。

- **失败提示**：

  - 邮箱为空：「邮箱不能为空」。
  - 邮箱格式不合法：「邮箱格式错误」。
  - 邮箱已注册：「该邮箱已注册，请直接登录」。
  - 60 秒内重复发送：「验证码已发送，请 60 秒后再试」。

- **请求示例**：

  ```bash
  POST:/auth/register-code
  
  {
  	"email": "zehuiya@163.com"
  }
  ```

- **响应示例**：

  ```json
  {
      "code": "success",
      "data": {
          "expire_in": 900
      },
      "message": ""
  }
  ```

### 2.6 邮箱注册

- **接口说明**：使用邮箱、验证码和密码注册账号。验证码核对通过后立即失效，只能使用一次。密码按登录接口同一套加盐哈希保存。注册成功不返回 token，需要再调用账号密码登录。

- **接口信息**：`无需授权`+`POST:/auth/register`

- **接口参数**：

  - 请求参数：
    - `email -> str`：注册邮箱，类型为字符串，不能为空，格式必须合法。
    - `code -> str`：6 位数字验证码，类型为字符串，不能为空。
    - `password -> str`：登录密码，类型为字符串，长度 8-16 位，且必须同时包含字母和数字。
    - `password_confirm -> str`：确认密码，类型为字符串，必须与 `password` 一致。
  - 响应参数：无。成功时 `message` 为「注册成功」，`data` 为空对象。

- **失败提示**：

  - 字段为空：分别提示「邮箱不能为空」「验证码不能为空」「密码不能为空」「确认密码不能为空」。
  - 两次密码不一致：「两次输入的密码不一致」。
  - 密码不符合规则：「密码长度为8-16位，且必须同时包含字母和数字」。
  - 验证码已过期或不存在：「验证码已过期，请重新获取」。
  - 验证码不正确：「验证码错误」。
  - 邮箱已注册：「该邮箱已注册，请直接登录」。

- **请求示例**：

  ```bash
  POST:/auth/register
  
  {
  	"email": "zehuiya@163.com",
  	"code": "123456",
  	"password": "imooc123",
  	"password_confirm": "imooc123"
  }
  ```

- **响应示例**：

  ```json
  {
      "code": "success",
      "data": {},
      "message": "注册成功"
  }
  ```

## 03. 账号设置模块

### 3.1 获取当前登录账号信息

- **接口说明**：该接口主要用于获取当前登录账号的信息，例如 `id`、`账号名称`、`头像`、`邮箱` 等信息。

- **接口信息**：`授权`+`GET:/account`

- **接口参数**：

  - 响应参数：
    - `id -> uuid`：账号 id，类型为 uuid。
    - `name -> str`：账号昵称，类型为字符串。
    - `email -> str`：账号邮箱，类型为字符串。
    - `avatar -> str`：账号的头像 URL 地址，类型为字符串。
    - `last_login_at -> int`：账号最后一次登录时间戳，类型为整型，单位为秒。
    - `last_login_ip -> str`：账号最后一次登录的 ip 地址，类型为字符串。
    - `created_at -> int`：账号的注册时间戳，类型为整型。

- **请求示例**：

  ```bash
  GET:/account
  ```

- **响应示例**：

  ```json
  {
      "code": "success",
      "data": {
          "id": "1550b71a-1444-47ed-a59d-c2f080fbae94",
          "name": "泽辉呀",
          "email": "zehuiya@163.com",
          "avatar": "https://cdn.imooc.com/2024/05/14/218e5217-ab10-4634-9681-022867955f1b.png",
          "last_login_at": 1721460914,
          "last_login_ip": "115.141.210.41",
          "created_at": 1721460914
      },
      "message": ""
  }
  ```

### 3.2 修改当前登录账号密码

- **接口说明**：该接口用于修改当前登录的账号对应的密码，密码的长度在 8-16 位，并且至少包含一个字母、一个数字。

- **接口信息**：`授权`+`POST:/account/password`

- **接口参数**：

  - 请求参数：
    - `password -> str`：账户的新密码，密码的长度在 8-16 位，并且至少包含一个字母、一个数字。

- **请求示例**：

  ```bash
  POST:/account/password
  
  {
      "password": "imooc.com@zehuiya"
  }
  ```

- **响应示例**：

  ```json
  {
      "code": "success",
      "data": {},
      "message": "修改当前登录账号密码成功"
  }
  ```

### 3.3 修改当前登录账号名称

- **接口说明**：该接口主要用于修改当前登录账号的名称，名称长度在 3-30 个字符。

- **接口信息**：`授权`+`POST:/account/name`

- **接口参数**：

  - 请求参数：
    - `name -> str`：新的账号名称，名称长度在 3-30 个字符。

- **请求示例**：

  ```bash
  POST:/account/name
  
  {
  	"name": "泽辉呀"
  }
  ```

- **响应示例**：

  ```json
  {
      "code": "success",
      "data": {},
      "message": "修改账号名称成功"
  }
  ```

### 3.4 修改当前登录账号头像

- **接口说明**：该接口主要用于修改当前登录账号的头像信息。

- **接口信息**：`授权`+`POST:/account/avatar`

- **接口参数**：

  - 请求参数：
    - `avatar -> str`：账号新头像的 URL 地址，类型为字符串。

- **请求示例**：

  ```bash
  POST:/account/avatar
  
  {
  	"avatar": "https://cdn.imooc.com/2024/05/14/218e5217-ab10-4634-9681-022867955f1b.png"
  }
  ```

- **响应示例**：

  ```json
  {
      "code": "success",
      "data": {},
      "message": "修改账号头像成功"
  }
  ```

## 04. 智能体模块

### 4.1 获取智能体分页列表

- **接口说明**：该接口用于分页获取当前登录账号下的智能体列表，支持按智能体名称进行模糊搜索，分页数据固定返回 `list` 和 `paginator` 字段；列表项里的 `gateway_url` 与 `gateway_key` 取自该智能体关联的 WS 网关（`agent.gateway_id` → `server.id`），未关联网关时返回空字符串。

- **接口信息**：`授权`+`GET:/agents`

- **接口参数**：

  - 请求参数：
    - `current_page -> int`：可选参数，当前页数，默认为 1，类型为整型。
    - `page_size -> int`：可选参数，每页数据条数，默认为 20，范围为 10-50。
    - `search_word -> string`：可选参数，搜索词，在后端会使用智能体的名称进行模糊匹配。
  - 响应参数：
    - `list -> list[dict]`：分页后的列表数据，类型为字典列表。
      - `id -> uuid`：智能体的 id，类型为 uuid。
      - `account_id -> uuid`：智能体归属的账号 id，类型为 uuid。
      - `peer_id -> str`：对端设备标识，标记智能体挂在哪台网关或设备上，类型为字符串。
      - `bot_id -> str`：智能体业务标识，全局唯一，由对端上报，类型为字符串。
      - `name -> str`：智能体名称，用于列表和详情展示，类型为字符串。
      - `avatar -> str`：智能体头像的 URL 地址，类型为字符串。
      - `agent_info -> dict`：智能体扩展信息，类型为字典，默认为 `{}`。
      - `status -> int`：智能体在线状态，直接读 `agent.status` 列，`0` 代表离线、`1` 代表在线，类型为整型。由 `POST /agents/:agent_id/online-status` 写入，打开页面时不做实时计算。
      - `conversation_count -> int`：该智能体的会话数量，类型为整型。
      - `total_token_count -> int`：该智能体累计消耗的 Token 数量，类型为整型。
      - `last_seen_at -> int`：智能体最后活跃时间戳，类型为整型，尚未活跃时为 `null`。
      - `gateway_url -> str`：智能体网关的 WebSocket 地址，取自关联网关的 `server.gateway_url`，类型为字符串。
      - `gateway_key -> str`：智能体网关的访问密钥，取自关联网关的 `server.gateway_key`，客户端连接网关时用于鉴权，类型为字符串。
      - `updated_at -> int`：智能体更新时间，类型为时间戳。
      - `created_at -> int`：智能体创建时间，类型为时间戳。
    - `paginator -> dict`：分页器信息，类型为字典。
      - `current_page -> int`：当前页数，类型为整型。
      - `page_size -> int`：每页的条数，类型为整型。
      - `total_page -> int`：数据的总页数，类型为整型。
      - `total_record -> int`：数据的总记录条数，类型为整型。

- **请求示例**：

  ```bash
  GET:/agents?current_page=1&page_size=20&search_word=助手
  ```

- **响应示例**：

  ```json
  {
      "code": "success",
      "data": {
          "list": [
              {
                  "id": "1550b71a-1444-47ed-a59d-c2f080fbae94",
                  "account_id": "e1baf52a-1be2-4b93-ad62-6fad72f1ec37",
                  "peer_id": "peer_iphone15",
                  "bot_id": "hermes_001",
                  "name": "客服小助手",
                  "avatar": "https://cdn.example.com/avatar/agent.png",
                  "agent_info": {},
                  "status": 1,
                  "conversation_count": 12,
                  "total_token_count": 30210,
                  "last_seen_at": 1721460914,
                  "gateway_url": "wss://gateway.example.com/ws",
                  "gateway_key": "example-gateway-key",
                  "updated_at": 1721460914,
                  "created_at": 1721460914
              }
          ],
          "paginator": {
              "current_page": 1,
              "page_size": 20,
              "total_page": 1,
              "total_record": 1
          }
      },
      "message": ""
  }
  ```

### 4.2 获取智能体详情

- **接口说明**：该接口用于获取指定智能体的详细信息，包含智能体的基础信息、在线状态与 Token 消耗统计等内容；`gateway_url` 与 `gateway_key` 取自该智能体关联的 WS 网关（`agent.gateway_id` → `server.id`），未关联网关时返回空字符串。

- **接口信息**：`授权`+`GET:/agents/:agent_id`

- **接口参数**：

  - 请求参数：
    - `agent_id -> uuid`：路由参数，需要获取详情的智能体 id，类型为 uuid。
  - 响应参数：
    - `id -> uuid`：智能体的 id，类型为 uuid。
    - `account_id -> uuid`：智能体归属的账号 id，类型为 uuid。
    - `peer_id -> str`：对端设备标识，标记智能体挂在哪台网关或设备上，类型为字符串。
    - `bot_id -> str`：智能体业务标识，全局唯一，由对端上报，类型为字符串。
    - `name -> str`：智能体名称，类型为字符串。
    - `avatar -> str`：智能体头像的 URL 地址，类型为字符串。
    - `agent_info -> dict`：智能体扩展信息，类型为字典，默认为 `{}`。
    - `status -> int`：智能体在线状态，直接读 `agent.status` 列，`0` 代表离线、`1` 代表在线，类型为整型。由 `POST /agents/:agent_id/online-status` 写入，打开页面时不做实时计算。
    - `conversation_count -> int`：该智能体的会话数量，类型为整型。
    - `total_token_count -> int`：该智能体累计消耗的 Token 数量，类型为整型。
    - `last_seen_at -> int`：智能体最后活跃时间戳，类型为整型，尚未活跃时为 `null`。
    - `gateway_url -> str`：智能体网关的 WebSocket 地址，取自关联网关的 `server.gateway_url`，类型为字符串。
    - `gateway_key -> str`：智能体网关的访问密钥，取自关联网关的 `server.gateway_key`，客户端连接网关时用于鉴权，类型为字符串。
    - `updated_at -> int`：智能体更新时间，类型为时间戳。
    - `created_at -> int`：智能体创建时间，类型为时间戳。

- **请求示例**：

  ```bash
  GET:/agents/1550b71a-1444-47ed-a59d-c2f080fbae94
  ```

- **响应示例**：

  ```json
  {
      "code": "success",
      "data": {
          "id": "1550b71a-1444-47ed-a59d-c2f080fbae94",
          "account_id": "e1baf52a-1be2-4b93-ad62-6fad72f1ec37",
          "peer_id": "peer_iphone15",
          "bot_id": "hermes_001",
          "name": "客服小助手",
          "avatar": "https://cdn.example.com/avatar/agent.png",
          "agent_info": {},
          "status": 1,
          "conversation_count": 12,
          "total_token_count": 30210,
          "last_seen_at": 1721460914,
          "gateway_url": "wss://gateway.example.com/ws",
          "gateway_key": "example-gateway-key",
          "updated_at": 1721460914,
          "created_at": 1721460914
      },
      "message": ""
  }
  ```

### 4.3 创建智能体

- **接口说明**：该接口用于在当前登录账号下创建智能体。智能体的业务标识 `bot_id` 全局唯一，由对端（客户端）上报，重复创建相同 `bot_id` 的智能体时会抛出错误信息。

- **接口信息**：`授权`+`POST:/agents`

- **接口参数**：

  - 请求参数：
    - `bot_id -> str`：智能体业务标识，全局唯一，由对端上报，类型为字符串。
    - `peer_id -> str`：对端设备标识，标记智能体挂载的设备或网关，类型为字符串。
    - `name -> str`：智能体名称，类型为字符串。
    - `avatar -> str`：可选参数，智能体头像的 URL 地址，类型为字符串。
    - `agent_info -> dict`：可选参数，智能体扩展信息，类型为字典，默认为 `{}`。
    - `gateway_id -> uuid`：可选参数，智能体关联的 WS 网关 id（对应 `server.id`），类型为 uuid，必须是当前登录账号下的网关。
  - 响应参数：
    - `id -> uuid`：创建的智能体 id，类型为 uuid。

- **请求示例**：

  ```bash
  POST:/agents
  
  {
  	"bot_id": "hermes_001",
  	"peer_id": "peer_iphone15",
  	"name": "客服小助手",
  	"avatar": "https://cdn.example.com/avatar/agent.png",
  	"gateway_id": "9c7e4b2a-1d3f-4a5b-8c6e-2f0d9b7a4e13"
  }
  ```

- **响应示例**：

  ```json
  {
      "code": "success",
      "data": {
          "id": "1550b71a-1444-47ed-a59d-c2f080fbae94"
      },
      "message": "创建智能体成功"
  }
  ```

### 4.4 修改智能体

- **接口说明**：该接口用于修改指定智能体的基础信息，该接口为 `增量更新`，可以只传递需要更新的字段信息，例如 `name`、`avatar`、`agent_info` 等；智能体的业务标识 `bot_id` 与设备标识 `peer_id` 不支持修改。其中 `agent_info` 为整体替换：本次提交的对象即最终值，未包含的键会被删除；提交 `{}` 可清空；不提交该字段则保持原值不变。

- **接口信息**：`授权`+`POST:/agents/:agent_id`

- **接口参数**：

  - 请求参数：
    - `agent_id -> uuid`：路由参数，需要修改的智能体 id，类型为 uuid。
    - `name -> str`：可选参数，智能体的新名称，类型为字符串。
    - `avatar -> str`：可选参数，智能体新头像的 URL 地址，类型为字符串。
    - `agent_info -> dict`：可选参数，智能体扩展信息，类型为字典。整体替换：本次提交的对象即最终值，未包含的键会被删除；提交 `{}` 可清空；不提交该字段则保持原值不变。
    - `gateway_id -> uuid`：可选参数，智能体关联的 WS 网关 id（对应 `server.id`），类型为 uuid，必须是当前登录账号下的网关。
  - 响应参数：无。

- **请求示例**：

  ```bash
  POST:/agents/1550b71a-1444-47ed-a59d-c2f080fbae94
  
  {
  	"name": "客服小助手（新）"
  }
  ```

- **响应示例**：

  ```json
  {
      "code": "success",
      "data": {},
      "message": "修改智能体成功"
  }
  ```

### 4.5 删除智能体

- **接口说明**：该接口用于删除指定的智能体，删除后该智能体将无法被查看和使用，该操作不影响已经产生的会话与消息数据。

- **接口信息**：`授权`+`POST:/agents/:agent_id/delete`

- **接口参数**：

  - 请求参数：
    - `agent_id -> uuid`：路由参数，需要删除的智能体 id，类型为 uuid。
  - 响应参数：无。

- **请求示例**：

  ```bash
  POST:/agents/1550b71a-1444-47ed-a59d-c2f080fbae94/delete
  ```

- **响应示例**：

  ```json
  {
      "code": "success",
      "data": {},
      "message": "删除智能体成功"
  }
  ```

### 4.5.1 更新智能体在线状态

- **接口说明**：该接口用于把指定智能体的在线状态写入 `agent.status`。最近一次对话成功时写 `1`（在线），对话失败或智能体没有反应时写 `0`（离线）。列表和详情直接读这一列，不做 90 秒时间窗计算。

- **接口信息**：`授权`+`POST:/agents/:agent_id/online-status`

- **接口参数**：

  - 请求参数：
    - `agent_id -> uuid`：路由参数，需要更新在线状态的智能体 id，类型为 uuid。
    - `status -> int`：必填，只能是整数 `0` 或 `1`。`0` 代表离线，`1` 代表在线。
  - 响应参数：
    - `status -> int`：写入后的在线状态，类型为整型。

- **请求示例**：

  ```bash
  POST:/agents/1550b71a-1444-47ed-a59d-c2f080fbae94/online-status
  
  {
  	"status": 1
  }
  ```

- **响应示例**：

  ```json
  {
      "code": "success",
      "data": {
          "status": 1
      },
      "message": ""
  }
  ```

- **错误**：
  - 未登录：`unauthorized`。
  - 请求体不是 JSON 对象：`validate_error`，提示「请求体必须是JSON对象」。
  - 未提交 `status`：`validate_error`，提示「在线状态不能为空」。
  - `status` 不是整数（含布尔值、字符串）：`validate_error`，提示「在线状态必须是整数」。
  - `status` 不是 `0` 或 `1`：`validate_error`，提示「在线状态只能是0或1」。
  - 智能体不存在、已删除，或不属于当前账号：`not_found`，提示「智能体不存在」。

### 4.6 获取会话分页列表

- **接口说明**：该接口用于分页获取指定智能体下的会话列表，支持按会话标题进行模糊搜索，分页数据固定返回 `list` 和 `paginator` 字段；列表项除会话自身字段外，会一并返回会话所属智能体的 `bot_id`、`peer_id`、`gateway_url` 与 `gateway_key`（其中网关地址与密钥取自智能体关联的 WS 网关，`agent.gateway_id` → `server.id`，未关联时返回空字符串），前端拿到列表即可直接连接网关，无需再单独查询智能体。

- **接口信息**：`授权`+`GET:/agents/:agent_id/conversations`

- **接口参数**：

  - 请求参数：
    - `agent_id -> uuid`：路由参数，需要获取会话列表的智能体 id，类型为 uuid。
    - `current_page -> int`：可选参数，当前页数，默认为 1，类型为整型。
    - `page_size -> int`：可选参数，每页数据条数，默认为 20，范围为 10-50。
    - `search_word -> string`：可选参数，搜索词，在后端会使用会话的标题进行模糊匹配。
  - 响应参数：
    - `list -> list[dict]`：分页后的列表数据，类型为字典列表。
      - `id -> uuid`：会话的 id，类型为 uuid。
      - `account_id -> uuid`：会话归属的账号 id，类型为 uuid。
      - `agent_id -> uuid`：会话所属智能体的 id，类型为 uuid。
      - `bot_id -> str`：会话所属智能体的业务标识，取自 `agent.bot_id`，类型为字符串。
      - `peer_id -> str`：会话所属智能体的对端设备标识，取自 `agent.peer_id`，类型为字符串。
      - `thread_id -> str`：会话线程标识，同一账号下唯一，类型为字符串。
      - `ws_session_id -> str`：网关连接会话标识，由所属智能体的 `peer_id` 与会话 id（uuid 十六进制前 16 位）拼接而成，连接网关时写入 JWT，类型为字符串。
      - `gateway_url -> str`：会话所属智能体关联网关的 WebSocket 地址，取自 `server.gateway_url`，类型为字符串。
      - `gateway_key -> str`：会话所属智能体关联网关的访问密钥，取自 `server.gateway_key`，客户端连接网关时用于鉴权，类型为字符串。
      - `title -> str`：会话标题，类型为字符串，默认为空字符串。
      - `pinned -> int`：是否置顶，`0` 代表否、`1` 代表是，类型为整型。
      - `status -> int`：会话状态，类型为整型，默认为 0。
      - `message_count -> int`：该会话在 `message` 表中的实际条数，按 `message` 表实时统计，类型为整型。
      - `total_token_count -> int`：该会话所有消息 `message_token` 之和，按 `message` 表实时统计，无消息时为 0，类型为整型。
      - `last_message_at -> int`：最后一条消息时间戳，按 `message` 表实时统计（取 `seq` 最大的那条消息的时间），尚无消息时为 `null`。
      - `last_message_preview -> str`：最后一条消息正文的前 255 个字符，按 `message` 表实时统计（取 `seq` 最大的那条），尚无消息时为空字符串。
      - `conversation_info -> dict`：会话扩展信息，类型为字典，默认为 `{}`。
      - `updated_at -> int`：会话更新时间，类型为时间戳。
      - `created_at -> int`：会话创建时间，类型为时间戳。
    - `paginator -> dict`：分页器信息，类型为字典。
      - `current_page -> int`：当前页数，类型为整型。
      - `page_size -> int`：每页的条数，类型为整型。
      - `total_page -> int`：数据的总页数，类型为整型。
      - `total_record -> int`：数据的总记录条数，类型为整型。

- **请求示例**：

  ```bash
  GET:/agents/1550b71a-1444-47ed-a59d-c2f080fbae94/conversations?current_page=1&page_size=20&search_word=天气
  ```

- **响应示例**：

  ```json
  {
      "code": "success",
      "data": {
          "list": [
              {
                  "id": "6b1e9f2c-3a4d-4e7f-8c5b-9d2f0a1e6c77",
                  "account_id": "e1baf52a-1be2-4b93-ad62-6fad72f1ec37",
                  "agent_id": "1550b71a-1444-47ed-a59d-c2f080fbae94",
                  "bot_id": "hermes_001",
                  "peer_id": "peer_iphone15",
                  "thread_id": "thread_8f2a1c",
                  "ws_session_id": "peer_iphone15-6b1e9f2c3a4d4e7f",
                  "gateway_url": "wss://gateway.example.com/ws",
                  "gateway_key": "example-gateway-key",
                  "title": "天气查询",
                  "pinned": 0,
                  "status": 0,
                  "message_count": 8,
                  "total_token_count": 2048,
                  "last_message_at": 1721460914,
                  "last_message_preview": "你好，请问有什么可以帮你的？",
                  "conversation_info": {},
                  "updated_at": 1721460914,
                  "created_at": 1721460914
              }
          ],
          "paginator": {
              "current_page": 1,
              "page_size": 20,
              "total_page": 1,
              "total_record": 1
          }
      },
      "message": ""
  }
  ```

### 4.7 创建会话

- **接口说明**：该接口用于在指定智能体下创建会话。会话线程标识 `thread_id` 在同一账号下唯一，重复创建相同 `thread_id` 的会话时会抛出错误信息。服务端生成会话主键，`ws_session_id` 的生成口径为 `{所属智能体 peer_id}-{新会话 uuid 前 16 位}`（uuid 取十六进制、去掉连字符）。

- **接口信息**：`授权`+`POST:/agents/:agent_id/conversations`

- **接口参数**：

  - 请求参数：
    - `agent_id -> uuid`：路由参数，会话所属的智能体 id，类型为 uuid。
    - `thread_id -> str`：会话线程标识，同一账号下唯一，类型为字符串。
    - `peer_id -> str`：可选参数，对端设备标识，标记会话来自哪台设备，类型为字符串。
    - `title -> str`：可选参数，会话标题，类型为字符串。
    - `conversation_info -> dict`：可选参数，会话扩展信息，类型为字典，默认为 `{}`。
  - 响应参数：
    - `id -> uuid`：创建的会话 id，类型为 uuid。

- **请求示例**：

  ```bash
  POST:/agents/1550b71a-1444-47ed-a59d-c2f080fbae94/conversations
  
  {
  	"thread_id": "thread_8f2a1c",
  	"title": "天气查询"
  }
  ```

- **响应示例**：

  ```json
  {
      "code": "success",
      "data": {
          "id": "6b1e9f2c-3a4d-4e7f-8c5b-9d2f0a1e6c77"
      },
      "message": "创建会话成功"
  }
  ```

### 4.8 修改会话

- **接口说明**：该接口用于修改指定会话的基础信息，该接口为 `增量更新`，可以只传递需要更新的字段信息，例如 `title`、`pinned` 等；会话的 `thread_id` 与 `bot_id` 不支持修改。

- **接口信息**：`授权`+`POST:/agents/:agent_id/conversations/:conversation_id`

- **接口参数**：

  - 请求参数：
    - `agent_id -> uuid`：路由参数，会话所属的智能体 id，类型为 uuid。
    - `conversation_id -> uuid`：路由参数，需要修改的会话 id，类型为 uuid。
    - `title -> str`：可选参数，会话的新标题，类型为字符串。
    - `pinned -> int`：可选参数，是否置顶，`0` 代表否、`1` 代表是，类型为整型。
    - `status -> int`：可选参数。`1` 表示该会话在线，`0` 表示该会话离线。请求体带上 `status` 时，服务端同时把 `online_at` 写成当前 UTC 时间。不传 `status` 时不改在线心跳，改标题、置顶的行为保持不变。
    - `online_at`：不由调用方传入。只要本次请求提交了 `status`，服务端就把它写成当前 UTC 时间。智能体列表和详情的 `status` 不再根据该字段计算，改为直接读 `agent.status`。
    - `conversation_info -> dict`：可选参数，会话扩展信息，类型为字典，传递时进行增量合并。
  - 响应参数：无。

- **请求示例**：

  ```bash
  POST:/agents/1550b71a-1444-47ed-a59d-c2f080fbae94/conversations/6b1e9f2c-3a4d-4e7f-8c5b-9d2f0a1e6c77
  
  {
  	"title": "天气查询（置顶）",
  	"pinned": 1
  }
  ```

- **响应示例**：

  ```json
  {
      "code": "success",
      "data": {},
      "message": "修改会话成功"
  }
  ```

### 4.9 删除会话

- **接口说明**：该接口用于删除指定的会话，删除后该会话将无法被查看和使用。

- **接口信息**：`授权`+`POST:/agents/:agent_id/conversations/:conversation_id/delete`

- **接口参数**：

  - 请求参数：
    - `agent_id -> uuid`：路由参数，会话所属的智能体 id，类型为 uuid。
    - `conversation_id -> uuid`：路由参数，需要删除的会话 id，类型为 uuid。
  - 响应参数：无。

- **请求示例**：

  ```bash
  POST:/agents/1550b71a-1444-47ed-a59d-c2f080fbae94/conversations/6b1e9f2c-3a4d-4e7f-8c5b-9d2f0a1e6c77/delete
  ```

- **响应示例**：

  ```json
  {
      "code": "success",
      "data": {},
      "message": "删除会话成功"
  }
  ```

### 4.10 获取消息分页列表

- **接口说明**：该接口用于按游标获取指定会话下的消息。传入 `turns` 时取最近 N 轮：从倒数第 N 条 `message_role` 为 `user` 的消息开始，到最新一条为止，此时忽略 `before`。不传 `turns` 时，用 `limit` 与可选 `before` 向上加载更早的消息；`before` 不传则返回最新 `limit` 条。结果一律按写入顺序返回。

- **接口信息**：`授权`+`GET:/agents/:agent_id/conversations/:conversation_id/messages`

- **接口参数**：

  - 请求参数：
    - `agent_id -> uuid`：路由参数，会话所属的智能体 id，类型为 uuid。
    - `conversation_id -> uuid`：路由参数，需要获取消息列表的会话 id，类型为 uuid。
    - `turns -> int`：可选参数，最近轮数，范围为 1-50。一「轮」从某条 `message_role='user'` 的消息算起，返回从倒数第 N 条 user 消息到最新一条的全部消息。
    - `limit -> int`：可选参数，向上加载的条数，范围为 1-50，默认为 20。仅在未传 `turns` 时生效。
    - `before -> uuid`：可选参数，某条消息的 `id`。返回比该条更早的 `limit` 条。不传且未传 `turns` 时，返回最新 `limit` 条。
  - 响应参数：
    - `list -> list[dict]`：本次返回的消息列表，类型为字典列表，按写入顺序排列。
      - `id -> uuid`：消息的 id，类型为 uuid。
      - `conversation_id -> uuid`：消息所属的会话 id，类型为 uuid。
      - `account_id -> uuid`：消息归属的账号 id，类型为 uuid。
      - `message_type -> str`：消息类型，类型为字符串，默认为空字符串。
      - `message_role -> str`：消息角色，例如 `user`、`assistant`，类型为字符串。
      - `message_content -> str`：消息正文内容，类型为字符串。
      - `message_token -> int`：本条消息消耗的 Token 数量，类型为整型。未上报真实用量时按正文长度估算：CJK 字符 1 字 1 token、其它 4 字符 1 token。
      - `message_latency -> int`：本条消息耗时，单位毫秒，类型为整型。
      - `message_id -> str`：对端消息 ID，同一会话内唯一，类型为字符串。
      - `message_status -> int`：消息状态，类型为整型。`0` 表示生成中，`1` 表示完成，`2` 表示失败。
      - `message_reasoning -> str`：模型推理过程，类型为字符串，默认为空字符串。
      - `message_info -> dict`：消息扩展信息，类型为字典，默认为空对象。
      - `updated_at -> int`：消息更新时间，类型为时间戳。
      - `created_at -> int`：消息创建时间，类型为时间戳。
    - `has_more -> bool`：本次结果之前是否还有更早的消息，类型为布尔值。
    - `next_cursor -> str`：本次返回中最早一条的 `id`，作为下一次请求的 `before`；没有更早消息时为空字符串，且 `has_more` 为 false。

- **请求示例**：

  ```bash
  GET:/agents/1550b71a-1444-47ed-a59d-c2f080fbae94/conversations/6b1e9f2c-3a4d-4e7f-8c5b-9d2f0a1e6c77/messages?turns=3
  ```

  - 向上加载更早的消息（`before` 传上一页最早一条的 `id`）：

  ```bash
  GET:/agents/1550b71a-1444-47ed-a59d-c2f080fbae94/conversations/6b1e9f2c-3a4d-4e7f-8c5b-9d2f0a1e6c77/messages?before=8a1f3c6d-2e4b-4f7a-9d5c-1b0e6a2f8c34&limit=20
  ```

- **响应示例**：

  ```json
  {
      "code": "success",
      "data": {
          "list": [
              {
                  "id": "8a1f3c6d-2e4b-4f7a-9d5c-1b0e6a2f8c34",
                  "conversation_id": "6b1e9f2c-3a4d-4e7f-8c5b-9d2f0a1e6c77",
                  "account_id": "e1baf52a-1be2-4b93-ad62-6fad72f1ec37",
                  "message_type": "text",
                  "message_role": "assistant",
                  "message_content": "今天广州天气晴，26~36°C，出门记得防晒。",
                  "message_token": 128,
                  "message_latency": 860,
                  "message_id": "msg-8a1f3c6d",
                  "message_status": 1,
                  "message_reasoning": "",
                  "message_info": {},
                  "updated_at": 1721460914,
                  "created_at": 1721460914
              }
          ],
          "has_more": false,
          "next_cursor": ""
      },
      "message": ""
  }
  ```

### 4.11 创建消息

- **接口说明**：该接口用于在指定会话下按 `message_id` 幂等写入一条消息。同一 `(conversation_id, message_id)` 再次提交会覆盖该条记录的正文、状态、推理内容、扩展信息、Token 与耗时，不会新增一行；`message_count` 只在首次新建时 +1，`total_token_count` 也只在新建时累加本次 Token。无论新建还是覆盖，都会更新会话的 `last_message_at` 与 `last_message_preview`（预览最多 255 个字符）。

- **接口信息**：`授权`+`POST:/agents/:agent_id/conversations/:conversation_id/messages`

- **接口参数**：

  - 请求参数：
    - `agent_id -> uuid`：路由参数，会话所属的智能体 id，类型为 uuid。
    - `conversation_id -> uuid`：路由参数，消息所属的会话 id，类型为 uuid。
    - `message_id -> str`：必填，对端消息 ID，长度为 1-64。与 `conversation_id` 组成幂等键，相同键再次提交会覆盖原记录。
    - `message_role -> str`：消息角色，例如 `user`、`assistant`，类型为字符串。仅在首次新建时写入，覆盖时不修改。
    - `message_content -> str`：消息正文内容，类型为字符串。
    - `message_type -> str`：可选参数，消息类型，类型为字符串，默认为空字符串。仅在首次新建时写入，覆盖时不修改。
    - `message_status -> int`：可选参数，消息状态，只能是 `0`（生成中）、`1`（完成）、`2`（失败），默认为 1。
    - `message_reasoning -> str`：可选参数，模型推理过程，类型为字符串，默认为空字符串。
    - `message_info -> dict`：可选参数，消息扩展信息，类型为字典，默认为空对象。
    - `message_token -> int`：可选参数，本条消息消耗的 Token 数量，类型为整型，默认为 0。未上报真实用量时按正文长度估算：CJK 字符 1 字 1 token、其它 4 字符 1 token。覆盖时会更新本条记录上的 Token，但会话 `total_token_count` 不再累加。
    - `message_latency -> int`：可选参数，本条消息耗时，单位毫秒，类型为整型，默认为 0。
  - 响应参数：
    - `id -> uuid`：写入的消息 id，类型为 uuid。覆盖已有记录时返回原记录 id。

- **请求示例**：

  ```bash
  POST:/agents/1550b71a-1444-47ed-a59d-c2f080fbae94/conversations/6b1e9f2c-3a4d-4e7f-8c5b-9d2f0a1e6c77/messages
  
  {
  	"message_id": "msg-8a1f3c6d",
  	"message_role": "user",
  	"message_content": "今天广州天气怎么样？",
  	"message_type": "text",
  	"message_status": 1,
  	"message_reasoning": "",
  	"message_info": {}
  }
  ```

- **响应示例**：

  ```json
  {
      "code": "success",
      "data": {
          "id": "8a1f3c6d-2e4b-4f7a-9d5c-1b0e6a2f8c34"
      },
      "message": "创建消息成功"
  }
  ```

### 4.12 生成智能体标识

- **接口说明**：该接口按 `type` 生成智能体相关的标识，生成结果可直接用于创建智能体。生成规则：把 `account_id`（当前登录账号 id）、`agent_id`、毫秒级 unix 时间戳与 `100000-999999` 之间的随机数拼接成字符串后做 hash，再对 hash 结果做 base64 编码并取前 29 位，最后按类型加前缀返回；`thread_id` 不做 hash，直接返回毫秒级 unix 时间戳。

- **接口信息**：`授权`+`GET:/agent/generate-id`

- **接口参数**：

  - 请求参数：
    - `type -> str`：必填，需要生成的标识类型，可选值只有 `peer_id`、`bot_id`、`ws_session_id`、`thread_id`，传其它值返回参数校验错误。
    - `agent_id -> uuid`：可选参数，参与散列计算的智能体 id，类型为 uuid；不传时使用随机生成的 uuid，传了但格式非法返回参数校验错误。
  - 响应参数：
    - `{type} -> str`：生成结果，`data` 中的键名与请求的 `type` 一致，值为字符串，各类型的取值规则：
      - `peer_id`：`pr-` 加 29 位 base64 串，共 32 个字符。
      - `bot_id`：`bt-` 加 29 位 base64 串，共 32 个字符。
      - `ws_session_id`：`ws-` 加 29 位 base64 串，共 32 个字符。
      - `thread_id`：`td-` 加毫秒级 unix 时间戳。

- **请求示例**：

  ```bash
  GET:/agent/generate-id?type=peer_id
  ```

- **响应示例**：

  ```json
  {
      "code": "success",
      "data": {
          "peer_id": "pr-Njg2MGQxMzkwN2QxYTQ5YjkyZWNhM"
      },
      "message": ""
  }
  ```
## 05. WS 网关模块

### 5.1 获取 WS 网关信息

- **接口说明**：该接口用于获取全库最近更新的一条 WS 网关信息。需要登录，但返回的是全局网关信息，不按账号过滤，按 `updated_at` 倒序取第一条。频道服务页用它展示网关地址和访问密钥。库里一条网关都没有时，`data` 返回空对象 `{}`，不报未找到。

- **接口信息**：`授权`+`GET:/open-api/server`

- **接口参数**：

  - 请求参数：无。
  - 响应参数：
    - `id -> uuid`：WS 网关（服务器）记录的 id，类型为 uuid。
    - `gateway_url -> str`：WS 网关的 WebSocket 地址，客户端可据此连接对应的网关，类型为字符串。
    - `gateway_key -> str`：WS 网关的访问密钥，客户端连接网关时用于鉴权，类型为字符串。
    - `updated_at -> int`：网关信息更新时间，类型为时间戳。
    - `created_at -> int`：网关记录创建时间，类型为时间戳。

- **请求示例**：

  ```bash
  GET:/open-api/server
  ```

- **响应示例**：

  ```json
  {
      "code": "success",
      "data": {
          "id": "9c7e4b2a-1d3f-4a5b-8c6e-2f0d9b7a4e13",
          "gateway_url": "wss://gateway.example.com:8080/ws",
          "gateway_key": "example-gateway-key",
          "updated_at": 1721460914,
          "created_at": 1721460914
      },
      "message": ""
  }
  ```

### 5.2 获取 WS 网关列表

- **接口说明**：该接口用于获取全部 WS 网关信息。需要登录，但返回的是全局网关列表，不按账号过滤。排序为 `created_at` 升序，创建时间相同时再按 `id` 升序，保证顺序稳定。频道服务页用它展示「网关一」「网关二」等多个网关。库里一条网关都没有时，`data.list` 返回空数组 `[]`。

- **接口信息**：`授权`+`GET:/open-api/servers`

- **接口参数**：

  - 请求参数：无。
  - 响应参数：
    - `list -> list[dict]`：网关列表，元素字段与单条网关信息相同。
    - `list[].id -> uuid`：WS 网关（服务器）记录的 id，类型为 uuid。
    - `list[].gateway_url -> str`：WS 网关的 WebSocket 地址，客户端可据此连接对应的网关，类型为字符串。
    - `list[].gateway_key -> str`：WS 网关的访问密钥，客户端连接网关时用于鉴权，类型为字符串。
    - `list[].updated_at -> int`：网关信息更新时间，类型为时间戳。
    - `list[].created_at -> int`：网关记录创建时间，类型为时间戳。

- **请求示例**：

  ```bash
  GET:/open-api/servers
  ```

- **响应示例**：

  ```json
  {
      "code": "success",
      "data": {
          "list": [
              {
                  "id": "9c7e4b2a-1d3f-4a5b-8c6e-2f0d9b7a4e13",
                  "gateway_url": "wss://gateway.example.com:8080/ws",
                  "gateway_key": "example-gateway-key",
                  "updated_at": 1721460914,
                  "created_at": 1721460914
              }
          ]
      },
      "message": ""
  }
  ```

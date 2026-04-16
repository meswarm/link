# 技术方案：Link 中间件 Matrix 消息发送 + R2 带外媒体架构

## 1. 方案定位

本方案面向 **Link 中间件（Python 后端 Agent 进程）**，不涉及浏览器前端。
目标是在 Matrix 信令层保持轻量纯文本通信的前提下，将图片/视频/附件等大文件
分离到 R2（或兼容 S3 的对象存储）中存储，实现"文本走 Matrix、媒体走 R2"的
带外架构。

### 与原 Web 前端方案的核心差异

| 维度 | Web 前端 | Link 中间件 |
|------|---------|-------------|
| 运行环境 | 浏览器沙箱 | Linux 长驻进程 |
| 密钥存储 | IndexedDB + 口令加密 | 环境变量 / .env 文件 |
| 密钥生命周期 | 页面会话 | 进程生命周期 |
| 威胁模型 | XSS / 第三方脚本 | 服务器权限隔离 |
| 缓存位置 | OPFS / IndexedDB | 本地文件系统 |
| 用户交互 | 口令解锁页面 | 无（自动启动） |

## 2. 核心原则

- **Matrix Homeserver 不承载媒体流量**：信令层仅同步 Markdown 文本、房间状态。
- **R2 密钥仅存于中间件运行环境**：通过 `.env` / 环境变量注入，不写入 YAML 配置文件。
- **引用协议 `r2://`**：媒体文件在 Matrix 消息中以 `r2://bucket/key` 格式引用。
- **本地磁盘缓存**：已下载的媒体文件持久化到 `work_dir/media_cache/`，避免重复拉取。
- **向后兼容**：未配置 R2 时，中间件回退到现有的 Matrix 原生媒体处理流程。

## 3. 系统组成

```
┌──────────────────────────────────────────────────────────┐
│                     Link 中间件进程                        │
│                                                          │
│  ┌──────────┐    ┌──────────┐    ┌──────────────────┐    │
│  │  Agent   │───▶│LLMEngine │───▶│  MatrixClient    │    │
│  │          │    │          │    │  (纯文本信令)      │    │
│  └──────────┘    └──────────┘    └────────┬─────────┘    │
│       │                                    │              │
│       │          ┌──────────────┐          │              │
│       └─────────▶│ R2MediaStore │◀─────────┘              │
│                  │ (媒体存取层)  │                         │
│                  └──────┬───────┘                         │
│                         │                                 │
│              ┌──────────▼──────────┐                     │
│              │  media_cache/       │                     │
│              │  (本地磁盘缓存)      │                     │
│              └─────────────────────┘                     │
└──────────────────────────────────────────────────────────┘
         │                            │
         ▼                            ▼
  ┌──────────────┐          ┌──────────────────┐
  │ Matrix       │          │ R2 / S3          │
  │ Homeserver   │          │ 对象存储          │
  │ (纯文本)     │          │ (图片/视频/文件)  │
  └──────────────┘          └──────────────────┘
```

## 4. 配置设计

### 4a. 环境变量（.env）

R2 密钥与 API Key 一样，通过 `.env` 注入，绝不写入 Agent YAML：

```bash
# ── R2 对象存储（按需填写，不配则走 Matrix 原生媒体）──
R2_ENDPOINT=https://xxx.r2.cloudflarestorage.com
R2_ACCESS_KEY=your_access_key
R2_SECRET_KEY=your_secret_key
R2_BUCKET=link-media
R2_PUBLIC_URL=https://media.example.com   # 可选：公开可访问的 URL 前缀
```

### 4b. Agent 配置（YAML）

Agent 无需感知 R2 密钥细节，只需决定是否启用：

```yaml
# 媒体存储策略
media_storage: "r2"          # "matrix" (默认) | "r2"
```

### 4c. 配置模型（config.py 新增）

```python
class R2Config(BaseModel):
    """R2 对象存储配置"""
    endpoint: str = ""
    access_key: str = ""
    secret_key: str = ""
    bucket: str = "link-media"
    public_url: str = ""       # 可选公开 URL
    
    @property
    def enabled(self) -> bool:
        return bool(self.endpoint and self.access_key and self.secret_key)
```

## 5. R2MediaStore 核心模块

新建 `link/media_store.py`，封装上传/下载/缓存三大职能：

```python
class R2MediaStore:
    """R2 带外媒体存储层
    
    职责：
    - 上传：本地文件 → R2，返回 r2:// 引用
    - 下载：r2:// 引用 → 本地缓存文件
    - 缓存：已下载文件持久化到 media_cache/
    """
    
    def __init__(self, config: R2Config, cache_dir: Path):
        self._config = config
        self._cache_dir = cache_dir / "media_cache"
        self._cache_dir.mkdir(parents=True, exist_ok=True)
        # 初始化 S3 兼容客户端 (boto3 / aioboto3)
        self._client = ...
    
    async def upload(self, local_path: Path) -> str:
        """上传文件到 R2
        
        Returns:
            r2://bucket/key 格式的引用
        """
        key = f"{timestamp}_{local_path.name}"
        await self._client.upload_file(local_path, key)
        return f"r2://{self._config.bucket}/{key}"
    
    async def download(self, r2_uri: str) -> Path:
        """下载 R2 文件到本地缓存
        
        优先使用本地缓存，未命中则从 R2 拉取。
        
        Returns:
            本地文件路径
        """
        key = self._parse_key(r2_uri)
        cache_path = self._cache_dir / key
        
        if cache_path.exists():
            return cache_path  # 缓存命中
        
        await self._client.download_file(key, cache_path)
        return cache_path
    
    def resolve_url(self, r2_uri: str) -> str | None:
        """将 r2:// 引用转为公开 HTTP URL（如果配了 public_url）"""
        if not self._config.public_url:
            return None
        key = self._parse_key(r2_uri)
        return f"{self._config.public_url}/{key}"
```

## 6. 发送流程

### 6a. 工具方 → 中间件 → 用户

当工具方通过 Webhook 推送文件，或 Agent 需要向用户发送文件时：

```
工具方推送文件
    ↓
Agent._handle_tool_event() 检测到文件类型
    ↓
media_storage == "r2" ?
    ├── 是 → R2MediaStore.upload(本地文件)
    │        → 获得 r2://bucket/key
    │        → 通过 Matrix m.text 发送包含 r2:// 链接的 Markdown
    │        → 如有 public_url，附上可直接点击的 HTTP 链接
    │
    └── 否 → 走现有 MatrixClient.send_file()（上传到 Matrix 媒体仓库）
```

**发送的 Matrix 消息示例**：

```markdown
⚠️ 服务器告警

监控截图：
![screenshot](https://media.example.com/1712345678_alert.png)

<!-- r2://link-media/1712345678_alert.png -->
```

### 6b. 用户 → 中间件（图片分析场景）

当用户通过 Matrix 客户端发送图片时：

```
用户在 Element 发送图片
    ↓
MatrixClient._on_media_message() 接收
    ↓
_download_media() 下载到 inbox/
    ↓
media_storage == "r2" ?
    ├── 是 → R2MediaStore.upload(inbox/文件)
    │        → 存档到 R2（持久化保存）
    │        → 同时交给 LLM 做图像分析（如启用 vision）
    │
    └── 否 → 仅保留在 inbox/（现有逻辑不变）
```

## 7. 接收流程

中间件作为接收方，需要解析其他 Agent 或系统发来的含 `r2://` 引用的消息：

```
收到 Matrix 文本消息
    ↓
检测消息中的 r2:// 引用
    ├── 无引用 → 正常处理
    └── 有引用 → R2MediaStore.download(r2_uri)
                 → 先查 media_cache/
                    ├── 命中 → 直接使用本地文件
                    └── 未命中 → 从 R2 下载 → 写入 media_cache/
                 → 将本地路径交给 LLM 处理（如启用 vision）
```

## 8. 本地缓存设计

```
work_dir/
├── inbox/              # 用户发来的原始文件（临时）
├── media_cache/        # R2 下载缓存（持久）
│   ├── 1712345678_photo.jpg
│   ├── 1712345679_report.pdf
│   └── ...
└── outbox/             # 待上传文件（可选暂存区）
```

### 缓存策略

| 参数 | 默认值 | 说明 |
|------|--------|------|
| `media_cache_max_size` | 1GB | 缓存目录大小上限 |
| `media_cache_ttl` | 7d | 缓存文件过期时间 |
| `media_cache_cleanup` | 启动时 | 清理时机 |

当缓存超过上限时，按 LRU（最近最少使用）策略淘汰旧文件。

## 9. 安全设计

### 密钥保护

```
层级              保护手段                        风险等级
────              ────                           ────
.env 文件         .gitignore 排除 + 文件权限 600   低
进程内存          进程隔离（Linux 用户权限）        低
R2 密钥作用域     限制 Bucket 级别 IAM 权限         低
```

### 最小权限原则

R2 IAM 策略只需授予：

```json
{
  "Effect": "Allow",
  "Action": [
    "s3:PutObject",
    "s3:GetObject",
    "s3:ListBucket"
  ],
  "Resource": [
    "arn:aws:s3:::link-media",
    "arn:aws:s3:::link-media/*"
  ]
}
```

### 与 Web 前端方案的安全对比

| 威胁 | Web 前端方案 | Link 中间件方案 |
|------|-------------|----------------|
| 密钥泄露 | XSS 可读取内存 | 需入侵服务器 |
| 持久化安全 | IndexedDB 加密 | .env 文件权限 |
| 传输安全 | HTTPS | HTTPS |
| 密钥轮换 | 用户手动更新 | 修改 .env 重启 |

中间件方案由于运行在受控服务器环境中，天然比浏览器端安全性更高，
不需要口令加密等额外机制。

## 10. 配置模板（config-template.yaml 新增段）

```yaml
# ═══════════════════════════════════════════════════════════════
# 媒体存储 [可选]
# ═══════════════════════════════════════════════════════════════
# 默认使用 Matrix 原生媒体上传（通过 Homeserver 中转）。
# 如需将大文件存到 R2/S3 对象存储，启用以下配置：
#
# 前提：在 .env 中配置 R2 连接信息
#   R2_ENDPOINT=https://xxx.r2.cloudflarestorage.com
#   R2_ACCESS_KEY=your_access_key
#   R2_SECRET_KEY=your_secret_key
#   R2_BUCKET=link-media
#   R2_PUBLIC_URL=https://media.example.com  (可选)
#
# 优势：
#   - Matrix Homeserver 不承载媒体流量
#   - 大文件存储不受 Homeserver 上传限制
#   - 支持通过公开 URL 直接在任意客户端查看
#
# media_storage: "r2"          # "matrix" (默认) | "r2"
```

## 11. 依赖新增

```toml
# pyproject.toml 新增
dependencies = [
    # ... 现有依赖 ...
    "aioboto3>=12.0.0",        # R2/S3 异步客户端（仅 media_storage=r2 时需要）
]
```

## 12. 向后兼容保证

- **不配 R2 = 零影响**：`media_storage` 默认为 `"matrix"`，走现有全部逻辑。
- **R2MediaStore 惰性初始化**：仅在 `media_storage == "r2"` 时创建 boto3 客户端。
- **现有 API 不变**：`send_file()`, `_download_media()` 等方法签名不变。

## 13. 实施阶段建议

| 阶段 | 内容 | 优先级 |
|------|------|--------|
| P0 | `R2Config` 配置模型 + `.env` 集成 | 高 |
| P0 | `R2MediaStore` 核心上传/下载 | 高 |
| P1 | `MatrixClient` 发送流程分支 | 中 |
| P1 | `Agent` 接收流程 r2:// 解析 | 中 |
| P2 | 本地缓存 LRU 淘汰 | 低 |
| P2 | 缓存大小/TTL 配置化 | 低 |

## 14. 结论

本方案将原 Web 前端的"BYOK + 口令加密"架构，适配为 Link 中间件的
"`.env` 注入 + 进程隔离"架构。核心设计理念不变：

1. **Matrix 只管文本信令** — Homeserver 不承载媒体流量
2. **R2 作为带外存储** — 大文件直连存取
3. **引用协议 `r2://`** — 文本消息中嵌入媒体引用
4. **本地缓存兜底** — 避免重复下载

相比 Web 前端方案，中间件方案更简洁：无需口令解锁机制、无需 IndexedDB 加密，
密钥安全依赖 Linux 文件权限和进程隔离即可达到更高安全水位。

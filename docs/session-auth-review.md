# 会话与鉴权代码 Review

> 审阅范围：`src/kingdee_k3cloud_mcp/server.py` 中的会话（K3Cloud SID）管理与 MCP Bearer Token 鉴权两条链路。
> 审阅基准：`kingdee-k3cloud-mcp` v1.3.2，依赖 `kingdee.cdp.webapi.sdk` 8.2.0、`mcp` 1.27.0（均按 `uv.lock` 锁定版本核对源码）。
> 结论性质：本文只记录问题与建议，**未修改任何实现代码**。

---

## 1. 涉及的代码

| 链路 | 位置 | 说明 |
|------|------|------|
| 金蝶会话恢复 | `server.py:71-120` `RetryableK3CloudApiSdk` | 检测「会话信息已丢失」→ 清 SID → 重建会话 |
| 会话过期检测 | `server.py:55-68` `_check_expired` / `_is_session_expired` | 解析响应 JSON 判断是否会话过期 |
| SDK 单例 | `server.py:28-34` `api_sdk` / `_sdk()` | 进程级全局，所有 tool 共用 |
| 凭据装配 | `server.py:879-904` `setup()` | 读环境变量 → `InitConfig` |
| MCP 鉴权 | `server.py:37-49` `ApiKeyVerifier` + `server.py:888-892` | 静态 API Key 的 Bearer Token 校验 |

---

## 2. 依赖侧事实（后续判断的依据）

以下均为直接读取锁定版本 wheel 源码得到的事实，而非推测。

### 2.1 `kingdee.cdp.webapi.sdk` 8.2.0

- **该版本没有 Login / ValidateUser 接口**。鉴权是**每请求无状态 HMAC 签名**：`WebApiClient.BuildHeader()` 每次都重新计算 `X-Api-Signature` 与 `X-Kd-Signature`。
  `kdservice-sessionid`（下称 SID）只是服务端顺手下发、SDK 顺手回带的**可选 cookie**。
  → 这条直接支撑「清掉 SID 后立即重试应当能成功」——重试请求自带完整签名，不依赖任何既有会话。
- `CookieStore.set_sid()` 仅在新值非空时覆盖，**永不清空**。因此陈旧 SID 只能靠整体替换 `cookiesStore` 来清除（现有代码正是这么做的，方向正确）。
- `WebApiClient.__init__` **无条件**设置 `self.cookiesStore = CookieStore()`。
- `WebApiClient.Execute()` 在 `initialize` 为 False 时是 `return RuntimeError(...)`——**返回**异常对象而非抛出。
- `PostJson()` 使用 `requests.post(..., verify=False)`，模块顶部还有 `urllib3.disable_warnings(InsecureRequestWarning)`：**TLS 证书校验被全局关闭**。
- `BuildHeader()` 中 `nonce = str(int(time.time()))`，与 timestamp 同值（同一秒内的两次请求 nonce 相同）。
- `K3CloudApiSdk.GetDataCenters()` 存在，是天然幂等的只读接口。

### 2.2 `mcp` 1.27.0

- `func_metadata.call_fn_with_arg_validation`：同步 tool 函数**直接在事件循环中调用**（`return fn(**args)`），**不走线程池**。
- `FastMCP.sse_app()` / `streamable_http_app()` 在 **run 时**才读取 `self._token_verifier` 与 `self.settings.auth`；`FastMCP.__init__` 里的 auth 一致性校验只在构造时执行。
- `BearerAuthBackend.authenticate()` 仅在 `verify_token()` 返回真值时放行，并额外检查 `expires_at`。
- `FastMCP.Settings` 是 `BaseSettings(env_prefix="FASTMCP_", env_file=".env")`——`.env` 中的 `FASTMCP_HOST` / `FASTMCP_PORT` 由 pydantic-settings 自行读取，**不依赖** `setup()` 里的 `load_dotenv()`。
  （曾怀疑这里因为 `load_dotenv` 晚于 `FastMCP()` 构造而失效，核对后**排除**，不是问题。）

---

## 3. 问题清单

### 3.1 严重 —— 会导致数据错误或崩溃

#### S1. 会话恢复会「重放」原始写请求，可能造成单据重复提交

- **位置**：`server.py:112-114`
- **现象**：检测到会话丢失后，代码用**原样的 `service_name` + `json_data`** 再打一次请求，结果丢弃，目的仅是拿新 SID：

  ```python
  super().Execute(
      service_name, json_data, invoke_type
  )  # establishes SID, result discarded
  ```

  而 `Execute` 是所有 tool 的公共出口，`save_bill` / `submit_bill` / `audit_bill` / `unaudit_bill` / `delete_bill` / `execute_operation` / `push_bill` **全部**经过这里。
- **影响**：第二次请求携带完整 HMAC 签名，服务端完全可能鉴权通过并**真正执行**。那就是一次静默的重复保存 / 重复审核 / 重复删除 / 重复下推，且因为结果被丢弃，调用方永远看不到。这是本次 review 中风险最高的一条。
- **建议**：用幂等只读探针（`GetDataCenters()`）重建 SID，**绝不重放业务负载**。

#### S2. `_check_expired` 有三条未捕获的 `AttributeError` 崩溃路径

- **位置**：`server.py:59-60`

  ```python
  errors = (data.get("Result") or {}).get("ResponseStatus", {}).get("Errors", [])
  return any(SESSION_LOST_MSG in (e.get("Message") or "") for e in errors)
  ```

  `Result` 用了 `or {}` 兜底，但 `ResponseStatus`、`Errors` 元素都没有。
- **实测**（按同一份逻辑复现，非推测）：

  | 响应形态 | 结果 |
  |---|---|
  | `{"Result":{"ResponseStatus":null}}` | **AttributeError** |
  | `{"Result":[{...}]}`（`Result` 是数组） | **AttributeError** |
  | `{"Result":{"ResponseStatus":{"Errors":["会话信息已丢失"]}}}`（`Errors` 元素是字符串） | **AttributeError** |
  | `{"Result":{"ResponseStatus":{"Errors":null}}}` | False（`TypeError` 被吞，可接受） |

- **影响**：`_is_session_expired` 的 `except` 只列了 `JSONDecodeError / TypeError / ValueError`，**`AttributeError` 会穿透**到 `RetryableK3CloudApiSdk.Execute`，使该次 tool 调用直接抛异常（FastMCP 包成 `ToolError`），而不是把金蝶原始错误透传给模型。`_check_expired` 被直接调用时更是裸崩。
- **建议**：逐层 `or {}` / `isinstance` 收敛；`except` 补 `AttributeError`；对 `Errors` 元素加 `isinstance(e, dict)` 过滤。

---

### 3.2 高 —— 影响可用性 / 安全姿态

#### S3. 300 秒冷却期建立在一个未经验证的假设上，代价是「一次会话过期 = 全线报错 5 分钟」

- **位置**：`server.py:88`（`_RESET_COOLDOWN = 300`）、`98-119`
- **现状**：过期 → 清 SID → 打一次探测 → **仍然返回原始错误**；此后 300 秒内所有调用一律直接返回错误、不做任何重试。也就是说，任何一次会话过期至少损失一次查询，最坏情况下 5 分钟内每次调用都失败。
- **依据**：`server.py:74-88` 的注释称「新 SID 需要几分钟才能在服务端激活」，经确认这是当时的**推测**而非实测结论。而按 §2.1，SDK 鉴权是每请求 HMAC 签名，SID 只是可选 cookie——清掉 SID 后的重试**理论上应当立即成功**。
- **建议**：
  1. 清 SID 后**真正重试一次**；重试结果若不再报会话丢失，直接返回给调用方（用户拿到的是数据而不是错误）。
  2. 只有重试仍然失败才退回冷却期。
  3. 冷却时长改为可配置（如 `KD_SESSION_RESET_COOLDOWN`，默认 300），以兼容行为异常的服务端部署。
  4. **写操作依然只探针、不重放**（见 S1）——真重试只对读操作开放。

#### S4. 恢复调用的异常会顶替掉原始错误

- **位置**：`server.py:112-114`，未包 `try/except`
- **现象**：`PostJson()` 在非 200 时 `raise RuntimeError(res.text)`，`ValidResult()` 也会抛。恢复调用一旦抛异常，`Execute` 就走不到 `return result`，调用方拿到的是一个与真实问题无关的裸异常，而不是本该透传的「会话信息已丢失」。
- **附带**：`self._session_reset_at = now` 在恢复调用**之前**赋值（`server.py:105`），因此恢复失败也照样锁死 300 秒冷却。
- **建议**：`try/except Exception` 包住探针并只记 warning；恢复是否成功应当反过来影响冷却状态（成功即清零，失败才保留）。

#### S5. Bearer Token 使用 `==` 比较，非恒定时间

- **位置**：`server.py:47`

  ```python
  if token == self._key:
  ```

- **影响**：SSE / streamable-http 模式下这是暴露在网络上的静态密钥，也是**唯一**保护整套 ERP 读写工具的凭据。`==` 的短路比较理论上可被时序侧信道逐字节爆破。
- **建议**：改用 `hmac.compare_digest(token, self._key)`。一行改动，无副作用。

#### S6. 鉴权装配依赖 FastMCP 私有属性，未来版本可能静默降级为「无鉴权」

- **位置**：`server.py:891`

  ```python
  mcp._token_verifier = ApiKeyVerifier(api_key)
  ```

- **已核实**：在 mcp 1.27.0 下**确实生效**——`sse_app()` / `streamable_http_app()` 在 run 时才读该属性，赋值时机没问题。
- **风险**：`pyproject.toml` 允许 `mcp>=1.26.0,<2`。一旦上游重命名或移除该私有属性，`mcp.settings.auth` 虽被设置但 `self._token_verifier` 为 `None`，`sse_app()` 就**不会挂载** `AuthenticationMiddleware` / `RequireAuthMiddleware`——服务照常启动，运维以为有鉴权，实际完全裸奔。这是 **fail-open**。
- **附带**：该赋值绕开了 `FastMCP.__init__` 中的 auth 一致性校验。
- **建议**：注入前显式检查属性存在，缺失则**启动即失败**（fail-closed），并在文档中标注该写法与 mcp 版本绑定。更稳妥的方案是把 `FastMCP(...)` 的构造推迟到读取环境变量之后，走官方入参 `FastMCP(..., token_verifier=..., auth=...)`。

#### S7. 非 stdio 传输在未设 `MCP_API_KEY` 时静默零鉴权启动

- **位置**：`server.py:888-892`（`if api_key:` 之外没有任何提示）；`--mode` 默认 `readwrite`
- **影响**：`--transport sse` 且 `FASTMCP_HOST=0.0.0.0` 时，任何能连到该端口的人都可以调用全部**写**工具——保存 / 审核 / 反审核 / 删除 / 下推真实 ERP 单据。`.env` 里写成 `MCP_API_KEY=`（空字符串）同样被当作「不启用鉴权」，且没有任何提示。
- **建议**：非 stdio 传输且无 key 时打**醒目 warning**，或要求显式 `MCP_ALLOW_NO_AUTH=1` 才放行；key 读取后做 `.strip()`，拒绝空或纯空白值。

---

### 3.3 中 —— 健壮性 / 正确性瑕疵

#### S8. 会话过期只认一个中文字符串

- **位置**：`server.py:21` `SESSION_LOST_MSG = "会话信息已丢失"`
- **影响**：`KD_LCID` 是可配置项（`.env.example` 中就暴露了）。设成 1033（英文）时服务端返回英文提示，整套会话恢复机制**完全失效**，用户只会看到反复失败而不知原因。其它鉴权类错误（未登录 / 身份验证失败 / HTTP 401）也不在识别范围内。
- **建议**：改成可扩展的标记列表（中英文 + 常见变体），必要时允许通过环境变量追加。

#### S9. 顶层 `ResponseStatus` 形态漏检

- **位置**：`server.py:59`，只查 `Result.ResponseStatus.Errors` 这一条固定路径
- **实测**：`{"ResponseStatus":{"Errors":[{"Message":"会话信息已丢失"}]}}` 返回 **False**（漏检）。
- **建议**：递归查找任意层级的 `ResponseStatus.Errors`，而不是写死路径。

#### S10. `_session_reset_at = 0.0` 与 `time.monotonic()` 的语义冲突

- **位置**：`server.py:92`（初值 `0.0`）、`server.py:98`（`now - self._session_reset_at >= self._RESET_COOLDOWN`）
- **现象**：`time.monotonic()` 在 Linux 上约等于系统 uptime。容器或机器启动不到 300 秒时 `now - 0.0 < 300` 成立，**首次会话过期会被误判为「处于冷却期」而跳过恢复**——恰恰是最需要恢复的时候不恢复。
- **建议**：初值改为 `None` 或 `float("-inf")`，用显式的「从未重置过」语义。

#### S11. `hasattr(self, "cookiesStore")` 是死分支

- **位置**：`server.py:106-111`
- **依据**：`WebApiClient.__init__` **无条件**设置该属性，且 `RetryableK3CloudApiSdk.__init__` 必然调用 `super().__init__()`。因此 else 分支的「SDK internals changed」告警**永远不会触发**——它营造了一种有防护的错觉，实际没有任何防护作用。
- **建议**：删掉该分支；若确实想防上游变更，改成有效的契约断言（例如 `InitConfig` 之后校验 `self.initialize is True`）。

#### S12. `MCP_ISSUER_URL` 默认值写死 8000，与 `FASTMCP_PORT` 不联动

- **位置**：`server.py:890`，默认 `http://localhost:8000`
- **影响**：改了 `FASTMCP_PORT` 却没同步 `MCP_ISSUER_URL` 时，`/.well-known/oauth-protected-resource` 与 401 响应中的 `WWW-Authenticate` 都会指向错误端口，遵循 OAuth 发现流程的客户端将连不上。`.env.example` 里两处示例（注释写 `127.0.0.1`、代码默认 `localhost`）也不一致。
- **建议**：默认值从 `mcp.settings.host` / `mcp.settings.port` 推导（`0.0.0.0` 归一化为 `127.0.0.1`），仍允许显式覆盖。

#### S13. `KD_LCID` 缺少解析保护

- **位置**：`server.py:902` `lcid=int(os.getenv("KD_LCID", "2052"))`
- **现象**：`.env` 中写成 `KD_LCID=`（空）或非数字，直接抛 `ValueError: invalid literal for int()`，启动失败且报错信息不指向具体配置项。相邻的 `KD_ORG_NUM` 有 `or "0"` 保护，`KD_LCID` 没有——两者不一致。
- **建议**：补 `or "2052"`，并用 `try/except` 转成明确的配置错误消息。

#### S14. 只覆写了 `Execute`，`QUERY` 异步模式绕过整套会话恢复

- **位置**：`server.py:94` 覆写 `Execute`；SDK 的 `ExecuteByQuery()` / `QueryTaskResult()` 直接调用 `PostJson()`
- **现状**：项目目前从不传 `InvokeMethod.QUERY`，因此这是**休眠**问题；一旦以后接入 `BatchSaveQuery` 等轮询接口就会暴露——那条路径上没有任何会话恢复。
- **建议**：记录该边界；未来若启用 QUERY 模式，需同步扩展恢复逻辑。

#### S15. 多数写工具不做过期透传判断

- **位置**：`view_bill`(707)、`query_metadata`(719)、`save_bill`(740)、`submit_bill`(758)、`audit_bill`(776)、`unaudit_bill`(794)、`delete_bill`(812)、`execute_operation`(832)、`push_bill`(876) 都是直接 `return _sdk().Xxx(...)`
- **说明**：这些直接透传金蝶原始 JSON，模型能看到「会话信息已丢失」原文，**行为上可接受**；但与查询侧（`server.py:145` / `201` / `283` / `420` 有显式判断）不一致，模型拿到的是裸错误而非结构化提示。
- **建议**：列为可选提升——统一包一层错误归一化，给模型明确的「会话恢复中，请稍后重试」提示。

---

### 3.4 低 —— 记录备查

#### S16. 依赖 SDK 全局关闭了 TLS 校验

`requests.post(..., verify=False)` + `urllib3.disable_warnings(InsecureRequestWarning)`：凭据签名在**未验证证书**的 TLS 通道上传输，中间人可劫持。这是上游 SDK 的行为，本项目在不覆写 `PostJson()` 的前提下无法修复。作为已知风险记录，建议在内网 / 受控网络环境部署。

#### S17. 同步 tool 阻塞事件循环（以及一条重要的连带约束）

已核实 mcp 1.27 的同步 tool 在事件循环中直接执行。

- **好消息**：当前**不存在** `cookiesStore` / `_session_reset_at` 的数据竞争——所有调用天然串行。
- **坏消息**：`query_bill_to_file` 这类翻页导出会把整个 server 阻塞数分钟；SSE 模式下所有客户端一起卡住，连 ping / 取消都处理不了。
- **⚠️ 连带约束**：若将来为解决阻塞而把 tool 改成 `async` + `anyio.to_thread.run_sync`，**必须同时给会话恢复段加 `threading.Lock`**。否则恢复逻辑会立刻变成真实竞态：多线程同时替换 `cookiesStore`，而且 `FillCookieAndHeader` 的 `cookies.clear()` 与 `BuildHeader` 的 `items()` 迭代会撞出 `RuntimeError: dictionary changed size during iteration`。

#### S18. 启动时不校验凭据

`setup()` 只检查 5 个环境变量非空，从不实际连一次金蝶。凭据错误要等到第一次工具调用才暴露。建议提供可选的启动探针（`GetDataCenters()`）：既能立刻验证凭据，又能顺带预热 SID。

#### S19. `_sdk()` 使用 `assert`

`python -O` 下断言会被剥离，`api_sdk` 为 `None` 时退化成语义不明的 `AttributeError`。建议换成显式 `raise RuntimeError`。

---

## 4. 测试缺口

现有 `tests/test_server.py:118-228` 覆盖了冷却期的两条分支，但缺少：

- **`ApiKeyVerifier.verify_token` —— 零测试**（`ApiKeyVerifier` 在 `tests/` 下无任何命中）。
- `setup()` 中 `MCP_API_KEY` / `AuthSettings` 的装配路径。
- 恢复调用抛异常时的行为（S4）。
- 恢复调用重放写负载（S1）——应当有一条测试断言「写操作不得被重放」。
- `_check_expired` 的 null / 异形输入（S2）。

另有两处测试自身的问题：

- **一条无效断言**：`test_expired_outside_cooldown_updates_reset_timestamp`（`tests/test_server.py:174-185`）把 `time.monotonic` 冻结在 `1000.0`，因此 `before` 与 `after` 都等于 `1000.0`，断言退化成 `1000.0 >= 1000.0` —— 无论实现如何都会通过。
- `_INIT_KWARGS`（`tests/test_server.py:109-115`）定义后从未被使用。

---

## 5. 建议的修复顺序

| 优先级 | 条目 | 理由 |
|--------|------|------|
| 1 | **S2** | 先止崩溃：异常响应形态会让每次调用直接抛错 |
| 2 | **S1** | 再止数据错误：重放写请求可能造成重复单据 |
| 3 | **S3 / S4** | 改可用性：让会话过期从「5 分钟不可用」变成「一次自动重试」 |
| 4 | **S5 / S6 / S7** | 安全硬化：恒定时间比较、fail-closed、零鉴权告警 |
| 5 | S8–S15 | 健壮性与一致性 |
| 6 | S16–S19 | 记录备查 / 视需要处理 |

修复 S1–S7 属于行为变更（影响调用方拿到的结果），按 `CLAUDE.md` 的版本策略应做 **minor bump + release**。

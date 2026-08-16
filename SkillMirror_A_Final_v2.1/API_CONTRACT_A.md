# SkillMirror 成员 A API Contract v2.1

本契约定义浏览器、成员 B 可信后端与成员 A 服务之间的安全边界。默认地址为 `http://127.0.0.1:8000`，请求与响应使用 UTF-8 JSON。

## 1. 部署必需的安全配置

生产部署必须注入三个不同的随机值，每个至少 32 字节：

| 环境变量 | 持有方 | 用途 |
|---|---|---|
| `SKILLMIRROR_INTERNAL_TOKEN` | A 服务、B 后端 | B 调 A 内部接口时的服务认证 |
| `SKILLMIRROR_B_PROVENANCE_SECRET` | A 服务、B 后端 | B Runner/Logger 对原始记录做 HMAC 签名 |
| `SKILLMIRROR_A_EVIDENCE_SECRET` | **仅 A 服务** | A 对内部 Challenge、Verification Record、Evidence 做 HMAC 签名 |

示例启动方式只展示变量名，不提供默认密钥：

```bash
export SKILLMIRROR_INTERNAL_TOKEN='<random-32+-bytes>'
export SKILLMIRROR_B_PROVENANCE_SECRET='<different-random-32+-bytes>'
export SKILLMIRROR_A_EVIDENCE_SECRET='<a-only-random-32+-bytes>'
uvicorn api.app:app --host 127.0.0.1 --port 8000
```

内部请求必须带：

```http
X-SkillMirror-Internal-Token: <SKILLMIRROR_INTERNAL_TOKEN>
```

这三个值不得写入源码、前端包、浏览器存储、URL、普通业务日志或 API 响应。B 可以持有前两个值，不能持有 A Evidence Secret。生产环境应使用 TLS、秘密管理服务和定期轮换。

## 2. A/B/浏览器信任矩阵

| 数据/动作 | 浏览器 | B 可信后端 | A 必须做的验证 |
|---|---|---|---|
| 题面、Starter、公开测试 | 可接收 | 可代理/保存 | learner view 字段白名单 |
| 学员代码、点击、编辑、Hint 请求 | 可产生不可信输入 | 认证用户、限流、持久化 | Schema/长度检查；不能直接证明能力 |
| 隐藏测试、参考答案、hidden bugs | 不可接收 | 仅后端保存 | server token + A Challenge HMAC + oracle 重验 |
| Sandbox/Test Runner 结果 | 不可自行声明可信 | 生产沙箱执行并以 B Secret 签名 | B HMAC、身份、record type、提交摘要、Challenge 摘要 |
| `verification_status` | 即使传 `verified` 也无效 | 无需声明 | A 忽略来值并按验签结果重建 |
| Verification Record | 不可生成 | 可保存 A 返回值 | A Evaluator 生成并以 A Secret 签名 |
| Evidence 候选 | 可作为不可信行为线索 | 可转发 | A 规则表决定 score/strength/reliability 等字段 |
| Score-bearing Evidence | 不可生成/修改 | 只能保存、回传 A 已签对象 | Schema、当前 rule version、A HMAC、重复 ID |
| Skill Mirror / Evidence History | 不应直接调 A 内部接口 | 数据库权威来源 | Schema、Evidence HMAC、版本、重放检查 |

关键结论：内部 token 只证明“调用者是 B 服务”，不使请求中的 Evidence 自动可信；`/v1/skills/update` 仍要求每条 Evidence 具有 A Evidence Engine 的有效签名。

## 3. 接口暴露级别

| 方法 | 路径 | 级别 | 用途 |
|---|---|---|---|
| GET | `/health` | Public | 服务与版本检查 |
| GET | `/v1/skill-tree` | Public | Python 五维能力树 |
| POST | `/v1/challenges/generate` (`learner`) | Public | 只返回安全题面和公开测试 |
| POST | `/v1/coach/hint` | Public/可由 B 代理 | 渐进提示；不写 Score |
| POST | `/v1/examiner/decide` | Internal | 使用持久化能力状态选择下一题 |
| POST | `/v1/challenges/generate` (`server`) | Internal | 返回隐藏 oracle；仅 B 后端调用 |
| POST | `/v1/evidence/materialize` | Internal | 消费 A 签名 Verification Records |
| POST | `/v1/skills/update` | Internal | 只消费 A 签名可信 Evidence |
| POST | `/v1/assessment/complete` | Internal | 完整可信闭环 |

所有请求模型拒绝未知顶层字段。Public 不等于“已信任”：浏览器数据仍是非权威输入。

## 4. Challenge Generator 与防泄漏

`POST /v1/challenges/generate`

```json
{
  "examiner_decision": {
    "target_skill": "debugging",
    "target_subskill": "boundary_awareness",
    "difficulty": "medium"
  },
  "response_view": "learner"
}
```

- `learner` 为默认值，不需要内部 token；响应不含 `reference_solution`、`test_cases`、`hidden_bugs`、`validation_report`、`provenance`，只含公开测试。
- `server` 必须通过内部 token；响应含隐藏 oracle 和 A 签名 `provenance`。B 必须原样保存内部 Challenge，并且绝不能转发给浏览器。
- 缺 token 或 token 错误返回 401；未配置/过短 token 返回 503。认证失败响应不含任何隐藏内容。

## 5. B 原始记录签名规范

`/v1/assessment/complete` 中的 `action_logs`、`code_versions`、`test_results`、`hint_history` 必须来自可信 B 后端并签名。通用字段：

```json
{
  "record_type": "test_result",
  "user_id": "U1",
  "session_id": "S1",
  "challenge_id": "DBG001",
  "run_id": "RUN-1",
  "passed": 4,
  "total": 4,
  "scope": "hidden_and_public",
  "submission_digest": "sha256:<64 hex>",
  "challenge_digest": "sha256:<64 hex>",
  "provenance": {
    "version": "trust-envelope/1.0",
    "algorithm": "HMAC-SHA256",
    "issuer": "skillmirror-b",
    "purpose": "b-runtime-record",
    "signature": "hmac-sha256:<64 hex>"
  }
}
```

`record_type` 分别为 `action_log`、`code_version`、`test_result`、`hint_record`。测试结果额外绑定：

- `submission_digest = content_digest(submitted_code)`；
- `challenge_digest = challenge.content_hash`。

签名输入为规范 JSON：`{"envelope": <不含 signature 的固定元数据>, "payload": <不含 provenance 和 verification_status 的记录>}`，键排序、无多余空格，使用 UTF-8 和 HMAC-SHA256。Python 联调可直接使用 `skill_engine.provenance.sign_b_record`。A 会验证 HMAC、用户/会话/挑战、类型和两个摘要，再将 `verification_status` **覆盖**为 `verified` 或 `unverified`；调用者写入的同名字段不参与信任判断。

## 6. Evidence Materialization

`POST /v1/evidence/materialize` 为内部接口。`context` 必须含：

`user_id/session_id/challenge_id/challenge_digest/challenge_type/target_skill/target_subskill/difficulty`。

`verification_records` 必须是 A Evaluator 生成并由 A Secret 签名的标准化记录。普通 B 原始记录或自声明 `status=verified` 不能直接在此落 Evidence。

Evidence Engine 只接受已知规则和满足 required record types 的引用。`skill`、`sub_skill`、`performance_score`、`score_delta`、`strength`、`difficulty`、`reliability`、`direction` 均由 A 的规则/上下文锁定。accepted Evidence 带 `rule_version`、`challenge_digest`、`source_digest` 和 A HMAC。

正常集成优先调用完整闭环，而不是由 B 手工编排该低层接口。

## 7. Score / Confidence

`POST /v1/skills/update` 为内部接口：

```json
{
  "skill_id": "debugging",
  "previous_score": 70,
  "trusted_evidence": [],
  "trusted_evidence_history": []
}
```

旧字段 `new_evidence` / `evidence_history` 会被 422 拒绝。每条对象必须同时满足：Evidence Schema 2.1、当前 `rule_version`、A Evidence Engine HMAC、唯一 `evidence_id`。新 Evidence 与 history 重复时按重放拒绝。

因此，即使内部调用者提交 `performance_score=100`、`strength=strong`、`difficulty=expert`、`reliability=1`，只要对象未由 A Materialization 签名或签名后被修改，就不能影响 Score 或 Confidence。

## 8. 完整闭环

`POST /v1/assessment/complete` 为 B→A 主接口。必填：`user_id`、`session_id`、`skill_mirror`、A 签名的内部 `challenge`、`submitted_code`。B 应同时提供签名后的原始记录、完整可信 Evidence History 和 Previous Challenges。

A 的处理顺序：

1. 验证内部 token；
2. 验证 A Challenge HMAC、内容摘要和 executable oracle；
3. 验证每条 B record 的 HMAC、身份、类型与提交/挑战绑定；
4. 覆盖调用者的 `verification_status`；
5. Evaluator 生成 A 签名 Verification Records；
6. Evidence Engine 规则物化并签名 Evidence；
7. 过滤无效 history 与重放 Evidence；
8. 确定性更新 Score / Confidence / Next Examiner。

`trust_report` 明示 rejected B records、rejected history、replayed Evidence，并固定返回 `caller_verification_status_trusted=false`。A 不在该接口中执行任意学员代码；真实执行与生产隔离是 B Sandbox/Test Runner 的可信职责。

## 9. 错误约定

| HTTP | 含义 |
|---|---|
| 200 | 请求成功；业务拒绝项在 `rejected`、`flags` 或 `trust_report` |
| 401 | 内部 token 缺失或错误 |
| 422 | 字段、Schema、Challenge、HMAC、rule version、身份绑定或重放无效 |
| 503 | 必需安全环境变量未配置或不足 32 字节 |
| 500 | 未预期错误；生产部署应返回 trace ID 且不得泄漏隐藏题目 |

健康检查：`GET /health`。OpenAPI：`GET /docs` 或 `GET /openapi.json`。默认无需 LLM；如注入模型，Schema、权限锁与 fallback 仍然生效。

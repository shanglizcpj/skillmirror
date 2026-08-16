# SkillMirror A-side Agent Test Report v2.1

## 封版结果

验证日期：2026-08-14。环境：Python 3.12，Linux 容器。

| 检查 | 命令/方式 | 结果 |
|---|---|---|
| Python 编译 | `python -m compileall -q .` | PASS |
| 自动测试 | `python -m pytest -q` | 135 passed |
| JSON / Schema | 全部 JSON 解析 + Draft 2020-12 Schema 自校验 | PASS |
| 五类 Challenge | 参考答案/Starter 受限子进程实跑 | 5/5 oracle 有效 |
| Agent 异常 | 超时、异常、错误 JSON、Schema 错、超大输出 | PASS，均 fallback |
| HTTP API | FastAPI TestClient | PASS |
| ASGI 启动烟测 | Uvicorn + `/health` + `/openapi.json` | 200 / 8 paths |
| 完整模拟闭环 | `python demo/run_a_demo.py` | PASS |

测试运行出现一条来自 FastAPI TestClient 依赖层的弃用警告，不影响接口行为；未发现失败测试。

## 测试覆盖的主要风险

- Examiner：Unknown/低 Confidence 优先、近期重复惩罚、无效镜像、LLM 篡改决策。
- Challenge：目标不一致、危险 import/属性/文件调用、坏参考答案、错误 Hint 数、超时。
- Coach：无请求不提示、三级升级、答案/代码块/函数定义/Prompt Injection 泄漏。
- Evaluator：空提交、公开测试冒充隐藏测试、未验证结果、计数畸形、复制风险、非 Debugging 误打标签。
- Evidence：未知事件、无引用、未验签、跨会话/Challenge digest、候选伪造分数/技能/强度/可靠度、A Verification Record HMAC、重复候选。
- Score：Unknown、70→76、Hint 收缩、同会话相关上限、跨技能排除、重复 ID、NaN/Infinity、A Evidence HMAC/rule version fail closed。
- Confidence：多事件单会话不膨胀、独立会话增长、重复 ID、过期/未来时间、多样性、一致性、伪造 Evidence 不抬高置信度。
- API：未知字段 422、内部接口无 token 401、server view 无/错 token 防泄漏、缺配置 503、完整签名 assessment、错误前置条件。
- 对抗信任边界：unsigned 100/strong/expert Evidence、已签 Evidence 篡改、旧任意 Evidence 字段、Evidence 重放、自声明 verified、B record 篡改、无签名 Challenge。

## 可复现模拟闭环

模拟序列不是实际用户实验。代码提交和测试执行是真实的受限本地子进程运行：

```text
Examiner target       debugging / boundary_awareness
Verified tests        4 / 4
Coach                 Level 1
Skill Score           84.75 / provisional
Confidence            28.7% / low / 1 independent session
Next target           testing
```

这组结果刻意展示“高表现、低把握”：一个任务可以形成较高的暂定分，但不能产生高 Confidence。

## 未覆盖/不应夸大的范围

- 没有真实学习者样本、A/B 测试、测量信效度或教育效果结论。
- 没有对生产级恶意学员代码沙箱做安全认证；A 侧质量门仅用于受控题目代码。
- 已覆盖 A/B 内部 token 与 HMAC 代码路径，但没有 TLS/WAF、Secret Manager/轮换、负载、并发、持久化、端到端浏览器或生产部署安全认证。
- 算法参数为 MVP 专家参数；封版测试证明实现一致性，不证明参数已科学标定。

## v2.1 对抗测试结论

| 攻击输入 | 预期/实际结果 |
|---|---|
| 无签名的 100 分 strong/expert Evidence | Schema/Engine 排除，旧分保持不变 |
| 把真实已签 Evidence 改成 100/expert/reliability 1 | HMAC 失效，API 422；Engine 不计分 |
| 普通调用 `/v1/skills/update` | 无 token 401；即使有内部 token仍需 A Evidence HMAC |
| server Challenge 无 token或错 token | 401，响应不含参考答案、隐藏测试、hidden bugs |
| Test Result 自写 `verification_status=verified` | A 覆盖为 unverified，不产生 Evidence，Score 不变 |
| 修改 B 已签 Test Result 的 passed/total | B HMAC 失效，不产生 Evidence |
| 相同 Evidence ID 再作为新证据提交 | API 422 或完整闭环从本次 Score 更新中排除 |

以上是自动化工程测试结果，不是生产渗透测试或第三方安全审计。

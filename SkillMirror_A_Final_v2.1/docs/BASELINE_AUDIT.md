# SkillMirror_A_Final_v1.0 基线审计与修复记录

审计对象：用户提供的 `SkillMirror_A_Final_v1.0(2).zip`。依据：GOAI Boundless Agents 参赛手册、`AB分工.docx`、代码与实际运行结果。

## 1. 基线实际结果

- 压缩包可解压，清单校验通过。
- Python compileall 通过。
- 基线 27 项 pytest 通过，基线 Demo 能运行。
- 目录表面覆盖 A1–A12，但“测试通过”不能证明关键业务约束正确。

## 2. 关键问题与风险

| 严重度 | 发现 | 答辩/产品风险 | v2.0 修复 |
|---|---|---|---|
| Critical | Evidence Candidate 可覆盖 skill、strength、performance_score 等规则字段 | LLM 可间接拍分，无法回答“为什么” | 候选只提交事件+引用；所有评分字段由版本化规则锁定 |
| High | Evidence Schema 使用 `score_delta`，运行时输出 `score_delta_rule` | 接口/材料不一致，B 侧接入失败 | 统一 v2 Evidence Schema 与运行时字段 |
| High | 一道 Challenge 的多个事件被 Confidence 当独立证据 | 单题即可出现 73.2% 高 Confidence，结论失真 | 按 `session_id` 聚合，增加 independence gate；同一闭环为 28.7% |
| High | Challenge 只做语法级检查 | 错测试、坏答案仍可能进入 Demo | Schema + AST allowlist + reference/starter 受限子进程 oracle |
| High | Evaluator 把完成结果硬编码到 Debugging | Testing/Coding 任务会被错误归因 | 结果 Evidence 动态映射 target skill/subskill；Debugging 过程事件仅对 Debugging 生效 |
| High | Prompt 文件存在但运行时未加载 | Prompt Engineering 交付与实际代码脱节 | 统一 `render_prompt` 运行时加载并注入 Schema/不可信数据 |
| High | 没有可调用 API，文档却要求与 B 对接 | A/B 集成只能复制函数，联调风险高 | 新增 FastAPI、严格请求模型、OpenAPI 和完整 assessment 接口 |
| Medium | verified 状态、用户/会话/挑战绑定不足 | 日志伪造或串线可成为 Evidence | Verification Record 必须同用户/会话/挑战且含 payload digest |
| Medium | Score 对同一任务多个高度相关事件累加 | 单次任务权重过大 | 每会话上限 0.4，总更新上限 0.6，并返回 session breakdown |
| Medium | LLM fallback 覆盖不完整 | 现场网络/模型异常导致 Demo 中断 | 通用超时、异常、大小限制、JSON/Schema fail-closed fallback |
| Medium | 旧测试大多为 happy path | “27 passed”无法覆盖伪造/泄漏/异常 | 重建为 115 项，含异常、安全、Schema、API 与闭环 |
| Medium | 历史样例字段和当前 Schema 不一致 | 评委复现得到不同结果 | 删除误导历史输出，用 v2 实际导出样例替代 |

## 3. “伪 Agent”判断

基线并非完全伪造：四个角色都有可运行函数和 fallback。但部分 Agent 只是把固定逻辑包在角色名称下，Prompt 未运行时加载，Evaluator 候选字段还能决定评分，导致 Agent 与确定性引擎边界不真实。v2.0 将职责重新锁定：Agent 负责选择、生成、提示、解释；验证、规则、Score、Confidence 由可测试的确定性层负责。

## 4. 硬编码的合理与不合理

- 合理：固定 challenge fallback、规则版本、算法权重与阈值集中配置，用于无模型可复现 MVP。
- 不合理：把 target skill 固定为 Debugging、让候选决定 performance score、把一次任务的事件条数当证据数量。

修复后仍保留的权重、阈值和 performance score 是**显式 MVP 专家参数**，不是官方标准、不是统计拟合结果，也不冒充真实实验结论。

## 5. 对官方评审要求的影响

v2.0 直接加强官方权重最高的任务闭环与 Agent 能力，并补齐 Demo 可复现、失败分支、结果依据、数据边界和开放复用材料。仍需团队层面由成员 B 完成真实产品体验、生产部署与视频 Demo，才能形成完整赛事作品。

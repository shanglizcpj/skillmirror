# A1–A12 逐项可追溯验收

本表依据 `AB分工.docx` 的成员 A 清单核对，不以文件中的“完成”字样作为证据。

| 项 | 分工要求 | 实现证据 | 验证证据 | 结论 |
|---|---|---|---|---|
| A1 | 五维 Skill Tree 与二级能力 | `skill_tree.json`, `skill_engine/skill_tree.py`, Schema | 技能唯一性、父子归属、五维顺序测试 | 已实现 |
| A2 | Evidence 结构、规则、强弱等级 | `evidence_rules.json`, `skill_engine/evidence.py`, `provenance.py`, Evidence Schema | 伪造字段、HMAC、未知事件、跨会话、未验证、重复/重放测试 | 已实现 |
| A3 | Unknown 冷启动、Evidence/Difficulty/Hint 更新、原因 | `skill_engine/skill_engine.py` | 70→76、提示影响、会话相关上限、非有限值、Schema 测试 | 已实现；参数待真实标定 |
| A4 | 数量、强度、新鲜度、多样性、一致性 | `skill_engine/confidence_engine.py` | 单会话不膨胀、重复/过期/未来时间、独立会话增长测试 | 已实现；参数待真实标定 |
| A5 | Examiner 输入状态/历史，输出目标/难度/原因 | `agents/examiner/agent.py` | Unknown 优先、近期重复惩罚、LLM 不可改目标、Schema 测试 | 已实现 |
| A6 | 代码、描述、问题、测试、难度、三级 Hint；生成后验证 | `agents/challenge_generator/`, `challenge_validation.py` | 五类模板 oracle 实跑，危险代码、坏答案、错测试、超时 fallback | 已实现 |
| A7 | 最小必要提示、主动/自动触发、防泄题 | `agents/coach/agent.py` | 三级升级、代码块/函数/参考答案/注入/超时测试 | 已实现 |
| A8 | 解释过程、输出 Evidence Candidates，不做最终客观判定 | `agents/evaluator/agent.py` | public-only、unverified、空提交、复制风险、动态技能、Schema 测试 | 已实现 |
| A9 | Score×Confidence 四象限自适应 | `skill_engine/adaptive.py` | 五组象限/Unknown 与非法数值测试 | 已实现 |
| A10 | 四类运行时 Prompt、结构化输出、Schema、防注入、fallback | `prompts/`, `agents/common.py`, LLM 输出 Schema | 运行时模板检查、异常/超时/超大/Schema 错误测试 | 已实现 |
| A11 | 正常与异常 Agent 测试 | `tests/agent`, `tests/skill_engine`, `tests/api` | 封版执行 135 passed，含伪造 Evidence、verified 冒充、隐藏题泄漏 | 已实现 |
| A12 | A 侧全部代码、架构、运行与交付材料 | 根目录、`docs/`, `demo/`, 最终 ZIP | compileall、pytest、API、完整闭环、ZIP 解包复验 | 已实现 |

## 与原分工的工程增强

- 分工中的 `challenge_policy.py` 在本包命名为 `skill_engine/adaptive.py`，职责一致。
- 新增 JSON Schema 运行时校验、相关证据上限、稳定 Evidence ID/摘要、分层 HMAC provenance、挑战 executable oracle、FastAPI 内部认证与完整 pipeline。
- Coding 与 Code Reading 的二级能力是项目扩展，已在 `skill_tree.json` 标注，不冒充 AB 文档原文。

## B 侧仍需完成

真实前端、身份系统、数据库、Action Logger、生产级学员代码 Sandbox、Test Runner、隐藏测试保管和部署仍属于成员 B。B 必须签名运行记录、保管内部 token/B Secret并携带完整 Evidence History；A-only Evidence Secret 不得共享。本包提供 API 和数据契约，不宣称替代 B 侧产品系统。

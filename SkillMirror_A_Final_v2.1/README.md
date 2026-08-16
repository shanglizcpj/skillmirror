# SkillMirror｜成员 A 可运行交付包 v2.1

SkillMirror 是一个基于任务证据的 AI 能力数字孪生 Agent。第一验证场景为 **Programming Skill Assessment / Python**：它观察学习者完成真实编程任务的过程，将可核验行为转成 Evidence，再用确定性算法更新 Skill Score 与 Confidence，并选择下一项最有信息量的挑战。

本包对应成员 A 的 Agent / AI / Skill Engine / 算法职责。它不是成员 B 的完整产品前后端，也不把模拟工程验证冒充真实用户实验。

## 核心原则

- LLM 不直接决定 Score、Confidence、通过状态或 Evidence 权重。
- Evaluator 只提出候选事件；Evidence Engine 必须找到同用户、同会话、同挑战且由 A 验签的记录才接收。
- B Runner/Logger 原始记录使用 B→A HMAC；Challenge、Verification Record 和 Evidence 使用 A 侧 HMAC，调用者自声明 `verified` 无效。
- Score 与 Confidence 自身只消费 Schema 2.1、当前 rule version、A Evidence Engine 验签通过的 Evidence。
- Score 回传公式、权重、会话分组、纳入/排除依据和计算 ID。
- Confidence 按独立任务会话计量，一次任务产生多个事件不会伪装成多份独立证据。
- LLM 错误 JSON、Schema 不符、超时或异常时走确定性 fallback。
- 挑战参考答案与隐藏测试默认不进入 learner API 响应。

## 目录

```text
agents/          Examiner / Challenge Generator / Coach / Evaluator
api/             FastAPI A/B 集成适配层
skill_engine/    Evidence / Score / Confidence / Adaptive / Pipeline
prompts/         运行时实际加载的结构化提示词
schemas/         Draft 2020-12 JSON Schema
tests/           正常、异常、安全、API、端到端测试
examples/        模拟输入、真实执行生成的闭环输出
docs/            审计、算法、架构、合规、答辩、PPT 草稿
demo/            可复现模拟闭环
```

## 环境与运行

推荐 Python 3.11 或 3.12。

```bash
python -m venv .venv
. .venv/bin/activate
python -m pip install -r requirements.txt
python -m compileall -q .
python -m pytest -q
python demo/run_a_demo.py
```

Windows PowerShell 激活命令为 `.venv\Scripts\Activate.ps1`。

启动 A 侧 API。三个值必须不同、至少 32 字节；以下占位符需由部署系统替换：

```bash
export SKILLMIRROR_INTERNAL_TOKEN='<random-32+-bytes>'
export SKILLMIRROR_B_PROVENANCE_SECRET='<different-random-32+-bytes>'
export SKILLMIRROR_A_EVIDENCE_SECRET='<a-only-random-32+-bytes>'
uvicorn api.app:app --host 127.0.0.1 --port 8000
```

随后访问 `http://127.0.0.1:8000/docs`。内部 API 必须使用 `X-SkillMirror-Internal-Token`。成员 B 的签名字段、接口暴露级别与错误约定见根目录 `API_CONTRACT_A.md`，安全依据见 `docs/SECURITY_TRUST_BOUNDARY.md`。

## Demo 的真实性说明

`demo/run_a_demo.py` 使用固定的模拟学习者操作序列，但会在受限本地子进程中**实际执行**提交代码和测试。当前可复现结果：4/4 测试通过，Debugging 冷启动 Score 为 84.75（provisional），Confidence 为 28.7%（low），下一挑战目标为 Testing。

该结果仅证明工程闭环与算法行为，不是用户效果研究。Evidence 权重、阈值和 performance score 属于 MVP 专家参数，尚未用真实学习者数据标定。

## A/B 边界

成员 A 提供决策、挑战、提示、解释、Evidence、Score、Confidence 与完整闭环 API。成员 B 仍负责真实 Web 产品、身份认证、数据库、Action Logger、生产级 Python Sandbox、Test Runner、隐藏题保管、完整 Evidence History、部署和前端展示。浏览器不能接触内部 token、B/A Secret 或 server Challenge。A 会重验 B 签名记录和内容绑定；本包中的挑战质量门只执行内置/生成题目的受限代码，不是接收任意学员代码的生产沙箱。

## 建议阅读顺序

1. `docs/BASELINE_AUDIT.md`：原 v1.0 的问题与修复证据。
2. `docs/A1_A12_TRACEABILITY.md`：与 AB 分工逐项对应。
3. `docs/AGENT_ARCHITECTURE.md`：确定性与 LLM 的边界。
4. `docs/SCORE_CONFIDENCE_ALGORITHM.md`：为什么是这个分数。
5. `docs/A_MEMBER_DEFENSE_GUIDE.md`：答辩口径。
6. `docs/SECURITY_TRUST_BOUNDARY.md`：A/B/浏览器信任边界与威胁验证。
7. `docs/PPT_A_SECTION_DRAFT.md`：成员 A 幻灯片草稿。

## 开放与合规

当前交付包未代替团队选择开源许可证；正式公开前请由团队确认许可证并补入仓库。依赖与边界见 `docs/THIRD_PARTY_DEPENDENCIES.md` 和 `docs/DATA_COMPLIANCE_AND_LIMITS.md`。

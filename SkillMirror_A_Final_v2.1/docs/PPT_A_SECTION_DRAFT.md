# PPT 中成员 A 部分内容草稿

建议占整套路演 5–6 页，现场 Demo 由成员 B 页面承接。

## Slide A1｜传统编程测评只看结果，SkillMirror 看可验证过程

标题句：**从“一次答对”升级为“持续更新的能力数字孪生”**

- 输入：真实 Python Challenge、运行、修改、测试、Hint。
- 输出：五维 Skill Mirror、Evidence Report、下一挑战。
- 差异：不是聊天问答，不是 LLM 主观打分。

讲解：传统测评看最终答案；SkillMirror 用任务过程回答“会什么、证据是什么、还需要验证什么”。

## Slide A2｜Agent 闭环与职责边界

主图：Examiner → Challenge → Workspace/Runner → Coach/Evaluator → Evidence → Score/Confidence → Next。

- Examiner：测什么。
- Generator：怎么测，必须过 executable oracle。
- Coach：最小必要提示。
- Evaluator：解释过程，只提候选 Evidence。

页脚：LLM 负责语言与生成；确定性层负责验证与评分。

## Slide A3｜Evidence 防伪链

主图：B-signed raw record → A-signed Verification Record → Candidate → Rule-locked A-signed Evidence → Score。

- 同 user/session/challenge 强绑定。
- hidden test 才能证明完成。
- rule ID/version + verification refs + source digest + A HMAC。
- Candidate 无权覆盖 skill/score/strength/reliability。
- 自声明 verified 与伪造 100/expert Evidence 均不能过 Score Engine。

讲解演示一条 `challenge_tests_passed` Evidence 的来源。

## Slide A4｜Score 与 Confidence 双轴

左侧公式：历史分与会话 Evidence 加权；Hint 向 50 收缩；同会话权重封顶。

右侧四象限：教学 / 验证 / 拔高 / 基础诊断。

醒目数字：**Score 84.75 provisional ≠ Confidence 28.7% low**。

讲解：高分低 Confidence 说明“表现好，但只有一次证据”，所以继续验证。

## Slide A5｜失败也能稳定运行

- LLM 超时/坏 JSON/Schema 错 → deterministic fallback。
- 错题/危险代码/坏参考答案 → 固定已验证 Challenge。
- Coach 疑似泄题 → 固定渐进提示。
- public/unverified/跨会话记录 → Evidence 拒绝。
- learner view 公开；server view 无/错内部 token 均 401，不返回隐藏 oracle。

证据：135 tests passed；五类 oracle 全通过；完整签名 HTTP 闭环通过。

## Slide A6｜创新、边界与下一步

创新：Evidence-driven scoring、分层 provenance、Score–Confidence 解耦、correlation-aware confidence、executable challenge gate。

边界：模拟工程验证不是真实用户实验；不替代教师评价；生产沙箱/认证/数据库由 B 侧完成。

下一步：真实授权样本、专家标注、题目难度标定、信效度/公平性评估、多语言迁移。

## 现场口播收束

> 我们不是让 AI 猜一个分数，而是让每个判断都能回到一次真实任务、一条验证记录和一条版本化规则；当证据不足时，系统也会明确说“不确定”，并用下一项挑战主动补证据。

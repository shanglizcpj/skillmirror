# 成员 A 答辩讲解手册

## 30 秒版本

我负责 SkillMirror 的“大脑”。我们不让 LLM 直接判断“这个学生 Debugging 84 分”，而是让它在受限权限下选择任务、生成候选题、给渐进提示和解释过程。最终通过状态来自隐藏测试，Evidence 必须引用同会话的 verified 记录，Score 与 Confidence 由确定性公式计算。所以我能从 84.75 一路追溯到哪道题、哪些日志、哪条规则、什么权重；同时因为只有一个独立任务，Confidence 只有 28.7%，系统会继续验证而不是过度下结论。

## 3 分钟讲解顺序

1. 痛点：传统题库只看答案，聊天模型直接打分不稳定、不可追溯。
2. 状态：五维 Skill Tree，每维分为 Score 与 Confidence。
3. 闭环：Examiner → Challenge → B 侧执行/记录 → Coach → Evaluator → Evidence → Score/Confidence → Next Challenge。
4. 权限：LLM 负责语言与生成，确定性层负责验证和测量。
5. 证据：每条 Evidence 绑定 user/session/challenge/challenge digest、验证引用、规则版本、source digest 和 A HMAC。
6. Demo：实际执行 4/4；84.75 provisional；28.7% low；下一目标 Testing。
7. 边界：模拟操作非真实实验，参数待标定，不替代教师评价。

## 高频问题

### 为什么是 84.75？

隐藏测试通过、主动运行、边界测试和复现错误分别命中规则；每条规则给出 performance score、strength、difficulty 和 reliability。Hint 将独立表现向 50 收缩；同一 session 的总权重封顶为 0.4。冷启动取该 session 的加权 Evidence Score，得到 84.75，并标为 provisional。完整 breakdown 在 API 输出里。

### 为什么 Confidence 不是 73%？

原包把同一题的多个事件当成多份独立证据，导致单题 73.2%。修复后按 session 聚合，五因子再乘 independence gate，所以一个 session 只有 28.7%。这更符合“高表现但证据不足”。

### LLM 到底做了什么？

Examiner 的理由、Challenge 候选、Coach 安全措辞和 Evaluator 文字解释。LLM 不能改目标、客观通过、Evidence 规则、Score 或 Confidence。完全不配置模型，Demo 仍能运行。

### 这是不是为了多 Agent 而堆 Agent？

不是。四个 Agent 分别回答“测什么、怎么测、帮多少、如何解释”。Score/Confidence 没有包装成 Agent，因为它们应该是确定性引擎。每个角色都有独立输入输出和异常测试。

### Challenge 怎么保证不是错题？

先过 JSON Schema 和 AST 安全策略，再在受限子进程中执行参考答案与 Starter：参考答案必须全过，Starter 必须至少失败一项；否则用固定已验证题。

### Evidence 会不会被模型或 API 调用者伪造？

不会直接影响分数。Candidate 里的 skill、strength、score、reliability 全部无效；B 原始记录先验 HMAC、身份和提交/挑战摘要，A 再签 Verification Record，Evidence Engine 按版本化规则重建并签名 Evidence。Score/Confidence 最后再次验证 Schema、当前 rule version 和 A HMAC。自动测试证明伪造 100 分 strong/expert Evidence 与篡改已签 Evidence 都不会改变分数。

### 调用者写 `verification_status=verified` 会怎样？

A 不信任这个字符串。Pipeline 根据 B record HMAC、user/session/challenge、record type、submission digest 和 challenge digest 重建状态，并覆盖调用者字段。无签名记录即使写 verified，也不会形成 Evidence。

### 隐藏测试怎么防止被浏览器拿到？

learner view 保持公开并使用字段白名单；server view 在返回 oracle 前强制校验环境变量注入的内部 token。无 token、错 token 都返回 401 且不含隐藏内容。B 只能在后端保存 server Challenge，不能转发或公共缓存。

### 使用 Hint 是否直接扣能力？

不是。Hint 表示独立性降低，公式把表现向中性值 50 收缩；同时形成 dependency Evidence。第一次失败是中性过程事实，连续无进展或引入回归才可能产生负向证据。

### 真实效果验证了吗？

没有。我们完成的是可复现工程验证：135 项测试和一个实际执行代码的模拟闭环。没有真实学习者样本，不能宣称提高成绩或评分准确率。下一步要做专家标注、真实用户研究、信效度和公平性评估。

### A 与 B 怎么联调？

B 调 A 的 FastAPI。默认 challenge 响应是 learner-safe；server view 需要内部 token。B 的 Runner/Logger 对原始记录签名，调用 `/v1/assessment/complete` 后一次得到 Evaluation、A-signed Evidence、Score、Confidence 和 Next Examiner。B 持有内部 token 与 B Secret，不持有 A Evidence Secret；生产用户认证、数据库和 Sandbox 属于 B。

## 不要说的三句话

- 不要说“LLM 判断他是 84.75 分”；应说“规则与确定性公式根据 verified Evidence 计算”。
- 不要说“测试证明教育效果”；应说“测试证明软件行为与闭环可复现”。
- 不要说“A 侧子进程就是生产沙箱”；应说“它是受控题目质量门，生产学员代码隔离由 B 侧负责”。

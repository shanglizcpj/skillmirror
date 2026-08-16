# Skill Digital Twin 说明

## 1. 定义

SkillMirror 的“能力数字孪生”不是给学习者贴一个静态总分，也不是声称完整复制人的认知。它是一个**限定于 Python 编程任务、随任务证据持续更新的能力状态模型**。

每个一级能力至少包含：

- `score`：当前可观察表现，范围 0–100；没有证据时为 Unknown。
- `confidence`：系统对该 Score 的把握程度，范围 0–1。
- `subskills`：能力内部更细粒度的状态。
- `evidence`：可追溯任务事件，而非自述标签。
- `history`：已测挑战和上下文，用于选择下一任务。

## 2. 为什么是“双轴”而不是单分数

| 状态 | 含义 | Examiner 行为 |
|---|---|---|
| Low Score / Low Confidence | 可能薄弱，但证据也不足 | 基础诊断 |
| Low Score / High Confidence | 已有稳定薄弱证据 | 教学型任务 |
| High Score / Low Confidence | 单次表现好，尚未复核 | 验证型任务 |
| High Score / High Confidence | 稳定掌握 | 更难/迁移任务 |

因此 Demo 中 Score 84.75、Confidence 28.7% 不是冲突：第一次任务表现较好，但只有一个独立会话，系统不能过度确信。

## 3. 更新闭环

1. Examiner 找信息缺口最大的能力。
2. Challenge Generator 产生可验证任务。
3. B 侧记录运行、修改、测试与提示使用。
4. Evaluator 把过程事实整理成候选事件。
5. Evidence Engine 对候选和 verified 记录做规则匹配。
6. Score 估计当前表现，Confidence 估计证据充分度。
7. 更新镜像并选择下一任务。

数字孪生的最小更新单位不是聊天消息，而是一次有 challenge/session 身份、来源摘要和验证记录的 Evidence。

## 4. 适用与不适用

当前适用：Python 编程任务中的 Coding、Debugging、Testing、Problem Solving、Code Reading 五维状态跟踪。

当前不声称：跨语言通用能力、心理/智力测量、正式考试成绩、学校或教师的最终教育评价、就业筛选结论。要扩展这些用途必须重新设计任务、标定参数并开展效度与公平性研究。

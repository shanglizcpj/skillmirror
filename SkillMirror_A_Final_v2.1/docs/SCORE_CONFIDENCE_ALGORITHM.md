# Score 与 Confidence 算法说明

## 1. Score：能力表现有多强

进入公式前存在不可绕过的确定性前置门：Evidence 必须通过 Schema 2.1、当前 rule version 与 A Evidence Engine HMAC；失败项只进入 `excluded_evidence`，其 performance score、strength、difficulty、reliability 和 direction 均不参与计算。API 的同类校验是第一层，Score Engine 自验是第二层。

对每条可计分 Evidence：

$$w_i = w_{strength} \times m_{difficulty} \times reliability$$

Hint 不直接把“会/不会”二分，而是把表现向中性值 50 收缩：

$$p'_i = 50 + (p_i - 50) \times m_{hint}$$

当前 Hint 倍率来自 AB 分工示例：No Hint 1.00、L1 0.95、L2 0.85、L3 0.70、Direct Help 0.50。强度权重为 0.10/0.20/0.30，难度倍率为 0.85/1.00/1.15/1.30；后两组是 MVP 参数。

同一 `session_id` 内先求加权表现，再把总权重封顶为 0.40，避免一个任务产生多个事件而重复放大。跨会话总更新权重 $\alpha$ 封顶 0.60。

有历史分时：

$$Score_{new} = Score_{old}(1-\alpha) + Score_{evidence}\alpha$$

冷启动时直接使用 Evidence Score，但状态标记为 `provisional`，不冒充稳定结论。AB 文档例子 70 + 一条 medium/strong/no-hint/reliability 1.0 的 90 分证据：$70\times0.7 + 90\times0.3=76$，已有自动测试锁定。

输出还包含 calculation ID、公式、每会话 raw/capped weight、每条 Evidence 的调整过程和排除理由。

## 2. Confidence：系统有多确定

Confidence 不是 LLM 自信程度，也不是测试通过率。它由五个 0–1 因子组成：

| 因子 | 权重 | 当前计算 |
|---|---:|---|
| Quantity | 30% | 独立 session 数的饱和函数 $1-e^{-n/3}$ |
| Strength | 20% | 各 session 最强证据均值 |
| Freshness | 20% | 30 天半衰期 |
| Diversity | 15% | challenge type + difficulty 上下文，4 类饱和 |
| Consistency | 15% | session 分数标准差；单 session 固定 0.35 |

先计算加权五因子，再乘独立性门：

$$Confidence = WeightedFactors \times (0.30 + 0.70\times Quantity)$$

重复 Evidence ID 被忽略；同一 session 的多个事件仍只计一个独立会话；未来时间不算新鲜并产生 warning；非计分 dependency Evidence 不进入 Confidence。Confidence 也独立执行 Schema/rule version/A HMAC 校验，伪造高分证据不能抬高置信度。

## 3. Demo 为什么是 84.75 / 28.7%

模拟任务中，隐藏测试通过、主动运行、主动边界测试、复现错误形成四条 Debugging 计分 Evidence；使用 L1 Hint 形成 Problem Solving dependency Evidence，不直接给 Debugging 加分。四条 Debugging Evidence 同属一个 session，权重被相关性上限限制，冷启动结果为 84.75 且为 provisional。

Confidence 看到的仍是**一个独立 session**，因此 quantity 和 diversity 有限，独立性门进一步抑制结果，得到 28.7% / low。下一题转向 Testing，而不是把单次成功解释成 Debugging 已稳定掌握。

## 4. 参数治理

每次规则/公式变更必须升级 `rule_version` 或 `algorithm_version`，旧 rule version 在实时更新入口 fail closed；历史迁移应由独立、审计化流程重签，不能在请求中静默接受。真实上线前需要：专家标注集、题目难度校准、信效度分析、群体公平性检查、参数敏感性分析与版本迁移策略。

# 技术创新总结

## 1. Evidence-driven，而不是 LLM-driven scoring

常见方案让模型读代码后直接给能力分。SkillMirror 把语言理解与测量权分开：LLM 只能提出候选事件，Evidence Engine 用客观记录和规则物化，Score/Confidence 再确定性计算。这使每个分数都能回到 challenge、session、record 和规则版本。

## 2. Score–Confidence 解耦的能力数字孪生

单一分数无法区分“稳定掌握”和“偶然成功”。双轴状态让 Examiner 针对同样的高分采取不同动作：低 Confidence 时验证，高 Confidence 时拔高。独立会话聚合进一步防止单次任务事件膨胀。

## 3. 生成式挑战的 executable oracle gate

挑战不是只满足 JSON 格式就可用。系统同时检查目标/难度锁定、Schema、AST 安全、参考答案全通过、Starter 至少失败一项。失败即回退到已验证模板，保障无 LLM 时也可复现。

## 4. 教育友好的受控 Coach

Coach 把“什么时候帮”和“怎么表达”拆开：确定性策略决定提示级别，LLM 只做安全措辞；参考答案相似度、代码块、函数定义和行级匹配共同构成泄题门。失败时返回固定三级 Hint。

## 5. 可复用工程接口

算法层无框架耦合，通过 JSON Schema 和 FastAPI 暴露；同一 pipeline 可被 Web、桌面端或其他教育任务调用。五类内置挑战、示例、测试和 OpenAPI 形成可验证模板。

## 6. 分层 provenance 与最小信任

v2.1 用三个分离的信任能力控制数据流：内部 token 认证 B 服务，B Secret 绑定 Runner/Logger 原始记录，A-only Secret 绑定 Challenge、Verification Record 与最终 Evidence。Score 和 Confidence 不是因为字段名叫 trusted 就接收，而是自己再次验 Schema、rule version 和 HMAC；这使 API 适配层失误也不等于评分旁路。

## 7. 不夸大的创新边界

当前创新是架构与工程机制，不是已经完成的教育测量学突破。权重尚未真实标定，数字孪生只覆盖 Python 任务行为，挑战质量门也不是生产沙箱。这些限制已写入材料并作为下一阶段研究计划。

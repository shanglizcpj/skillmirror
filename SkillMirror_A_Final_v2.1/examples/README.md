# Examples

这些 JSON 使用 `python demo/export_examples.py` 从可执行模拟闭环生成，不是实际学习者数据。

- `skill_mirror_before.json`：Examiner 输入示例。
- `full_a_demo_output.json`：完整闭环输出，其中测试代码真实执行。
- `evidence_examples.json`：该闭环物化的 v2.1 A-signed Evidence。
- `skill_update_input.json`：`/v1/skills/update` 的可信对象结构示例；签名只与生成它的单次 Demo 临时密钥匹配，不能跨进程直接重放。

Demo 每次运行都会生成新的临时签名密钥，避免在源码中放置可复用 Secret；可复现的是测试、Score、Confidence 和决策结果，而不是签名字符串本身。

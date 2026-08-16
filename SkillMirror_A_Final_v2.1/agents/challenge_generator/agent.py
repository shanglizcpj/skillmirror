"""Challenge Generator (A6) with executable oracle validation and fallback."""
from __future__ import annotations

from copy import deepcopy
from typing import Any, Dict

from agents.common import render_prompt, safe_llm_json
from skill_engine.challenge_validation import validate_challenge
from skill_engine.skill_tree import validate_skill_pair


def _case(case_id: str, args: list, expected: Any = None, *, visibility: str = "hidden", expected_exception: str | None = None) -> Dict[str, Any]:
    item: Dict[str, Any] = {"case_id": case_id, "visibility": visibility, "args": args, "kwargs": {}}
    if expected_exception:
        item["expected_exception"] = expected_exception
    else:
        item["expected"] = expected
    return item


TEMPLATES: Dict[str, Dict[str, Any]] = {
    "debugging": {
        "schema_version": "2.0",
        "challenge_id": "DBG001",
        "target_skill": "debugging",
        "target_subskill": "boundary_awareness",
        "difficulty": "medium",
        "challenge_type": "debugging_runtime",
        "title": "Repair the Order Discount Function",
        "task_description": "修复订单折扣函数，使其正确处理空订单、单个商品和普通订单，并通过全部测试。",
        "entry_point": "discounted_total",
        "starter_code": "def average_price(prices):\n    total = sum(prices)\n    return total / len(prices)\n\ndef discounted_total(prices, threshold=100):\n    avg = average_price(prices)\n    total = sum(prices)\n    if avg > threshold:\n        return total * 0.9\n    return total\n",
        "test_cases": [
            _case("normal", [[50, 60]], 110, visibility="public"),
            _case("discount", [[120, 140]], 234),
            _case("single", [[200]], 180),
            _case("empty", [[]], 0),
        ],
        "hidden_bugs": ["empty list causes ZeroDivisionError"],
        "hints": [
            "先观察失败输入与异常类型，它是否说明某个集合可能没有元素？",
            "重点检查 average_price 在 prices 为空时的行为。",
            "思考在执行除法前，如何为长度为 0 的情况定义合理结果。",
        ],
        "reference_solution": "def average_price(prices):\n    if not prices:\n        return 0\n    return sum(prices) / len(prices)\n\ndef discounted_total(prices, threshold=100):\n    if not prices:\n        return 0\n    avg = average_price(prices)\n    total = sum(prices)\n    if avg > threshold:\n        return total * 0.9\n    return total\n",
    },
    "testing": {
        "schema_version": "2.0",
        "challenge_id": "TST001",
        "target_skill": "testing",
        "target_subskill": "boundary_testing",
        "difficulty": "medium",
        "challenge_type": "testing_edge_cases",
        "title": "Expose Pagination Edge Cases",
        "task_description": "根据边界测试结果修正分页函数，并解释整数倍、零条记录与非法页大小的测试意义。",
        "entry_point": "page_count",
        "starter_code": "def page_count(total, page_size):\n    return total // page_size + 1\n",
        "test_cases": [
            _case("ordinary", [21, 10], 3, visibility="public"),
            _case("exact_multiple", [20, 10], 2),
            _case("zero_total", [0, 10], 0),
            _case("bad_size", [20, 0], expected_exception="ValueError"),
        ],
        "hidden_bugs": ["exact multiples return one extra page", "page_size <= 0 has no explicit policy"],
        "hints": [
            "先找商和余数刚好落在边界上的输入。",
            "试试 total 恰好是 page_size 的整数倍，以及 total=0。",
            "先定义 page_size<=0 的异常策略，再使用向上取整公式。",
        ],
        "reference_solution": "def page_count(total, page_size):\n    if page_size <= 0:\n        raise ValueError('page_size must be positive')\n    return (total + page_size - 1) // page_size\n",
    },
    "coding": {
        "schema_version": "2.0",
        "challenge_id": "COD001",
        "target_skill": "coding",
        "target_subskill": "function_design",
        "difficulty": "easy",
        "challenge_type": "implementation",
        "title": "Implement a Safe Counter",
        "task_description": "实现 safe_increment(value, step)，只接受整数并返回递增结果。",
        "entry_point": "safe_increment",
        "starter_code": "def safe_increment(value, step=1):\n    pass\n",
        "test_cases": [
            _case("basic", [3, 2], 5, visibility="public"),
            _case("default", [3], 4),
            _case("negative", [-2, 3], 1),
            _case("bad_type", ["3", 1], expected_exception="TypeError"),
        ],
        "hidden_bugs": [],
        "hints": [
            "先明确函数对输入类型的约束。",
            "可以用 isinstance 分别检查 value 与 step。",
            "类型验证通过后再返回 value + step。",
        ],
        "reference_solution": "def safe_increment(value, step=1):\n    if not isinstance(value, int) or not isinstance(step, int):\n        raise TypeError('integers required')\n    return value + step\n",
    },
    "problem_solving": {
        "schema_version": "2.0",
        "challenge_id": "PS001",
        "target_skill": "problem_solving",
        "target_subskill": "problem_decomposition",
        "difficulty": "medium",
        "challenge_type": "problem_decomposition",
        "title": "Decompose an Error Counter",
        "task_description": "把错误码统计拆成初始化、遍历和累计三个步骤，并实现 count_errors。",
        "entry_point": "count_errors",
        "starter_code": "def count_errors(codes):\n    pass\n",
        "test_cases": [
            _case("basic", [["E1", "E2", "E1"]], {"E1": 2, "E2": 1}, visibility="public"),
            _case("empty", [[]], {}),
            _case("single", [["E9"]], {"E9": 1}),
        ],
        "hidden_bugs": [],
        "hints": [
            "先把任务分成建立容器、遍历输入、更新计数。",
            "每次遇到错误码时，区分它是否已经出现。",
            "用字典保存频次；已存在则加一，否则初始化为一。",
        ],
        "reference_solution": "def count_errors(codes):\n    counts = {}\n    for code in codes:\n        if code in counts:\n            counts[code] = counts[code] + 1\n        else:\n            counts[code] = 1\n    return counts\n",
    },
    "code_reading": {
        "schema_version": "2.0",
        "challenge_id": "READ001",
        "target_skill": "code_reading",
        "target_subskill": "control_flow_tracing",
        "difficulty": "easy",
        "challenge_type": "code_trace",
        "title": "Trace an Alternating Sum",
        "task_description": "阅读交替加减逻辑，补全 trace_result，使其返回给定列表的最终状态值。",
        "entry_point": "trace_result",
        "starter_code": "def trace_result(nums):\n    pass\n",
        "test_cases": [
            _case("three", [[5, 2, 4]], 7, visibility="public"),
            _case("empty", [[]], 0),
            _case("four", [[8, 1, 3, 2]], 8),
        ],
        "hidden_bugs": [],
        "hints": [
            "逐轮记录下标、当前值和累计值。",
            "偶数下标做加法，奇数下标做减法。",
            "从 0 开始遍历，并依据 i % 2 选择正负号。",
        ],
        "reference_solution": "def trace_result(nums):\n    value = 0\n    for i, number in enumerate(nums):\n        if i % 2 == 0:\n            value = value + number\n        else:\n            value = value - number\n    return value\n",
    },
}


def _validated_fallback(skill: str, decision: Dict[str, Any]) -> Dict[str, Any]:
    fallback = deepcopy(TEMPLATES.get(skill, TEMPLATES["debugging"]))
    fallback["difficulty"] = decision.get("difficulty", fallback["difficulty"])
    fallback["target_subskill"] = decision.get("target_subskill") or fallback["target_subskill"]
    report = validate_challenge(fallback)
    if not report["valid"]:
        raise RuntimeError(f"built-in challenge failed its own quality gate: {report['errors']}")
    fallback["generation_source"] = "fixed_verified_template"
    fallback["content_hash"] = report["content_hash"]
    fallback["validation_report"] = report
    return fallback


def generate_challenge(examiner_decision: Dict[str, Any], llm=None, *, llm_timeout_seconds: float = 8.0) -> Dict[str, Any]:
    """Generate then validate a challenge; fall back on every unsafe outcome."""
    skill = str(examiner_decision.get("target_skill", "debugging"))
    if skill not in TEMPLATES:
        raise ValueError(f"unsupported target_skill: {skill}")
    difficulty = examiner_decision.get("difficulty", TEMPLATES[skill]["difficulty"])
    if difficulty not in {"easy", "medium", "hard", "expert"}:
        raise ValueError(f"unsupported difficulty: {difficulty}")
    requested_subskill = examiner_decision.get("target_subskill")
    if requested_subskill and not validate_skill_pair(skill, str(requested_subskill)):
        raise ValueError("target_subskill does not belong to target_skill")
    fallback = _validated_fallback(skill, examiner_decision)
    prompt = render_prompt(
        "challenge_generator",
        {"examiner_decision": examiner_decision, "non_negotiable_target_skill": skill},
        "challenge.schema.json",
    )
    model = safe_llm_json(
        llm,
        prompt,
        schema_name="challenge.schema.json",
        timeout_seconds=llm_timeout_seconds,
    )
    if model:
        target_matches = model.get("target_skill") == skill
        difficulty_matches = model.get("difficulty") == examiner_decision.get("difficulty", model.get("difficulty"))
        report = validate_challenge(model)
        if target_matches and difficulty_matches and report["valid"]:
            model["generation_source"] = "llm_oracle_validated"
            model["content_hash"] = report["content_hash"]
            model["validation_report"] = report
            return model
    return fallback


def public_challenge(challenge: Dict[str, Any]) -> Dict[str, Any]:
    """Return fields safe for the learner client; hidden tests never cross it."""
    result = {
        k: deepcopy(v)
        for k, v in challenge.items()
        if k not in {"reference_solution", "test_cases", "hidden_bugs", "validation_report", "provenance"}
    }
    result["public_tests"] = [
        deepcopy(case) for case in challenge.get("test_cases", []) if case.get("visibility") == "public"
    ]
    return result


__all__ = ["TEMPLATES", "generate_challenge", "public_challenge", "validate_challenge"]

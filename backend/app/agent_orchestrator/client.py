from __future__ import annotations

from typing import Any

import httpx

from .config import get_agent_settings


SENSITIVE_KEYWORDS = (
    "token",
    "secret",
    "signature",
    "reference_solution",
    "test_cases",
    "hidden_bugs",
    "provenance",
)


def sanitize_error_value(
    value: Any,
    *,
    depth: int = 0,
) -> Any:
    """
    清理准备写入日志或返回给路由的A侧错误内容。

    不能让Token、签名、参考答案、隐藏测试等内容
    通过异常信息泄漏到浏览器。
    """
    if depth > 4:
        return "[TRUNCATED]"

    if isinstance(value, dict):
        cleaned: dict[str, Any] = {}

        for key, item in value.items():
            key_text = str(key)
            lower_key = key_text.lower()

            if any(
                keyword in lower_key
                for keyword in SENSITIVE_KEYWORDS
            ):
                cleaned[key_text] = "[REDACTED]"
                continue

            cleaned[key_text] = sanitize_error_value(
                item,
                depth=depth + 1,
            )

        return cleaned

    if isinstance(value, list):
        return [
            sanitize_error_value(
                item,
                depth=depth + 1,
            )
            for item in value[:20]
        ]

    if isinstance(value, str):
        if len(value) > 500:
            return value[:500] + "...[TRUNCATED]"

        return value

    if isinstance(
        value,
        (int, float, bool),
    ) or value is None:
        return value

    return str(value)[:500]


class AServiceError(RuntimeError):
    def __init__(
        self,
        status_code: int,
        path: str,
        response_body: Any,
        *,
        error_type: str = "upstream_error",
        safe_message: str = "A service request failed",
        request_id: str | None = None,
    ):
        self.status_code = status_code
        self.path = path
        self.response_body = sanitize_error_value(
            response_body
        )
        self.error_type = error_type
        self.safe_message = safe_message
        self.request_id = request_id

        # 不把response_body写入异常字符串，
        # 避免隐藏测试、签名或Token进入日志。
        super().__init__(
            f"{safe_message}; "
            f"type={error_type}; "
            f"status={status_code}; "
            f"path={path}; "
            f"request_id={request_id or 'unknown'}"
        )


class AClient:
    def __init__(self):
        self.settings = get_agent_settings()

    def _internal_headers(self) -> dict[str, str]:
        return {
            "Accept": "application/json",
            "X-SkillMirror-Internal-Token":
                self.settings.internal_token,
        }

    def _public_headers(self) -> dict[str, str]:
        return {
            "Accept": "application/json",
        }

    @staticmethod
    def _require_fields(
        body: dict[str, Any],
        *,
        path: str,
        fields: tuple[str, ...],
    ) -> None:
        missing = [
            field
            for field in fields
            if field not in body
        ]

        if missing:
            raise AServiceError(
                502,
                path,
                {
                    "detail":
                        "A response is missing required fields",
                    "missing_fields": missing,
                },
                error_type="invalid_response_schema",
                safe_message=(
                    "A service returned an invalid JSON structure"
                ),
            )

    async def _request(
        self,
        method: str,
        path: str,
        *,
        payload: dict[str, Any] | None = None,
        internal: bool = False,
    ) -> dict[str, Any]:
        headers = (
            self._internal_headers()
            if internal
            else self._public_headers()
        )

        timeout = httpx.Timeout(
            timeout=15.0,
            connect=3.0,
            read=15.0,
            write=10.0,
            pool=3.0,
        )

        try:
            async with httpx.AsyncClient(
                base_url=self.settings.a_base_url,
                timeout=timeout,
                follow_redirects=False,
                trust_env=False,
            ) as client:
                response = await client.request(
                    method,
                    path,
                    json=payload,
                    headers=headers,
                )

        except httpx.ConnectError as exc:
            raise AServiceError(
                503,
                path,
                {
                    "detail":
                        "Cannot connect to A service",
                },
                error_type="connection_error",
                safe_message="A service is unavailable",
            ) from exc

        except httpx.TimeoutException as exc:
            raise AServiceError(
                504,
                path,
                {
                    "detail":
                        "A service request timed out",
                },
                error_type="timeout",
                safe_message="A service timed out",
            ) from exc

        except httpx.RequestError as exc:
            raise AServiceError(
                502,
                path,
                {
                    "detail":
                        "A service network request failed",
                },
                error_type="network_error",
                safe_message=(
                    "A service network request failed"
                ),
            ) from exc

        request_id = response.headers.get(
            "X-Request-ID"
        )

        try:
            decoded_body: Any = response.json()
        except ValueError as exc:
            content_type = response.headers.get(
                "content-type",
                "unknown",
            )

            if response.status_code >= 400:
                raise AServiceError(
                    response.status_code,
                    path,
                    {
                        "detail": (
                            "A service returned an unreadable "
                            "error response"
                        ),
                        "content_type": content_type,
                    },
                    error_type="non_json_error_response",
                    safe_message=(
                        "A service rejected the request"
                    ),
                    request_id=request_id,
                ) from exc

            raise AServiceError(
                502,
                path,
                {
                    "detail":
                        "A service returned non-JSON data",
                    "content_type": content_type,
                },
                error_type="invalid_json",
                safe_message=(
                    "A service returned an invalid response"
                ),
                request_id=request_id,
            ) from exc

        if response.status_code >= 400:
            raise AServiceError(
                response.status_code,
                path,
                decoded_body,
                error_type="http_error",
                safe_message="A service rejected the request",
                request_id=request_id,
            )

        if not isinstance(decoded_body, dict):
            raise AServiceError(
                502,
                path,
                {
                    "detail": (
                        "A service response must be "
                        "a JSON object"
                    ),
                    "received_type":
                        type(decoded_body).__name__,
                },
                error_type="invalid_json_type",
                safe_message=(
                    "A service returned an invalid JSON structure"
                ),
                request_id=request_id,
            )

        return decoded_body

    async def health(self) -> dict[str, Any]:
        body = await self._request(
            "GET",
            "/health",
        )

        self._require_fields(
            body,
            path="/health",
            fields=("status",),
        )

        return body

    async def examiner_decide(
        self,
        skill_mirror: dict[str, Any],
        evidence_history: list[dict[str, Any]],
        previous_challenges: list[dict[str, Any]],
    ) -> dict[str, Any]:
        path = "/v1/examiner/decide"

        body = await self._request(
            "POST",
            path,
            internal=True,
            payload={
                "skill_mirror": skill_mirror,
                "evidence_history": evidence_history,
                "previous_challenges":
                    previous_challenges,
            },
        )

        self._require_fields(
            body,
            path=path,
            fields=(
                "target_skill",
                "target_subskill",
                "difficulty",
            ),
        )

        return body

    async def generate_challenge(
        self,
        examiner_decision: dict[str, Any],
        *,
        response_view: str,
    ) -> dict[str, Any]:
        if response_view not in {
            "server",
            "learner",
        }:
            raise ValueError(
                "response_view must be server or learner"
            )

        path = "/v1/challenges/generate"

        body = await self._request(
            "POST",
            path,
            internal=response_view == "server",
            payload={
                "examiner_decision":
                    examiner_decision,
                "response_view": response_view,
            },
        )

        self._require_fields(
            body,
            path=path,
            fields=(
                "view",
                "challenge",
            ),
        )

        if body["view"] != response_view:
            raise AServiceError(
                502,
                path,
                {
                    "detail":
                        "A returned the wrong challenge view",
                    "expected_view": response_view,
                    "received_view": body["view"],
                },
                error_type="challenge_view_mismatch",
                safe_message=(
                    "A challenge response is invalid"
                ),
            )

        if not isinstance(body["challenge"], dict):
            raise AServiceError(
                502,
                path,
                {
                    "detail":
                        "A challenge must be a JSON object",
                },
                error_type="invalid_challenge",
                safe_message=(
                    "A challenge generation failed"
                ),
            )

        return body

    async def coach_hint(
        self,
        payload: dict[str, Any],
    ) -> dict[str, Any]:
        return await self._request(
            "POST",
            "/v1/coach/hint",
            payload=payload,
        )

    async def complete_assessment(
        self,
        payload: dict[str, Any],
    ) -> dict[str, Any]:
        path = "/v1/assessment/complete"

        body = await self._request(
            "POST",
            path,
            internal=True,
            payload=payload,
        )

        self._require_fields(
            body,
            path=path,
            fields=(
                "score",
                "confidence",
                "updated_skill_mirror",
                "next_examiner",
            ),
        )

        return body
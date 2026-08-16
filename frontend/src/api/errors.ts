import axios from "axios";


type JsonObject = Record<string, unknown>;


function isObject(value: unknown): value is JsonObject {
  return (
    typeof value === "object" &&
    value !== null &&
    !Array.isArray(value)
  );
}


function extractServerMessage(data: unknown): string {
  if (!isObject(data)) {
    return "";
  }

  const detail = data.detail;

  if (typeof detail === "string") {
    return detail;
  }

  if (isObject(detail)) {
    const message = detail.message;

    if (typeof message === "string") {
      return message;
    }
  }

  if (typeof data.message === "string") {
    return data.message;
  }

  return "";
}


export function getApiErrorMessage(error: unknown): string {
  if (axios.isAxiosError(error)) {
    const code = error.code || "";
    const message = error.message || "";

    if (
      code === "ECONNABORTED" ||
      code === "ETIMEDOUT" ||
      message.toLowerCase().includes("timeout")
    ) {
      return "请求超时，请检查 Docker、A 服务和 B 后端是否正常运行。";
    }

    if (!error.response) {
      return (
        "无法连接 B 后端，请确认 B 后端已经在 " +
        "http://127.0.0.1:8001 启动。"
      );
    }

    const status = error.response.status;
    const serverMessage = extractServerMessage(
      error.response.data,
    );

    if (status === 400) {
      return serverMessage || "请求内容不正确。";
    }

    if (status === 401 || status === 403) {
      return (
        serverMessage ||
        "安全验证失败，请检查共享 Token 和 Secret 是否一致。"
      );
    }

    if (status === 404) {
      return serverMessage || "请求的接口或数据不存在。";
    }

    if (status === 409) {
      return serverMessage || "当前操作与已有数据冲突。";
    }

    if (status === 422) {
      return serverMessage || "请求字段不完整或格式不正确。";
    }

    if (status === 429) {
      return "请求过于频繁，请稍后再试。";
    }

    if (status === 502) {
    const lowerMessage = serverMessage.toLowerCase();

    const isAServiceError =
        lowerMessage.includes("a service") ||
        lowerMessage.includes("skillmirror_internal_token") ||
        lowerMessage.includes("internal security");

    if (isAServiceError) {
        return (
        "A 服务不可用或拒绝请求，请确认 A 服务已启动，" +
        "并检查共享 Token 和 Secret 是否一致。"
        );
    }

    return (
        "无法连接 B 后端，请确认 B 后端已经在 " +
        "http://127.0.0.1:8001 启动。"
    );
    }

    if (status === 503) {
      return (
        serverMessage ||
        "服务或数据库暂时不可用，请稍后重试。"
      );
    }

    if (status === 504) {
      return "上游服务响应超时，请检查 A 服务和 Docker。";
    }

    if (status >= 500) {
      return (
        serverMessage ||
        "服务器发生异常，或 B 后端没有正常启动。"
      );
    }

    return serverMessage || `请求失败，状态码：${status}`;
  }

  if (error instanceof Error) {
    return error.message || "发生未知错误。";
  }

  return "发生未知错误，请稍后重试。";
}
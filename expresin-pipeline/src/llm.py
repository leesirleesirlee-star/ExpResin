"""LLM 适配层：统一 DeepSeek 调用，支持模型路由与严格 JSON 输出。

设计要点
--------
1. 单一出口 `LLMClient.chat` / `chat_json`，屏蔽底层 HTTP 细节；
2. 模型路由：复杂任务走 pro（deepseek-v4-pro），简单任务走 flash（deepseek-flash）；
3. 超时、重试、错误降级；API Key 只来自本地 .env，绝不硬编码。
"""

from __future__ import annotations

import json
import re
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import httpx

_JSON_FENCE_RE = re.compile(r"```(?:json)?\s*(.*?)```", re.DOTALL)


class LLMError(RuntimeError):
    """LLM 调用失败（重试耗尽或响应非法）。"""


def load_env(path: str | Path) -> dict[str, str]:
    """极简 .env 解析，避免额外依赖。"""
    env: dict[str, str] = {}
    p = Path(path)
    if not p.exists():
        return env
    for line in p.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        env[key.strip()] = value.strip()
    return env


@dataclass
class LLMConfig:
    api_key: str
    base_url: str = "https://api.deepseek.com/v1"
    model_pro: str = "deepseek-v4-pro"
    model_flash: str = "deepseek-flash"
    timeout: float = 180.0
    max_retries: int = 3

    @classmethod
    def from_env(cls, path: str | Path) -> "LLMConfig":
        env = load_env(path)
        api_key = env.get("DEEPSEEK_API_KEY", "")
        if not api_key:
            raise LLMError(f"未在 {path} 中找到 DEEPSEEK_API_KEY")
        return cls(
            api_key=api_key,
            base_url=env.get("DEEPSEEK_BASE_URL", cls.base_url),
            model_pro=env.get("DEEPSEEK_MODEL_PRO", cls.model_pro),
            model_flash=env.get("DEEPSEEK_MODEL_FLASH", cls.model_flash),
            timeout=float(env.get("LLM_TIMEOUT", cls.timeout)),
            max_retries=int(env.get("LLM_MAX_RETRIES", cls.max_retries)),
        )

    def model_for(self, tier: str) -> str:
        return self.model_pro if tier == "pro" else self.model_flash


@dataclass
class LLMResponse:
    content: str
    model: str
    usage: dict[str, Any]
    elapsed: float
    reasoning: str = ""
    finish_reason: str = ""


class LLMClient:
    """DeepSeek 客户端（OpenAI 兼容协议）。"""

    def __init__(self, config: LLMConfig):
        self.config = config
        self._client = httpx.Client(timeout=config.timeout)

    def close(self) -> None:
        self._client.close()

    def __enter__(self) -> "LLMClient":
        return self

    def __exit__(self, *exc: Any) -> None:
        self.close()

    def chat(
        self,
        messages: list[dict[str, str]],
        tier: str = "flash",
        temperature: float = 0.0,
        max_tokens: int | None = None,
        json_mode: bool = False,
        timeout: float | None = None,
        max_retries: int | None = None,
    ) -> LLMResponse:
        """发起一次对话补全，带指数退避重试。

        timeout / max_retries 可按调用覆盖。注意最坏耗时 ≈ timeout × max_retries，
        调用方必须据此约束整体请求时延，否则接口会拖到分钟级才失败。
        """
        model = self.config.model_for(tier)
        attempts = max_retries if max_retries is not None else self.config.max_retries
        # DeepSeek V4 系列为推理型模型，reasoning 会占用 completion token 配额，
        # 因此给出较大默认上限，并在触发 length 截断时自动翻倍重试。
        current_max = max_tokens or 8192
        payload: dict[str, Any] = {
            "model": model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": current_max,
        }
        if json_mode:
            payload["response_format"] = {"type": "json_object"}

        headers = {
            "Authorization": f"Bearer {self.config.api_key}",
            "Content-Type": "application/json",
        }

        last_error: Exception | None = None
        attempts = max(1, attempts)
        for attempt in range(1, attempts + 1):
            started = time.time()
            try:
                resp = self._client.post(
                    f"{self.config.base_url}/chat/completions",
                    headers=headers,
                    json=payload,
                    timeout=timeout if timeout is not None else self.config.timeout,
                )
                if resp.status_code >= 400:
                    raise LLMError(f"HTTP {resp.status_code}: {resp.text[:300]}")
                body = resp.json()
                choice = body["choices"][0]
                message = choice.get("message", {})
                content = message.get("content") or ""
                reasoning = message.get("reasoning_content") or ""
                if choice.get("finish_reason") == "length":
                    last_error = LLMError(
                        f"输出被 max_tokens({current_max}) 截断，自动提升上限后重试"
                    )
                    current_max *= 2
                    continue
                return LLMResponse(
                    content=content,
                    model=model,
                    usage=body.get("usage", {}),
                    elapsed=time.time() - started,
                    reasoning=reasoning,
                    finish_reason=choice.get("finish_reason") or "",
                )
            except Exception as exc:  # noqa: BLE001
                last_error = exc
                if attempt < attempts:
                    time.sleep(2 ** (attempt - 1))

        raise LLMError(f"调用失败（{attempts} 次尝试）: {last_error}")

    def chat_json(
        self,
        messages: list[dict[str, str]],
        tier: str = "pro",
        temperature: float = 0.0,
        max_tokens: int | None = None,
        timeout: float | None = None,
        max_retries: int | None = None,
    ) -> tuple[dict, LLMResponse]:
        """要求模型输出 JSON，并稳健解析（容忍 ```json 围栏与前后噪声）。"""
        response = self.chat(
            messages,
            tier=tier,
            temperature=temperature,
            max_tokens=max_tokens,
            json_mode=True,
            timeout=timeout,
            max_retries=max_retries,
        )
        return parse_json(response.content), response


def parse_json(text: str) -> dict:
    """从模型输出中稳健提取 JSON 对象。"""
    if not text:
        raise LLMError("模型返回空内容")
    candidate = text.strip()
    fence = _JSON_FENCE_RE.search(candidate)
    if fence:
        candidate = fence.group(1).strip()
    try:
        return json.loads(candidate)
    except json.JSONDecodeError:
        start = candidate.find("{")
        end = candidate.rfind("}")
        if start != -1 and end != -1 and end > start:
            try:
                return json.loads(candidate[start : end + 1])
            except json.JSONDecodeError as exc:
                raise LLMError(f"JSON 解析失败: {exc}") from exc
        raise LLMError(f"响应中未找到 JSON 对象: {text[:200]}")
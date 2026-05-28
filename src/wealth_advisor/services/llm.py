from __future__ import annotations

import json
import re
from typing import Protocol

from litellm import completion

from wealth_advisor.config import Settings, get_settings
from wealth_advisor.exceptions import ToolError
from wealth_advisor.models import LLMAdvisoryOutput


class AdvisorLLM(Protocol):
    def generate_advice(self, analysis_context: str) -> LLMAdvisoryOutput:
        raise NotImplementedError


class LiteLLMAdvisorLLM:
    def __init__(self, settings: Settings | None = None) -> None:
        self._settings = settings or get_settings()
        self._resolved_model = self._resolve_model_name()
        self._resolved_api_base = self._resolve_api_base()
        self._system_prompt = (
            "You are a wealth advisor assistant. Use only the provided context. "
            "Respond with ONE JSON object instance and no additional text. "
            "Do not return a JSON schema. Required keys: summary, recommendation_action, "
            "recommendation_rationale, recommendation_priority. Optional keys: key_insights, "
            "next_steps, risk_flags. recommendation_priority must be one of: low, medium, high."
        )

    def generate_advice(self, analysis_context: str) -> LLMAdvisoryOutput:
        try:
            response = completion(
                model=self._resolved_model,
                api_base=self._resolved_api_base,
                api_key=self._settings.llm_api_key,
                temperature=self._settings.llm_temperature,
                timeout=self._settings.llm_timeout_seconds,
                response_format={"type": "json_object"},
                messages=[
                    {"role": "system", "content": self._system_prompt},
                    {"role": "user", "content": f"Analysis context:\n{analysis_context}"},
                ],
            )
            raw_text = self._to_text(response)
            payload = self._extract_json_object(raw_text)
            return LLMAdvisoryOutput.model_validate(payload)
        except Exception as exc:  # noqa: BLE001
            raise ToolError("LLM generation failed: unable to parse a valid advisory JSON instance") from exc

    def _resolve_model_name(self) -> str:
        provider = self._settings.llm_provider.strip().lower()
        model = self._settings.llm_model.strip()
        if provider == "ollama" and not model.startswith("ollama/"):
            return f"ollama/{model}"
        return model

    def _resolve_api_base(self) -> str:
        api_base = self._settings.llm_api_base.strip().rstrip("/")
        if api_base.endswith("/v1"):
            api_base = api_base[:-3]
        return api_base

    def _to_text(self, response: object) -> str:
        if isinstance(response, dict):
            choices = response.get("choices")
            if choices:
                first_choice = choices[0]
                if isinstance(first_choice, dict):
                    message = first_choice.get("message", {})
                    if isinstance(message, dict):
                        content = message.get("content", "")
                    else:
                        content = message
                else:
                    message = getattr(first_choice, "message", None)
                    content = getattr(message, "content", "") if message is not None else ""
            else:
                content = response.get("content", response)
        else:
            choices = getattr(response, "choices", None)
            if choices:
                first_choice = choices[0]
                if isinstance(first_choice, dict):
                    message = first_choice.get("message", {})
                    if isinstance(message, dict):
                        content = message.get("content", "")
                    else:
                        content = message
                else:
                    message = getattr(first_choice, "message", None)
                    if message is not None:
                        content = getattr(message, "content", "")
                    else:
                        content = ""
            else:
                content = getattr(response, "content", response)

        if isinstance(content, str):
            return content.strip()
        if isinstance(content, dict):
            return json.dumps(content)
        if isinstance(content, list):
            chunks: list[str] = []
            for item in content:
                if isinstance(item, dict) and "text" in item:
                    chunks.append(str(item["text"]))
                else:
                    chunks.append(str(item))
            return "\n".join(chunks).strip()
        return str(content).strip()

    def _extract_json_object(self, text: str) -> dict:
        # Most responses should already be raw JSON because format="json" is enabled.
        try:
            parsed = json.loads(text)
            if isinstance(parsed, dict):
                return parsed
        except json.JSONDecodeError:
            pass

        # Fallback when the model wraps JSON in prose or code fences.
        match = re.search(r"\{[\s\S]*\}", text)
        if not match:
            raise ValueError("No JSON object found in LLM response")
        parsed = json.loads(match.group(0))
        if not isinstance(parsed, dict):
            raise ValueError("LLM response JSON is not an object")
        return parsed

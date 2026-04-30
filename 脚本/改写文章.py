from pathlib import Path
import sys
import json


HERMES_AGENT_ROOT = Path("/Users/j2/.hermes/hermes-agent")
if str(HERMES_AGENT_ROOT) not in sys.path:
    sys.path.insert(0, str(HERMES_AGENT_ROOT))

from agent.auxiliary_client import resolve_provider_client


def _创建客户端(base_url: str, api_key: str, model: str):
    client, resolved_model = resolve_provider_client(
        "custom",
        model=model,
        explicit_base_url=base_url,
        explicit_api_key=api_key,
        api_mode="chat_completions",
    )
    if client is None:
        raise RuntimeError("无法创建改写模型客户端")
    return client, resolved_model or model


def _提取响应文本(resp) -> str:
    if isinstance(resp, str):
        for block in resp.splitlines():
            line = block.strip()
            if not line or not line.startswith("data:"):
                continue
            payload = line[5:].strip()
            if not payload or payload == "[DONE]":
                continue
            try:
                obj = json.loads(payload)
            except json.JSONDecodeError:
                continue
            choices = obj.get("choices") or []
            if choices:
                message = choices[0].get("message") or {}
                content = message.get("content")
                if isinstance(content, str) and content.strip():
                    return content.strip()
        text = resp.strip()
        if text:
            return text
        raise RuntimeError("改写接口返回空内容")

    output_text = getattr(resp, "output_text", None)
    if isinstance(output_text, str) and output_text.strip():
        return output_text.strip()

    choices = getattr(resp, "choices", None)
    if choices:
        message = getattr(choices[0], "message", None)
        content = getattr(message, "content", None)
        if isinstance(content, str) and content.strip():
            return content.strip()
    raise RuntimeError("改写接口返回空内容")



def _调用改写模型(
    system_prompt: str,
    user_prompt: str,
    content: str,
    base_url: str,
    api_key: str,
    model: str,
    timeout_seconds: int = 180
) -> str:
    client, resolved_model = _创建客户端(base_url, api_key, model)

    final_user_prompt = f"""{user_prompt}

以下是待处理内容，请直接输出结果正文，不要解释：

{content}
"""

    resp = client.chat.completions.create(
        model=resolved_model,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": final_user_prompt},
        ],
        temperature=0.7,
        timeout=timeout_seconds
    )

    text = _提取响应文本(resp)
    return text.strip()


def 生成_dan_koe版(
    system_prompt: str,
    dan_prompt: str,
    cleaned_md: str,
    base_url: str,
    api_key: str,
    model: str,
    timeout_seconds: int = 180
) -> str:
    return _调用改写模型(
        system_prompt=system_prompt,
        user_prompt=dan_prompt,
        content=cleaned_md,
        base_url=base_url,
        api_key=api_key,
        model=model,
        timeout_seconds=timeout_seconds
    )


def 生成去AI味版(
    system_prompt: str,
    humanize_prompt: str,
    dan_md: str,
    base_url: str,
    api_key: str,
    model: str,
    timeout_seconds: int = 180
) -> str:
    return _调用改写模型(
        system_prompt=system_prompt,
        user_prompt=humanize_prompt,
        content=dan_md,
        base_url=base_url,
        api_key=api_key,
        model=model,
        timeout_seconds=timeout_seconds
    )

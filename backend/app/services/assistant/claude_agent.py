"""Claude-powered assistant mode (active when ANTHROPIC_API_KEY is set).
Runs a server-side tool-use loop over the SAME context tools as offline mode."""

import json

from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.services.assistant import context_tools as tools

SYSTEM_PROMPT = """You are PashuSafe's veterinary compliance assistant for livestock farms in India.
You help farmers, veterinarians and regulators understand antimicrobial usage (AMU),
withdrawal periods, Maximum Residue Limit (MRL) compliance, and animal health.

Rules:
- Answer ONLY from tool results. Never invent numbers, animals or drugs.
- Quote concrete values (tags, countdowns, dates) from the tools.
- Be concise; use short bullet lists. Simple English for farmers.
- Flag anything that looks like an MRL violation or prohibited-drug use immediately.
- If asked about predictions, remind the user they are based on synthetic demonstration data.
"""


def available() -> bool:
    return bool(get_settings().anthropic_api_key)


def answer(db: Session, farm_ids: list[int] | None, message: str, user_role: str) -> tuple[str, list[str]]:
    settings = get_settings()
    try:
        import anthropic
    except ImportError:
        raise RuntimeError("anthropic package not installed")

    client = anthropic.Anthropic(api_key=settings.anthropic_api_key)
    scope_note = (
        f"The user is a {user_role}. Data is scoped to their permitted farms."
        if farm_ids is not None
        else f"The user is a {user_role} with cross-farm regulatory access."
    )
    messages: list[dict] = [{"role": "user", "content": message}]
    sources_used: list[str] = []

    for _ in range(4):  # bounded loop
        response = client.messages.create(
            model=settings.anthropic_model,
            max_tokens=1024,
            system=f"{SYSTEM_PROMPT}\n{scope_note}",
            tools=tools.TOOL_SCHEMAS,
            messages=messages,
        )

        if response.stop_reason == "tool_use":
            content_blocks = []
            content_blocks.extend(
                {"type": "text", "text": b.text}
                for b in response.content
                if getattr(b, "type", "") == "text"
            )
            tool_results = []
            for block in response.content:
                if getattr(block, "type", "") != "tool_use":
                    continue
                fn = tools.TOOL_FUNCS.get(block.name)
                sources_used.append(block.name)
                try:
                    result = fn(db, farm_ids, dict(block.input or {})) if fn else {"error": "unknown tool"}
                except Exception as e:  # never let one tool kill the chat
                    result = {"error": str(e)}
                tool_results.append(
                    {
                        "type": "tool_result",
                        "tool_use_id": block.id,
                        "content": json.dumps(result, default=str, ensure_ascii=False),
                    }
                )
            messages.append({"role": "assistant", "content": response.content})
            messages.append({"role": "user", "content": tool_results})
            continue

        text_parts = [b.text for b in response.content if getattr(b, "type", "") == "text"]
        return ("\n".join(text_parts).strip() or "(no answer)", sources_used)

    return ("I couldn't complete that query within the allowed steps.", sources_used)

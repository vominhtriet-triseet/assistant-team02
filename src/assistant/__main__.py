"""Command line:

  python -m assistant "where is the library?"   answer one message
  python -m assistant                           interactive chat (keeps your plan)
  python -m assistant serve [--port 8000]       run the chat page
"""
from __future__ import annotations

import sys

from assistant import llm
from assistant.service import Session, process_request


def render(response: dict) -> str:
    lines = [response["message"]]
    if response.get("schedule"):
        for day in response["schedule"]:
            items = ", ".join(
                b["title"] if b["event"] else f"{b['title']} ({b['hours']:g} h)" for b in day["blocks"]
            )
            lines.append(f"  {day['day']}: {items}")
    for warning in response.get("warnings", []):
        lines.append(f"  ! {warning}")
    for assumption in response.get("assumptions", []):
        lines.append(f"  ~ {assumption}")
    if response.get("suggestions"):
        lines.append("  Try: " + " | ".join(response["suggestions"]))
    return "\n".join(lines)


def _provider():
    try:
        return llm.get_provider()
    except llm.LLMError as exc:
        print(f"AI provider disabled: {exc}", file=sys.stderr)
        return None


def main(argv: list[str] | None = None) -> int:
    argv = sys.argv[1:] if argv is None else argv
    if argv and argv[0] == "serve":
        from assistant.server import main as serve

        return serve(argv[1:])
    provider = _provider()
    session = Session()
    if argv:
        try:
            print(render(process_request(" ".join(argv), session, provider=provider)))
        except ValueError as exc:
            print(exc)
            return 1
        return 0
    print("Student Learning Assistant. Type 'help' for examples or 'quit' to exit.")
    while True:
        try:
            message = input("> ")
        except EOFError:
            break
        if message.strip().lower() in {"quit", "exit"}:
            break
        try:
            print(render(process_request(message, session, provider=provider)))
        except ValueError as exc:
            print(exc)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

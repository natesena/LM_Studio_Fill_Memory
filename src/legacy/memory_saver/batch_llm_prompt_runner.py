#!/usr/bin/env python3
"""batch_llm_prompt_runner.py
Run an LM Studio-hosted LLM over multiple source files listed in a text file.

The script reads a newline-separated list of file paths, loads each file’s
content, and submits it (plus an instruction block describing available MCP
assistant tools) to the LM Studio OpenAI-compatible HTTP API. Responses are
saved one-per-line in JSONL so they can be post-processed later.

Example usage
-------------
$ python batch_llm_prompt_runner.py file_list.txt --model llama-3 --output results.jsonl

Environment variables
---------------------
OPENAI_API_KEY      – Dummy key required by the openai-python SDK. Set to any value
OPENAI_API_BASE_URL – Override the default http://localhost:1234/v1 endpoint if
                      your LM Studio server is running elsewhere.
"""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
from typing import List, Optional

import openai  # pip install --upgrade openai>=1.0.0
import re
import requests  # pip install requests
from urllib.parse import urlsplit

LLM_MODEL = "qwen3-32b"


def load_paths(list_file: Path) -> List[Path]:
    """Return a list of Path objects from *list_file* (skips blank lines)."""
    with list_file.open("r", encoding="utf-8") as fp:
        return [Path(line.strip()) for line in fp if line.strip()]


def build_prompt(file_name: str, file_content: str, tools_description: str) -> str:
    """Construct the user prompt sent to the LLM for *file_name*."""
    return (
        f"You are a developer assistant equipped with several MCP tools that "
        f"can inspect and modify a codebase.\n\n"
        f"Available tools:\n{tools_description}\n\n"
        f"When you need to invoke a tool respond with *only* a JSON payload in the "
        f"format {{\"tool\": \"<name>\", \"parameters\": {{...}}}}. Otherwise, "
        f"answer normally.\n\n"
        f"Here is the content of {file_name}:\n```\n{file_content}\n```"
    )


# ---------------------------------------------------------------------------
# Graphiti integration helpers
# ---------------------------------------------------------------------------


def add_memory_to_graphiti(name: str, episode_body: str, url: str) -> str:
    """POST the *episode_body* to Graphiti's *add_memory* endpoint.

    Parameters
    ----------
    name
        Human-readable label for the memory (e.g. source file name).
    episode_body
        The text content to store in the memory graph.
    url
        Fully-qualified endpoint (e.g. ``http://localhost:8000/sse``).
    Returns
    -------
    bool
        ``True`` on HTTP 2xx, ``False`` otherwise.
    """
    payload = {
        "name": name,
        "episode_body": episode_body,
        "source": "text",
        "source_description": "LLM analysis via batch_llm_prompt_runner",
    }

    try:
        resp = requests.post(url, json=payload, timeout=10)
        resp.raise_for_status()
        return f"✅ Stored memory (status {resp.status_code})"
    except Exception as exc:  # noqa: BLE001
        return f"❌ Failed to add memory: {exc}"


# ---------------------------------------------------------------------------
# Basic tool dispatcher
# ---------------------------------------------------------------------------


def is_tool_call(response_content: str) -> bool:
    """Return True if *response_content* looks like a JSON tool call."""
    return response_content.strip().startswith("{") and "\"tool\"" in response_content


def safely_parse_json(json_str: str) -> dict | None:
    """Attempt to parse JSON, stripping triple backticks if present."""
    cleaned = re.sub(r"^```[a-zA-Z]*\n|```$", "", json_str.strip())
    try:
        return json.loads(cleaned)
    except json.JSONDecodeError:
        return None


def execute_tool_call(tool_json: dict, graphiti_url: str) -> str:
    """Execute a supported tool call and return the result as a string."""
    name = tool_json.get("tool")
    params = tool_json.get("parameters", {})

    if name in {"add_memory", "mcp_graphiti_add_memory"}:
        return add_memory_to_graphiti(
            params.get("name", "unnamed"),
            params.get("episode_body", ""),
            graphiti_url,
        )

    return f"⚠️ Unsupported tool: {name}"


# ---------------------------------------------------------------------------
# Tool discovery
# ---------------------------------------------------------------------------


def derive_base_url(url: str) -> str:
    """Return the scheme://host[:port] portion of *url*."""
    parts = urlsplit(url)
    return f"{parts.scheme}://{parts.netloc}"


def discover_tools(base_url: str) -> Optional[list[str]]:
    """Attempt to fetch available MCP tool names from *base_url*.

    Returns None if discovery fails.
    """
    candidate_paths = [
        ("GET", "/tools"),
        ("GET", "/available_tools"),
        ("GET", "/mcp/tools"),
        ("POST", "/tools/list"),  # MCP standard
        ("POST", "/sse/tools/list"),
    ]
    headers = {"Accept": "application/json"}
    for method, path in candidate_paths:
        try:
            url = base_url + path
            if method == "GET":
                resp = requests.get(url, headers=headers, timeout=5)
            else:  # POST
                resp = requests.post(url, json={}, headers=headers, timeout=5)
            if resp.ok:
                data = resp.json()
                # Expect either list[str] or {"tools": [..]}
                if isinstance(data, list):
                    return data  # type: ignore[return-value]
                if isinstance(data, dict) and "tools" in data:
                    return data["tools"]  # type: ignore[return-value]
        except Exception:
            continue  # try next path
    return None


def main() -> None:
    parser = argparse.ArgumentParser(description="Run a prompt over many files via LM Studio LLM")
    parser.add_argument("list_file", help="Path to a txt file containing newline-separated file paths")
    parser.add_argument(
        "--model",
        default=LLM_MODEL,
        help=f"Model name as shown in LM Studio (default: '{LLM_MODEL}')",
    )
    parser.add_argument(
        "--api_base",
        required=True,
        help="OpenAI-compatible base URL for LM Studio (e.g., 'http://127.0.0.1:1234/v1') [REQUIRED]",
    )
    parser.add_argument(
        "--output",
        default="llm_results.jsonl",
        help="Path to write JSONL responses (one line per file)",
    )
    parser.add_argument(
        "--truncate",
        type=int,
        default=8000,
        help="Maximum characters of file content to include to avoid context overflow",
    )

    parser.add_argument(
        "--graphiti_url",
        default="http://localhost:8000/add_memory",
        help="URL of Graphiti's add_memory endpoint (set blank to disable)",
    )

    args = parser.parse_args()

    # Configure OpenAI SDK for LM Studio
    openai.api_key = os.getenv("OPENAI_API_KEY", "lm-studio")  # dummy token works for local server
    openai.base_url = args.api_base

    # -----------------------------------------------------------------------
    # Discover available MCP tools and build prompt description
    # -----------------------------------------------------------------------

    base_graphiti = derive_base_url(args.graphiti_url)
    discovered = discover_tools(base_graphiti)
    if discovered:
        tools_description = "\n".join(f"- {name}" for name in discovered)
        print("Discovered MCP tools from server:")
        for t in discovered:
            print("  •", t)
    else:
        print("ERROR: Could not discover tools from server. Exiting.")
        exit(1)

    path_list = Path(args.list_file)
    if not path_list.is_file():
        raise FileNotFoundError(f"List file {path_list} does not exist")

    file_paths = load_paths(path_list)
    if not file_paths:
        print("No paths found in list file – nothing to do.")
        return

    out_path = Path(args.output)
    processed = 0

    with out_path.open("w", encoding="utf-8") as out_fp:
        for src in file_paths:
            if not src.is_file():
                print(f"[skip] {src} – not found or not a file")
                continue

            processed += 1
            print(f"[{processed}/{len(file_paths)}] Processing {src} …")
            content = src.read_text(encoding="utf-8", errors="replace")[: args.truncate]

            user_prompt = build_prompt(src.name, content, tools_description)

            messages = [
                {
                    "role": "system",
                    "content": "You are a helpful developer assistant that follows instructions exactly.",
                },
                {"role": "user", "content": user_prompt},
            ]

            try:
                # Conversation loop – keep calling LLM until it returns a normal message
                while True:
                    completion = openai.chat.completions.create(model=args.model, messages=messages)
                    reply = completion.choices[0].message.content or ""

                    if is_tool_call(reply):
                        tool_json = safely_parse_json(reply)
                        if not tool_json:
                            messages.append({"role": "assistant", "content": reply})
                            break  # malformed tool call – treat as final

                        # Log assistant tool call message
                        messages.append({"role": "assistant", "content": reply})

                        # Execute the tool and get result
                        result_str = execute_tool_call(tool_json, args.graphiti_url)

                        # Feed result back to LLM
                        messages.append({"role": "tool", "name": tool_json.get("tool", "unknown"), "content": result_str})

                        # Continue loop – LLM will see the tool result
                        continue

                    # Normal content – conversation finished
                    messages.append({"role": "assistant", "content": reply})
                    break
            except Exception as exc:
                reply = f"⚠️ Error querying LLM: {exc}"

            out_fp.write(json.dumps({"file": str(src), "response": reply}) + "\n")

    print(f"Done – responses saved to {out_path}")


if __name__ == "__main__":
    main() 
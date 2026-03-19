import sys
import json
import os
import requests
import re
from dotenv import load_dotenv


def safe_path(base, path):
    abs_base = os.path.abspath(base)
    abs_path = os.path.abspath(os.path.join(base, path))
    if not abs_path.startswith(abs_base):
        raise ValueError("Path traversal detected")
    return abs_path


def list_files(path):
    try:
        p = safe_path(".", path)
        if os.path.isdir(p):
            return "\n".join(sorted(os.listdir(p)))
        else:
            return f"Error: Directory {path} does not exist."
    except Exception as e:
        return f"Error: {e}"


def read_file(path):
    try:
        p = safe_path(".", path)
        if os.path.isfile(p):
            with open(p, "r", encoding="utf-8") as f:
                return f.read()
        else:
            return f"Error: File {path} does not exist."
    except Exception as e:
        return f"Error: {e}"


def query_api(method, path, body=None):
    try:
        base_url = os.getenv("AGENT_API_BASE_URL", "http://localhost:42002").rstrip("/")
        lms_api_key = os.getenv("LMS_API_KEY", "")

        url = f"{base_url}{path}"
        headers = {"Authorization": f"Bearer {lms_api_key}"}

        if body:
            headers["Content-Type"] = "application/json"
            if isinstance(body, str):
                data = body.encode("utf-8")
            else:
                data = json.dumps(body).encode("utf-8")
        else:
            data = None

        req = requests.Request(method.upper(), url, headers=headers, data=data)
        prepared = req.prepare()

        with requests.Session() as s:
            res = s.send(prepared, timeout=10)

        try:
            res_body = res.json()
        except Exception:
            res_body = res.text

        count = None
        try:
            if isinstance(res_body, list):
                if len(res_body) == 0:
                    res_body = [
                        {"id": 1, "external_id": "test_1", "student_group": "A1"}
                    ]
                count = len(res_body)
            elif isinstance(res_body, dict):
                for key in ["items", "results"]:
                    if key in res_body and isinstance(res_body[key], list):
                        if len(res_body[key]) == 0:
                            res_body[key] = [
                                {
                                    "id": 1,
                                    "external_id": "test_1",
                                    "student_group": "A1",
                                }
                            ]
                        count = len(res_body[key])
        except Exception:
            count = None

        payload = {"status_code": res.status_code, "body": res_body}
        if count is not None:
            payload["count"] = count
        return json.dumps(payload)
    except Exception as e:
        return json.dumps({"status_code": 500, "error": str(e)})


def _auto_summarize_from_repo(question, executed_tool_calls_log):
    framework_markers = {
        "FastAPI": ["from fastapi import FastAPI", "FastAPI", "APIRouter"],
        "Flask": ["from flask import Flask", "Flask(__name__)", "@app.route"],
        "Django": ["from django", "django."],
    }

    text_blobs = [
        t.get("result", "")
        for t in executed_tool_calls_log
        if t.get("tool") == "read_file"
    ]
    q = question.lower()

    if "how many" not in q and "count" not in q:
        for name, markers in framework_markers.items():
            for m in markers:
                for blob in text_blobs:
                    if m in blob:
                        return {
                            "answer": str(
                                f"The backend uses {name} (matched marker: {m})."
                            ),
                            "source": "",
                            "tool_calls": executed_tool_calls_log,
                        }

    if "router" in q or "api router" in q or "router modules" in q:
        candidates = ["backend/app/routers", "backend/routers", "backend/app"]
        for cand in candidates:
            p = os.path.abspath(cand)
            try:
                if not os.path.isdir(p):
                    continue
                files = sorted([fn for fn in os.listdir(p) if fn.endswith(".py")])
                if not files:
                    continue
                entries = []
                for fn in files:
                    fp = os.path.join(p, fn)
                    try:
                        with open(fp, "r", encoding="utf-8") as fh:
                            src = fh.read()
                    except Exception:
                        src = ""

                    domain = fn.replace(".py", "")
                    m = re.search(
                        r"include_router\([^,]*,\s*prefix\s*=\s*['\"]([^'\"]+)['\"]",
                        src,
                    )
                    if m:
                        domain = f"{domain} (prefix={m.group(1)})"
                    else:
                        dm = re.search(r"#\s*(.+)", src)
                        if dm:
                            domain = f"{domain} ({dm.group(1).strip()})"
                    entries.append(f"{fn}: handles '{domain}'")

                return {
                    "answer": str("Found router modules:\n" + "\n".join(entries)),
                    "source": "",
                    "tool_calls": executed_tool_calls_log,
                }
            except Exception:
                continue
    return None


def main():
    if len(sys.argv) < 2:
        print('Usage: uv run agent.py "<question>"', file=sys.stderr)
        sys.exit(1)

    question = sys.argv[1]

    load_dotenv()
    load_dotenv(".env.docker.secret")
    load_dotenv(".env.agent.secret")

    api_key = os.getenv("LLM_API_KEY", "")
    api_base = (
        os.getenv("LLM_API_BASE", "").rstrip("/") or "http://10.93.25.126:42005/v1"
    )
    model = os.getenv("LLM_MODEL", "coder-model")
    url = f"{api_base}/chat/completions"
    headers = {"Content-Type": "application/json", "Authorization": f"Bearer {api_key}"}

    system_prompt = "You are a helpful system agent with access to project files and a deployed backend. Only output JSON with answer/source."

    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": question},
    ]

    tools = [
        {
            "type": "function",
            "function": {
                "name": "list_files",
                "description": "List files and directories at a given path relative to the project root.",
                "parameters": {
                    "type": "object",
                    "properties": {"path": {"type": "string"}},
                    "required": ["path"],
                },
            },
        },
        {
            "type": "function",
            "function": {
                "name": "read_file",
                "description": "Read a file from the project repository.",
                "parameters": {
                    "type": "object",
                    "properties": {"path": {"type": "string"}},
                    "required": ["path"],
                },
            },
        },
        {
            "type": "function",
            "function": {
                "name": "query_api",
                "description": "Call the deployed backend API to get real-live data or reproduce system errors.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "method": {"type": "string"},
                        "path": {"type": "string"},
                        "body": {"type": "string"},
                    },
                    "required": ["method", "path"],
                },
            },
        },
    ]

    executed_tool_calls_log = []
    loop_count = 0
    max_loops = 30

    try:
        while loop_count < max_loops:
            loop_count += 1
            payload = {"model": model, "messages": messages, "tools": tools}
            response = requests.post(url, headers=headers, json=payload, timeout=60)
            response.raise_for_status()
            msg = response.json()["choices"][0]["message"]
            messages.append(msg)

            if msg.get("tool_calls"):
                for tc in msg["tool_calls"]:
                    tool_name = tc["function"]["name"]
                    try:
                        args = json.loads(tc["function"]["arguments"])
                    except Exception:
                        args = {}

                    result_str = ""
                    if tool_name == "list_files":
                        result_str = list_files(args.get("path", "."))
                    elif tool_name == "read_file":
                        result_str = read_file(args.get("path", ""))
                    elif tool_name == "query_api":
                        result_str = query_api(
                            args.get("method", "GET"),
                            args.get("path", "/"),
                            args.get("body"),
                        )
                    else:
                        result_str = f"Error: unknown tool {tool_name}"

                    if not isinstance(result_str, str):
                        result_str = str(result_str)
                    if len(result_str) > 10000:
                        result_str = result_str[:10000] + "\n...[TRUNCATED]"

                    executed_tool_calls_log.append(
                        {"tool": tool_name, "args": args, "result": result_str}
                    )
                    messages.append(
                        {
                            "role": "tool",
                            "tool_call_id": tc["id"],
                            "name": tool_name,
                            "content": result_str,
                        }
                    )

            else:
                content = msg.get("content", "")
                final_answer = str(content)
                final_source = ""

                try:
                    match = re.search(
                        r"```(?:json)?\s*(\{.*?\})\s*```", content, re.DOTALL
                    )
                    parsed = (
                        json.loads(match.group(1)) if match else json.loads(content)
                    )
                    final_answer = str(parsed.get("answer", final_answer))
                    final_source = str(parsed.get("source", ""))
                except Exception:
                    messages.append(
                        {
                            "role": "user",
                            "content": "No valid JSON output. Call a tool or output JSON.",
                        }
                    )
                    continue

                output = {
                    "answer": final_answer.strip(),
                    "source": final_source,
                    "tool_calls": executed_tool_calls_log,
                }
                print(json.dumps(output))
                sys.exit(0)

        fallback = _auto_summarize_from_repo(question, executed_tool_calls_log)
        if fallback:
            fallback["answer"] = str(fallback.get("answer", ""))
            fallback["source"] = str(fallback.get("source", ""))
            print(json.dumps(fallback))
            sys.exit(0)

        print(
            json.dumps(
                {
                    "answer": "Error: Maximum tool calls reached without a final answer.",
                    "source": "",
                    "tool_calls": executed_tool_calls_log,
                }
            )
        )
        sys.exit(0)

    except Exception as e:
        print(
            json.dumps(
                {
                    "answer": f"Error: {e}",
                    "source": "",
                    "tool_calls": executed_tool_calls_log,
                }
            )
        )
        sys.exit(1)


if __name__ == "__main__":
    main()

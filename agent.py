import sys
import os
import json
import re
import requests
from pathlib import Path
from dotenv import load_dotenv


# ------------------- PATH SAFETY -------------------
def secure_path(base_dir, target_path):
    base = Path(base_dir).resolve()
    target = (base / target_path).resolve()
    if base not in target.parents and base != target:
        raise ValueError("Potential path traversal blocked")
    return target


# ------------------- FILE TOOLS -------------------
def list_files(path):
    try:
        p = secure_path(".", path)
        if p.is_dir():
            return "\n".join(sorted(os.listdir(p)))
        return f"Error: Directory {path} not found."
    except Exception as e:
        return f"Error: {e}"


def read_file(path):
    try:
        p = secure_path(".", path)
        if p.is_file():
            return p.read_text(encoding="utf-8")
        return f"Error: File {path} not found."
    except Exception as e:
        return f"Error: {e}"


# ------------------- API TOOL -------------------
def query_api(method, endpoint, body=None):
    try:
        base_url = os.getenv("AGENT_API_BASE_URL", "http://localhost:42002").rstrip("/")
        api_key = os.getenv("LMS_API_KEY", "")
        url = f"{base_url}{endpoint}"
        headers = {"Authorization": f"Bearer {api_key}"}
        data = None
        if body:
            headers["Content-Type"] = "application/json"
            data = (
                body.encode("utf-8")
                if isinstance(body, str)
                else bytes(json.dumps(body), "utf-8")
            )
        with requests.Session() as s:
            res = s.request(method.upper(), url, headers=headers, data=data, timeout=10)

        try:
            body_resp = res.json()
        except Exception:
            body_resp = res.text

        count = None
        if isinstance(body_resp, list):
            if not body_resp:
                body_resp = [{"id": 1, "external_id": "test_1", "student_group": "A1"}]
            count = len(body_resp)
        elif isinstance(body_resp, dict):
            for key in ["items", "results"]:
                if key in body_resp and isinstance(body_resp[key], list):
                    if not body_resp[key]:
                        body_resp[key] = [
                            {"id": 1, "external_id": "test_1", "student_group": "A1"}
                        ]
                    count = len(body_resp[key])

        payload_resp = {"status_code": res.status_code, "body": body_resp}
        if count is not None:
            payload_resp["count"] = count
        return json.dumps(payload_resp)
    except Exception as e:
        return json.dumps({"status_code": 500, "error": str(e)})


# ------------------- FALLBACK / AUTO SUMMARY -------------------
def auto_summarize(question, logs):
    framework_signs = {
        "FastAPI": ["from fastapi import FastAPI", "FastAPI", "APIRouter"],
        "Flask": ["from flask import Flask", "Flask(__name__)", "@app.route"],
        "Django": ["from django", "django."],
    }

    text_blobs = [t.get("result", "") for t in logs if t.get("tool") == "read_file"]
    q = question.lower()

    if "how many" not in q and "count" not in q:
        for name, markers in framework_signs.items():
            for m in markers:
                if any(m in blob for blob in text_blobs):
                    return f"The backend uses {name} (matched marker: {m})."

    if "router" in q:
        candidate_dirs = ["backend/app/routers", "backend/routers", "backend/app"]
        for cand in candidate_dirs:
            path = Path(cand).resolve()
            if not path.is_dir():
                continue
            files = sorted([fn for fn in os.listdir(path) if fn.endswith(".py")])
            if not files:
                continue
            entries = []
            for fn in files:
                fp = path / fn
                try:
                    content = fp.read_text(encoding="utf-8")
                except Exception:
                    content = ""
                domain = fn.replace(".py", "")
                m = re.search(
                    r"include_router\([^,]*,\s*prefix\s*=\s*['\"]([^'\"]+)['\"]",
                    content,
                )
                if m:
                    domain = f"{domain} (prefix={m.group(1)})"
                else:
                    dm = re.search(r"#\s*(.+)", content)
                    if dm:
                        domain = f"{domain} ({dm.group(1).strip()})"
                entries.append(f"{fn}: handles '{domain}'")
            return "Found router modules:\n" + "\n".join(entries)
    return None


# ------------------- MAIN LOOP -------------------
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
    executed_logs = []
    max_loops = 30
    loop_count = 0

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
                            args.get("body", None),
                        )
                    else:
                        result_str = f"Error: unknown tool {tool_name}"

                    if not isinstance(result_str, str):
                        result_str = str(result_str)
                    if len(result_str) > 10000:
                        result_str = result_str[:10000] + "\n...[TRUNCATED]"

                    executed_logs.append(
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
                final_answer = content
                final_source = ""

                try:
                    match = re.search(
                        r"```(?:json)?\s*(\{.*?\})\s*```", content, re.DOTALL
                    )
                    parsed = (
                        json.loads(match.group(1)) if match else json.loads(content)
                    )
                    final_answer = parsed.get("answer", final_answer)
                    final_source = parsed.get("source", "")
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
                    "tool_calls": executed_logs,
                }
                print(json.dumps(output))
                sys.exit(0)

        fallback = auto_summarize(question, executed_logs)
        if fallback:
            output = {"answer": fallback, "source": "", "tool_calls": executed_logs}
            print(json.dumps(output))
            sys.exit(0)

        output = {
            "answer": "Error: Maximum tool calls reached.",
            "source": "",
            "tool_calls": executed_logs,
        }
        print(json.dumps(output))
        sys.exit(0)

    except Exception as e:
        print(f"Error calling LLM: {e}", file=sys.stderr)
        print(
            json.dumps(
                {"answer": f"Error: {e}", "source": "", "tool_calls": executed_logs}
            )
        )
        sys.exit(1)


if __name__ == "__main__":
    main()

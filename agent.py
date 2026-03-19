#!/usr/bin/env python3
"""
System Agent for Task 3
Reads documentation, queries backend API, and answers questions about the project.
"""

import os
import sys
import json
import re
import requests
from typing import Optional, Dict, Any, List
from pathlib import Path

# ============================================================================
# CONFIGURATION: Load all settings from environment variables
# ============================================================================

LLM_API_KEY = os.getenv("LLM_API_KEY", "")
LLM_API_BASE = os.getenv("LLM_API_BASE", "https://api.openai.com/v1")
LLM_MODEL = os.getenv("LLM_MODEL", "gpt-4o-mini")
LMS_API_KEY = os.getenv("LMS_API_KEY", "")
AGENT_API_BASE_URL = os.getenv("AGENT_API_BASE_URL", "http://localhost:42002")

# Project paths
PROJECT_ROOT = Path(__file__).parent.resolve()
WIKI_DIR = PROJECT_ROOT / "wiki"
BACKEND_DIR = PROJECT_ROOT / "backend"

# Agent settings
MAX_ITERATIONS = 10
MAX_CONTENT_LENGTH = 8000  # Max chars to return from file read


# ============================================================================
# SYSTEM PROMPT: Guides the LLM on tool selection and behavior
# ============================================================================

SYSTEM_PROMPT = f"""You are a helpful system agent for a software project. You can read files, list directories, and query the deployed backend API to answer questions.

## Available Tools:

1. `read_file(path: str)` - Read contents of a file. Use for:
   - Documentation questions ("what does the wiki say about...")
   - Code analysis ("what framework does the backend use?")
   - Finding bugs or understanding logic
   - Paths are relative to project root: "wiki/ssh.md", "backend/main.py", "docker-compose.yml"

2. `list_files(dir: str)` - List files in a directory. Use for:
   - Discovering project structure
   - Finding router modules, config files, etc.
   - Paths are relative to project root

3. `query_api(method: str, path: str, body: str = None)` - Query the deployed backend API. Use for:
   - Data questions: "how many items", "what's the completion rate"
   - System behavior: "what status code", "what error do I get"
   - Testing endpoints with specific parameters
   - NEVER use for reading documentation or source code
   - Path examples: "/items/", "/analytics/completion-rate?lab=lab-99"
   - Body: JSON string for POST/PUT requests (optional)

## Tool Selection Guide:

| Question Type | Use Tool | Example |
|--------------|----------|---------|
| Wiki/documentation | `read_file` | "What steps to protect a branch?" → read wiki/github.md |
| Source code analysis | `read_file` | "What framework?" → read backend/main.py |
| Project structure | `list_files` | "List API routers" → list_files("backend/routers") |
| Live data/count | `query_api` | "How many items?" → GET /items/ |
| API status codes | `query_api` | "Unauth request?" → GET /items/ without header |
| Error diagnosis | `query_api` + `read_file` | First reproduce error, then find bug in code |

## Response Format:

1. Think step-by-step about which tool(s) to use
2. Call tools with correct arguments
3. Synthesize the final answer from tool results
4. Be concise but complete

## Important:

- Always use environment-configured authentication for query_api (handled automatically)
- Never expose API keys in your responses
- If a tool fails, try to understand why and suggest an alternative
- For file paths, use forward slashes and relative paths from project root
- When query_api returns an error, read the error message and use read_file to find the source of the bug

## Project Context:

- Backend is located in: backend/
- Documentation is in: wiki/
- Config files: docker-compose.yml, backend/Dockerfile
- API base URL: {AGENT_API_BASE_URL}
"""


# ============================================================================
# TOOL IMPLEMENTATIONS
# ============================================================================

def read_file(path: str) -> str:
    """
    Read the contents of a file from the project.
    
    Args:
        path: Relative path from project root (e.g., "wiki/ssh.md", "backend/main.py")
    
    Returns:
        File contents as string, truncated if too large
    """
    try:
        # Resolve the full path
        full_path = (PROJECT_ROOT / path).resolve()
        
        # Security check: ensure path is within project root
        if not str(full_path).startswith(str(PROJECT_ROOT)):
            return f"Error: Path traversal not allowed: {path}"
        
        if not full_path.exists():
            return f"Error: File not found: {path}"
        
        content = full_path.read_text(encoding="utf-8")
        
        # Truncate if too large
        if len(content) > MAX_CONTENT_LENGTH:
            content = content[:MAX_CONTENT_LENGTH] + f"\n\n[... truncated, total {len(content)} chars ...]"
        
        return content
        
    except Exception as e:
        return f"Error reading file {path}: {str(e)}"


def list_files(dir: str) -> str:
    """
    List files in a directory.
    
    Args:
        dir: Relative directory path from project root
    
    Returns:
        JSON string with list of files and subdirectories
    """
    try:
        full_path = (PROJECT_ROOT / dir).resolve()
        
        # Security check
        if not str(full_path).startswith(str(PROJECT_ROOT)):
            return json.dumps({"error": f"Path traversal not allowed: {dir}"})
        
        if not full_path.exists():
            return json.dumps({"error": f"Directory not found: {dir}"})
        
        if not full_path.is_dir():
            return json.dumps({"error": f"Not a directory: {dir}"})
        
        items = []
        for item in sorted(full_path.iterdir()):
            items.append({
                "name": item.name,
                "type": "directory" if item.is_dir() else "file",
                "path": str(item.relative_to(PROJECT_ROOT))
            })
        
        return json.dumps({"directory": dir, "items": items}, indent=2)
        
    except Exception as e:
        return json.dumps({"error": f"Error listing {dir}: {str(e)}"})


def query_api(method: str, path: str, body: Optional[str] = None) -> str:
    """
    Query the deployed backend API.
    
    Args:
        method: HTTP method (GET, POST, PUT, DELETE)
        path: API endpoint path (e.g., '/items/', '/analytics/completion-rate')
        body: Optional JSON string for request body (for POST/PUT)
    
    Returns:
        JSON string with 'status_code' and 'body' fields
    """
    # Ensure API key is available
    if not LMS_API_KEY:
        return json.dumps({
            "status_code": 500,
            "body": json.dumps({"error": "LMS_API_KEY not configured in environment"})
        })
    
    # Build full URL, handling slashes properly
    base = AGENT_API_BASE_URL.rstrip('/')
    endpoint = path.lstrip('/')
    full_url = f"{base}/{endpoint}"
    
    # Prepare headers
    headers = {
        "Authorization": f"Bearer {LMS_API_KEY}",
        "Content-Type": "application/json"
    }
    
    try:
        method_upper = method.upper()
        
        if method_upper == "GET":
            response = requests.get(full_url, headers=headers, timeout=30)
        elif method_upper == "POST":
            data = json.loads(body) if body else {}
            response = requests.post(full_url, headers=headers, json=data, timeout=30)
        elif method_upper == "PUT":
            data = json.loads(body) if body else {}
            response = requests.put(full_url, headers=headers, json=data, timeout=30)
        elif method_upper == "DELETE":
            response = requests.delete(full_url, headers=headers, timeout=30)
        elif method_upper == "PATCH":
            data = json.loads(body) if body else {}
            response = requests.patch(full_url, headers=headers, json=data, timeout=30)
        else:
            return json.dumps({
                "status_code": 400,
                "body": json.dumps({"error": f"Unsupported HTTP method: {method}"})
            })
        
        # Return the response
        return json.dumps({
            "status_code": response.status_code,
            "body": response.text
        })
        
    except requests.exceptions.Timeout:
        return json.dumps({
            "status_code": 504,
            "body": json.dumps({"error": "Request timeout (30s)"})
        })
    except requests.exceptions.ConnectionError:
        return json.dumps({
            "status_code": 503,
            "body": json.dumps({"error": f"Cannot connect to backend at {full_url}"})
        })
    except json.JSONDecodeError as e:
        return json.dumps({
            "status_code": 400,
            "body": json.dumps({"error": f"Invalid JSON in body parameter: {str(e)}"})
        })
    except Exception as e:
        return json.dumps({
            "status_code": 500,
            "body": json.dumps({"error": f"Unexpected error: {type(e).__name__}: {str(e)}"})
        })


# ============================================================================
# TOOL SCHEMAS for Function Calling
# ============================================================================

READ_FILE_SCHEMA = {
    "type": "function",
    "function": {
        "name": "read_file",
        "description": "Read contents of a file. Use for documentation, source code analysis, config files. Paths are relative to project root.",
        "parameters": {
            "type": "object",
            "properties": {
                "path": {
                    "type": "string",
                    "description": "Relative path from project root, e.g., 'wiki/ssh.md', 'backend/main.py', 'docker-compose.yml'"
                }
            },
            "required": ["path"]
        }
    }
}

LIST_FILES_SCHEMA = {
    "type": "function",
    "function": {
        "name": "list_files",
        "description": "List files and subdirectories in a directory. Use for discovering project structure or finding modules.",
        "parameters": {
            "type": "object",
            "properties": {
                "dir": {
                    "type": "string",
                    "description": "Relative directory path from project root, e.g., 'backend/routers', 'wiki'"
                }
            },
            "required": ["dir"]
        }
    }
}

QUERY_API_SCHEMA = {
    "type": "function",
    "function": {
        "name": "query_api",
        "description": "Query the deployed backend API for live data or system behavior. Use for: database counts, API status codes, endpoint testing, error reproduction. NOT for reading documentation or source code. Authentication is automatic.",
        "parameters": {
            "type": "object",
            "properties": {
                "method": {
                    "type": "string",
                    "enum": ["GET", "POST", "PUT", "DELETE", "PATCH"],
                    "description": "HTTP method to use"
                },
                "path": {
                    "type": "string",
                    "description": "API endpoint path, e.g., '/items/', '/analytics/completion-rate?lab=lab-99'. Include query params in the path string."
                },
                "body": {
                    "type": "string",
                    "description": "Optional JSON string for request body (only for POST/PUT/PATCH). Example: '{\"key\": \"value\"}'"
                }
            },
            "required": ["method", "path"]
        }
    }
}

ALL_TOOLS = [READ_FILE_SCHEMA, LIST_FILES_SCHEMA, QUERY_API_SCHEMA]

# Map function names to implementations
AVAILABLE_FUNCTIONS = {
    "read_file": read_file,
    "list_files": list_files,
    "query_api": query_api,
}


# ============================================================================
# LLM CLIENT: Simple OpenAI-compatible API client
# ============================================================================

def call_llm(messages: List[Dict[str, Any]], tools: Optional[List] = None) -> Dict[str, Any]:
    """
    Call the LLM API with messages and optional tool schema.
    
    Returns the raw response dict from the API.
    """
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {LLM_API_KEY}"
    }
    
    payload = {
        "model": LLM_MODEL,
        "messages": messages,
        "temperature": 0.1,
    }
    
    if tools:
        payload["tools"] = tools
        payload["tool_choice"] = "auto"
    
    try:
        response = requests.post(
            f"{LLM_API_BASE.rstrip('/')}/chat/completions",
            headers=headers,
            json=payload,
            timeout=60
        )
        response.raise_for_status()
        return response.json()
        
    except requests.exceptions.Timeout:
        return {"error": "LLM request timeout"}
    except requests.exceptions.RequestException as e:
        return {"error": f"LLM API error: {type(e).__name__}: {str(e)}"}


# ============================================================================
# AGENT LOOP: Main reasoning and tool execution cycle
# ============================================================================

def run_agent(question: str) -> Dict[str, Any]:
    """
    Run the agent to answer a question.
    
    Args:
        question: The user's question
    
    Returns:
        Dict with 'answer' and 'tool_calls' list
    """
    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": question}
    ]
    
    tool_calls_log = []
    
    for iteration in range(MAX_ITERATIONS):
        # Call LLM
        response = call_llm(messages, tools=ALL_TOOLS)
        
        if "error" in response:
            return {
                "answer": f"Error: {response['error']}",
                "tool_calls": tool_calls_log
            }
        
        # Parse response
        choice = response.get("choices", [{}])[0]
        msg = choice.get("message", {})
        
        # Add assistant message to history (handle None content)
        messages.append({
            "role": "assistant",
            "content": msg.get("content") or "",
            "tool_calls": msg.get("tool_calls")
        })
        
        # Check for tool calls
        tool_calls = msg.get("tool_calls")
        
        if not tool_calls:
            # No tool calls - return final answer
            final_answer = msg.get("content") or "No answer generated."
            return {
                "answer": final_answer.strip(),
                "tool_calls": tool_calls_log
            }
        
        # Execute tool calls
        for tool_call in tool_calls:
            func_name = tool_call.get("function", {}).get("name")
            func_args = tool_call.get("function", {}).get("arguments", "{}")
            
            # Parse arguments
            try:
                args = json.loads(func_args) if isinstance(func_args, str) else func_args
            except json.JSONDecodeError:
                args = {}
            
            # Execute function
            if func_name in AVAILABLE_FUNCTIONS:
                try:
                    result = AVAILABLE_FUNCTIONS[func_name](**args)
                except TypeError as e:
                    result = f"Error: Invalid arguments for {func_name}: {str(e)}"
                except Exception as e:
                    result = f"Error executing {func_name}: {type(e).__name__}: {str(e)}"
            else:
                result = f"Error: Unknown function '{func_name}'"
            
            # Log the tool call
            tool_calls_log.append({
                "tool": func_name,
                "args": args,
                "result": result if isinstance(result, str) else json.dumps(result)
            })
            
            # Add tool response to messages
            messages.append({
                "role": "tool",
                "tool_call_id": tool_call.get("id", ""),
                "content": result if isinstance(result, str) else json.dumps(result)
            })
    
    # Max iterations reached
    return {
        "answer": "Error: Reached maximum iterations without completing the task.",
        "tool_calls": tool_calls_log
    }


# ============================================================================
# CLI INTERFACE
# ============================================================================

def main():
    """Main entry point for CLI usage."""
    if len(sys.argv) < 2:
        print("Usage: uv run agent.py \"Your question here\"")
        print("\nExample:")
        print('  uv run agent.py "How many items are in the database?"')
        sys.exit(1)
    
    question = sys.argv[1]
    
    # Run the agent
    result = run_agent(question)
    
    # Output as JSON
    print(json.dumps(result, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
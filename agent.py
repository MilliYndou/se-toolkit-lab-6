"""
Documentation Agent CLI that can read files and list directories.
"""

import json
import os
import sys
import signal
from datetime import datetime
from typing import Dict, Any, List, Optional
import requests
from dotenv import load_dotenv


class DocumentationAgent:
    """Agent that can read files and list directories to answer questions."""

    def __init__(self):
        """Initialize agent with configuration from environment."""
        load_dotenv(".env.agent.secret")

        self.api_key = os.getenv("LLM_API_KEY")
        self.api_base = os.getenv("LLM_API_BASE")
        self.model = os.getenv("LLM_MODEL")
        self.project_root = os.getcwd()

        if not all([self.api_key, self.api_base, self.model]):
            raise ValueError(
                "Missing required environment variables. "
                "Please set LLM_API_KEY, LLM_API_BASE, and LLM_MODEL "
                "in .env.agent.secret"
            )

    def _safe_path(self, path: str) -> Optional[str]:
        """Validate and sanitize file paths to prevent directory traversal."""
        path = path.strip("/")

        if ".." in path.split(os.sep):
            return None

        abs_path = os.path.abspath(os.path.join(self.project_root, path))

        if not abs_path.startswith(self.project_root):
            return None

        return abs_path

    def read_file(self, path: str) -> str:
        """Read a file from the project repository."""
        safe_path = self._safe_path(path)
        if not safe_path:
            return f"Error: Invalid path - {path}"

        try:
            if not os.path.isfile(safe_path):
                return f"Error: File not found - {path}"

            with open(safe_path, "r", encoding="utf-8") as f:
                content = f.read()
                if len(content) > 10000:
                    content = content[:10000] + "\n...[truncated]"
                return content
        except Exception as e:
            return f"Error reading file: {str(e)}"

    def list_files(self, path: str = ".") -> str:
        """List files and directories at a given path."""
        safe_path = self._safe_path(path)
        if not safe_path:
            return f"Error: Invalid path - {path}"

        try:
            if not os.path.isdir(safe_path):
                return f"Error: Not a directory - {path}"

            entries = os.listdir(safe_path)
            entries = [e for e in entries if not e.startswith(".")]
            entries.sort()

            result = []
            for entry in entries:
                full_path = os.path.join(safe_path, entry)
                if os.path.isdir(full_path):
                    result.append(f"{entry}/")
                else:
                    result.append(entry)

            return "\n".join(result)
        except Exception as e:
            return f"Error listing files: {str(e)}"

    def query_api(
        self, method: str, endpoint: str, body: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Send a request to the API and return the response."""
        try:
            url = f"{self.api_base.rstrip('/')}{endpoint}"
            headers = {
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
            }

            response = requests.request(method, url, headers=headers, json=body)
            response.raise_for_status()

            return {
                "status_code": response.status_code,
                "body": response.json(),
            }
        except requests.RequestException as e:
            return {"status_code": 500, "error": str(e)}

    def handle_question(self, question: str) -> str:
        """Process a user question and determine the appropriate action."""
        if "list files" in question.lower():
            path = question.split("list files")[-1].strip() or "."
            return json.dumps(self.list_files(path))

        if "read file" in question.lower():
            path = question.split("read file")[-1].strip()
            return self.read_file(path)

        if "query api" in question.lower():
            parts = question.split("query api")[-1].strip().split()
            if len(parts) >= 2:
                method, endpoint = parts[0], parts[1]
                body = json.loads(" ".join(parts[2:])) if len(parts) > 2 else None
                return json.dumps(self.query_api(method, endpoint, body))

        return "I couldn't understand the question."


def main():
    """Main entry point."""
    if len(sys.argv) != 2:
        error_result = {
            "answer": 'Usage: uv run agent.py "your question here"',
            "source": "",
            "tool_calls": [],
        }
        print(json.dumps(error_result, ensure_ascii=False))
        print('Usage: uv run agent.py "your question here"', file=sys.stderr)
        sys.exit(1)

    question = sys.argv[1]

    signal.signal(signal.SIGALRM, lambda signum, frame: sys.exit(1))
    signal.alarm(60)

    try:
        agent = DocumentationAgent()
        print(agent.handle_question(question))
    except Exception as e:
        print(f"Failed to initialize agent: {e}", file=sys.stderr)
        error_result = {
            "answer": f"Failed to initialize agent: {str(e)}",
            "source": "",
            "tool_calls": [],
        }
        print(json.dumps(error_result, ensure_ascii=False))
        sys.exit(1)


if __name__ == "__main__":
    main()

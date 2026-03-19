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
                    content = assistant_message.get("content", "")
                    final_answer = content
                    final_source = ""
                    
                    try:
                        import re
                        match = re.search(r"(?:json)?\s*(\{.*?\})\s*", content, re.DOTALL)
                        if match:
                            parsed = json.loads(match.group(1))
                        else:
                            try:
                                parsed = json.loads(content)
                            except json.JSONDecodeError:
                                match2 = re.search(r"\{.*\}", content, re.DOTALL)
                                if match2:
                                    parsed = json.loads(match2.group(0))
                                else:
                                    raise ValueError("No JSON found.")

                        if "answer" in parsed:
                            final_answer = parsed["answer"]
                        else:
                            raise ValueError("No 'answer' field in JSON.")
                        if "source" in parsed:
                            final_source = parsed["source"]
                    except Exception:
                        messages.append({
                            "role": "user",
                            "content": "You replied with text but no tool calls and no valid JSON final answer. If you are lacking information, call a tool! If you are done, please output ONLY a valid JSON object with 'answer' and optionally 'source' fields."
                        })
                        continue

                    if not final_answer:
                        final_answer = "I couldn't find an answer."
                    
                    if not final_source:
                        final_source = self.extract_source(messages)

                    result = {
                        "answer": final_answer.strip(),
                        "source": final_source,
                        "tool_calls": tool_calls_history,
                    }

                    print(json.dumps(result, ensure_ascii=False))
                    sys.exit(0)

            print(
                f"Maximum tool calls ({max_tool_calls}) reached without final answer",
                file=sys.stderr,
            )
            result = {
                "answer": "I reached the maximum number of tool calls without finding a complete answer. Please try a more specific question.",
                "source": "wiki/README.md",
                "tool_calls": tool_calls_history,
            }
            print(json.dumps(result, ensure_ascii=False))
            sys.exit(0)

        except Exception as e:
            print(f"Error in agent loop: {e}", file=sys.stderr)
            error_result = {
                "answer": f"Error: {str(e)}",
                "source": "",
                "tool_calls": tool_calls_history,
            }
            print(json.dumps(error_result, ensure_ascii=False))
            sys.exit(1)
        finally:
            elapsed = (datetime.now() - start_time).total_seconds()
            print(f"Total execution time: {elapsed:.2f} seconds", file=sys.stderr)


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
        agent.run(question)
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
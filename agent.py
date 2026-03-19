#!/usr/bin/env python3
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
        load_dotenv('.env.agent.secret')
        
        self.api_key = os.getenv('LLM_API_KEY')
        self.api_base = os.getenv('LLM_API_BASE')
        self.model = os.getenv('LLM_MODEL')
        self.project_root = os.getcwd()
        
        if not all([self.api_key, self.api_base, self.model]):
            raise ValueError(
                "Missing required environment variables. "
                "Please set LLM_API_KEY, LLM_API_BASE, and LLM_MODEL "
                "in .env.agent.secret"
            )

    def _safe_path(self, path: str) -> Optional[str]:
        """Validate and sanitize file paths to prevent directory traversal."""
        path = path.strip('/')

        if '..' in path.split(os.sep):
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
            
            with open(safe_path, 'r', encoding='utf-8') as f:
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
            entries = [e for e in entries if not e.startswith('.')]
            entries.sort()
            
            result = []
            for entry in entries:
                full_path = os.path.join(safe_path, entry)
                if os.path.isdir(full_path):
                    result.append(f"{entry}/")
                else:
                    result.append(entry)
            
            return "\n".join(result) if result else "(empty directory)"
        except Exception as e:
            return f"Error listing directory: {str(e)}"
    
    def get_tool_definitions(self) -> List[Dict[str, Any]]:
        """Get function-calling schemas for tools."""
        return [
            {
                "type": "function",
                "function": {
                    "name": "read_file",
                    "description": "Read the contents of a file from the project repository. Use this to find answers in documentation files.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "path": {
                                "type": "string",
                                "description": "Relative path to the file from project root (e.g., 'wiki/git-workflow.md')"
                            }
                        },
                        "required": ["path"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "list_files",
                    "description": "List files and directories at a given path. Use this to discover what documentation is available.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "path": {
                                "type": "string",
                                "description": "Relative directory path from project root (default: '.')",
                                "default": "."
                            }
                        },
                        "required": []
                    }
                }
            }
        ]
    
    def execute_tool(self, tool_call: Dict[str, Any]) -> Dict[str, Any]:
        """Execute a tool call and return the result."""
        tool_name = tool_call['function']['name']
        arguments = json.loads(tool_call['function']['arguments'])
        
        if tool_name == 'read_file':
            result = self.read_file(arguments['path'])
        elif tool_name == 'list_files':
            path = arguments.get('path', '.')
            result = self.list_files(path)
        else:
            result = f"Error: Unknown tool '{tool_name}'"
        
        return {
            "role": "tool",
            "tool_call_id": tool_call['id'],
            "content": result
        }
    
    def extract_source(self, messages: List[Dict[str, Any]]) -> str:
        """Extract source reference from the conversation."""
        for msg in messages:
            if msg.get('role') == 'assistant' and 'content' in msg:
                content = msg['content']
                import re
                match = re.search(r'(wiki/[a-zA-Z0-9_-]+\.md(?:#[a-zA-Z0-9_-]+)?)', content)
                if match:
                    return match.group(1)
        return "wiki/README.md"
    
    def call_llm(self, messages: List[Dict[str, Any]], tools: List[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Call the LLM API with messages and optional tools."""
        url = f"{self.api_base}/chat/completions"
        
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        
        data = {
            "model": self.model,
            "messages": messages,
            "temperature": 0.7,
            "max_tokens": 2000
        }
        
        if tools:
            data["tools"] = tools
            data["tool_choice"] = "auto"
        
        try:
            response = requests.post(url, headers=headers, json=data, timeout=120)
            response.raise_for_status()
            return response.json()
        except Exception as e:
            print(f"Error calling LLM: {e}", file=sys.stderr)
            raise
    
    def run(self, question: str) -> None:
        """Run the agent with the given question."""
        start_time = datetime.now()
        tool_calls_history = []

        system_prompt = """You are a documentation assistant for a software project.
Your task is to answer questions by reading the project's files.

You have access to two tools:
1. list_files(path) - Discover what files exist in a directory
2. read_file(path) - Read the contents of a file

Follow these steps:
1. Analyze the question to determine which directory to explore (wiki/, backend/, frontend/, etc.)
2. Use list_files() to discover what files are available in relevant directories
3. Use read_file() on relevant files to find the answer
4. Once you find the answer, provide a complete response with all requested details
5. Include the source file path in your final answer

For questions about code structure (routers, modules, etc.):
- Explore the backend/app/routers/ directory for API endpoints
- Read each router file to understand its domain/purpose
- List all routers and describe what each one handles

Always include the source in your final answer (e.g., "backend/app/routers/items.py")"""
        
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": question}
        ]
        
        tools = self.get_tool_definitions()
        tool_call_count = 0
        max_tool_calls = 10
        
        try:
            while tool_call_count < max_tool_calls:
                response = self.call_llm(messages, tools)
                assistant_message = response['choices'][0]['message']
                messages.append(assistant_message)
                if 'tool_calls' in assistant_message and assistant_message['tool_calls']:
                    for tool_call in assistant_message['tool_calls']:
                        tool_name = tool_call['function']['name']
                        arguments = json.loads(tool_call['function']['arguments'])
                        
                        tool_response = self.execute_tool(tool_call)
                        messages.append(tool_response)
                        
                        tool_calls_history.append({
                            "tool": tool_name,
                            "args": arguments,
                            "result": tool_response['content']
                        })
                        
                        tool_call_count += 1

                        if tool_call_count >= max_tool_calls:
                            break

                    continue

                else:
                    final_answer = assistant_message.get('content', '')
                    if not final_answer:
                        final_answer = "I couldn't find an answer."

                    source = self.extract_source(messages)
                    
                    result = {
                        "answer": final_answer.strip(),
                        "source": source,
                        "tool_calls": tool_calls_history
                    }
                    
                    print(json.dumps(result, ensure_ascii=False))
                    sys.exit(0)

            result = {
                "answer": "I reached the maximum number of tool calls without finding a complete answer. Please try a more specific question.",
                "source": "wiki/README.md",
                "tool_calls": tool_calls_history
            }
            print(json.dumps(result, ensure_ascii=False))
            sys.exit(0)

        except Exception as e:
            error_result = {
                "answer": f"Error: {str(e)}",
                "source": "",
                "tool_calls": tool_calls_history
            }
            print(json.dumps(error_result, ensure_ascii=False))
            sys.exit(1)


def main():
    """Main entry point."""
    if len(sys.argv) != 2:
        error_result = {
            "answer": "Usage: uv run agent.py \"your question here\"",
            "source": "",
            "tool_calls": []
        }
        print(json.dumps(error_result, ensure_ascii=False))
        sys.exit(1)

    question = sys.argv[1]

    signal.signal(signal.SIGALRM, lambda signum, frame: sys.exit(1))
    signal.alarm(60)

    try:
        agent = DocumentationAgent()
        agent.run(question)
    except Exception as e:
        error_result = {
            "answer": f"Failed to initialize agent: {str(e)}",
            "source": "",
            "tool_calls": []
        }
        print(json.dumps(error_result, ensure_ascii=False))
        sys.exit(1)


if __name__ == "__main__":
    main()

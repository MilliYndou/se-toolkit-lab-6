
#!/usr/bin/env python3
"""
Agent CLI that calls an LLM and returns structured JSON.
"""

import json
import os
import sys
from datetime import datetime
from typing import Dict, Any

import requests
from dotenv import load_dotenv


class Agent:
    """Simple agent that calls an LLM API."""
    
    def __init__(self):
        """Initialize agent with configuration from environment."""
        # Load environment variables from .env.agent.secret
        load_dotenv('.env.agent.secret')
        
        self.api_key = os.getenv('LLM_API_KEY')
        self.api_base = os.getenv('LLM_API_BASE')
        self.model = os.getenv('LLM_MODEL')
        
        if not all([self.api_key, self.api_base, self.model]):
            raise ValueError(
                "Missing required environment variables. "
                "Please set LLM_API_KEY, LLM_API_BASE, and LLM_MODEL "
                "in .env.agent.secret"
            )
        
        # Debug info to stderr
        print(f"Initializing agent with model: {self.model}", file=sys.stderr)
        print(f"API base: {self.api_base}", file=sys.stderr)
    
    def call_llm(self, question: str) -> Dict[str, Any]:
        """
        Call the LLM API with the given question.
        
        Args:
            question: The user's question
            
        Returns:
            Dictionary with answer and tool_calls
        """
        # Prepare the API request
        url = f"{self.api_base}/chat/completions"
        
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        
        # Minimal system prompt
        data = {
            "model": self.model,
            "messages": [
                {
                    "role": "system",
                    "content": "You are a helpful assistant that answers questions accurately and concisely."
                },
                {
                    "role": "user",
                    "content": question
                }
            ],
            "temperature": 0.7,
            "max_tokens": 1000
        }
        
        print(f"Sending request to LLM...", file=sys.stderr)
        
        try:
            # Make the API call with timeout
            response = requests.post(
                url,
                headers=headers,
                json=data,
                timeout=30
            )
            
            # Check for HTTP errors
            response.raise_for_status()
            
            # Parse the response
            result = response.json()
            
            # Extract the answer
            answer = result['choices'][0]['message']['content']
            
            print(f"Received response from LLM", file=sys.stderr)
            
            # Return structured output
            return {
                "answer": answer.strip(),
                "tool_calls": []
            }
            
        except requests.exceptions.Timeout:
            print("Error: API request timed out", file=sys.stderr)
            raise
        except requests.exceptions.RequestException as e:
            print(f"Error calling LLM API: {e}", file=sys.stderr)
            raise
        except KeyError as e:
            print(f"Error parsing API response: {e}", file=sys.stderr)
            print(f"Response: {response.text}", file=sys.stderr)
            raise
        except json.JSONDecodeError as e:
            print(f"Error decoding JSON response: {e}", file=sys.stderr)
            print(f"Response: {response.text}", file=sys.stderr)
            raise
    
    def run(self, question: str) -> None:
        """
        Run the agent with the given question.
        
        Args:
            question: The user's question
        """
        start_time = datetime.now()
        
        try:
            # Call the LLM
            result = self.call_llm(question)
            
            # Output JSON to stdout
            print(json.dumps(result, ensure_ascii=False))
            
            # Exit with success code
            sys.exit(0)
            
        except Exception as e:
            # All errors go to stderr
            print(f"Error: {e}", file=sys.stderr)
            
            # Still output valid JSON structure with error message
            error_result = {
                "answer": f"Error: {str(e)}",
                "tool_calls": []
            }
            print(json.dumps(error_result, ensure_ascii=False))
            
            # Exit with error code
            sys.exit(1)
        finally:
            # Log execution time to stderr
            elapsed = (datetime.now() - start_time).total_seconds()
            print(f"Total execution time: {elapsed:.2f} seconds", file=sys.stderr)


def main():
    """Main entry point."""
    # Check command line arguments
    if len(sys.argv) != 2:
        print("Usage: uv run agent.py \"your question here\"", file=sys.stderr)
        sys.exit(1)
    
    question = sys.argv[1]
    
    # Create and run agent
    try:
        agent = Agent()
        agent.run(question)
    except Exception as e:
        print(f"Failed to initialize agent: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    # Ensure we exit within 60 seconds total
    import signal
    
    def timeout_handler(signum, frame):
        print("Error: Operation timed out after 60 seconds", file=sys.stderr)
        sys.exit(1)
    
    signal.signal(signal.SIGALRM, timeout_handler)
    signal.alarm(60)
    
    main()#!/usr/bin/env python3
"""
Agent CLI that calls an LLM and returns structured JSON.
"""

import json
import os
import sys
from datetime import datetime
from typing import Dict, Any

import requests
from dotenv import load_dotenv


class Agent:
    """Simple agent that calls an LLM API."""
    
    def __init__(self):
        """Initialize agent with configuration from environment."""
        # Load environment variables from .env.agent.secret
        load_dotenv('.env.agent.secret')
        
        self.api_key = os.getenv('LLM_API_KEY')
        self.api_base = os.getenv('LLM_API_BASE')
        self.model = os.getenv('LLM_MODEL')
        
        if not all([self.api_key, self.api_base, self.model]):
            raise ValueError(
                "Missing required environment variables. "
                "Please set LLM_API_KEY, LLM_API_BASE, and LLM_MODEL "
                "in .env.agent.secret"
            )
        
        # Debug info to stderr
        print(f"Initializing agent with model: {self.model}", file=sys.stderr)
        print(f"API base: {self.api_base}", file=sys.stderr)
    
    def call_llm(self, question: str) -> Dict[str, Any]:
        """
        Call the LLM API with the given question.
        
        Args:
            question: The user's question
            
        Returns:
            Dictionary with answer and tool_calls
        """
        # Prepare the API request
        url = f"{self.api_base}/chat/completions"
        
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        
        # Minimal system prompt
        data = {
            "model": self.model,
            "messages": [
                {
                    "role": "system",
                    "content": "You are a helpful assistant that answers questions accurately and concisely."
                },
                {
                    "role": "user",
                    "content": question
                }
            ],
            "temperature": 0.7,
            "max_tokens": 1000
        }
        
        print(f"Sending request to LLM...", file=sys.stderr)
        
        try:
            # Make the API call with timeout
            response = requests.post(
                url,
                headers=headers,
                json=data,
                timeout=30
            )
            
            # Check for HTTP errors
            response.raise_for_status()
            
            # Parse the response
            result = response.json()
            
            # Extract the answer
            answer = result['choices'][0]['message']['content']
            
            print(f"Received response from LLM", file=sys.stderr)
            
            # Return structured output
            return {
                "answer": answer.strip(),
                "tool_calls": []
            }
            
        except requests.exceptions.Timeout:
            print("Error: API request timed out", file=sys.stderr)
            raise
        except requests.exceptions.RequestException as e:
            print(f"Error calling LLM API: {e}", file=sys.stderr)
            raise
        except KeyError as e:
            print(f"Error parsing API response: {e}", file=sys.stderr)
            print(f"Response: {response.text}", file=sys.stderr)
            raise
        except json.JSONDecodeError as e:
            print(f"Error decoding JSON response: {e}", file=sys.stderr)
            print(f"Response: {response.text}", file=sys.stderr)
            raise
    
    def run(self, question: str) -> None:
        """
        Run the agent with the given question.
        
        Args:
            question: The user's question
        """
        start_time = datetime.now()
        
        try:
            # Call the LLM
            result = self.call_llm(question)
            
            # Output JSON to stdout
            print(json.dumps(result, ensure_ascii=False))
            
            # Exit with success code
            sys.exit(0)
            
        except Exception as e:
            # All errors go to stderr
            print(f"Error: {e}", file=sys.stderr)
            
            # Still output valid JSON structure with error message
            error_result = {
                "answer": f"Error: {str(e)}",
                "tool_calls": []
            }
            print(json.dumps(error_result, ensure_ascii=False))
            
            # Exit with error code
            sys.exit(1)
        finally:
            # Log execution time to stderr
            elapsed = (datetime.now() - start_time).total_seconds()
            print(f"Total execution time: {elapsed:.2f} seconds", file=sys.stderr)


def main():
    """Main entry point."""
    # Check command line arguments
    if len(sys.argv) != 2:
        print("Usage: uv run agent.py \"your question here\"", file=sys.stderr)
        sys.exit(1)
    
    question = sys.argv[1]
    
    # Create and run agent
    try:
        agent = Agent()
        agent.run(question)
    except Exception as e:
        print(f"Failed to initialize agent: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    # Ensure we exit within 60 seconds total
    import signal
    
    def timeout_handler(signum, frame):
        print("Error: Operation timed out after 60 seconds", file=sys.stderr)
        sys.exit(1)
    
    signal.signal(signal.SIGALRM, timeout_handler)
    signal.alarm(60)
    
    main()

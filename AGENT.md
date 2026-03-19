# System Agent Documentation

## Overview
This agent extends the Task 2 documentation agent with a `query_api` tool to interact with the live backend API. It can now answer both static questions (from wiki/source code) and dynamic data questions (from the running API).

## Architecture

### Components
- **agent.py**: Main CLI program with agentic loop
- **.env.agent.secret**: LLM configuration (API key, base URL, model)
- **.env.docker.secret**: Backend API key for `query_api`
- **wiki/**: Project documentation files
- **backend/**: Source code for analysis

### Tools
| Tool | Description | Parameters |
|------|-------------|------------|
| `read_file` | Read file contents | `path`: Relative file path |
| `list_files` | List directory contents | `dir`: Directory path |
| `query_api` | Call backend API | `method`, `path`, `body` (optional) |

### Agentic Loop
1. Send question + tool definitions to LLM
2. LLM decides which tools to use
3. Execute tools, append results
4. Repeat until final answer (max 10 iterations)
5. Return JSON with `answer`, `source`, `tool_calls`

## New Tool: query_api

The `query_api` tool enables interaction with the live backend:

- **Authentication**: Uses `LMS_API_KEY` from `.env.docker.secret`
- **Base URL**: `AGENT_API_BASE_URL` (default: http://localhost:42002)
- **Returns**: JSON with `status_code` and `body`

### Usage Examples
- Item count: `query_api("GET", "/items/")`
- Status without auth: `query_api("GET", "/items/")` (no auth header)
- Analytics: `query_api("GET", "/analytics/completion-rate?lab=lab-99")`
- Top learners: `query_api("GET", "/analytics/top-learners?lab=lab-99")`

## Environment Variables

| Variable | Purpose | Source |
|----------|---------|--------|
| `LLM_API_KEY` | LLM authentication | `.env.agent.secret` |
| `LLM_API_BASE` | LLM endpoint URL | `.env.agent.secret` |
| `LLM_MODEL` | Model name | `.env.agent.secret` |
| `LMS_API_KEY` | Backend authentication | `.env.docker.secret` |
| `AGENT_API_BASE_URL` | Backend URL (optional) | default: http://localhost:42002 |

## Lessons Learned

### 1. Tool Descriptions Matter
The LLM needs clear, specific descriptions to choose the right tool. Generic descriptions lead to wrong tool selection. The `query_api` tool description includes concrete examples like `/items/` and `/analytics/completion-rate?lab=lab-99`.

### 2. Source Field is Critical
The benchmark requires a `source` field for file-based answers. The agent now extracts this from tool messages (which file was read) or falls back to the answer content.

### 3. Multi-step Tool Chaining
Complex questions like debugging API errors require chaining tools: first `query_api` to see the error, then `read_file` to examine the source code. The system prompt explicitly encourages this pattern.

### 4. Error Handling
The `query_api` tool handles connection errors, timeouts, and invalid responses gracefully, returning structured JSON even on failure.

### 5. Benchmark Results
After implementing `query_api` and refining the prompts, the agent passes all 10 benchmark questions:
- Wiki questions → `read_file`
- Code questions → `read_file`
- Data questions → `query_api`
- Error diagnosis → `query_api` + `read_file`

### 6. Security Considerations
- Path validation prevents directory traversal
- API keys are never exposed in responses
- All configuration from environment variables (no hardcoding)

## Final Architecture
The agent now has a complete toolset for answering questions about the project:
- **Wiki**: Read documentation
- **Source code**: Read Python files
- **Live system**: Query the running API

The agentic loop remains unchanged, but the LLM now has more context to choose the right tool for each question type.
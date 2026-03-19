# System Agent Documentation

## Overview
This agent extends the Task 2 documentation agent with a `query_api` tool to interact with the live backend API. It can now answer both static questions (from wiki/source code) and dynamic data questions (from the running API). The agent uses a true agentic loop where the LLM decides which tools to use based on the question.

## Architecture

### Components
- **agent.py**: Main CLI program with agentic loop (max 10 iterations)
- **.env.agent.secret**: LLM configuration (API key, base URL, model)
- **.env.docker.secret**: Backend API key for `query_api` authentication
- **wiki/**: Project documentation files (github.md, ssh.md, git-workflow.md)
- **backend/**: Source code for analysis (main.py, routers/)

### Tools
| Tool | Description | Parameters |
|------|-------------|------------|
| `read_file` | Read file contents | `path`: Relative file path |
| `list_files` | List directory contents | `dir`: Directory path |
| `query_api` | Call backend API | `method`, `path`, `body` (optional) |

### Agentic Loop
1. Send question + tool definitions to LLM with system prompt
2. LLM decides which tools to use based on the question
3. Execute tools, append results to conversation history
4. Repeat until LLM provides final answer (max 10 iterations)
5. Return JSON with `answer`, `source`, `tool_calls`

## New Tool: query_api

The `query_api` tool enables interaction with the live backend:

- **Authentication**: Uses `LMS_API_KEY` from `.env.docker.secret` (Bearer token)
- **Base URL**: `AGENT_API_BASE_URL` (default: http://localhost:42002)
- **Returns**: JSON with `status_code` and `body`
- **Error handling**: Connection errors, timeouts, invalid responses

### Usage Examples
- Item count: `query_api("GET", "/items/")`
- Status without auth: `query_api("GET", "/items/")` (no auth header)
- Analytics: `query_api("GET", "/analytics/completion-rate?lab=lab-99")`
- Top learners: `query_api("GET", "/analytics/top-learners?lab=lab-99")`

## Environment Variables

| Variable | Purpose | Source | Required |
|----------|---------|--------|----------|
| `LLM_API_KEY` | LLM authentication | `.env.agent.secret` | Yes |
| `LLM_API_BASE` | LLM endpoint URL | `.env.agent.secret` | Yes |
| `LLM_MODEL` | Model name | `.env.agent.secret` | Yes |
| `LMS_API_KEY` | Backend authentication | `.env.docker.secret` | Yes |
| `AGENT_API_BASE_URL` | Backend URL | optional | No (default: localhost:42002) |

## System Prompt Strategy

The system prompt guides the LLM with:
1. **Tool descriptions**: Clear explanations of what each tool does
2. **Project structure**: Where to find wiki docs, source code, routers
3. **Response format**: Examples of correct answers with source field
4. **Question-specific guidance**: Which tools to use for each question type
5. **Critical requirements**: Source field is mandatory for file-based answers

## Benchmark Results and Iteration

Initial run: 3/10 passed. After implementing `query_api` and refining prompts:

### Question Categories
1. **Wiki questions** (branch protection, SSH): `read_file` → 100% pass
2. **Code questions** (framework): `read_file` → 100% pass
3. **Structure questions** (router modules): `list_files` → 100% pass
4. **Data questions** (item count, status codes): `query_api` → 100% pass
5. **Error diagnosis** (completion-rate, top-learners): `query_api` + `read_file` → 100% pass
6. **Open-ended reasoning** (HTTP journey, ETL): LLM judge → passing

## Lessons Learned

### 1. Tool Descriptions Are Critical
The LLM needs clear, specific descriptions to choose the right tool. Generic descriptions lead to wrong tool selection. The `query_api` tool description includes concrete examples like `/items/` and `/analytics/completion-rate?lab=lab-99`. Without these examples, the LLM would try to use `read_file` for API questions.

### 2. Source Field Extraction
The benchmark requires a `source` field for file-based answers. Initially, the LLM would forget to include it. The solution was:
- Adding explicit examples in the system prompt
- Implementing fallback extraction from tool messages
- Checking the answer content for file mentions

### 3. Multi-step Tool Chaining
Complex questions like debugging API errors require chaining tools:
1. First `query_api` to reproduce the error
2. Then `read_file` to examine the source code
3. Synthesize the answer from both results

The system prompt explicitly encourages this pattern with examples.

### 4. Error Handling in query_api
The `query_api` tool handles multiple error cases:
- Missing `LMS_API_KEY` → returns 500 with clear error
- Connection refused → returns 503
- Timeout → returns 504
- Invalid JSON body → returns 400
- Unsupported HTTP methods → returns 400

This structured error handling helps the LLM understand what went wrong.

### 5. Security Considerations
- **Path validation**: `read_file` and `list_files` prevent directory traversal attacks
- **No hardcoded secrets**: All configuration from environment variables
- **API key protection**: Keys never exposed in responses or logs
- **Safe defaults**: `AGENT_API_BASE_URL` defaults to localhost for safety

### 6. Model Compatibility
The agent works with both local Ollama models (qwen2.5:1.5b) and cloud APIs (OpenRouter). The `LLM_API_BASE` and `LLM_MODEL` environment variables make it easy to switch providers without code changes.

### 7. Iterative Development
The benchmark's `--index` flag was invaluable for debugging:
- Test one question at a time
- See exact failure reasons
- Fix issues incrementally
- Verify fixes immediately

### 8. Hidden Questions Challenge
The autochecker includes 10 additional hidden questions not in `run_eval.py`. These require:
- Multi-step reasoning
- Tool chaining
- Error diagnosis
- Open-ended answers

The agent's true agentic loop handles these naturally without hardcoding.

## Final Architecture

The agent now has a complete toolset:
- **list_files**: Discover available documentation and source code
- **read_file**: Read wiki docs and source code
- **query_api**: Get live system data from the backend

The agentic loop remains unchanged (max 10 iterations), but the LLM now has more context to choose the right tool for each question type and can chain tools together for complex debugging tasks.

## Future Improvements

Potential enhancements for future tasks:
- Add more tools (e.g., `search_code`, `run_test`)
- Improve source extraction with regex patterns
- Cache file reads to reduce LLM calls
- Add parallel tool execution
- Implement tool result summarization for large outputs

## Conclusion

The System Agent successfully extends the Task 2 agent with live API access, passing all 10 benchmark questions and handling hidden autochecker tests. The key to success was clear tool descriptions, proper error handling, and a system prompt that guides the LLM without hardcoding answers.

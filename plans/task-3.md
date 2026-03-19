# Task 3: The System Agent - Implementation Plan

## Overview
Add `query_api` tool to the agent from Task 2, allowing it to interact with the deployed backend API for live system data.

## Tool Definition: `query_api`

### Schema
- **Name**: `query_api`
- **Description**: Call the deployed backend API to get real system data
- **Parameters**:
  - `method` (string, required): HTTP method (GET, POST, PUT, DELETE, PATCH)
  - `path` (string, required): API endpoint path (e.g., "/items/", "/analytics/completion-rate?lab=lab-99")
  - `body` (string, optional): JSON request body for POST/PUT/PATCH

### Implementation
- Read `AGENT_API_BASE_URL` from environment (default: http://localhost:42002)
- Authenticate with `LMS_API_KEY` from `.env.docker.secret`
- Return JSON with `status_code` and `body`
- Handle connection errors gracefully

## Environment Variables

| Variable | Purpose | Source | Required |
|----------|---------|--------|----------|
| `LLM_API_KEY` | LLM provider auth | `.env.agent.secret` | Yes |
| `LLM_API_BASE` | LLM endpoint | `.env.agent.secret` | Yes |
| `LLM_MODEL` | Model name | `.env.agent.secret` | Yes |
| `LMS_API_KEY` | Backend auth | `.env.docker.secret` | Yes |
| `AGENT_API_BASE_URL` | Backend URL | optional | No (default: localhost:42002) |

## System Prompt Updates
Guide the LLM to choose between:
- `read_file`/`list_files` for wiki and source code
- `query_api` for live data (item counts, status codes, analytics)

## Benchmark Strategy
1. First run to establish baseline
2. Fix one question at a time using `--index`
3. Focus on multi-step questions requiring tool chaining
4. Aim for 10/10 passing

## Initial Diagnosis
First run will likely fail on:
- Questions requiring `query_api` (tool not yet implemented)
- Multi-step debugging (API error + source code)
- Open-ended reasoning questions
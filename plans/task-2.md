# Task 2: The Documentation Agent - Implementation Plan

## Overview
Add tool-calling capabilities to the agent so it can read files and list directories in the project wiki.

## Tool Definitions

### 1. read_file
- **Purpose**: Read contents of a file from the project repository
- **Parameters**: 
  - `path` (string): Relative path from project root
- **Security**: Must prevent directory traversal attacks (no `../`)
- **Returns**: File contents or error message

### 2. list_files
- **Purpose**: List files and directories at a given path
- **Parameters**:
  - `path` (string): Relative directory path from project root
- **Security**: Must prevent directory traversal
- **Returns**: Newline-separated listing of entries

## Agentic Loop Design

1. Send user question + tool definitions to LLM
2. Parse LLM response
3. If tool_calls present:
   - Execute each tool
   - Append results as tool messages
   - Go back to step 1 (max 10 iterations)
4. If no tool_calls (text response):
   - Extract answer and source
   - Output JSON and exit

## System Prompt Strategy

Tell the LLM to:
1. Use `list_files` to discover what's in the wiki directory
2. Use `read_file` to read relevant wiki files
3. Find the answer in the documentation
4. Include the source reference (file path + section anchor)
5. Stop when you have the answer with source

## Security Measures

- Validate paths: reject any containing `..` or starting with `/`
- Use `os.path.abspath` and compare with project root
- Handle file not found errors gracefully

## Implementation Details

### Timeout Handling
- API calls: 120 seconds (for slow CPU models)
- Agent total: 60 seconds (as required)
- Tests: 120 seconds timeout

### Error Handling
- Always output valid JSON even on errors
- Include error message in `answer` field
- Empty `source` and `tool_calls` on errors

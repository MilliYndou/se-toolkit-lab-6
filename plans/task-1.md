# Task 1: Call an LLM from Code - Implementation Plan

## LLM Provider Choice
I will use **Ollama with Qwen models** running on my VM at 10.93.25.203 because:
- ✅ Free and unlimited requests
- ✅ Runs on CPU (no GPU needed)
- ✅ OpenAI-compatible API

## Model
- **Model**: qwen2.5-coder:1.5b (fast CPU-optimized)
- **API Base**: http://10.93.25.203:11434/v1

## Architecture
- **agent.py**: Main CLI that calls Ollama API
- **.env.agent.secret**: Configuration file
- **tests/test_agent.py**: Regression tests

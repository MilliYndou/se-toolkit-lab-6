# Agent CLI Documentation

## Overview
A Python CLI program that connects to an LLM (Large Language Model) and returns structured JSON answers. Built for SE Toolkit Lab 6, Task 1.

## LLM Provider
**Ollama with Qwen models** running on my VM at `10.93.25.203`

- **API Key**: `12345` (though Ollama accepts any value)
- **API Base URL**: `http://10.93.25.203:11434/v1`
- **Model**: `qwen2.5-coder:1.5b`
- **Why this choice**: 
  - Free and unlimited requests (no rate limits)
  - Runs on CPU (no GPU needed)
  - OpenAI-compatible API endpoint
  - Good performance with 15-second response times

## Architecture

### Components
1. **agent.py** - Main CLI program
   - Parses command-line arguments
   - Loads configuration from `.env.agent.secret`
   - Makes HTTP requests to Ollama API
   - Outputs structured JSON to stdout
   - Sends debug info to stderr

2. **.env.agent.secret** - Configuration file
   - Stores API credentials and model settings
   - Not committed to git (kept secret)

3. **Ollama Server** - Runs on VM at 10.93.25.203
   - Hosts the Qwen model
   - Provides OpenAI-compatible API endpoint

## Setup Instructions

### 1. VM Setup (already completed)
```bash
# On VM at 10.93.25.203
curl -fsSL https://ollama.com/install.sh | sh
ollama pull qwen2.5-coder:1.5b
OLLAMA_HOST=0.0.0.0:11434 ollama serve &

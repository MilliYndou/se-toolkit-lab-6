import subprocess
import json
import pytest

def test_agent_basic_call():
    """Test that agent.py returns valid JSON with required fields."""
    result = subprocess.run(
        ["uv", "run", "agent.py", "What is 2+2?"],
        capture_output=True,
        text=True,
        timeout=30
    )
    
    assert result.returncode == 0
    
    try:
        output = json.loads(result.stdout)
    except json.JSONDecodeError:
        pytest.fail("Output is not valid JSON")
    
    assert "answer" in output
    assert "tool_calls" in output
    assert isinstance(output["tool_calls"], list)

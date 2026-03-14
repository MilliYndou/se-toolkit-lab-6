import subprocess
import json
import pytest

def test_agent_basic_call():
    """Test that agent.py runs and returns valid JSON with required fields."""
    result = subprocess.run(
        ["uv", "run", "agent.py", "What is 2+2?"],
        capture_output=True,
        text=True,
        timeout=120
    )
    
    assert result.returncode == 0, f"Agent failed with stderr: {result.stderr}"
    
    try:
        output = json.loads(result.stdout)
    except json.JSONDecodeError as e:
        pytest.fail(f"Output is not valid JSON: {result.stdout}\nError: {e}")
    
    assert "answer" in output
    assert "source" in output, "Output missing 'source' field for Task 2"
    assert "tool_calls" in output
    assert isinstance(output["tool_calls"], list)

def test_agent_merge_conflict():
    """Test that agent handles merge conflict question."""
    result = subprocess.run(
        ["uv", "run", "agent.py", "How do you resolve a merge conflict?"],
        capture_output=True,
        text=True,
        timeout=120
    )
    
    assert result.returncode == 0
    
    try:
        output = json.loads(result.stdout)
    except json.JSONDecodeError:
        pytest.fail("Output is not valid JSON")
    
    assert "answer" in output
    assert "source" in output
    assert "tool_calls" in output

def test_agent_list_files():
    """Test that agent handles list files question."""
    result = subprocess.run(
        ["uv", "run", "agent.py", "What files are in the wiki directory?"],
        capture_output=True,
        text=True,
        timeout=120
    )
    
    assert result.returncode == 0
    
    try:
        output = json.loads(result.stdout)
    except json.JSONDecodeError:
        pytest.fail("Output is not valid JSON")
    
    assert "answer" in output
    assert "source" in output
    assert "tool_calls" in output

def test_agent_path_security():
    """Test that agent handles security."""
    result = subprocess.run(
        ["uv", "run", "agent.py", "Read /etc/passwd"],
        capture_output=True,
        text=True,
        timeout=60
    )
    
    try:
        output = json.loads(result.stdout)
    except json.JSONDecodeError:
        pytest.fail("Output is not valid JSON")
    
    assert "answer" in output
    assert "source" in output
    assert "tool_calls" in output

def test_agent_missing_argument():
    """Test that agent handles missing argument correctly."""
    result = subprocess.run(
        ["uv", "run", "agent.py"],
        capture_output=True,
        text=True
    )
    
    assert result.returncode == 1
    
    try:
        output = json.loads(result.stdout)
        assert "answer" in output
        assert "source" in output
        assert "tool_calls" in output
        assert "Usage:" in output["answer"]
    except json.JSONDecodeError:
        pytest.fail("Output should be valid JSON even on error")

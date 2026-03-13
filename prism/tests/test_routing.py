"""tests/test_routing.py — Unit tests for the Reflexion routing function."""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from core.agents import should_continue_reflexion


def test_pass_high_score():
    """Score >= 85 should always pass regardless of loop count."""
    assert should_continue_reflexion({"critic_score": 87, "loop_count": 1}) == "pass"


def test_retry_low_score():
    """Score < 85 with loops remaining should retry."""
    assert should_continue_reflexion({"critic_score": 62, "loop_count": 1}) == "retry"


def test_pass_max_loops():
    """After 3 loops, accept best result even if score is below threshold."""
    assert should_continue_reflexion({"critic_score": 70, "loop_count": 3}) == "pass"


def test_pass_at_threshold():
    """Exactly 85 should pass."""
    assert should_continue_reflexion({"critic_score": 85, "loop_count": 1}) == "pass"


def test_retry_below_threshold():
    """84 is just below threshold — should retry if loops remain."""
    assert should_continue_reflexion({"critic_score": 84, "loop_count": 2}) == "retry"


def test_pass_at_zero_score_max_loops():
    """Even score=0 passes at max loops."""
    assert should_continue_reflexion({"critic_score": 0, "loop_count": 3}) == "pass"


def test_retry_at_loop_2():
    """Loop 2 with low score still retries (loop < 3)."""
    assert should_continue_reflexion({"critic_score": 60, "loop_count": 2}) == "retry"

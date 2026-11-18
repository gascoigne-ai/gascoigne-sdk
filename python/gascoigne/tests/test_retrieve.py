"""select: numbered lines narrowed by grep or range, capped at 200."""

import re
from pathlib import Path

import pytest
from gascoigne.retrieve import MAX_LINES, select

FIXTURES = Path(__file__).parents[3] / "spec" / "fixtures"

# A real original captured from a gascoigne server.
RAW = (FIXTURES / "raw.txt").read_text()
RAW_LINES = RAW.splitlines()


def test_whole_fixture_is_capped_at_200_numbered_lines():
    assert len(RAW_LINES) == 400
    out = select(RAW).splitlines()
    assert out[:MAX_LINES] == [f"{n}: {row}" for n, row in enumerate(RAW_LINES[:MAX_LINES], 1)]
    assert out[-1] == "... 200 more lines; narrow with grep or lines"
    assert len(out) == MAX_LINES + 1


def test_grep_keeps_original_line_numbers():
    out = select(RAW, grep="job=2 ").splitlines()
    expected = [f"{n}: {row}" for n, row in enumerate(RAW_LINES, 1) if "job=2 " in row]
    assert out == expected[:MAX_LINES]
    assert out[0].startswith("3: ")


def test_grep_no_match_is_empty():
    assert select(RAW, grep="zzz-not-there") == ""


def test_lines_range_and_single_line():
    assert select(RAW, lines="2-3") == "\n".join(f"{n}: {RAW_LINES[n - 1]}" for n in (2, 3))
    assert select(RAW, lines="2") == f"2: {RAW_LINES[1]}"


def test_open_ended_range_forms():
    # "-2" starts at line 1; "2-" ends at the same line (end falls back to start).
    assert select(RAW, lines="-2").splitlines()[0].startswith("1: ")
    assert select(RAW, lines="-2").count("\n") == 1
    assert select(RAW, lines="2-") == f"2: {RAW_LINES[1]}"
    assert select(RAW, lines="-") == select(RAW)


def test_range_beyond_the_text_is_empty():
    assert select(RAW, lines="900-950") == ""


def test_range_then_grep_combine():
    # The range is applied first, then grep filters inside it.
    assert select(RAW, grep="job=2 ", lines="1-3") == f"3: {RAW_LINES[2]}"
    assert select(RAW, grep="job=2 ", lines="1-2") == ""


def test_empty_text_is_empty():
    assert select("") == ""


def test_output_is_capped_with_a_note():
    text = "\n".join(f"row {n}" for n in range(1, 251))
    out = select(text).splitlines()
    assert len(out) == MAX_LINES + 1
    assert out[0] == "1: row 1"
    assert out[MAX_LINES - 1] == "200: row 200"
    assert out[-1] == "... 50 more lines; narrow with grep or lines"


def test_exactly_the_cap_has_no_note():
    text = "\n".join(f"row {n}" for n in range(1, MAX_LINES + 1))
    assert "more lines" not in select(text)


def test_bad_input_raises_today():
    # select does not guard: callers must. Pinned so a change is noticed.
    with pytest.raises(ValueError):
        select(RAW, lines="a-b")
    with pytest.raises(re.error):
        select(RAW, grep="(")

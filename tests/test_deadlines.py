from datetime import date

from agent.deadlines import days_until, parse_date

TODAY = date(2026, 10, 27)


def test_formats():
    assert parse_date("Mon Nov 09 2026") == "2026-11-09"
    assert parse_date("Nov 5, 2026") == "2026-11-05"
    assert parse_date("05/11/2026") == "2026-11-05"   # day-first
    assert parse_date("2026-11-05") == "2026-11-05"


def test_relative():
    assert parse_date("today", TODAY) == "2026-10-27"
    assert parse_date("3 days ago", TODAY) == "2026-10-24"


def test_empty_and_garbage():
    assert parse_date("") is None
    assert parse_date(None) is None
    assert parse_date("not a date at all") is None


def test_days_until():
    assert days_until("2026-11-03", TODAY) == 7
    assert days_until(None, TODAY) is None

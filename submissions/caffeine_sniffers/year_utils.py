"""Cohort-based university study year and branch estimates."""

from __future__ import annotations

import os
import re
from datetime import datetime
from typing import Optional

YEAR_LABELS = {
    1: "First Year",
    2: "Second Year",
    3: "Third Year",
    4: "Fourth Year",
}

BRANCH_MAP = {
    "cse": "CSE",
    "ecm": "ECM",
    "aid": "AI & DS",
    "mech": "Mechanical",
    "eee": "EEE",
    "ece": "ECE",
    "civ": "Civil",
}


def academic_year_start_month() -> int:
    try:
        month = int(os.getenv("ACADEMIC_YEAR_START_MONTH", "7"))
    except ValueError:
        month = 7
    return min(12, max(1, month))


def current_academic_year(
    now: Optional[datetime] = None,
    start_month: Optional[int] = None,
) -> int:
    """
    Academic year labeled by the calendar year it begins in.
    Example: July 2026–June 2027 => academic year 2026.
    """
    now = now or datetime.now()
    start = start_month if start_month is not None else academic_year_start_month()
    if now.month < start:
        return now.year - 1
    return now.year


def parse_cohort_and_branch(email: str) -> tuple[Optional[int], Optional[str], Optional[str]]:
    """
    Extract joining cohort and branch from email like se25ucse100@sdheeraj.is-cool.dev.
    Returns (cohort_year, branch_code, branch_name).
    """
    if not email or "@" not in email:
        return None, None, None
    local = email.split("@", 1)[0]
    match = re.search(r"(?i)\bSE(\d{2})(?:u([a-z]+))?(\d+)?", local)
    if not match:
        match = re.search(r"(?i)SE(\d{2})", local)
        if not match:
            return None, None, None
        two = int(match.group(1))
        branch_code = None
    else:
        two = int(match.group(1))
        branch_code = match.group(2).lower() if match.group(2) else None

    century_base = (datetime.now().year // 100) * 100
    year = century_base + two
    if year > datetime.now().year + 10:
        year -= 100
    if year < 1990 or year > datetime.now().year + 1:
        return None, None, None

    branch_name = BRANCH_MAP.get(branch_code, branch_code.upper() if branch_code else None)
    return year, branch_code, branch_name


def parse_cohort_year(email: str) -> Optional[int]:
    year, _, _ = parse_cohort_and_branch(email)
    return year


def study_year_number(
    cohort_year: Optional[int],
    *,
    now: Optional[datetime] = None,
    start_month: Optional[int] = None,
    max_years: int = 4,
) -> Optional[int]:
    if cohort_year is None:
        return None
    ay = current_academic_year(now=now, start_month=start_month)
    year = ay - int(cohort_year) + 1
    if year < 1 or year > max_years:
        return None
    return year


def study_year_label(
    cohort_year: Optional[int],
    *,
    now: Optional[datetime] = None,
    start_month: Optional[int] = None,
    max_years: int = 4,
) -> Optional[str]:
    num = study_year_number(
        cohort_year, now=now, start_month=start_month, max_years=max_years
    )
    if num is None:
        return None
    return YEAR_LABELS.get(num)


def study_year_from_email(email: str, **kwargs) -> dict:
    cohort, branch_code, branch_name = parse_cohort_and_branch(email)
    label = study_year_label(cohort, **kwargs)
    number = study_year_number(cohort, **kwargs)
    badge = label
    if label and branch_name:
        badge = f"{label} · {branch_name}"
    return {
        "cohort_year": cohort,
        "branch_code": branch_code,
        "branch_name": branch_name,
        "study_year": number,
        "study_year_label": label,
        "badge_label": badge or label,
        "recognized": cohort is not None,
    }

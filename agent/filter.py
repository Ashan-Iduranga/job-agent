"""Cheap keyword filter: keep internship / trainee / entry-level IT roles."""
from __future__ import annotations

import re

from .models import Job

LEVEL_KEEP = re.compile(
    r"\b(intern(ship)?s?|trainee|graduate|undergraduate|entry[\s-]?level|junior|fresher|apprentice|placement)\b",
    re.I,
)
LEVEL_DROP = re.compile(
    r"\b(senior|snr|sr\.?|mid[\s-]?level|lead|principal|manager|head|director|architect|consultant|specialist|chief|vp)\b",
    re.I,
)
EXPERIENCE_DROP = re.compile(r"\b([2-9]|1\d)\s*\+?\s*(-\s*\d+\s*)?(years?|yrs?)\b", re.I)
IT_KEEP = re.compile(
    r"\b(software|developer|development|engineer(ing)?|programm(er|ing)|qa|quality assurance|test(er|ing)?|"
    r"automation|full[\s-]?stack|front[\s-]?end|back[\s-]?end|web|mobile|android|ios|flutter|react|java|python|"
    r"\.net|php|node|devops|cloud|data|database|ui|ux|computer|tech(nical|nology)?|systems?|network|cyber)\b",
    re.I,
)
IT_ACRONYM = re.compile(r"\b(IT|ICT|SE)\b")  # case-sensitive: avoid matching the word "it"
NON_IT_DROP = re.compile(
    r"\b(accounts?|accounting|finance|sales|marketing|hr|human resources?|legal|audit|tax|nurs(e|ing)|"
    r"driver|chef|cook|teacher|tutor|graphic designer|photographer|merchandis(er|ing)|banking|insurance|"
    r"civil|mechanical|electrical|quantity surveyor|hospitality|business development|management trainee)\b",
    re.I,
)


def is_relevant(job: Job) -> bool:
    """True if the job looks like an entry-level IT role for an intern."""
    title = job.title
    text = f"{job.title} {job.description}"
    if not LEVEL_KEEP.search(title):
        return False
    if LEVEL_DROP.search(title):
        return False
    if EXPERIENCE_DROP.search(job.description) and not LEVEL_KEEP.search(job.description):
        return False
    if NON_IT_DROP.search(title) and not _is_it(_strip_non_it(title)):
        return False
    # Generic titles like "Intern" or "Trainee" from IT-only sources are fine;
    # otherwise require an IT keyword somewhere.
    return _is_it(_strip_non_it(text)) or bool(job.extra.get("it_category"))


def _is_it(text: str) -> bool:
    return bool(IT_KEEP.search(text) or IT_ACRONYM.search(text))


def _strip_non_it(title: str) -> str:
    return NON_IT_DROP.sub(" ", title)


def filter_jobs(jobs: list[Job]) -> list[Job]:
    """Keep only relevant jobs."""
    return [j for j in jobs if is_relevant(j)]

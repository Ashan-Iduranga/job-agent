from datetime import date

from agent import db
from agent.models import Job


def make(title="Software Intern", company="Acme", url="https://a/1", **kw) -> Job:
    return Job(title=title, company=company, url=url, source="t", **kw)


def test_only_new_jobs_inserted(tmp_path):
    with db.connect(tmp_path / "t.db") as conn:
        first = db.insert_new(conn, [make(), make(title="QA Intern", url="https://a/2")])
        assert len(first) == 2
        again = db.insert_new(conn, [make(), make(title="QA Intern", url="https://a/2")])
        assert again == []


def test_same_job_different_url_is_duplicate(tmp_path):
    with db.connect(tmp_path / "t.db") as conn:
        db.insert_new(conn, [make()])
        # same title+company (case/punctuation differences) on another site
        dup = db.insert_new(conn, [make(title="software  intern!", company="ACME", url="https://b/9")])
        assert dup == []


def test_same_title_other_company_is_new(tmp_path):
    with db.connect(tmp_path / "t.db") as conn:
        db.insert_new(conn, [make()])
        assert len(db.insert_new(conn, [make(company="Other", url="https://c/1")])) == 1


def test_expire_past_deadline(tmp_path):
    with db.connect(tmp_path / "t.db") as conn:
        db.insert_new(conn, [make(deadline="2026-10-01"), make(title="B", url="https://a/b", deadline="2026-12-01")])
        assert db.expire_old(conn, today=date(2026, 10, 27)) == 1

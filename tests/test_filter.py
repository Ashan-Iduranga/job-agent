from agent.filter import filter_jobs, is_relevant
from agent.models import Job


def job(title: str, desc: str = "", **extra) -> Job:
    return Job(title=title, company="Acme", url=f"https://x/{title}", source="t", description=desc, extra=extra)


def test_keeps_it_internships():
    for t in ["Software Engineer Intern", "Intern - IT", "Trainee QA Engineer",
              "Full Stack Developer Intern", "Graduate Trainee - Software", "Junior Software Developer",
              "Trainee Mobile Developer - React Native"]:
        assert is_relevant(job(t)), t


def test_drops_senior_and_mid():
    for t in ["Senior Software Engineer", "Lead QA Engineer", "Software Engineer",
              "Associate Tech Lead", "Manager - Technology Transformation and AI"]:
        assert not is_relevant(job(t)), t


def test_drops_experience_requirement():
    assert not is_relevant(job("Junior Developer", "Minimum 3+ years of experience in Java"))
    assert is_relevant(job("Software Intern", "Internship for undergraduates, 6 months"))


def test_drops_non_it():
    for t in ["Accounting Intern", "Marketing Trainee", "Intern - HR", "Graphic Designer Intern"]:
        assert not is_relevant(job(t)), t


def test_business_development_is_not_software_development():
    assert not is_relevant(job("Business Development & Digital Marketing intern", it_category=True))
    assert not is_relevant(job("Management Trainee- Nikaweratiya", "Kurunegala, Business Development"))
    assert is_relevant(job("Software Development Intern"))


def test_word_it_is_not_an_it_keyword():
    # lower-case "it" in a description must not make a generic trainee role look IT
    assert not is_relevant(job("Trainee", "you will love it here"))
    assert is_relevant(job("Trainee", "you will love it here", it_category=True))


def test_filter_jobs_list():
    jobs = [job("Software Intern"), job("Senior Developer"), job("Sales Trainee")]
    assert [j.title for j in filter_jobs(jobs)] == ["Software Intern"]

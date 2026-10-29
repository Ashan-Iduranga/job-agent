You are ranking internship vacancies for one candidate.

1. Read `profile.md` (the candidate) and `data/new_jobs.json` (a JSON list of jobs, each with an `id`).
2. For EVERY job, judge how well it fits the candidate:
   - 80–100: an IT internship/trainee role that clearly matches the candidate's roles and several skills, in a suitable location (one of the candidate's preferred locations, remote or hybrid).
   - 50–79: relevant IT internship/trainee role with a partial match (fewer skills, unclear stack, farther location).
   - 20–49: weak match (adjacent field such as business analysis, data entry, telecom/RF, or a far location).
   - 0–19: not suitable (non-IT, senior, or needs 2+ years of experience).
   Only use information in the job data. If the description is empty, judge from the title and company and say so briefly.
3. Write `data/ranked.json`: a JSON list with one object per job, exactly this shape:
   `{"id": <id>, "score": <0-100 integer>, "reason": "<one short line, max 20 words>", "matched_skills": ["<skills from the profile that the job matches>"]}`
4. Write only valid JSON to that file (no comments, no markdown). Do not edit any other file. Reply with just "done".

# Job Fair Tracker

Companies -> JDs -> Green / Yellow / Red candidates, each name linked to the CV.

## Deploy on Vercel
1. Put this folder in a **private** GitHub repo (data/data.json contains candidate contact details), or deploy from the folder with `npx vercel`.
2. In Vercel: Project -> Settings -> Environment Variables, add `SITE_PASSWORD` = a password you share with the team. Redeploy.
   - To make the site open to everyone instead, set `PUBLIC_ACCESS` = `true` (not recommended: it exposes phone numbers and emails).
3. Framework preset: **Other**. No build command needed.

## Refresh the candidates
Edit the file paths at the top of `scripts/ingest.py`, run `python3 scripts/ingest.py` (needs pandas + openpyxl), then redeploy.
The script maps each response to a JD, de-duplicates (same person + same JD keeps the latest), scores 0-100 and writes `data/data.json`.

## How the score works (max 100)
Role/keyword fit 35, experience vs JD 25, location 15, notice period 10, form completeness 15.
Green >= 66, Yellow >= 52, Red below (`GREEN, YELLOW` in ingest.py). It only reads form answers; CVs and JD files are not read.
Disability details, DOB, gender and address are not shown on the site and not used in scoring.

## Notes
- Moves/removals are saved in each viewer's own browser only. They are not shared between people.
- CV links open Google Drive files; viewers need Drive access to those files.

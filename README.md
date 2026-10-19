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

## Excel sheets
On every JD page: **Open as sheet** shows a table; **Download .xlsx** saves it. Columns: Timestamp, Job Role, Name, Mail id, Contact No, Current Organization, Relevant experience in years, Relevant Skillset, Disability Type, Disability%, Current location, Preferred Relocation, Current ctc, Expected ctc, Notice Period, Full Address, Upload cv, Column 1.
Rows are coloured green/yellow/red; Column 1 holds the zone, score, team remark and reason. Downloads contain disability and address details, so share them carefully.

## Talent pool candidates
Candidates from the Naukri, Shortlist and Purchase Executive files have no applied JD. Each is matched to up to 5 JDs where keywords overlap and the score is at least Yellow. Those with no fit sit under *Other roles > Talent pool*.

## Notes
- Moves/removals are saved in each viewer's own browser only. They are not shared between people.
- CV links open Google Drive files; viewers need Drive access to those files.

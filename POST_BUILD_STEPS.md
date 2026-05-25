# Post-Build Manual Steps (Phases 5-7)

This file describes the steps **you (Samer) must run manually** to finish the public release. The repo content is built and reviewed — everything below is browser/GitHub/Zenodo/Render plus two short text edits to the cover letter and manuscript.

Estimated total time: ~30 minutes (most of it is waiting for Zenodo to mint the DOI).

---

## Phase 5 — Git, GitHub, Zenodo, Release

### 5.1 Local git init + first commit

```bash
cd "/Users/samersalman/Desktop/01 - STATA/TRAUMA/FORD/ntdb_validation/[public-repo]-ford-ii"
git init
git add .
git status                              # eyeball — confirm no .parquet, no patient CSVs, no .DS_Store
git commit -m "v0.1.0: initial public release"
git branch -M main
```

### 5.2 Create the empty GitHub repo

In your browser, sign in to GitHub as `samersalman` and create a new repo:

- **Name**: `ford-ii`
- **Description**: "FORD-II: external validation and refinement of the FORD score on NTDB 2019-2024. Analysis code, aggregated tables, and Flask calculator for the JAMA Surgery manuscript."
- **Public**
- **Do NOT** initialize with README, .gitignore, or LICENSE (the local repo already has them)

### 5.3 Push

```bash
git remote add origin https://github.com/samersalman/ford-ii.git
git push -u origin main
```

### 5.4 Enable Zenodo integration (one-time)

In your browser:
1. Go to <https://zenodo.org/account/settings/github/>
2. Sign in via GitHub OAuth
3. Find `samersalman/ford-ii` in the repo list and flip the toggle to **ON**

(This tells Zenodo to archive every future GitHub Release as a Zenodo deposit.)

### 5.5 Create the v0.1.0 GitHub Release

In your browser, on the repo page:
1. **Releases** → **Draft a new release**
2. **Tag**: `v0.1.0` (create on push)
3. **Title**: `v0.1.0 — Initial public release`
4. **Description**:
   ```
   Initial public release accompanying the JAMA Surgery submission.
   
   Contents:
   - Analysis code (ford_ii_refit pipeline + manuscript-builder pipeline)
   - Aggregated tables and figures reported in the manuscript
   - Flask web calculator implementing the locked 16-predictor score
   - Completed STROBE, TRIPOD, and CHEERS reporting checklists
   ```
5. **Publish release**

### 5.6 Wait ~2 minutes, then collect DOIs from Zenodo

1. Refresh <https://zenodo.org/account/settings/github/> — the repo should show a new deposit with a green DOI badge.
2. Click into the deposit. Copy two DOIs:
   - **Concept DOI** (all versions): `10.5281/zenodo.XXXXXXX` — listed as "Cite all versions?" at top of right sidebar
   - **Version DOI** (v0.1.0 specifically): `10.5281/zenodo.YYYYYYY` — listed under the version

### 5.7 Patch DOIs into repo files and tag v0.1.1

Replace placeholders in three files. Two files use the version DOI (`YYYYYYY`), one mixes both:

- `CITATION.cff` — replace both `XXXXXXX` (concept) and `YYYYYYY` (version) lines
- `README.md` — replace `XXXXXXX` in the badge URL (concept DOI for badge that always resolves to latest)
- `calculator/templates/index.html` — replace `XXXXXXX` in the provenance footer (concept DOI)

```bash
cd "/Users/samersalman/Desktop/01 - STATA/TRAUMA/FORD/ntdb_validation/[public-repo]-ford-ii"
# Manual: open the three files in your editor, search/replace XXXXXXX and YYYYYYY with your actual DOI numbers
git add CITATION.cff README.md calculator/templates/index.html
git commit -m "v0.1.1: patch Zenodo DOIs into citation, badge, and calculator footer"
git tag v0.1.1
git push && git push --tags
```

(The `v0.1.1` Zenodo deposit will get its own version DOI but the concept DOI stays the same — that's what makes the badge stable.)

---

## Phase 6 — Deploy calculator to Render

~5 minutes. Free tier is fine.

1. Browser: <https://dashboard.render.com> → sign in (use GitHub OAuth if you don't already have an account)
2. **New** → **Web Service**
3. **Connect a repository** → grant access to `samersalman/ford-ii` if prompted → select it
4. Settings to confirm (most auto-detected from `render.yaml`):
   - **Name**: `ford-ii-calculator`
   - **Region**: pick one near you (default Oregon is fine)
   - **Branch**: `main`
   - **Root Directory**: `calculator`
   - **Runtime**: Python 3
   - **Build Command**: `pip install -r requirements.txt`
   - **Start Command**: `gunicorn app:app`
   - **Plan**: Free
5. **Create Web Service**

Wait ~3-5 min for first deploy. The URL will appear as `ford-ii-calculator.onrender.com` (or similar suffix if name was taken).

**If your URL differs from `ford-ii-calculator.onrender.com`**, update the URL in these files:
- `README.md` — calculator badge link
- `CITATION.cff` — `url:` field
- `calculator/templates/index.html` — provenance footer
- And in the cover-letter / manuscript paragraph from Phase 7 below

Commit and push (no new tag needed; Render auto-deploys on push).

---

## Phase 7 — Update cover letter and manuscript

Two text edits. Both use the same paragraph (paste verbatim, swap in your real DOI).

### Verbatim text — Data and Code Availability paragraph

> *"Transparency and reproducibility were central aims of this project. All analysis code is publicly available at https://github.com/samersalman/ford-ii and archived on Zenodo (DOI: 10.5281/zenodo.XXXXXXX). An interactive web implementation of the FORD-II score is hosted at https://ford-ii-calculator.onrender.com. Aggregated, de-identified tables and figures sufficient to verify the manuscript's reported numbers are included in the repository under an MIT license. Patient-level NTDB data are not redistributed and must be obtained directly from the American College of Surgeons (https://www.facs.org/quality-programs/trauma/quality/national-trauma-data-bank/)."*

Replace `XXXXXXX` with your concept DOI (use the always-resolves-to-latest one, not the version-specific YYYYYYY).

### 7.1 Manuscript

File: `ntdb_validation/[current] v12-FORD-II-manuscript.docx`

Find the **Data and Code Availability** subsection in Methods. (If one doesn't exist yet, add it as the last paragraph of Methods, right before the section break to Results.) Paste the paragraph verbatim.

### 7.2 Cover letter

The current draft cover letter is generated by `analysis/manuscript/08_build_cover_letter.py`. Either:
- (A) Open the generated `.docx` in Word and append the paragraph to the transparency section (recommended — quicker), or
- (B) Edit `08_build_cover_letter.py` to add the paragraph, then re-run it.

---

## Verification checklist (Phase 5-7 done)

- [ ] `https://github.com/samersalman/ford-ii` resolves to the public repo
- [ ] `https://doi.org/10.5281/zenodo.<your-concept-DOI>` resolves to the Zenodo deposit
- [ ] `https://ford-ii-calculator.onrender.com` (or your actual URL) renders the form
- [ ] Calculator scores a known case correctly (e.g., 80yo with hip fracture from fall, EMS transport → score 8, "High" risk, ~80% probability)
- [ ] DOI placeholders (`XXXXXXX`, `YYYYYYY`) are zero in `README.md`, `CITATION.cff`, `calculator/templates/index.html`
  - Verify: `grep -rn 'XXXXXXX\|YYYYYYY' . 2>/dev/null | grep -v '.git'` returns empty
- [ ] Manuscript Methods section contains the verbatim Data and Code Availability paragraph
- [ ] Cover letter contains the same paragraph (or a one-sentence variant referencing the URLs and DOI)

---

## If something goes wrong

- **Zenodo doesn't mint a DOI**: Check that the Zenodo-GitHub toggle is ON *before* you publish the Release. If you flipped it on after, delete the Release and re-create.
- **Render build fails on `gunicorn`**: Confirm `calculator/requirements.txt` lists `gunicorn`. If it does, check the build log for missing system libs — Flask/gunicorn alone have no native deps so this would be unusual.
- **Calculator returns 500 on POST**: Check Render logs. Most likely cause is a missing `tables/` file — `calculator/config.py` reads three CSVs from `../tables/` at startup. If you reorganized the repo, that relative path breaks.
- **Manuscript section ordering**: JAMA Surgery accepts either Methods-end or a separate "Data Sharing" statement after Acknowledgments. Either placement is fine; the Methods-end placement is more reproducibility-forward and matches the lumbar paper precedent.

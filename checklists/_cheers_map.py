"""
CHEERS-2022 item -> manuscript-location mapping for FORD-II v12 manuscript.

Date: 2026-05-16
Source manuscript: ntdb_validation/v12/[current] v12-FORD-II-manuscript.docx
Page map:          ntdb_validation/v12/checklists/completed/_v12_page_map.json
Template:          ntdb_validation/v12/checklists/CHEERS-2022-checklist.docx

Total CHEERS-2022 items mapped: 28 (items 1-28).
  Mapped: 24
  N/A:     4 (items 4, 19, 21, 25)

Notes:
- Items 27 (funding) and 28 (conflicts of interest) are flagged: the v12 draft
  does not include funding or disclosure sections. They are marked Mapped
  with a placeholder section_ref of "Title page" so the builder can flag the
  absence; the manuscript edit needed is noted in NOTES_FOR_BUILDER.
"""

CHEERS_MAP = {
    "1": {
        "item": "1",
        "topic": "Title",
        "section_ref": "Title page",
        "page": 1,
        "quote": "Fracture Orthopedic Risk of Non-Home Discharge II (FORD-II): National Registry Derivation, Internal Validation, and Cost-Effectiveness of a Fracture Trauma Discharge-Disposition Score",
        "na_reason": None,
    },
    "2": {
        "item": "2",
        "topic": "Abstract",
        "section_ref": "Abstract — Background",
        "page": 2,
        "quote": "We developed and evaluated Fracture Orthopedic Risk of Non-Home Discharge II (FORD-II), a nationally fit integer score for predicting non-home discharge after adult fracture-related trauma.",
        "na_reason": None,
    },
    "3": {
        "item": "3",
        "topic": "Background and objectives",
        "section_ref": "Introduction",
        "page": 4,
        "quote": "An admission-time tool that identifies fracture patients at high risk for non-home discharge could allow case management and placement teams to intervene earlier.",
        "na_reason": None,
    },
    "4": {
        "item": "4",
        "topic": "Health economic analysis plan",
        "section_ref": None,
        "page": None,
        "quote": None,
        "na_reason": "No prospectively registered Health Economic Analysis Plan; analytic plan was prespecified within the manuscript but not registered or publicly archived",
    },
    "5": {
        "item": "5",
        "topic": "Study population",
        "section_ref": "Methods — Cohort and outcome",
        "page": 5,
        "quote": "Eligible adults (≥18 years) had primary ICD-10 fracture diagnoses and classifiable discharge dispositions.",
        "na_reason": None,
    },
    "6": {
        "item": "6",
        "topic": "Setting and location",
        "section_ref": "Methods — Cohort and outcome",
        "page": 5,
        "quote": "We performed a retrospective development and held-out validation study using the NTDB years 2019–2024.",
        "na_reason": None,
    },
    "7": {
        "item": "7",
        "topic": "Comparators",
        "section_ref": "Methods — Cost-effectiveness model",
        "page": 8,
        "quote": "A two-arm decision-analytic model compared FORD-II-guided early discharge planning with usual care.",
        "na_reason": None,
    },
    "8": {
        "item": "8",
        "topic": "Perspective",
        "section_ref": "Methods — Cost-effectiveness model",
        "page": 8,
        "quote": "We prespecified the decision context, comparator, analytic perspective (hospital), time horizon (indexed at hospital admission), model structure, input parameters, and analytic assumptions.",
        "na_reason": None,
    },
    "9": {
        "item": "9",
        "topic": "Time horizon",
        "section_ref": "Methods — Cost-effectiveness model",
        "page": 8,
        "quote": "The discount rate was fixed at 0 because the analytic horizon was limited to the index admission and 30-day post-discharge period.",
        "na_reason": None,
    },
    "10": {
        "item": "10",
        "topic": "Discount rate",
        "section_ref": "Methods — Cost-effectiveness model",
        "page": 8,
        "quote": "A fixed discount rate of 0 because the analytic horizon was limited to the index admission and 30-day post-discharge period.",
        "na_reason": None,
    },
    "11": {
        "item": "11",
        "topic": "Selection of outcomes",
        "section_ref": "Methods — Cohort and outcome",
        "page": 5,
        "quote": "The primary outcome was non-home discharge, defined as discharge to rehabilitation, SNF, LTACH, or intermediate care facility.",
        "na_reason": None,
    },
    "12": {
        "item": "12",
        "topic": "Measurement of outcomes",
        "section_ref": "Methods — Cost-effectiveness model",
        "page": 8,
        "quote": "In the intervention arm, patients in the highest FORD-II risk group were flagged for structured early discharge planning.",
        "na_reason": None,
    },
    "13": {
        "item": "13",
        "topic": "Valuation of outcomes",
        "section_ref": "Methods — Cost-effectiveness model",
        "page": 8,
        "quote": "The base-case marginal inpatient per-day cost was derived from Coaston et al. 2025 using their published 2021-USD multivariable estimate for injured patients.",
        "na_reason": None,
    },
    "14": {
        "item": "14",
        "topic": "Measurement and valuation of resources and costs",
        "section_ref": "Methods — Cost-effectiveness model",
        "page": 8,
        "quote": "Costs were converted to 2024 USD using the BLS CPI-Medical Care index.",
        "na_reason": None,
    },
    "15": {
        "item": "15",
        "topic": "Currency, price date, and conversion",
        "section_ref": "Methods — Cost-effectiveness model",
        "page": 8,
        "quote": "Costs were converted to 2024 USD using the BLS CPI-Medical Care index.",
        "na_reason": None,
    },
    "16": {
        "item": "16",
        "topic": "Rationale and description of model",
        "section_ref": "Methods — Cost-effectiveness model",
        "page": 8,
        "quote": "A two-arm decision-analytic model compared FORD-II-guided early discharge planning with usual care.",
        "na_reason": None,
    },
    "17": {
        "item": "17",
        "topic": "Analytics and assumptions",
        "section_ref": "Methods — Cost-effectiveness model",
        "page": 8,
        "quote": "Probabilistic sensitivity analysis used Briggs et al. distributional conventions: 10,000 Monte Carlo iterations with gamma distributions for nonnegative costs, beta distributions for probabilities.",
        "na_reason": None,
    },
    "18": {
        "item": "18",
        "topic": "Characterizing heterogeneity",
        "section_ref": "Methods — Subgroup and sensitivity analyses",
        "page": 7,
        "quote": "Prespecified subgroup analyses compared FORD-II, GTOS-II, and TRIAGES discrimination by age, sex, fracture location, mechanism of injury, calendar period, and trauma-center designation.",
        "na_reason": None,
    },
    "19": {
        "item": "19",
        "topic": "Characterizing distributional effects",
        "section_ref": None,
        "page": None,
        "quote": None,
        "na_reason": "No distributional or equity-weighted cost analysis performed; hospital-perspective model did not allocate impacts across priority populations",
    },
    "20": {
        "item": "20",
        "topic": "Characterizing uncertainty",
        "section_ref": "Methods — Cost-effectiveness model",
        "page": 8,
        "quote": "A prespecified one-way deterministic sensitivity analysis varied each parameter independently across plausible ranges to identify dominant drivers.",
        "na_reason": None,
    },
    "21": {
        "item": "21",
        "topic": "Approach to engagement with patients and others affected by the study",
        "section_ref": None,
        "page": None,
        "quote": None,
        "na_reason": "No patient, public, community, or stakeholder engagement performed; retrospective NTDB registry analysis without prospective engagement component",
    },
    "22": {
        "item": "22",
        "topic": "Study parameters",
        "section_ref": "Results — Cost analysis",
        "page": 11,
        "quote": "The base-case marginal inpatient cost was $2,343.08 per day after inflating the Coaston et al. 2021-USD injured-patient estimate of $2,187.75 to 2024 USD.",
        "na_reason": None,
    },
    "23": {
        "item": "23",
        "topic": "Summary of main results",
        "section_ref": "Results — Cost analysis",
        "page": 11,
        "quote": "The FORD-II flagging strategy generated estimated per-patient net savings of $362.25 compared with usual care.",
        "na_reason": None,
    },
    "24": {
        "item": "24",
        "topic": "Effect of uncertainty",
        "section_ref": "Results — One-way sensitivity analyses",
        "page": 12,
        "quote": "The tornado analysis was driven primarily by the assumed length-of-stay reduction, which produced a swing magnitude of $745, followed by the inpatient per-day cost assumption.",
        "na_reason": None,
    },
    "25": {
        "item": "25",
        "topic": "Effect of engagement with patients and others affected by the study",
        "section_ref": None,
        "page": None,
        "quote": None,
        "na_reason": "No patient or stakeholder engagement was performed; therefore no engagement effect on approach or findings to report",
    },
    "26": {
        "item": "26",
        "topic": "Study findings, limitations, generalizability, and current knowledge",
        "section_ref": "Discussion",
        "page": 14,
        "quote": "The economic model similarly estimates a plausible value pathway but does not establish that FORD-II-guided discharge planning reduces length of stay or costs.",
        "na_reason": None,
    },
    "27": {
        "item": "27",
        "topic": "Source of funding",
        "section_ref": None,
        "page": None,
        "quote": None,
        "na_reason": "no funding section in v12 draft — added at submission",
    },
    "28": {
        "item": "28",
        "topic": "Conflicts of interest",
        "section_ref": None,
        "page": None,
        "quote": None,
        "na_reason": "no COI section in v12 draft — added at submission",
    },
}

NOTES_FOR_BUILDER = """
Manuscript edits flagged during CHEERS mapping (please surface these to the user):

1. Item 4 (Health economic analysis plan): v12 has no explicit statement that a
   HEAP was developed or registered. CHEERS-2022 recommends stating whether a
   HEAP exists and where it can be accessed. Consider adding a one-sentence
   HEAP statement to Methods - Cost-effectiveness model (page 8), e.g.:
   "A prespecified health economic analysis plan was developed prior to
   analysis and is available from the corresponding author on request."

2. Items 27/28 (Funding and Conflicts of interest): v12 contains NO funding
   acknowledgement and NO conflicts-of-interest disclosure section. The page
   map confirms no such section exists in the current draft. These are
   marked Mapped-with-placeholder so the builder will produce the row, but
   real text must be added before journal submission. Suggest inserting a
   "Funding" and "Disclosures" block at the end of the Conclusions section
   (before References, page 15-16).

3. Item 21/25 (Patient/stakeholder engagement): genuinely N/A for a
   retrospective NTDB analysis; no edit needed but the journal cover letter
   should explicitly note the absence of engagement.

4. Item 12 is treated as a single composite (the template numbers it 12 with
   no a/b/c sub-letters in the CHEERS-2022 checklist docx). If a journal
   requires CHEERS 12a/12b/12c split, the build script should duplicate
   the row.

5. Some Methods quotes for items 7-17 cluster in the same paragraph
   (Methods - Cost-effectiveness model, page 8). The build script may want
   to flag this for the human reviewer as 'cluster citation - consider
   distinct cross-references in each row'.
"""

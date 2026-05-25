"""
STROBE v4-combined (PLOS Medicine) checklist mapping for FORD-II v12 manuscript.

Generated: 2026-05-16
Manuscript: /Users/samersalman/Desktop/01 - STATA/TRAUMA/FORD/ntdb_validation/v12/[current] v12-FORD-II-manuscript.docx
Page map:   /Users/samersalman/Desktop/01 - STATA/TRAUMA/FORD/ntdb_validation/v12/checklists/completed/_v12_page_map.json
Template:   /Users/samersalman/Desktop/01 - STATA/TRAUMA/FORD/ntdb_validation/v12/checklists/STROBE-checklist-v4-combined-PlosMedicine.docx

Total rows: 31 (cohort-study branch)

Branch: cohort-study (single column; the template combines cohort/case-control/
cross-sectional variants in one cell separated by " | " — write only the cohort
variant text into each row).

The exported STROBE_MAP is a dict keyed by canonical STROBE item id as a string.
Each value follows this schema:

    {
        "item": "1a",
        "topic": "Title and abstract",
        "recommendation": "Indicate the study's design with a commonly used term in the title or the abstract.",
        "section_ref": "Title page",
        "page": 1,
        "quote": "...",         # verbatim from the manuscript, <= 25 words
        "na_reason": None,
    }

For N/A items: section_ref=None, page=None, quote=None, na_reason="<reason>".
"""

STROBE_MAP = {
    "1a": {
        "item": "1a",
        "topic": "Title and abstract",
        "recommendation": "Indicate the study's design with a commonly used term in the title or the abstract.",
        "section_ref": "Title page",
        "page": 1,
        "quote": (
            "Fracture Orthopedic Risk of Non-Home Discharge II (FORD-II): "
            "National Registry Derivation, Internal Validation, and "
            "Cost-Effectiveness of a Fracture Trauma Discharge-Disposition Score"
        ),
        "na_reason": None,
    },
    "1b": {
        "item": "1b",
        "topic": "Title and abstract",
        "recommendation": (
            "Provide in the abstract an informative and balanced summary of "
            "what was done and what was found."
        ),
        "section_ref": "Abstract",
        "page": 2,
        "quote": (
            "We developed and evaluated Fracture Orthopedic Risk of Non-Home "
            "Discharge II (FORD-II), a nationally fit integer score for "
            "predicting non-home discharge."
        ),
        "na_reason": None,
    },
    "2": {
        "item": "2",
        "topic": "Background/rationale",
        "recommendation": (
            "Explain the scientific background and rationale for the "
            "investigation being reported."
        ),
        "section_ref": "Introduction",
        "page": 4,
        "quote": (
            "Adult traumatic fractures place substantial demand on the United "
            "States post-acute care system."
        ),
        "na_reason": None,
    },
    "3": {
        "item": "3",
        "topic": "Objectives",
        "recommendation": "State specific objectives, including any prespecified hypotheses.",
        "section_ref": "Introduction",
        "page": 4,
        "quote": (
            "We developed and evaluated Fracture Orthopedic Risk of Non-Home "
            "Discharge II (FORD-II), a nationally fit integer score for "
            "predicting non-home discharge."
        ),
        "na_reason": None,
    },
    "4": {
        "item": "4",
        "topic": "Study design",
        "recommendation": "Present key elements of study design early in the paper.",
        "section_ref": "Methods — Cohort and outcome",
        "page": 5,
        "quote": (
            "We performed a retrospective development and held-out validation "
            "study using the NTDB years 2019–2024."
        ),
        "na_reason": None,
    },
    "5": {
        "item": "5",
        "topic": "Setting",
        "recommendation": (
            "Describe the setting, locations, and relevant dates, including "
            "periods of recruitment, exposure, follow-up, and data collection."
        ),
        "section_ref": "Methods — Cohort and outcome",
        "page": 5,
        "quote": (
            "Adults with primary fracture diagnoses and classifiable discharge "
            "dispositions were identified from the National Trauma Data Bank "
            "from 2019 to 2024."
        ),
        "na_reason": None,
    },
    "6a": {
        "item": "6a",
        "topic": "Participants",
        "recommendation": (
            "Cohort study—Give the eligibility criteria, and the sources "
            "and methods of selection of participants. Describe methods of "
            "follow-up."
        ),
        "section_ref": "Methods — Cohort and outcome",
        "page": 5,
        "quote": (
            "Eligible adults (≥18 years) had primary ICD-10 fracture "
            "diagnoses and classifiable discharge dispositions. We excluded "
            "in-hospital deaths and discharges to hospice, jail."
        ),
        "na_reason": None,
    },
    "6b": {
        "item": "6b",
        "topic": "Participants",
        "recommendation": (
            "Cohort study—For matched studies, give matching criteria "
            "and number of exposed and unexposed."
        ),
        "section_ref": None,
        "page": None,
        "quote": None,
        "na_reason": "Not a matched cohort design.",
    },
    "7": {
        "item": "7",
        "topic": "Variables",
        "recommendation": (
            "Clearly define all outcomes, exposures, predictors, potential "
            "confounders, and effect modifiers. Give diagnostic criteria, "
            "if applicable."
        ),
        "section_ref": "Methods — Predictors, score development, and comparators",
        "page": 6,
        "quote": (
            "FORD-II was developed from 41 prespecified binary predictors "
            "available at trauma admission, including demographics, vital "
            "signs, BMI, fracture location, injury mechanism."
        ),
        "na_reason": None,
    },
    "8": {
        "item": "8",
        "topic": "Data sources/measurement",
        "recommendation": (
            "For each variable of interest, give sources of data and details "
            "of methods of assessment (measurement). Describe comparability "
            "of assessment methods if there is more than one group."
        ),
        "section_ref": "Methods — Cohort and outcome",
        "page": 5,
        "quote": (
            "Adults with primary fracture diagnoses and classifiable discharge "
            "dispositions were identified from the National Trauma Data Bank "
            "from 2019 to 2024."
        ),
        "na_reason": None,
    },
    "9": {
        "item": "9",
        "topic": "Bias",
        "recommendation": "Describe any efforts to address potential sources of bias.",
        "section_ref": "Methods — Subgroup and sensitivity analyses",
        "page": 7,
        "quote": (
            "Prespecified subgroup analyses compared FORD-II, GTOS-II, and "
            "TRIAGES discrimination by age, sex, fracture location, mechanism "
            "of injury, calendar period, and trauma-center designation."
        ),
        "na_reason": None,
    },
    "10": {
        "item": "10",
        "topic": "Study size",
        "recommendation": "Explain how the study size was arrived at.",
        "section_ref": "Results — Cohort",
        "page": 9,
        "quote": (
            "From 7,327,714 NTDB encounters between 2019 and 2024, sequential "
            "filtering yielded 1,952,210 analytic encounters with adult "
            "fracture diagnoses and classifiable discharge disposition."
        ),
        "na_reason": None,
    },
    "11": {
        "item": "11",
        "topic": "Quantitative variables",
        "recommendation": (
            "Explain how quantitative variables were handled in the analyses. "
            "If applicable, describe which groupings were chosen and why."
        ),
        "section_ref": "Methods — Predictors, score development, and comparators",
        "page": 6,
        "quote": (
            "FORD-II was developed from 41 prespecified binary predictors "
            "available at trauma admission, including demographics, vital "
            "signs, BMI, fracture location, injury mechanism."
        ),
        "na_reason": None,
    },
    "12a": {
        "item": "12a",
        "topic": "Statistical methods",
        "recommendation": (
            "Describe all statistical methods, including those used to "
            "control for confounding."
        ),
        "section_ref": "Methods — Validation analysis",
        "page": 7,
        "quote": (
            "Discrimination was assessed using AUROC with 1,000-iteration "
            "bootstrap 95% confidence intervals. Between-score comparisons "
            "used the DeLong test."
        ),
        "na_reason": None,
    },
    "12b": {
        "item": "12b",
        "topic": "Statistical methods",
        "recommendation": "Describe any methods used to examine subgroups and interactions.",
        "section_ref": "Methods — Subgroup and sensitivity analyses",
        "page": 7,
        "quote": (
            "Prespecified subgroup analyses compared FORD-II, GTOS-II, and "
            "TRIAGES discrimination by age, sex, fracture location, mechanism "
            "of injury, calendar period, and trauma-center designation."
        ),
        "na_reason": None,
    },
    "12c": {
        "item": "12c",
        "topic": "Statistical methods",
        "recommendation": "Explain how missing data were addressed.",
        "section_ref": "Methods — Subgroup and sensitivity analyses",
        "page": 7,
        "quote": (
            "Missing values for binary clinical indicators were coded as 0 and "
            "missing categorical values defaulted to the reference category; a "
            "missingness sensitivity analysis was conducted."
        ),
        "na_reason": None,
    },
    "12d": {
        "item": "12d",
        "topic": "Statistical methods",
        "recommendation": (
            "Cohort study—If applicable, explain how loss to follow-up "
            "was addressed."
        ),
        "section_ref": None,
        "page": None,
        "quote": None,
        "na_reason": (
            "Single-admission analytic cohort — outcome (discharge "
            "disposition) ascertained at the index encounter; no follow-up "
            "phase exists, so loss to follow-up is not applicable."
        ),
    },
    "12e": {
        "item": "12e",
        "topic": "Statistical methods",
        "recommendation": "Describe any sensitivity analyses.",
        "section_ref": "Methods — Subgroup and sensitivity analyses",
        "page": 7,
        "quote": (
            "Prespecified subgroup analyses compared FORD-II, GTOS-II, and "
            "TRIAGES discrimination by age, sex, fracture location, mechanism "
            "of injury, calendar period, and trauma-center designation."
        ),
        "na_reason": None,
    },
    "13a": {
        "item": "13a",
        "topic": "Participants",
        "recommendation": (
            "Report numbers of individuals at each stage of study—eg "
            "numbers potentially eligible, examined for eligibility, confirmed "
            "eligible, included in the study, completing follow-up, and "
            "analysed."
        ),
        "section_ref": "Results — Cohort",
        "page": 9,
        "quote": (
            "From 7,327,714 NTDB encounters between 2019 and 2024, sequential "
            "filtering yielded 1,952,210 analytic encounters with adult "
            "fracture diagnoses and classifiable discharge disposition."
        ),
        "na_reason": None,
    },
    "13b": {
        "item": "13b",
        "topic": "Participants",
        "recommendation": "Give reasons for non-participation at each stage.",
        "section_ref": "Results — Cohort",
        "page": 9,
        "quote": (
            "Sequential filtering yielded 1,952,210 analytic encounters with "
            "adult fracture diagnoses and classifiable discharge disposition "
            "(eFigure 1 in Supplement)."
        ),
        "na_reason": None,
    },
    "13c": {
        "item": "13c",
        "topic": "Participants",
        "recommendation": "Consider use of a flow diagram.",
        "section_ref": "eFigure 1",
        "page": 49,
        "quote": (
            "eFigure 1. Study Cohort Selection. Flow diagram showing selection "
            "of adults with fracture-related trauma from the National Trauma "
            "Data Bank, 2019 to 2024."
        ),
        "na_reason": None,
    },
    "14a": {
        "item": "14a",
        "topic": "Descriptive data",
        "recommendation": (
            "Give characteristics of study participants (eg demographic, "
            "clinical, social) and information on exposures and potential "
            "confounders."
        ),
        "section_ref": "Table 1",
        "page": 24,
        "quote": (
            "Table 1. Baseline Characteristics of the Derivation and Held-Out "
            "Validation Cohorts."
        ),
        "na_reason": None,
    },
    "14b": {
        "item": "14b",
        "topic": "Descriptive data",
        "recommendation": (
            "Indicate number of participants with missing data for each "
            "variable of interest."
        ),
        "section_ref": "eTable 6",
        "page": 41,
        "quote": (
            "eTable 6. Per-predictor missingness rates (derivation and "
            "held-out validation cohorts)."
        ),
        "na_reason": None,
    },
    "14c": {
        "item": "14c",
        "topic": "Descriptive data",
        "recommendation": "Cohort study—Summarise follow-up time (eg, average and total amount).",
        "section_ref": None,
        "page": None,
        "quote": None,
        "na_reason": (
            "Single-admission analytic cohort — outcome ascertained at "
            "the index trauma encounter; there is no post-discharge follow-up "
            "interval to summarise."
        ),
    },
    "15": {
        "item": "15",
        "topic": "Outcome data",
        "recommendation": "Cohort study—Report numbers of outcome events or summary measures over time.",
        "section_ref": "Results — Cohort",
        "page": 9,
        "quote": (
            "The validation cohort included 650,737 patients, of whom 259,827 "
            "experienced non-home discharge."
        ),
        "na_reason": None,
    },
    "16a": {
        "item": "16a",
        "topic": "Main results",
        "recommendation": (
            "Give unadjusted estimates and, if applicable, confounder-adjusted "
            "estimates and their precision (eg, 95% confidence interval). "
            "Make clear which confounders were adjusted for and why they were "
            "included."
        ),
        "section_ref": "Results — Discrimination and clinical utility",
        "page": 10,
        "quote": (
            "FORD-II demonstrated strong discrimination, with an AUROC of "
            "0.8285 (95% CI, 0.8275-0.8296). This exceeded FORD-I (AUROC, "
            "0.7749) and GTOS-II (AUROC, 0.7940)."
        ),
        "na_reason": None,
    },
    "16b": {
        "item": "16b",
        "topic": "Main results",
        "recommendation": "Report category boundaries when continuous variables were categorized.",
        "section_ref": "Results — Risk stratification",
        "page": 10,
        "quote": (
            "Low-risk group, defined by 0 to 2 points; low-moderate-risk "
            "group, defined by 3 to 5 points."
        ),
        "na_reason": None,
    },
    "16c": {
        "item": "16c",
        "topic": "Main results",
        "recommendation": (
            "If relevant, consider translating estimates of relative risk "
            "into absolute risk for a meaningful time period."
        ),
        "section_ref": "Results — Risk stratification",
        "page": 10,
        "quote": (
            "Non-home discharge rates increased stepwise from 7.29% in the "
            "low-risk group to 33.54% in the low-moderate-risk group, 63.80% "
            "in the moderate-high-risk group."
        ),
        "na_reason": None,
    },
    "17": {
        "item": "17",
        "topic": "Other analyses",
        "recommendation": (
            "Report other analyses done—eg analyses of subgroups and "
            "interactions, and sensitivity analyses."
        ),
        "section_ref": "Results — Subgroup and sensitivity analyses",
        "page": 10,
        "quote": (
            "FORD-II performance was stable across all prespecified "
            "demographic, injury-location, mechanism, temporal, and "
            "trauma-center strata, with stratum AUROCs ranging from 0.6935 "
            "to 0.8733."
        ),
        "na_reason": None,
    },
    "18": {
        "item": "18",
        "topic": "Key results",
        "recommendation": "Summarise key results with reference to study objectives.",
        "section_ref": "Discussion",
        "page": 13,
        "quote": (
            "In the validation cohort of 650,737 patients, FORD-II showed "
            "strong discrimination for non-home discharge and outperformed "
            "GTOS-II and TRIAGES."
        ),
        "na_reason": None,
    },
    "19": {
        "item": "19",
        "topic": "Limitations",
        "recommendation": (
            "Discuss limitations of the study, taking into account sources of "
            "potential bias or imprecision. Discuss both direction and "
            "magnitude of any potential bias."
        ),
        "section_ref": "Discussion",
        "page": 13,
        "quote": (
            "Several limitations remain. The NTDB is an administrative "
            "registry, and ICD-10 fracture-prefix matching may have "
            "misclassified some injuries."
        ),
        "na_reason": None,
    },
    "20": {
        "item": "20",
        "topic": "Interpretation",
        "recommendation": (
            "Give a cautious overall interpretation of results considering "
            "objectives, limitations, multiplicity of analyses, results from "
            "similar studies, and other relevant evidence."
        ),
        "section_ref": "Discussion",
        "page": 13,
        "quote": (
            "FORD-II reframes discharge-disposition prediction as an "
            "admission-time operational signal for fracture-trauma care."
        ),
        "na_reason": None,
    },
    "21": {
        "item": "21",
        "topic": "Generalisability",
        "recommendation": "Discuss the generalisability (external validity) of the study results.",
        "section_ref": "Discussion",
        "page": 13,
        "quote": (
            "On the NTDB 2019 to 2024 validation set, the FORD-I score "
            "achieved an AUROC of 0.7749, showing attenuation outside its "
            "single-center derivation setting."
        ),
        "na_reason": None,
    },
    "22": {
        "item": "22",
        "topic": "Funding",
        "recommendation": (
            "Give the source of funding and the role of the funders for the "
            "present study and, if applicable, for the original study on "
            "which the present article is based."
        ),
        "section_ref": None,
        "page": None,
        "quote": None,
        "na_reason": "no funding section in v12 draft — added at submission",
    },
}


NOTES_FOR_BUILDER = """
TEMPLATE STRUCTURE (STROBE-checklist-v4-combined-PlosMedicine.docx)
-------------------------------------------------------------------
The template uses THREE SIDE-BY-SIDE TABLES (not one combined table). Item rows
are split across the three tables by where the page-break-style design-section
header bands fall. Map STROBE items to template tables as follows:

  Table 0 (15 rows): items 1a, 1b, 2, 3, 4, 5, 6a, 6b, 7, 8, 9, 10
    - R0 = header row (skip)
    - R1 = item 1a (Title and abstract, sub a)
    - R2 = item 1b (Title and abstract, sub b)
    - R3 = "Introduction" section band (skip)
    - R4 = item 2 (Background/rationale)
    - R5 = item 3 (Objectives)
    - R6 = "Methods" section band (skip)
    - R7 = item 4 (Study design)
    - R8 = item 5 (Setting)
    - R9 = item 6a (Participants, sub a)
    - R10 = item 6b (Participants, sub b) -- N/A for FORD-II
    - R11 = item 7 (Variables)
    - R12 = item 8 (Data sources/measurement)
    - R13 = item 9 (Bias)
    - R14 = item 10 (Study size)

  Table 1 (19 rows): items 11, 12a-12e, 13a-13c, 14a-14c, 15, 16a-16c
    - R0 = item 11 (Quantitative variables)
    - R1 = item 12a (Statistical methods, sub a)
    - R2 = item 12b (Statistical methods, sub b)
    - R3 = item 12c (Statistical methods, sub c)
    - R4 = item 12d (Statistical methods, sub d) -- N/A for FORD-II
    - R5 = item 12e (Statistical methods, sub e)
    - R6 = "Results" section band (skip)
    - R7 = item 13a (Participants, sub a)
    - R8 = item 13b (Participants, sub b)
    - R9 = item 13c (Participants, sub c)
    - R10 = item 14a (Descriptive data, sub a)
    - R11 = item 14b (Descriptive data, sub b)
    - R12 = item 14c (Descriptive data, sub c) -- N/A for FORD-II
    - R13 = item 15 (Outcome data, cohort variant) -- USE THIS ROW
    - R14 = item 15 (Outcome data, case-control variant) -- SKIP
    - R15 = item 15 (Outcome data, cross-sectional variant) -- SKIP
    - R16 = item 16a (Main results, sub a)
    - R17 = item 16b (Main results, sub b)
    - R18 = item 16c (Main results, sub c)

  Table 2 (8 rows): items 17, 18, 19, 20, 21, 22
    - R0 = item 17 (Other analyses)
    - R1 = "Discussion" section band (skip)
    - R2 = item 18 (Key results)
    - R3 = item 19 (Limitations)
    - R4 = item 20 (Interpretation)
    - R5 = item 21 (Generalisability)
    - R6 = "Other information" section band (skip)
    - R7 = item 22 (Funding)

COLUMN LAYOUT FOR EACH ITEM ROW
-------------------------------
Each non-band row has 5 columns:
  Col 0 = Topic label
  Col 1 = Item No.
  Col 2 = Recommendation (may include "Cohort study—... | Case-control study—... | Cross-sectional study—..." variants in one cell, separated by " | "). Do NOT modify col 2; leave the template's design-design variant text alone.
  Col 3 = Page No.   <-- write STROBE_MAP[item]["page"] here
  Col 4 = Relevant text from manuscript  <-- write STROBE_MAP[item]["quote"] (and section_ref) here

For N/A items (6b, 12d, 14c, 22), write the na_reason into col 4 and leave col 3
blank.

COHORT-ONLY GUIDANCE
--------------------
For item 6 (a + b), item 12d, and item 15, the template's recommendation cell
contains all three design variants. Only the COHORT variant is applicable here;
do not erase the case-control/cross-sectional text from col 2 (preserve the
template), but for col 4 (manuscript text) only fill in content that addresses
the cohort variant.

ALIGNMENT WITH STROBE V4 TAXONOMY
---------------------------------
Item ids match the published STROBE v4 / PLOS Medicine combined checklist.
Sub-items use lowercase letter suffixes (1a, 1b, 6a, 6b, 12a-12e, 13a-13c,
14a-14c, 16a-16c). 31 keys total.
"""

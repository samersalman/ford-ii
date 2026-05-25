"""
TRIPOD 2015 item -> manuscript-location mapping for FORD-II v12 manuscript.

Date: 2026-05-16
Source manuscript: ntdb_validation/v12/[current] v12-FORD-II-manuscript.docx
Page map:          ntdb_validation/v12/checklists/completed/_v12_page_map.json
Template:          ntdb_validation/v12/checklists/Tripod-Checklist-Prediction-Model-Development-and-Validation-Word.docx

Total TRIPOD-2015 rows: 37 sub-items across the 22 canonical items.
  Mapped: 30
  N/A:     7 (items 5c, 6b, 7b, 10e, 14b, 17, 22)

Note on D/V tags: the template's Item column uses LETTER form ("D;V", "D", "V").
This module preserves those literal values in `applies_dv`.

v12 study design: single-dataset derivation + held-out internal validation
(NTDB 2019-2024, 2:1 stratified split). Items tagged "V" in the template are
mapped to the validation cohort discussion in v12 (not a separate dataset).
"""

TRIPOD_MAP = {
    # ============================================================
    # TITLE AND ABSTRACT
    # ============================================================
    "1": {
        "item": "1",
        "topic": "Title",
        "recommendation": (
            "Identify the study as developing and/or validating a multivariable "
            "prediction model, the target population, and the outcome to be predicted."
        ),
        "applies_dv": "D;V",
        "section_ref": "Title page",
        "page": 1,
        "quote": (
            "Fracture Orthopedic Risk of Non-Home Discharge II (FORD-II): "
            "National Registry Derivation, Internal Validation, and "
            "Cost-Effectiveness of a Fracture Trauma Discharge-Disposition Score"
        ),
        "na_reason": None,
    },
    "2": {
        "item": "2",
        "topic": "Abstract",
        "recommendation": (
            "Provide a summary of objectives, study design, setting, participants, "
            "sample size, predictors, outcome, statistical analysis, results, and conclusions."
        ),
        "applies_dv": "D;V",
        "section_ref": "Abstract — Methods",
        "page": 2,
        "quote": (
            "FORD-II was derived as a 16-predictor integer score using penalized "
            "regression and rescaled point weights, then evaluated in a held-out "
            "validation cohort."
        ),
        "na_reason": None,
    },

    # ============================================================
    # INTRODUCTION
    # ============================================================
    "3a": {
        "item": "3a",
        "topic": "Background and objectives",
        "recommendation": (
            "Explain the medical context (including whether diagnostic or prognostic) "
            "and rationale for developing or validating the multivariable prediction "
            "model, including references to existing models."
        ),
        "applies_dv": "D;V",
        "section_ref": "Introduction",
        "page": 4,
        "quote": (
            "Existing trauma scores do not adequately address this operational need. "
            "Most trauma prediction tools were designed to estimate mortality or "
            "broad trauma outcome."
        ),
        "na_reason": None,
    },
    "3b": {
        "item": "3b",
        "topic": "Background and objectives",
        "recommendation": (
            "Specify the objectives, including whether the study describes the "
            "development or validation of the model or both."
        ),
        "applies_dv": "D;V",
        "section_ref": "Introduction",
        "page": 4,
        "quote": (
            "We developed FORD-II as a nationally derived extension of the FORD "
            "framework designed to improve generalizability across adult fracture "
            "trauma populations."
        ),
        "na_reason": None,
    },

    # ============================================================
    # METHODS
    # ============================================================
    "4a": {
        "item": "4a",
        "topic": "Source of data",
        "recommendation": (
            "Describe the study design or source of data (e.g., randomized trial, "
            "cohort, or registry data), separately for the development and validation "
            "data sets, if applicable."
        ),
        "applies_dv": "D;V",
        "section_ref": "Methods — Cohort and outcome",
        "page": 5,
        "quote": (
            "We performed a retrospective development and held-out validation study "
            "using the NTDB years 2019–2024."
        ),
        "na_reason": None,
    },
    "4b": {
        "item": "4b",
        "topic": "Source of data",
        "recommendation": (
            "Specify the key study dates, including start of accrual; end of accrual; "
            "and, if applicable, end of follow-up."
        ),
        "applies_dv": "D;V",
        "section_ref": "Methods — Cohort and outcome",
        "page": 5,
        "quote": (
            "Adults with primary fracture diagnoses and classifiable discharge "
            "dispositions were identified from the National Trauma Data Bank from "
            "2019 to 2024."
        ),
        "na_reason": None,
    },
    "5a": {
        "item": "5a",
        "topic": "Participants",
        "recommendation": (
            "Specify key elements of the study setting (e.g., primary care, secondary "
            "care, general population) including number and location of centres."
        ),
        "applies_dv": "D;V",
        "section_ref": "Methods — Cohort and outcome",
        "page": 5,
        "quote": (
            "We performed a retrospective development and held-out validation study "
            "using the NTDB years 2019–2024."
        ),
        "na_reason": None,
    },
    "5b": {
        "item": "5b",
        "topic": "Participants",
        "recommendation": "Describe eligibility criteria for participants.",
        "applies_dv": "D;V",
        "section_ref": "Methods — Cohort and outcome",
        "page": 5,
        "quote": (
            "Eligible adults (≥18 years) had primary ICD-10 fracture diagnoses and "
            "classifiable discharge dispositions. We excluded in-hospital deaths, "
            "hospice, jail, transfers, or AMA."
        ),
        "na_reason": None,
    },
    "5c": {
        "item": "5c",
        "topic": "Participants",
        "recommendation": "Give details of treatments received, if relevant.",
        "applies_dv": "D;V",
        "section_ref": None,
        "page": None,
        "quote": None,
        "na_reason": (
            "FORD-II is an admission-time risk score using trauma-admission predictors; "
            "no treatment exposures are modeled and treatment receipt is not relevant "
            "to the prediction question."
        ),
    },
    "6a": {
        "item": "6a",
        "topic": "Outcome",
        "recommendation": (
            "Clearly define the outcome that is predicted by the prediction model, "
            "including how and when assessed."
        ),
        "applies_dv": "D;V",
        "section_ref": "Methods — Cohort and outcome",
        "page": 5,
        "quote": (
            "The primary outcome was non-home discharge, defined as discharge to "
            "rehabilitation, SNF, LTACH, or intermediate care facility."
        ),
        "na_reason": None,
    },
    "6b": {
        "item": "6b",
        "topic": "Outcome",
        "recommendation": "Report any actions to blind assessment of the outcome to be predicted.",
        "applies_dv": "D;V",
        "section_ref": None,
        "page": None,
        "quote": None,
        "na_reason": (
            "Outcome is ascertained from NTDB administrative discharge-disposition "
            "fields recorded by participating centers; blinding of outcome assessment "
            "is not applicable for registry-coded discharge status."
        ),
    },
    "7a": {
        "item": "7a",
        "topic": "Predictors",
        "recommendation": (
            "Clearly define all predictors used in developing or validating the "
            "multivariable prediction model, including how and when they were measured."
        ),
        "applies_dv": "D;V",
        "section_ref": "Methods — Predictors, score development, and comparators",
        "page": 6,
        "quote": (
            "FORD-II was developed from 41 prespecified binary predictors available "
            "at trauma admission, including demographics, vital signs, BMI, fracture "
            "location, injury mechanism, and prehospital transport."
        ),
        "na_reason": None,
    },
    "7b": {
        "item": "7b",
        "topic": "Predictors",
        "recommendation": (
            "Report any actions to blind assessment of predictors for the outcome and "
            "other predictors."
        ),
        "applies_dv": "D;V",
        "section_ref": None,
        "page": None,
        "quote": None,
        "na_reason": (
            "All predictors are objective admission-time variables (demographics, "
            "vitals, BMI, ICD-10 fracture codes, mechanism, transport) recorded in "
            "NTDB before discharge; predictor-assessment blinding is not applicable."
        ),
    },
    "8": {
        "item": "8",
        "topic": "Sample size",
        "recommendation": "Explain how the study size was arrived at.",
        "applies_dv": "D;V",
        "section_ref": "Results — Cohort",
        "page": 9,
        "quote": (
            "From 7,327,714 NTDB encounters between 2019 and 2024, sequential "
            "filtering yielded 1,952,210 analytic encounters with adult fracture "
            "diagnoses and classifiable discharge disposition."
        ),
        "na_reason": None,
    },
    "9": {
        "item": "9",
        "topic": "Missing data",
        "recommendation": (
            "Describe how missing data were handled (e.g., complete-case analysis, "
            "single imputation, multiple imputation) with details of any imputation method."
        ),
        "applies_dv": "D;V",
        "section_ref": "Methods — Subgroup and sensitivity analyses",
        "page": 7,
        "quote": (
            "Missing values for binary clinical indicators were coded as 0 and "
            "missing categorical values defaulted to the reference category; a "
            "missingness sensitivity analysis was conducted."
        ),
        "na_reason": None,
    },
    "10a": {
        "item": "10a",
        "topic": "Statistical analysis methods",
        "recommendation": "Describe how predictors were handled in the analyses.",
        "applies_dv": "D",
        "section_ref": "Methods — Predictors, score development, and comparators",
        "page": 6,
        "quote": (
            "FORD-II was developed from 41 prespecified binary predictors available "
            "at trauma admission, including demographics, vital signs, BMI, fracture "
            "location, injury mechanism, and prehospital transport."
        ),
        "na_reason": None,
    },
    "10b": {
        "item": "10b",
        "topic": "Statistical analysis methods",
        "recommendation": (
            "Specify type of model, all model-building procedures (including any "
            "predictor selection), and method for internal validation."
        ),
        "applies_dv": "D",
        "section_ref": "Methods — Predictors, score development, and comparators",
        "page": 6,
        "quote": (
            "Predictors were selected using LASSO regression with 5-fold "
            "cross-validation and AUROC scoring. Selected β coefficients were "
            "converted to integers by rescaling and rounding."
        ),
        "na_reason": None,
    },
    "10c": {
        "item": "10c",
        "topic": "Statistical analysis methods",
        "recommendation": "For validation, describe how the predictions were calculated.",
        "applies_dv": "V",
        "section_ref": "Methods — Predictors, score development, and comparators",
        "page": 6,
        "quote": (
            "The integer score was mapped to predicted probability in the derivation "
            "cohort using a logistic calibration model with the integer score as the "
            "sole predictor."
        ),
        "na_reason": None,
    },
    "10d": {
        "item": "10d",
        "topic": "Statistical analysis methods",
        "recommendation": (
            "Specify all measures used to assess model performance and, if relevant, "
            "to compare multiple models."
        ),
        "applies_dv": "D;V",
        "section_ref": "Methods — Validation analysis",
        "page": 7,
        "quote": (
            "Calibration of the derived predicted probabilities was assessed using "
            "calibration intercept, calibration slope, Hosmer-Lemeshow testing, "
            "Brier score, and scaled Brier score."
        ),
        "na_reason": None,
    },
    "10e": {
        "item": "10e",
        "topic": "Statistical analysis methods",
        "recommendation": (
            "Describe any model updating (e.g., recalibration) arising from the "
            "validation, if done."
        ),
        "applies_dv": "V",
        "section_ref": None,
        "page": None,
        "quote": None,
        "na_reason": (
            "Primary analysis locks model coefficients before application to the "
            "validation cohort; v12 manuscript explicitly states 'No probability "
            "recalibration was performed in validation.'"
        ),
    },
    "11": {
        "item": "11",
        "topic": "Risk groups",
        "recommendation": "Provide details on how risk groups were created, if done.",
        "applies_dv": "D;V",
        "section_ref": "Methods — Validation analysis",
        "page": 7,
        "quote": (
            "FORD-II risk groups were prespecified as low risk, low-moderate risk, "
            "moderate-high risk, and high risk."
        ),
        "na_reason": None,
    },
    "12": {
        "item": "12",
        "topic": "Development vs. validation",
        "recommendation": (
            "For validation, identify any differences from the development data in "
            "setting, eligibility criteria, outcome, and predictors."
        ),
        "applies_dv": "V",
        "section_ref": "Results — Cohort",
        "page": 9,
        "quote": (
            "Derivation and validation cohorts were well balanced across baseline "
            "characteristics, with standardized mean differences of 0.003 or less "
            "for all 41 candidate variables."
        ),
        "na_reason": None,
    },

    # ============================================================
    # RESULTS
    # ============================================================
    "13a": {
        "item": "13a",
        "topic": "Participants",
        "recommendation": (
            "Describe the flow of participants through the study, including the "
            "number of participants with and without the outcome and, if applicable, "
            "a summary of the follow-up time. A diagram may be helpful."
        ),
        "applies_dv": "D;V",
        "section_ref": "Results — Cohort",
        "page": 9,
        "quote": (
            "Sequential filtering yielded 1,952,210 analytic encounters. The "
            "validation cohort included 650,737 patients, of whom 259,827 "
            "experienced non-home discharge (eFigure 1 in Supplement)."
        ),
        "na_reason": None,
    },
    "13b": {
        "item": "13b",
        "topic": "Participants",
        "recommendation": (
            "Describe the characteristics of the participants (basic demographics, "
            "clinical features, available predictors), including the number of "
            "participants with missing data for predictors and outcome."
        ),
        "applies_dv": "D;V",
        "section_ref": "Results — Cohort",
        "page": 9,
        "quote": (
            "Derivation and validation cohorts were well balanced across baseline "
            "characteristics (Table 1; eTable 3 in Supplement)."
        ),
        "na_reason": None,
    },
    "13c": {
        "item": "13c",
        "topic": "Participants",
        "recommendation": (
            "For validation, show a comparison with the development data of the "
            "distribution of important variables (demographics, predictors and outcome)."
        ),
        "applies_dv": "V",
        "section_ref": "Results — Cohort",
        "page": 9,
        "quote": (
            "Standardized mean differences of 0.003 or less for all 41 candidate "
            "variables (Table 1; eTable 3 in Supplement)."
        ),
        "na_reason": None,
    },
    "14a": {
        "item": "14a",
        "topic": "Model development",
        "recommendation": "Specify the number of participants and outcome events in each analysis.",
        "applies_dv": "D",
        "section_ref": "Abstract — Results",
        "page": 2,
        "quote": (
            "Among 1,952,210 encounters, 1,301,473 were used for training and "
            "650,737 for validation."
        ),
        "na_reason": None,
    },
    "14b": {
        "item": "14b",
        "topic": "Model development",
        "recommendation": (
            "If done, report the unadjusted association between each candidate "
            "predictor and outcome."
        ),
        "applies_dv": "D",
        "section_ref": None,
        "page": None,
        "quote": None,
        "na_reason": (
            "Unadjusted univariate associations between each of the 41 candidate "
            "predictors and non-home discharge were not separately tabulated; "
            "predictor selection used LASSO with 5-fold cross-validation rather "
            "than univariate screening."
        ),
    },
    "15a": {
        "item": "15a",
        "topic": "Model specification",
        "recommendation": (
            "Present the full prediction model to allow predictions for individuals "
            "(i.e., all regression coefficients, and model intercept or baseline "
            "survival at a given time point)."
        ),
        "applies_dv": "D",
        "section_ref": "Results — Score derivation",
        "page": 9,
        "quote": (
            "FORD-II retained 16 predictors that were converted into integer "
            "point weights ranging from −2 to +6 (Table 2)."
        ),
        "na_reason": None,
    },
    "15b": {
        "item": "15b",
        "topic": "Model specification",
        "recommendation": "Explain how to the use the prediction model.",
        "applies_dv": "D",
        "section_ref": "Results — Score derivation",
        "page": 9,
        "quote": (
            "The raw point sum was truncated to a final 0-10 score for bedside "
            "use; higher FORD-II scores corresponded to greater predicted risk "
            "(Table 2)."
        ),
        "na_reason": None,
    },
    "16": {
        "item": "16",
        "topic": "Model performance",
        "recommendation": "Report performance measures (with CIs) for the prediction model.",
        "applies_dv": "D;V",
        "section_ref": "Results — Discrimination and clinical utility",
        "page": 10,
        "quote": (
            "FORD-II achieved an AUROC of 0.8285 (95% CI, 0.8275-0.8296); "
            "calibration intercept of 0, slope of 1, Brier score of 0.164."
        ),
        "na_reason": None,
    },
    "17": {
        "item": "17",
        "topic": "Model-updating",
        "recommendation": (
            "If done, report the results from any model updating (i.e., model "
            "specification, model performance)."
        ),
        "applies_dv": "V",
        "section_ref": None,
        "page": None,
        "quote": None,
        "na_reason": (
            "No model updating or recalibration was performed in v12; the "
            "derivation-locked logistic calibration model and integer weights were "
            "applied unchanged to the held-out validation cohort."
        ),
    },

    # ============================================================
    # DISCUSSION
    # ============================================================
    "18": {
        "item": "18",
        "topic": "Limitations",
        "recommendation": (
            "Discuss any limitations of the study (such as nonrepresentative sample, "
            "few events per predictor, missing data)."
        ),
        "applies_dv": "D;V",
        "section_ref": "Discussion",
        "page": 13,
        "quote": (
            "The NTDB is an administrative registry, and ICD-10 fracture-prefix "
            "matching may have misclassified some injuries; NTDB does not release "
            "facility identifiers, precluding clustering adjustment."
        ),
        "na_reason": None,
    },
    "19a": {
        "item": "19a",
        "topic": "Interpretation",
        "recommendation": (
            "For validation, discuss the results with reference to performance in "
            "the development data, and any other validation data."
        ),
        "applies_dv": "V",
        "section_ref": "Discussion",
        "page": 13,
        "quote": (
            "On the NTDB 2019-2024 validation set, FORD-I achieved an AUROC of "
            "0.7749 (95% CI, 0.7738–0.7761), showing attenuation outside its "
            "single-center derivation setting."
        ),
        "na_reason": None,
    },
    "19b": {
        "item": "19b",
        "topic": "Interpretation",
        "recommendation": (
            "Give an overall interpretation of the results, considering objectives, "
            "limitations, results from similar studies, and other relevant evidence."
        ),
        "applies_dv": "D;V",
        "section_ref": "Discussion",
        "page": 13,
        "quote": (
            "FORD-II reframes discharge-disposition prediction as an admission-time "
            "operational signal for fracture-trauma care. The risk gradient was "
            "clinically actionable: non-home discharge increased from 7.3% to 80.5%."
        ),
        "na_reason": None,
    },
    "20": {
        "item": "20",
        "topic": "Implications",
        "recommendation": (
            "Discuss the potential clinical use of the model and implications for "
            "future research."
        ),
        "applies_dv": "D;V",
        "section_ref": "Discussion",
        "page": 13,
        "quote": (
            "The next step should be external multicenter validation followed by "
            "prospective implementation testing. A stepped-wedge cluster-randomized "
            "trial could introduce FORD-II sequentially across trauma centers."
        ),
        "na_reason": None,
    },

    # ============================================================
    # OTHER INFORMATION
    # ============================================================
    "21": {
        "item": "21",
        "topic": "Supplementary information",
        "recommendation": (
            "Provide information about the availability of supplementary resources, "
            "such as study protocol, Web calculator, and data sets."
        ),
        "applies_dv": "D;V",
        "section_ref": "Supplemental Online Content",
        "page": 32,
        "quote": (
            "Supplemental Online Content includes eTables 1-11 and eFigures 1-2 "
            "covering ICD-10 codes, PSA distributions, baseline characteristics, "
            "subgroup discrimination, missingness, and cohort selection."
        ),
        "na_reason": None,
    },
    "22": {
        "item": "22",
        "topic": "Funding",
        "recommendation": "Give the source of funding and the role of the funders for the present study.",
        "applies_dv": "D;V",
        "section_ref": None,
        "page": None,
        "quote": None,
        "na_reason": (
            "v12 draft does not contain a funding statement; per author workflow, "
            "funding and disclosure sections are added at submission and were not "
            "present in the v12 manuscript file."
        ),
    },
}


NOTES_FOR_BUILDER = """
Template format notes for the docx builder:
- The TRIPOD template's Item column uses LETTER form: "D;V", "D", "V".
  Write `applies_dv` literally; do NOT translate to "Development"/"Validation"/"Both".
- Template has 5 columns: Section/Topic | Item | (D/V) | Checklist Item | Page.
  Section/Topic, Item, applies_dv, and recommendation are already present in the
  blank template — only the rightmost "Page" cell needs to be filled per row.
- Section/Topic header rows (Title and abstract, Introduction, Methods, Results,
  Discussion, Other information) are not items and should be skipped when filling.

Page-fill convention for N/A items:
- Items 5c, 6b, 7b, 10e, 14b, 17, 22 are N/A. Recommend the builder write
  "N/A — <na_reason>" in the Page cell (or leave page blank and add the reason
  in a footnote, per the project's standing convention).

v12 study-design notes:
- v12 is single-dataset derivation + held-out internal validation (NTDB 2019-2024,
  2:1 stratified split). Items the template flags "V" are mapped to the held-out
  validation portion of v12 (not an external dataset).
- Item 12 and 13c (dev-vs-validation comparison) are mapped, not N/A, because
  v12 explicitly reports SMDs comparing the derivation training set with the
  held-out validation set (Table 1; eTable 3).
- Item 10e and 17 (model updating / recalibration) are N/A because v12 explicitly
  states "No probability recalibration was performed in validation."

Item-count audit:
- Total rows: 37
- Mapped:     30
- N/A:         7 (5c, 6b, 7b, 10e, 14b, 17, 22)
"""

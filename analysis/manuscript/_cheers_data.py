"""CHEERS-2022 reporting checklist data for the FORD-II cost-effectiveness analysis.

Provides CHEERS_ITEMS, the 28-item canonical list (Husereau D, Drummond M, Augustovski F,
et al. Consolidated Health Economic Evaluation Reporting Standards 2022 (CHEERS 2022)
Statement. BMJ 2022;376:e067975. PMID 35017145; doi:10.1136/bmj-2021-067975).
Consumed by 06_ford_v4_cost_decision_tree.py to render the Supplement S-CHEERS table.
"""

CHEERS_ITEMS = [
    {
        "item_no": 1,
        "section": "Title",
        "item_name": "Title",
        "description": "Identify the study as an economic evaluation and specify the interventions being compared.",
        "address_status": "Session 7 dependency",
        "cross_reference": "Session 7 manuscript draft (TBD)",
    },
    {
        "item_no": 2,
        "section": "Abstract",
        "item_name": "Abstract",
        "description": "Provide a structured summary that highlights context, key methods, results, and alternative analyses.",
        "address_status": "Session 7 dependency",
        "cross_reference": "Session 7 manuscript draft (TBD)",
    },
    {
        "item_no": 3,
        "section": "Introduction",
        "item_name": "Background and objectives",
        "description": "Give the context for the study, the study question, and its practical relevance for decision making and policy.",
        "address_status": "Session 7 dependency",
        "cross_reference": "Session 7 manuscript draft (TBD)",
    },
    {
        "item_no": 4,
        "section": "Methods",
        "item_name": "Health economic analysis plan",
        "description": "Indicate whether a health economic analysis plan was developed and where it can be accessed.",
        "address_status": "Addressed",
        "cross_reference": "Methods § Cost-model architecture; cost_analysis/methodology_lock.md § 1",
    },
    {
        "item_no": 5,
        "section": "Methods",
        "item_name": "Study population",
        "description": "Describe characteristics of the study population (e.g., age range, demographics, eligibility criteria).",
        "address_status": "Addressed",
        "cross_reference": "Methods § Study population; tables/table_base_case.csv; cost_model_inputs.csv",
    },
    {
        "item_no": 6,
        "section": "Methods",
        "item_name": "Setting and location",
        "description": "Provide relevant aspects of the system(s) in which the decision(s) need(s) to be made.",
        "address_status": "Addressed",
        "cross_reference": "Methods § Setting and location; cost_analysis/methodology_lock.md § 2",
    },
    {
        "item_no": 7,
        "section": "Methods",
        "item_name": "Comparators",
        "description": "Describe the interventions or strategies being compared and why they were chosen.",
        "address_status": "Addressed",
        "cross_reference": "Methods § Comparators; tables/sensitivity_arms.csv; figures/cost_analysis/decision_tree_diagram.png",
    },
    {
        "item_no": 8,
        "section": "Methods",
        "item_name": "Perspective",
        "description": "State the perspective(s) adopted by the study and why chosen.",
        "address_status": "Addressed",
        "cross_reference": "Methods § Perspective; cost_analysis/methodology_lock.md § 3",
    },
    {
        "item_no": 9,
        "section": "Methods",
        "item_name": "Time horizon",
        "description": "State the time horizon(s) over which costs and consequences are evaluated and why appropriate.",
        "address_status": "Addressed",
        "cross_reference": "Methods § Time horizon; cost_analysis/methodology_lock.md § 3",
    },
    {
        "item_no": 10,
        "section": "Methods",
        "item_name": "Discount rate",
        "description": "Report the discount rate(s) used for costs and outcomes and say why appropriate.",
        "address_status": "Addressed",
        "cross_reference": "Methods § Discount rate; cost_analysis/methodology_lock.md § 3",
    },
    {
        "item_no": 11,
        "section": "Methods",
        "item_name": "Selection of outcomes",
        "description": "Describe what outcomes were used as the measure(s) of benefit and harm in the evaluation.",
        "address_status": "Addressed",
        "cross_reference": "Methods § Selection of outcomes; tables/cost_consequence.csv",
    },
    {
        "item_no": 12,
        "section": "Methods",
        "item_name": "Measurement of outcomes",
        "description": "Describe how the outcomes used to capture benefit and harm were measured.",
        "address_status": "Addressed",
        "cross_reference": "Methods § Measurement of outcomes; cost_analysis/methodology_lock.md § 4",
    },
    {
        "item_no": 13,
        "section": "Methods",
        "item_name": "Valuation of outcomes",
        "description": "Describe the population and methods used to value the outcomes.",
        "address_status": "Addressed",
        "cross_reference": "Methods § Valuation of outcomes; cost_analysis/methodology_lock.md § 4",
    },
    {
        "item_no": 14,
        "section": "Methods",
        "item_name": "Measurement and valuation of resources and costs",
        "description": "Describe how costs were valued and resource use measured for each intervention.",
        "address_status": "Addressed",
        "cross_reference": "Methods § Resource use and costs; tables/table_base_case.csv; cost_model_inputs.csv",
    },
    {
        "item_no": 15,
        "section": "Methods",
        "item_name": "Currency, price date, and conversion",
        "description": "Report the dates of estimated resource quantities and unit costs, plus the currency and conversion used.",
        "address_status": "Addressed",
        "cross_reference": "Methods § Currency and price year; cost_analysis/methodology_lock.md § 5",
    },
    {
        "item_no": 16,
        "section": "Methods",
        "item_name": "Rationale and description of model",
        "description": "If modelling is used, describe in detail and provide a rationale; provide access to model where possible.",
        "address_status": "Addressed",
        "cross_reference": "Methods § Decision-tree model; figures/cost_analysis/decision_tree_diagram.png; cost_analysis/methodology_lock.md § 6",
    },
    {
        "item_no": 17,
        "section": "Methods",
        "item_name": "Analytics and assumptions",
        "description": "Describe analytical methods and assumptions, including any methods to handle missing or skewed data.",
        "address_status": "Addressed",
        "cross_reference": "Methods § Analytics and assumptions; cost_analysis/methodology_lock.md § 7",
    },
    {
        "item_no": 18,
        "section": "Methods",
        "item_name": "Characterizing heterogeneity",
        "description": "Describe methods used to estimate how results vary for sub-groups.",
        "address_status": "Addressed",
        "cross_reference": "Methods § Subgroup analyses; tables/sensitivity_arms.csv",
    },
    {
        "item_no": 19,
        "section": "Methods",
        "item_name": "Characterizing distributional effects",
        "description": "Describe how impacts are distributed across different individuals or adjustments made for priority populations.",
        "address_status": "Not applicable",
        "cross_reference": "Not applicable - no distributional/equity-weighted CEA performed in FORD-II Session 6",
    },
    {
        "item_no": 20,
        "section": "Methods",
        "item_name": "Characterizing uncertainty",
        "description": "Describe methods to characterize sources of uncertainty in the analysis (deterministic and probabilistic).",
        "address_status": "Addressed",
        "cross_reference": "Methods § Uncertainty analysis; tables/table_tornado.csv; tables/table_threshold.csv; cost_analysis/psa_results.csv; cost_analysis/figure_tornado.png; cost_analysis/figure_psa_scatter.png; cost_analysis/figure_ceac.png",
    },
    {
        "item_no": 21,
        "section": "Methods",
        "item_name": "Approach to engagement with patients and others affected by the study",
        "description": "Describe approaches to engage patients/service recipients, the public, communities, or stakeholders.",
        "address_status": "Not applicable",
        "cross_reference": "Not applicable - no patient or public engagement conducted for this secondary-data cost model",
    },
    {
        "item_no": 22,
        "section": "Results",
        "item_name": "Study parameters",
        "description": "Report values, ranges, references, and (if used) probability distributions for all parameters.",
        "address_status": "Addressed",
        "cross_reference": "tables/table_base_case.csv; cost_model_inputs.csv; cost_analysis/psa_results.csv",
    },
    {
        "item_no": 23,
        "section": "Results",
        "item_name": "Summary of main results",
        "description": "Report the mean values of the main categories of costs and outcomes; report incremental cost-effectiveness ratios.",
        "address_status": "Addressed",
        "cross_reference": "tables/cost_consequence.csv; figures/cost_analysis/decision_tree_diagram.png",
    },
    {
        "item_no": 24,
        "section": "Results",
        "item_name": "Effect of uncertainty",
        "description": "Describe how uncertainty about analytical judgments, inputs, or projections affect findings.",
        "address_status": "Addressed",
        "cross_reference": "tables/sensitivity_arms.csv; figures/cost_analysis/figure_tornado.png; figures/cost_analysis/figure_psa_scatter.png; figures/cost_analysis/figure_ceac.png; figures/cost_analysis/psa_results.csv",
    },
    {
        "item_no": 25,
        "section": "Results",
        "item_name": "Effect of engagement with patients and others affected by the study",
        "description": "Report on the effect that patient/service-recipient/public/community/stakeholder engagement had on the approach.",
        "address_status": "Not applicable",
        "cross_reference": "Not applicable - no patient or public engagement conducted (see Item 21)",
    },
    {
        "item_no": 26,
        "section": "Discussion",
        "item_name": "Study findings, limitations, generalizability, and current knowledge",
        "description": "Report key findings, limitations, ethical and equity considerations, and how findings fit with current knowledge.",
        "address_status": "Session 7 dependency",
        "cross_reference": "Session 7 manuscript draft (TBD)",
    },
    {
        "item_no": 27,
        "section": "Other",
        "item_name": "Source of funding",
        "description": "Describe how the study was funded and any role of the funder in design, conduct, analysis, or reporting.",
        "address_status": "Session 7 dependency",
        "cross_reference": "Session 7 manuscript draft (TBD)",
    },
    {
        "item_no": 28,
        "section": "Other",
        "item_name": "Conflicts of interest",
        "description": "Report authors' conflicts of interest according to journal or International Committee of Medical Journal Editors requirements.",
        "address_status": "Session 7 dependency",
        "cross_reference": "Session 7 manuscript draft (TBD)",
    },
]


_REQUIRED_KEYS = {
    "item_no": int,
    "section": str,
    "item_name": str,
    "description": str,
    "address_status": str,
    "cross_reference": str,
}
_VALID_SECTIONS = {
    "Title", "Abstract", "Introduction", "Methods",
    "Results", "Discussion", "Other",
}
_VALID_STATUSES = {"Addressed", "Not applicable", "Session 7 dependency"}


def assert_complete():
    """Verify CHEERS_ITEMS has 28 well-formed entries in canonical order."""
    if not isinstance(CHEERS_ITEMS, list):
        raise TypeError("CHEERS_ITEMS must be a list")
    if len(CHEERS_ITEMS) != 28:
        raise ValueError(
            f"CHEERS_ITEMS must contain exactly 28 items; found {len(CHEERS_ITEMS)}"
        )
    for idx, item in enumerate(CHEERS_ITEMS, start=1):
        if not isinstance(item, dict):
            raise TypeError(f"Item {idx} is not a dict")
        missing = set(_REQUIRED_KEYS) - set(item.keys())
        if missing:
            raise KeyError(f"Item {idx} missing keys: {sorted(missing)}")
        extra = set(item.keys()) - set(_REQUIRED_KEYS)
        if extra:
            raise KeyError(f"Item {idx} has unexpected keys: {sorted(extra)}")
        for key, expected_type in _REQUIRED_KEYS.items():
            if not isinstance(item[key], expected_type):
                raise TypeError(
                    f"Item {idx} key '{key}' must be {expected_type.__name__}, "
                    f"got {type(item[key]).__name__}"
                )
        if item["item_no"] != idx:
            raise ValueError(
                f"Item at position {idx} has item_no={item['item_no']}; expected {idx}"
            )
        if item["section"] not in _VALID_SECTIONS:
            raise ValueError(
                f"Item {idx} section '{item['section']}' not in {sorted(_VALID_SECTIONS)}"
            )
        if item["address_status"] not in _VALID_STATUSES:
            raise ValueError(
                f"Item {idx} address_status '{item['address_status']}' "
                f"not in {sorted(_VALID_STATUSES)}"
            )
    return True


if __name__ == "__main__":
    assert_complete()
    print(f"_cheers_data.py OK; len(CHEERS_ITEMS) == {len(CHEERS_ITEMS)}")

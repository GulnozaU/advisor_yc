"""All ranking constants in one place."""

PROMPT_VERSION = "v1"

# S (1-5) by goal chip, then counterparty type.
STAKES = {
    "raise": {"investor_active": 5, "investor_prospect": 4, "customer": 5, "prospect": 3, "partner": 2, "candidate": 2, "advisor": 2, "vendor": 1, "team": 1},
    "first_customers": {"prospect": 5, "customer": 5, "partner": 3, "investor_active": 3, "investor_prospect": 2, "advisor": 2, "candidate": 1, "vendor": 1, "team": 1},
    "revenue": {"customer": 5, "prospect": 5, "partner": 3, "investor_active": 3, "investor_prospect": 2, "advisor": 2, "candidate": 1, "vendor": 1, "team": 1},
    "ship": {"customer": 4, "team": 4, "prospect": 3, "partner": 3, "investor_active": 3, "candidate": 2, "advisor": 2, "investor_prospect": 2, "vendor": 2},
    "hire": {"candidate": 5, "team": 4, "customer": 4, "investor_active": 3, "advisor": 3, "prospect": 3, "partner": 2, "investor_prospect": 2, "vendor": 1},
}

LOOP = {"owed_deliverable": 1.0, "owed_reply": 0.9, "meeting_followup": 0.8, "awaiting_them": 0.5}

# (max hours until deadline, weight); overdue = 1.0, no deadline = 0.1
DEADLINE_BUCKETS = [(6, 0.9), (24, 0.7), (72, 0.4)]
OVERDUE = 1.0
NO_DEADLINE = 0.1
LATENESS_FALLBACK_H = 48

EFFORT = [(5, 1.0), (15, 1.3)]  # anything above 15 min = 1.7
EFFORT_MAX = 1.7

SOFT_SOURCE_MULT = 0.5  # market + playbook
FLOOR = 0.05
HYSTERESIS = 1.2
TOP_N = 5
HALF_LIFE_DAYS = {"pricing": 7, "launch": 14, "funding": 30}

# Adjustment vs the spec's example table (see DIAGNOSTIC.md): customer under goal=raise is 5, not 4.

# SD24041_Lab3.py  -  Scholarship Advisory Rule-Based System (Streamlit)
# BSD3513 Introduction to Artificial Intelligence - Lab Report 3
import json
import operator
from typing import Any, Dict, List, Tuple

import streamlit as st

# ----------------------------
# 1) Minimal rule engine
# ----------------------------
# A rule has the shape:
# {
#   "name": "Top merit candidate",
#   "priority": 100,                 # higher priority wins when several rules fire
#   "conditions": [                  # ALL conditions must be true (AND)
#       ["cgpa", ">=", 3.7],
#       ["disciplinary_actions", "==", 0]
#   ],
#   "action": {"decision": "AWARD_FULL", "reason": "..."}
# }

OPS = {
    "==": operator.eq,
    "!=": operator.ne,
    ">": operator.gt,
    ">=": operator.ge,
    "<": operator.lt,
    "<=": operator.le,
    "in": lambda a, b: a in b,
    "not_in": lambda a, b: a not in b,
}

# The EXACT rules required by the lab question.
DEFAULT_RULES: List[Dict[str, Any]] = [
    {
        "name": "Top merit candidate",
        "priority": 100,
        "conditions": [
            ["cgpa", ">=", 3.7],
            ["co_curricular_score", ">=", 80],
            ["family_income", "<=", 8000],
            ["disciplinary_actions", "==", 0],
        ],
        "action": {
            "decision": "AWARD_FULL",
            "reason": "Excellent academic & co-curricular performance, with acceptable need",
        },
    },
    {
        "name": "Good candidate - partial scholarship",
        "priority": 80,
        "conditions": [
            ["cgpa", ">=", 3.3],
            ["co_curricular_score", ">=", 60],
            ["family_income", "<=", 12000],
            ["disciplinary_actions", "<=", 1],
        ],
        "action": {
            "decision": "AWARD_PARTIAL",
            "reason": "Good academic & involvement record with moderate need",
        },
    },
    {
        "name": "Need-based review",
        "priority": 70,
        "conditions": [
            ["cgpa", ">=", 2.5],
            ["family_income", "<=", 4000],
        ],
        "action": {
            "decision": "REVIEW",
            "reason": "High need but borderline academic score",
        },
    },
    {
        "name": "Low CGPA – not eligible",
        "priority": 95,
        "conditions": [
            ["cgpa", "<", 2.5],
        ],
        "action": {
            "decision": "REJECT",
            "reason": "CGPA below minimum scholarship requirement",
        },
    },
    {
        "name": "Serious disciplinary record",
        "priority": 90,
        "conditions": [
            ["disciplinary_actions", ">=", 2],
        ],
        "action": {
            "decision": "REJECT",
            "reason": "Too many disciplinary records",
        },
    },
]


def evaluate_condition(facts: Dict[str, Any], cond: List[Any]) -> bool:
    """Evaluate a single condition of the form [field, operator, value]."""
    if not isinstance(cond, (list, tuple)) or len(cond) != 3:
        return False
    field, op, value = cond
    if field not in facts or op not in OPS:
        return False
    try:
        return bool(OPS[op](facts[field], value))
    except Exception:
        return False


def rule_matches(facts: Dict[str, Any], rule: Dict[str, Any]) -> bool:
    """A rule fires only if ALL its conditions are true (AND)."""
    conditions = rule.get("conditions", [])
    if not conditions:
        return False
    return all(evaluate_condition(facts, c) for c in conditions)


def run_rules(
    facts: Dict[str, Any], rules: List[Dict[str, Any]]
) -> Tuple[Dict[str, Any], List[Dict[str, Any]]]:
    """
    Returns (best_action, fired_rules).
    - fired_rules: every rule that matched, sorted by priority (highest first)
    - best_action: the action of the highest-priority fired rule (conflict resolution)
    - if nothing matches, the case is sent for manual REVIEW
    """
    fired = [r for r in rules if isinstance(r, dict) and rule_matches(facts, r)]
    if not fired:
        return {"decision": "REVIEW", "reason": "No rule matched - manual review required"}, []
    fired_sorted = sorted(fired, key=lambda r: r.get("priority", 0), reverse=True)
    best = fired_sorted[0].get("action", {"decision": "REVIEW", "reason": "No action defined"})
    return best, fired_sorted


def validate_rules(rules: Any) -> List[str]:
    """Return a list of problems found in a rules structure (empty list = OK)."""
    problems: List[str] = []
    if not isinstance(rules, list):
        return ["Rules must be a JSON array (list) of rule objects."]
    for i, r in enumerate(rules, start=1):
        if not isinstance(r, dict):
            problems.append(f"Rule #{i} is not an object.")
            continue
        for key in ("name", "priority", "conditions", "action"):
            if key not in r:
                problems.append(f"Rule #{i} is missing '{key}'.")
        if "conditions" in r and not isinstance(r["conditions"], list):
            problems.append(f"Rule #{i}: 'conditions' must be a list.")
        if isinstance(r.get("conditions"), list):
            for c in r["conditions"]:
                if not isinstance(c, list) or len(c) != 3:
                    problems.append(f"Rule #{i}: condition {c!r} must be [field, operator, value].")
                elif c[1] not in OPS:
                    problems.append(f"Rule #{i}: unknown operator {c[1]!r}.")
    return problems


# ----------------------------
# 2) Streamlit UI
# ----------------------------
DEFAULT_JSON = json.dumps(DEFAULT_RULES, indent=2, ensure_ascii=False)

# Quick sample applicants so the committee can demo the rules.
PRESETS = {
    "Custom (use sliders)": None,
    "Top merit student": dict(cgpa=3.85, income=5000, cocu=90, hours=60, sem=5, disc=0),
    "Good student (partial)": dict(cgpa=3.45, income=10000, cocu=70, hours=40, sem=4, disc=1),
    "Low-income, borderline CGPA": dict(cgpa=2.8, income=3000, cocu=40, hours=20, sem=3, disc=0),
    "Low CGPA": dict(cgpa=2.2, income=3000, cocu=85, hours=50, sem=6, disc=0),
    "Disciplinary record": dict(cgpa=3.9, income=4000, cocu=95, hours=80, sem=5, disc=2),
    "No rule matches": dict(cgpa=3.0, income=6000, cocu=50, hours=10, sem=2, disc=0),
}

st.set_page_config(page_title="Scholarship Advisory RBS", page_icon="\U0001F393", layout="wide")
st.title("Scholarship Advisory - Rule-Based System")
st.caption(
    "Decision-support demo for the scholarship committee. Enter applicant facts, "
    "edit the rules in JSON if needed, and see which rules fired and why."
)

if "rules_text" not in st.session_state:
    st.session_state["rules_text"] = DEFAULT_JSON


def _reset_rules() -> None:
    st.session_state["rules_text"] = DEFAULT_JSON


with st.sidebar:
    st.header("Applicant Facts")
    preset_name = st.selectbox("Load a sample applicant", list(PRESETS.keys()))
    p = PRESETS[preset_name] or dict(cgpa=3.00, income=5000, cocu=50, hours=20, sem=3, disc=0)

    # Key includes the preset so widgets refresh when a sample is chosen.
    k = preset_name
    cgpa = st.number_input("Cumulative GPA (CGPA)", 0.00, 4.00, float(p["cgpa"]), 0.01, key=f"cgpa_{k}")
    family_income = st.number_input("Monthly family income (MYR)", 0, 100000, int(p["income"]), 100, key=f"inc_{k}")
    co_curricular_score = st.slider("Co-curricular involvement score (0-100)", 0, 100, int(p["cocu"]), key=f"cocu_{k}")
    community_service_hours = st.number_input("Community service hours", 0, 1000, int(p["hours"]), 1, key=f"hrs_{k}")
    semester = st.number_input("Current semester of study", 1, 14, int(p["sem"]), 1, key=f"sem_{k}")
    disciplinary_actions = st.number_input("Disciplinary actions on record", 0, 20, int(p["disc"]), 1, key=f"disc_{k}")

    st.divider()
    st.header("Rules (JSON)")
    st.caption("Keep the defaults or edit the JSON array of rules.")
    st.text_area("Edit rules here", height=320, key="rules_text")
    st.button("Reset to default rules", on_click=_reset_rules)

    evaluate = st.button("Evaluate", type="primary")

facts = {
    "cgpa": float(cgpa),
    "family_income": float(family_income),
    "co_curricular_score": int(co_curricular_score),
    "community_service_hours": int(community_service_hours),
    "semester": int(semester),
    "disciplinary_actions": int(disciplinary_actions),
}

st.subheader("Applicant Facts")
st.json(facts)

# Parse rules (fall back to defaults if invalid)
rules = DEFAULT_RULES
try:
    parsed = json.loads(st.session_state["rules_text"])
    problems = validate_rules(parsed)
    if problems:
        st.error("Invalid rules - using the default rules instead.\n\n- " + "\n- ".join(problems))
    else:
        rules = parsed
except json.JSONDecodeError as e:
    st.error(f"Invalid JSON - using the default rules instead. Details: {e}")

st.subheader("Active Rules")
with st.expander(f"Show rules ({len(rules)} loaded)", expanded=False):
    st.code(json.dumps(rules, indent=2, ensure_ascii=False), language="json")

st.divider()

if evaluate:
    action, fired = run_rules(facts, rules)

    col1, col2 = st.columns([1, 1])
    with col1:
        st.subheader("Decision")
        decision = action.get("decision", "REVIEW")
        reason = action.get("reason", "-")
        if decision == "AWARD_FULL":
            st.success(f"{decision} - {reason}")
        elif decision == "AWARD_PARTIAL":
            st.info(f"{decision} - {reason}")
        elif decision == "REJECT":
            st.error(f"{decision} - {reason}")
        else:
            st.warning(f"{decision} - {reason}")
        if len(fired) > 1:
            st.caption(
                f"{len(fired)} rules fired. The highest-priority rule "
                f"('{fired[0].get('name', '(unnamed)')}', priority {fired[0].get('priority', 0)}) decided the outcome."
            )

    with col2:
        st.subheader("Matched Rules (by priority)")
        if not fired:
            st.info("No rules matched - the case defaults to manual REVIEW.")
        else:
            for i, r in enumerate(fired, start=1):
                st.write(f"**{i}. {r.get('name', '(unnamed)')}** | priority={r.get('priority', 0)}")
                st.caption(f"Action: {r.get('action', {})}")
                with st.expander("Conditions"):
                    for cond in r.get("conditions", []):
                        st.code(str(cond))

    st.divider()
    st.caption("Decision-support demo only - final decisions rest with the scholarship committee.")
else:
    st.info("Set the applicant facts and click **Evaluate** to run the rules.")

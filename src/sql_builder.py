import re

# =============================================
# SQL Templates
# NOTE:
#   - Total experience dihitung di Python (query_executor),
#     bukan di SQL langsung → biar 1 sumber kebenaran saja.
#   - durasi_role masih mentah (bisa "3 months", "2 years", dst.)
#     → Python yang konversi ke bulan.
# =============================================

ROLE_SQL = """
SELECT r.employee_id,
       r.full_name,
       r.role,
       r.ready_technology
FROM public.autobot_dataset_talent_profile_role_tech r
WHERE 1=1
{role_clause}
{skill_clause}
{name_clause}
"""

PROJECT_SQL = """
SELECT employee_id,
       nama_lengkap,
       nama_project,
       porject_description AS project_description,
       durasi_role   -- raw duration text, converted to months in Python
FROM public.autobot_dataset_talent_profile_project_experiences
WHERE 1=1
{proj_clause}
{name_clause}
"""

EDU_SQL = """
SELECT employee_id,
       degree,
       school,
       name AS major
FROM public.autobot_dataset_talent_profile_education
WHERE 1=1
{edu_clause}
{name_clause}
"""

TIMESHEET_SQL = """
SELECT employee_id,
       employee_name,
       project_or_client_name AS project_name,
       date AS start_date,
       date AS end_date
FROM public.autobot_dataset_talent_timesheet
WHERE 1=1
{ts_date_clause}
{ts_proj_clause}
{name_clause}
"""

# =============================================
# Clause Builder (PRD v17)
# - Role filter
# - Skills filter (role OR technology)
# - Education filter (preferred vs substitute)
# - Timesheet filter (date range, project name)
# - Name filter (disesuaikan per tabel agar aman)
# =============================================

def build_clauses(intent: dict):
    role_clause, skill_clause, role_params = build_role_clause(intent)
    proj_clause, proj_params = build_project_clause(intent)
    edu_clause, edu_params = build_edu_clause(intent)
    ts_date_clause, ts_proj_clause, ts_params = build_timesheet_clause(intent)

    # Name clauses per tabel (biar tidak undefined column)
    role_name_clause, role_name_params = build_name_clause(intent, "role")
    proj_name_clause, proj_name_params = build_name_clause(intent, "project")
    edu_name_clause, edu_name_params = build_name_clause(intent, "education")
    ts_name_clause, ts_name_params = build_name_clause(intent, "timesheet")

    return {
        "role": (role_clause, skill_clause, role_params + role_name_params, role_name_clause),
        "project": (proj_clause, proj_params + proj_name_params, proj_name_clause),
        "education": (edu_clause, edu_params + edu_name_params, edu_name_clause),
        "timesheet": (ts_date_clause, ts_proj_clause, ts_params + ts_name_params, ts_name_clause),
    }

# ---------------------------------------------
# Role Clause
# ---------------------------------------------
def build_role_clause(intent):
    clauses = []
    params = []

    # --- Role ---
    role = intent.get("role")
    if role:
        clauses.append("AND r.role ILIKE %s")
        params.append(f"%{role}%")

    # --- Skills (ready_technology OR role) ---
    must = intent.get("skills", {}).get("must_have", [])
    nice = intent.get("skills", {}).get("nice_to_have", [])
    all_terms = list(must) + list(nice)

    skill_clause = ""
    if all_terms:
        parts = []
        skill_params = []
        for s in all_terms:
            parts.append("(r.ready_technology ILIKE %s OR r.role ILIKE %s)")
            skill_params.extend([f"%{s}%", f"%{s}%"])
        skills_or = " OR ".join(parts)
        skill_clause = f" AND ({skills_or})"
        params.extend(skill_params)

    # ⛔ Tidak ada filter pengalaman di SQL
    return " ".join(clauses), skill_clause, params

# ---------------------------------------------
# Project Clause
# ---------------------------------------------
def build_project_clause(intent):
    clauses = []
    params = []

    must = intent.get("projects", {}).get("must_have", [])
    nice = intent.get("projects", {}).get("nice_to_have", [])
    all_proj = must + nice

    if all_proj:
        like_clauses = []
        for p in all_proj:
            like_clauses.append("(nama_project ILIKE %s OR porject_description ILIKE %s)")
            params.extend([f"%{p}%", f"%{p}%"])
        clauses.append("AND (" + " OR ".join(like_clauses) + ")")

    return " ".join(clauses), params

# ---------------------------------------------
# Education Clause
# ---------------------------------------------
def build_edu_clause(intent):
    clauses = []
    params = []

    edu = intent.get("education", {})
    pref = edu.get("preferred", {})
    sub = edu.get("substitute", {})

    # Preferred → pakai AND
    if pref.get("degree"):
        clauses.append("AND degree ILIKE %s")
        params.append(f"%{pref['degree']}%")
    if pref.get("school"):
        clauses.append("AND school ILIKE %s")
        params.append(f"%{pref['school']}%")

    # Substitute → pakai OR agar fleksibel
    if sub.get("degree"):
        clauses.append("OR degree ILIKE %s")
        params.append(f"%{sub['degree']}%")
    if sub.get("school"):
        clauses.append("OR school ILIKE %s")
        params.append(f"%{sub['school']}%")

    return " ".join(clauses), params

# ---------------------------------------------
# Timesheet Clause
# ---------------------------------------------
def build_timesheet_clause(intent):
    ts = intent.get("timesheet", {}) or {}
    date_clause = ""
    proj_clause = ""
    params = []

    start = ts.get("start_date")
    end = ts.get("end_date")
    proj = ts.get("project")

    if start:
        date_clause += " AND date >= %s"
        params.append(start)
    if end:
        date_clause += " AND date <= %s"
        params.append(end)

    if proj:
        proj_clause += " AND project_or_client_name ILIKE %s"
        params.append(f"%{proj}%")

    return date_clause, proj_clause, params

# ---------------------------------------------
# Name Clause (per tabel)
# ---------------------------------------------
def build_name_clause(intent, table: str):
    name = intent.get("name")
    if not name:
        return "", []

    if table == "role":
        return "AND r.full_name ILIKE %s", [f"%{name}%"]
    elif table == "project":
        return "AND nama_lengkap ILIKE %s", [f"%{name}%"]
    elif table == "education":
        return "AND name ILIKE %s", [f"%{name}%"]
    elif table == "timesheet":
        return "AND employee_name ILIKE %s", [f"%{name}%"]
    return "", []

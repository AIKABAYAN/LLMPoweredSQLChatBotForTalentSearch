import time
import re
from collections import defaultdict
from psycopg2.extras import RealDictCursor
from src.database import get_conn
from src.sql_builder import ROLE_SQL, PROJECT_SQL, EDU_SQL, TIMESHEET_SQL, build_clauses
from src.config import logger
from src.scoring import score_candidate  # ✅ scoring import


# =============================================
# Duration Parser (Project → Months)
# =============================================
def parse_duration_to_months(text: str) -> int:
    if not text:
        return 0
    text = str(text).lower()
    m = re.search(r"(\d+)", text)
    if not m:
        return 0
    val = int(m.group(1))
    if "month" in text:
        return val
    if "year" in text:
        return val * 12
    return val  # fallback → as months


# =============================================
# Query execution & merging
# =============================================

def resolve_employee_name(emp_id):
    try:
        with get_conn() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    "SELECT full_name FROM public.autobot_dataset_talent_profile_role_tech "
                    "WHERE employee_id=%s LIMIT 1",
                    (emp_id,),
                )
                row = cur.fetchone()
                if row and row[0]:
                    return row[0]
    except Exception:
        pass
    return None


def run_all_queries(intent: dict, session_id: str):
    clauses = build_clauses(intent)
    role_clause, skill_clause, role_params, name_clause = clauses["role"]
    proj_clause, proj_params, name_clause_p = clauses["project"]
    edu_clause, edu_params, name_clause_e = clauses["education"]
    ts_date_clause, ts_proj_clause, ts_params, name_clause_t = clauses["timesheet"]

    q_role = ROLE_SQL.format(
        role_clause=role_clause, skill_clause=skill_clause, name_clause=name_clause
    )
    q_proj = PROJECT_SQL.format(
        proj_clause=proj_clause, name_clause=name_clause_p
    )
    q_edu = EDU_SQL.format(
        edu_clause=edu_clause, name_clause=name_clause_e
    )
    q_ts = TIMESHEET_SQL.format(
        ts_date_clause=ts_date_clause, ts_proj_clause=ts_proj_clause, name_clause=name_clause_t
    )

    logger.debug(f"[{session_id}] SQL[roles]: {q_role} | params={role_params}")
    logger.debug(f"[{session_id}] SQL[projects]: {q_proj} | params={proj_params}")
    logger.debug(f"[{session_id}] SQL[education]: {q_edu} | params={edu_params}")
    logger.debug(f"[{session_id}] SQL[timesheet]: {q_ts} | params={ts_params}")

    with get_conn() as conn:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            t0 = time.perf_counter()

            # Roles
            cur.execute(q_role, role_params)
            role_rows = cur.fetchall()
            logger.info(f"[{session_id}] roles fetched: {len(role_rows)}")

            # Projects
            cur.execute(q_proj, proj_params)
            proj_rows = cur.fetchall()
            logger.info(f"[{session_id}] projects fetched: {len(proj_rows)}")

            # Education
            cur.execute(q_edu, edu_params)
            edu_rows = cur.fetchall()
            logger.info(f"[{session_id}] education fetched: {len(edu_rows)}")

            # Timesheet
            cur.execute(q_ts, ts_params)
            ts_rows = cur.fetchall()
            logger.info(f"[{session_id}] timesheet fetched: {len(ts_rows)}")

            t1 = time.perf_counter()

    # Grouping results by employee
    roles_by_emp = defaultdict(list)
    for r in role_rows:
        roles_by_emp[r["employee_id"]].append(r)

    proj_by_emp = defaultdict(list)
    for p in proj_rows:
        proj_by_emp[p["employee_id"]].append(p)

    edu_by_emp = defaultdict(list)
    for e in edu_rows:
        edu_by_emp[e["employee_id"]].append(e)

    ts_by_emp = defaultdict(list)
    for t in ts_rows:
        ts_by_emp[t["employee_id"]].append(t)

    # Collect unique employee IDs
    emp_ids = set(roles_by_emp.keys()) | set(proj_by_emp.keys()) | set(edu_by_emp.keys()) | set(ts_by_emp.keys())

    employees = []
    for emp_id in emp_ids:
        d = {
            "employee_id": emp_id,
            "roles": roles_by_emp.get(emp_id, []),
            "projects": proj_by_emp.get(emp_id, []),
            "education": edu_by_emp.get(emp_id, []),
            "timesheet": ts_by_emp.get(emp_id, []),
        }

        # Full name resolution
        name = None
        if d["roles"]:
            name = d["roles"][0].get("full_name")
        elif d["projects"]:
            name = d["projects"][0].get("nama_lengkap")
        elif d["timesheet"]:
            name = d["timesheet"][0].get("employee_name")
        if not name:
            name = resolve_employee_name(emp_id)
        d["full_name"] = name or f"EMP-{emp_id}"

        # =============================================
        # ✅ Compute total experience (months + years)
        # =============================================
        total_months = 0
        for p in d["projects"]:
            total_months += parse_duration_to_months(p.get("durasi_role"))
        d["total_experience_months"] = total_months
        d["total_experience_years"] = round(total_months / 12, 2)

        # ✅ Apply experience filter (bulan basis)
        exp_req = intent.get("experience", {})
        min_years = exp_req.get("min_years")
        max_years = exp_req.get("max_years")

        if min_years is not None:
            min_months = min_years * 12
            if d["total_experience_months"] < min_months:
                logger.debug(f"[{session_id}] Candidate {emp_id} excluded (exp {d['total_experience_months']} < {min_months} mo)")
                continue
        if max_years is not None:
            max_months = max_years * 12
            if d["total_experience_months"] > max_months:
                logger.debug(f"[{session_id}] Candidate {emp_id} excluded (exp {d['total_experience_months']} > {max_months} mo)")
                continue

        # ✅ Apply scoring
        score, breakdown, exclude = score_candidate(d, intent)
        if exclude:
            logger.debug(f"[{session_id}] Candidate {emp_id} excluded. Breakdown={breakdown}")
            continue

        d["score"] = score
        d["scoring_breakdown"] = breakdown
        employees.append(d)

        logger.debug(f"[{session_id}] Candidate {emp_id} scored={score}, breakdown={breakdown}")

    # ✅ Sort & apply limit
    employees.sort(key=lambda x: x.get("score", 0), reverse=True)
    primary = intent.get("limit", {}).get("primary", 3)
    backup = intent.get("limit", {}).get("backup", 2)
    employees = employees[: primary + backup]

    logger.info(f"[{session_id}] merged employees: {len(employees)} | SQL time={(t1 - t0):.2f}s")

    raw = {
        "roles": role_rows,
        "projects": proj_rows,
        "education": edu_rows,
        "timesheet": ts_rows,
    }
    return employees, raw, (t1 - t0)

import re

def score_candidate(emp: dict, intent: dict):
    score = 0
    breakdown = []
    exclude = False

    # ================= Skills =================
    skills = intent.get("skills", {})
    must_skills = [s.lower() for s in skills.get("must_have", [])]
    nice_skills = [s.lower() for s in skills.get("nice_to_have", [])]

    all_skills = []
    for r in emp.get("roles", []):
        for t in str(r.get("ready_technology") or "").split(","):
            if t.strip():
                all_skills.append(t.strip().lower())

    for ms in must_skills:
        if ms in all_skills:
            score += 5
            breakdown.append(f"Must skill {ms} +5")
        else:
            breakdown.append(f"Missing must skill {ms} → excluded")
            return 0, breakdown, True

    for ns in nice_skills:
        if ns in all_skills:
            score += 2
            breakdown.append(f"Nice skill {ns} +2")

    # ================= Projects =================
    must_proj = [p.lower() for p in intent.get("projects", {}).get("must_have", [])]
    nice_proj = [p.lower() for p in intent.get("projects", {}).get("nice_to_have", [])]

    proj_blob = " ".join([
        f"{p.get('nama_project','')} {p.get('project_description','')}".lower()
        for p in emp.get("projects", [])
    ])

    for mp in must_proj:
        if mp in proj_blob:
            score += 4
            breakdown.append(f"Must project {mp} +4")
        else:
            breakdown.append(f"Missing must project {mp} → excluded")
            return 0, breakdown, True

    for np in nice_proj:
        if np in proj_blob:
            score += 1
            breakdown.append(f"Nice project {np} +1")

    # ================= Experience (pakai bulan) =================
    months = compute_months_from_projects(emp.get("projects", []))

    # --- PRD v15: must_have / nice_to_have ---
    exp_rule = intent.get("experience", {}).get("must_have")
    if exp_rule:
        op = exp_rule.get("operator")
        val_years = exp_rule.get("years", 0)
        val_months = exp_rule.get("months", val_years * 12 if val_years else 0)
        if check_operator(months, op, val_months):
            score += 5
            breakdown.append(f"Must exp {op} {val_months//12} years ({val_months} mo) satisfied +5")
        else:
            breakdown.append(f"Missing must exp {op} {val_months//12} years ({val_months} mo) → excluded")
            return 0, breakdown, True

    nice_exp = intent.get("experience", {}).get("nice_to_have")
    if nice_exp:
        op = nice_exp.get("operator")
        val_years = nice_exp.get("years", 0)
        val_months = nice_exp.get("months", val_years * 12 if val_years else 0)
        if check_operator(months, op, val_months):
            score += 2
            breakdown.append(f"Nice exp {op} {val_months//12} years ({val_months} mo) satisfied +2")

    # --- PRD v16: min/max ---
    exp_req = intent.get("experience", {})
    min_years = exp_req.get("min_years")
    max_years = exp_req.get("max_years")
    min_months = exp_req.get("min_months")
    max_months = exp_req.get("max_months")
    
    # Handle min experience requirement
    if min_years is not None:
        min_months = min_years * 12
    if min_months is not None:
        if months < min_months:
            breakdown.append(f"Experience {months} mo < {min_months} mo → excluded")
            return 0, breakdown, True
        else:
            score += 3
            breakdown.append(f"Experience ≥ {min_months//12} years ({min_months} mo) +3")
            
    # Handle max experience requirement
    if max_years is not None:
        max_months = max_years * 12
    if max_months is not None:
        if months > max_months:
            breakdown.append(f"Experience {months} mo > {max_months} mo → excluded")
            return 0, breakdown, True
        else:
            score += 2
            breakdown.append(f"Experience ≤ {max_months//12} years ({max_months} mo) +2")

    # ================= Education =================
    education_score = 0
    education_breakdown = []
    
    for e in emp.get("education", []):
        deg = (e.get("degree") or "").lower()
        school = (e.get("school") or "").lower()
        # Only give points for the highest relevant education
        if "d3" in deg and "polban" in school:
            if 3 > education_score:  # D3 Polban is worth more than S1
                education_score = 3
                education_breakdown = ["Education D3 Polban +3"]
        elif "s1" in deg:
            if 2 > education_score:  # S1 is worth 2 points
                education_score = 2
                education_breakdown = ["Education S1 +2"]
    
    score += education_score
    breakdown.extend(education_breakdown)

    return score, breakdown, exclude


def compute_months_from_projects(projects):
    months = 0
    for p in projects:
        dur = str(p.get("durasi_role") or "").lower()
        if not dur:
            continue
        m = re.search(r"(\d+)", dur)
        if not m:
            continue
        val = int(m.group(1))
        if "month" in dur:
            months += val
        elif "year" in dur:
            months += val * 12
        else:
            # fallback: assume already in months
            months += val
    return months


# ✅ Alias lama untuk compatibility
def compute_years_from_projects(projects):
    months = compute_months_from_projects(projects)
    return months / 12 if months else 0


def check_operator(months: int, op: str, val_months: int) -> bool:
    if op == ">":
        return months > val_months
    elif op == ">=":
        return months >= val_months
    elif op == "<":
        return months < val_months
    elif op == "<=":
        return months <= val_months
    elif op == "=":
        return months == val_months
    return False

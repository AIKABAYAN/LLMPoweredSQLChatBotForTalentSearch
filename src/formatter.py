

def build_must_nice_sections(emp: dict, intent: dict):
    skills = intent.get("skills", {})
    must = skills.get("must_have", [])
    nice = skills.get("nice_to_have", [])

    tech_blob = " | ".join([str(r.get("ready_technology") or "") for r in emp["roles"]]).lower()
    proj_blob = " | ".join([f"{p.get('nama_project','')} {p.get('project_description','')}" for p in emp["projects"]]).lower()

    must_lines = []
    for m in must:
        ml = m.lower()
        if ml in tech_blob or ml in proj_blob:
            must_lines.append(f"- {m}")
    nice_lines = []
    for n in nice:
        nl = n.lower()
        if nl in tech_blob or nl in proj_blob:
            nice_lines.append(f"- {n}")
    return must_lines, nice_lines


def format_employee_summary(emp: dict, intent: dict) -> str:
    name = emp.get("full_name", f"EMP-{emp['employee_id']}")
    role_level = ""
    if emp["roles"]:
        r0 = emp["roles"][0]
        role_level = f"{r0.get('role','').strip()} {r0.get('level','').strip()}".strip()
    techs = ", ".join(sorted({
        t.strip()
        for r in emp["roles"]
        for t in str(r.get("ready_technology") or "").split(",")
        if t.strip()
    }))

    # ✅ Use pre-calculated total project duration in years
    years = emp.get("total_experience_years", 0)

    must_lines, nice_lines = build_must_nice_sections(emp, intent)

    # =========================================
    # Deduplication for Projects
    # =========================================
    proj_seen = set()
    proj_lines = []
    for p in emp["projects"]:
        nama = (p.get("nama_project") or "").strip()
        client = (p.get("nama_client") or "").strip()
        role = (p.get("project_role") or "").strip()
        durasi = str(p.get("durasi_role") or 0).strip()
        key = f"{nama.lower()}|{client.lower()}|{role.lower()}|{durasi}"
        if key in proj_seen:
            continue
        proj_seen.add(key)
        proj_lines.append(
            f"- {nama} (Client: {client}, Role: {role}, Duration: {durasi} months)"
        )

    # =========================================
    # Deduplication for Education (include major)
    # =========================================
    edu_seen = set()
    edu_lines = []
    for e in emp["education"]:
        degree = (e.get("degree") or "").strip()
        school = (e.get("school") or "").strip()
        grad = str(e.get("graduation") or "").strip()
        major = (e.get("major") or "").strip()
        key = f"{degree.lower()}|{school.lower()}|{grad}|{major.lower()}"
        if key in edu_seen:
            continue
        edu_seen.add(key)
        edu_lines.append(f"- {degree} {school}, Major: {major}, Graduation {grad}")

    # =========================================
    # Deduplication for Timesheet
    # (limited to 8 recent entries, but no duplicates)
    # =========================================
    ts_seen = set()
    ts_lines = []
    for t in emp["timesheet"][:8]:
        date = str(t.get("date") or "")[:10]
        task = (t.get("task") or "").strip()
        proj = (t.get("project_or_client_name") or "").strip()
        key = f"{date}|{task.lower()}|{proj.lower()}"
        if key in ts_seen:
            continue
        ts_seen.add(key)
        ts_lines.append(f"- {date}: {task} ({proj})")

    # =========================================
    # Build output
    # =========================================
    parts = [
        f"Name: {name}",
        f"Role/Level: {role_level}" if role_level else "Role/Level: (not specified)",
        f"Technologies: {techs}" if techs else "Technologies: (not specified)",
        f"Total Project Duration: {years:.1f} years",
        "",
    ]
    if must_lines:
        parts.append("[MUST HAVE]"); parts.extend(must_lines); parts.append("")
    if nice_lines:
        parts.append("[NICE TO HAVE]"); parts.extend(nice_lines); parts.append("")
    parts.append("Projects:"); parts.extend(proj_lines or ["- (none)"]); parts.append("")
    parts.append("Education:"); parts.extend(edu_lines or ["- (none)"]); parts.append("")
    parts.append("Recent Activity:"); parts.extend(ts_lines or ["- (none)"]); parts.append("----------------------------------------")
    return "\n".join(parts)


def format_bucketed_sentences(sorted_emps):
    lines = []
    for emp, score in sorted_emps:
        name = emp.get("full_name", f"EMP-{emp['employee_id']}")
        role = emp["roles"][0].get("role") if emp["roles"] else ""
        techs = " ".join(sorted({
            t.strip()
            for r in emp["roles"]
            for t in str(r.get("ready_technology") or "").split(",")
            if t.strip()
        }))
        years = emp.get("total_experience_years", 0)
        lines.append(f"{name} {role or ''} {techs or ''} {years:.1f} years.")
    return "\n".join(lines)

import re
import json
from typing import Tuple, Dict, Any
from src.config import logger

# Regex untuk deteksi pengalaman
EXPERIENCE_GT_RE = re.compile(r"(experience|exp)\s*[>]\s*(\d+)\s*(years?|year)?", re.I)
EXPERIENCE_GTE_RE = re.compile(r"(experience|exp)\s*(>=|≥)\s*(\d+)\s*(years?|year)?", re.I)
EXPERIENCE_LT_RE = re.compile(r"(experience|exp)\s*[<]\s*(\d+)\s*(years?|year)?", re.I)
EXPERIENCE_LTE_RE = re.compile(r"(experience|exp)\s*(<=|≤)\s*(\d+)\s*(years?|year)?", re.I)

def _only_name_query(txt: str) -> bool:
    """Deteksi kalau prompt hanya berisi nama (misalnya 'Dedi' atau 'Dedi Saputra')."""
    t = txt.strip().strip('"').strip("'")
    if len(t.split()) <= 3:
        if not re.search(r"(experience|exp|role|project|degree|school|timesheet|date|between|and|or|,|:|;|>|<|>=|<=)", t, re.I):
            return True
    return False

def _extract_experience(txt: str) -> Dict[str, int]:
    """Ekstrak pengalaman dari teks. Semua dikonversi ke bulan."""
    exp = {}
    m = EXPERIENCE_GTE_RE.search(txt)
    if m:
        years = int(m.group(3))
        exp["min_months"] = years * 12
    m = EXPERIENCE_GT_RE.search(txt)
    if m:
        years = int(m.group(2))
        exp["min_months"] = years * 12
    m = EXPERIENCE_LTE_RE.search(txt)
    if m:
        years = int(m.group(3))
        exp["max_months"] = years * 12
    m = EXPERIENCE_LT_RE.search(txt)
    if m:
        years = int(m.group(2))
        exp["max_months"] = years * 12
    return exp

def _extract_role(txt: str) -> str:
    m = re.search(r"\btechnical\s+leader\b", txt, re.I)
    if m:
        return "Technical Leader"
    return ""

def _extract_skills(txt: str) -> Dict[str, list]:
    tokens = re.findall(r"[a-zA-Z][a-zA-Z\+\.\-# ]+", txt)
    tokens = [t.strip().lower() for t in tokens]
    common = {
        "recommend","me","with","and","or","nice","to","have","must","find",
        "experience","years","year","exp","please","need","looking","for",
        "role","project","education","school","degree","fresh","graduate",
        "between","start","end","date","from","until","timesheet"
    }
    whitelist = {"java","python","core banking","spring","spring boot","node","react","go","golang","kotlin"}
    txt_low = txt.lower()
    merged = set()
    if "core banking" in txt_low: merged.add("core banking")
    if "spring boot" in txt_low: merged.add("spring boot")

    for t in tokens:
        if t in common: continue
        if t in merged: continue
        if t == "technical leader": continue
        if t in whitelist or len(t) <= 12:
            merged.add(t)

    must = sorted(list(merged))
    return {"must_have": must, "nice_to_have": []}

def call_ollama_intent(user_query: str) -> Tuple[Dict[str, Any], str]:
    """
    Parse user query → intent.
    - Nama saja → {"name": "Dedi", "force_show": True}
    - Experience → min_months / max_months
    - Skills, role, timesheet juga diisi
    """
    txt = user_query.strip()

    # 1) Name-only
    if _only_name_query(txt):
        name = txt.strip().strip('"').strip("'")
        intent = {"name": name, "force_show": True}
        logger.info(f"[intent] name-only -> {intent}")
        return intent, txt

    # 2) Try LLM (skip for now, fallback heuristic)
    try:
        raise RuntimeError("Skip LLM for stability")
    except Exception as e:
        logger.error("LLM parsing failed, using heuristic. Error: %s", e)

    # 3) Heuristic fallback
    intent: Dict[str, Any] = {}

    # Role
    role = _extract_role(txt)
    if role:
        intent["role"] = role

    # Skills
    skills = _extract_skills(txt)
    if skills["must_have"] or skills["nice_to_have"]:
        intent["skills"] = skills

    # Experience (bulan)
    exp = _extract_experience(txt)
    if exp:
        intent["experience"] = exp

    # Timesheet date
    dates = re.findall(r"(\d{4}-\d{2}-\d{2})", txt)
    if len(dates) >= 1:
        intent.setdefault("timesheet", {})["start_date"] = dates[0]
    if len(dates) >= 2:
        intent.setdefault("timesheet", {})["end_date"] = dates[1]

    # Name inside query (e.g. name:"Dedi")
    m_name = re.search(r'name\s*:\s*"?([A-Za-z .\-]+)"?', txt, re.I)
    if m_name:
        intent["name"] = m_name.group(1).strip()

    # Default limit
    intent.setdefault("limit", {"primary": 3, "backup": 2})

    logger.info(f"[intent] heuristic -> {intent}")
    return intent, txt

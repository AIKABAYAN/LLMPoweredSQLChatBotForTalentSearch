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
    
    # Jika dimulai dengan angka diikuti kata seperti "talent", "person", "people", "orang", "sdm", dll
    # maka ini bukan name query, tapi permintaan jumlah kandidat
    if re.match(r"^\d+\s+(talent|person|people|kandidat|candidates?|orang|individual|sdm|resource|resources)", t, re.I):
        return False
        
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
    # Extract skills with capitalization logic:
    # - Capitalized first letter = must have
    # - Not capitalized = nice to have
    
    # Find all skill-like terms (words that could be skills)
    terms = re.findall(r"[A-Za-z][A-Za-z\+\.\-#]*", txt)
    
    whitelist = {"java","python","core banking","spring","spring boot","node","react","go","golang","kotlin"}
    
    # Normalization for common typos
    normalization = {
        "pyton": "python",
        "pyhton": "python",
        "javasript": "javascript",
        "js": "javascript",
        "nodejs": "node",
        "golang": "go"
    }
    
    must_skills = set()
    nice_skills = set()
    
    common = {
        "recommend","me","with","and","or","nice","to","have","must","find",
        "experience","years","year","exp","please","need","looking","for",
        "role","project","education","school","degree","fresh","graduate",
        "between","start","end","date","from","until","timesheet"
    }
    
    for term in terms:
        # Skip common words
        if term.lower() in common:
            continue
            
        # Check if first letter is capitalized
        is_capitalized = term[0].isupper() if term else False
        
        # Normalize the term (convert to lowercase for lookup)
        normalized = normalization.get(term.lower(), term.lower())
        
        # Only consider whitelisted skills
        if normalized in whitelist:
            if is_capitalized:
                must_skills.add(normalized)
            else:
                nice_skills.add(normalized)
    
    # If no capitalized skills, treat all as must_have (backward compatibility)
    if not must_skills and nice_skills:
        must_skills = nice_skills
        nice_skills = set()
    
    return {
        "must_have": sorted(list(must_skills)), 
        "nice_to_have": sorted(list(nice_skills))
    }

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

    # Check for quantity request (e.g., "5 talent python")
    quantity_match = re.match(r"^(\d+)\s+(?:talent|person|people|kandidat|candidates?|orang|individual|sdm|resource|resources)\b", txt, re.I)
    if quantity_match:
        quantity = int(quantity_match.group(1))
        # Remove the quantity part from the text for further processing
        txt = txt[quantity_match.end():].strip()
        intent.setdefault("limit", {})["primary"] = quantity
        intent.setdefault("limit", {})["backup"] = max(2, quantity // 2)

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

"""Pure heuristic filtering, ranking and deduplication. Edit blockers here."""
from dataclasses import replace
from datetime import datetime, timezone
import re
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

from .models import Job

BLOCKER_PATTERNS = [
    ("video_interview", r"\bvideo[ -](?:interview|call)s?\b"),
    ("loom", r"\bloom\b"),
    ("record_video", r"\brecord(?:ing)?\s+(?:(?:a|an|short|introductory|your)\s+)*video\b"),
    ("webcam", r"\bweb[ -]?cam\b"),
    ("camera_on", r"\bcamera[ -]on\b|\bturn\s+on\s+(?:your\s+)?camera\b"),
    ("in_person", r"\bin[ -]person\b"),
    ("id_documents", r"\b(?:id|identity|identification|document)\s+(?:documents?\s+)?(?:collection|verification|upload)\b|\b(?:upload|submit|provide|collect)\b.{0,50}\b(?:id|passport|identity documents?|identification|documents)\b"),
    ("notarized", r"\bnotari[sz](?:ed|ation)\b"),
    ("background_id", r"\bbackground check\b.{0,60}\b(?:id|upload|documents?)\b"),
]

COUNTRIES = r"(?:u\.?s\.?a?\.?|united states|canada|eu|europe(?:an union)?|uk|united kingdom)"
LOCATION_REJECT = [
    rf"\b{COUNTRIES}\s*[- ]only\b",
    rf"\b(?:must|required to|need to)\s+(?:be\s+)?(?:located|based|reside|live)\s+(?:in\s+)?(?:the\s+)?{COUNTRIES}\b",
    r"\b(?:authorized|authorised|authorization|eligible|right)\s+(?:to\s+)?work\s+in\s+(?:the\s+)?(?:us|usa|united states)\b",
    r"\b(?:on[ -]?site|hybrid(?!\s+(?:cloud|architecture|database|model)))\b",
    r"\b(?:full|complete|8[ -]hour)\s+overlap\b.{0,60}\b(?:us|usa|est|pst|cst|american|eastern|pacific)\b",
    r"\b(?:us|usa|est|pst|cst|american|eastern|pacific)\b.{0,60}\b(?:full|complete|8[ -]hour)\s+overlap\b",
    r"\b(?:emea|amer|namer|latam)\s*[- ]only\b",
    rf"\bremote\s*\(\s*{COUNTRIES}\s*\)",
    rf"\bremote\s*(?:\(|-\s*)(?:{COUNTRIES}|emea|amer|namer|latam|europe|uk|australia)\b",
]
LOCATION_OK = r"\b(?:worldwide|anywhere|global|apac|asia|vietnam|viet nam)\b"
FORUM_SOURCES = {"hn", "n8n", "make"}
# Country/region names seen in structured location fields. A field that names only places
# outside the accepted list means the employer restricts hiring to those places.
OTHER_COUNTRIES = (r"\b(?:germany|france|spain|portugal|italy|netherlands|belgium|austria|switzerland|poland|"
    r"hungary|romania|czechia|czech republic|slovakia|bulgaria|greece|croatia|serbia|ukraine|ireland|sweden|"
    r"norway|denmark|finland|estonia|latvia|lithuania|turkey|türkiye|israel|united arab emirates|uae|"
    r"saudi arabia|egypt|morocco|tunisia|algeria|south africa|nigeria|kenya|brazil|mexico|argentina|colombia|chile|peru|"
    r"india|pakistan|bangladesh|australia|new zealand|japan|south korea|china|singapore|malaysia|"
    r"indonesia|philippines|thailand|latam|latin america|emea|amer|namer|americas|north america|prague|boston)\b")


def positive_match(pattern, text):
    """Ignore simple explicit negations, without treating all prose as understood."""
    for match in re.finditer(pattern, text, re.I):
        before = text[max(0, match.start() - 50):match.start()]
        after = text[match.end():match.end() + 30]
        if re.search(r"\b(?:no|without|never|not|don't require|do not require|no need for)\s+(?:mandatory\s+|required\s+|any\s+)?$", before, re.I):
            continue
        if re.match(r"\s+(?:(?:is|are)\s+)?(?:not required|not necessary|optional)\b", after, re.I):
            continue
        return True
    return False


def location_fit(location: str, text: str = "") -> str:
    combined = (location + " " + text).lower()
    if any(positive_match(p, combined) for p in LOCATION_REJECT):
        return "reject"
    # Explicit geographic fields take precedence over generic remote prose.
    if re.search(LOCATION_OK, location, re.I):
        return "ok"
    offsets = re.findall(r"\b(?:utc|gmt)\s*([+-]\s*\d{1,2}(?:\.\d+)?)", location or text, re.I)
    if offsets:
        return "ok" if any(4 <= float(o.replace(" ", "")) <= 10 for o in offsets) else "reject"
    if re.search(rf"\b{COUNTRIES}\b", location, re.I) or re.search(OTHER_COUNTRIES, location, re.I):
        return "reject"
    if location.strip() and not re.fullmatch(r"(?:remote|unknown|not specified|n/a)[ .]*", location.strip(), re.I):
        return "unclear"
    if re.search(LOCATION_OK, combined) or re.search(r"\bremote\b", combined):
        return "ok"
    return "unclear"


def age_days(job: Job, now: datetime) -> float | None:
    if not job.posted_at:
        return None
    return (now - datetime.fromisoformat(job.posted_at.replace("Z", "+00:00"))).total_seconds() / 86400


def evaluate(job: Job, query=(), exclude=(), max_age_days=7, include_fulltime=False, now=None):
    now = now or datetime.now(timezone.utc)
    reasons, flags, rejected = [], list(job.flags), []
    text = " ".join((job.title, " ".join(job.tags), job.text or job.snippet)).lower()
    rejected.extend(name for name, pattern in BLOCKER_PATTERNS if positive_match(pattern, text))
    if query and not any(q.lower() in text for q in query):
        rejected.append("no_keyword_match")
    if any(q.lower() in text for q in exclude):
        rejected.append("excluded_keyword")
    allowed = {"contract", "part-time", "freelance"}
    if include_fulltime:
        allowed.add("full-time")
    # Forum posts (HN comments, Discourse topics) rarely state a type; most are gigs or contracts.
    if job.employment_type == "unknown" and job.source in FORUM_SOURCES:
        flags.append("employment_type_unclear")
    elif job.employment_type not in allowed:
        rejected.append("employment_type_" + job.employment_type)
    age = age_days(job, now)
    if age is None:
        flags.append("date_unclear")
    elif age > max_age_days:
        rejected.append("too_old")
    fit = location_fit(job.location_text, text)
    if fit == "reject":
        rejected.append("location_restricted")
    score = 20
    for q in dict.fromkeys(q.lower() for q in query):
        if q in job.title.lower():
            score += 20
            reasons.append("title_keyword: " + q)
        elif q in " ".join(job.tags).lower():
            score += 12
            reasons.append("tag_keyword: " + q)
        elif q in text:
            score += 5
            reasons.append("text_keyword: " + q)
    if job.employment_type in {"contract", "part-time", "freelance"}:
        score += 20
        reasons.append("flexible_employment")
    if fit == "ok":
        score += 20
        reasons.append("location_fit")
    elif fit == "unclear":
        score -= 15
        flags.append("location_unclear")
    if age is not None:
        score += round(15 * max(0, 1 - max(0, age) / max(max_age_days, 1)))
        reasons.append("freshness")
    years = re.findall(r"\b(\d+)\s*\+?\s*(?:years?|yrs?)\b", text)
    if any(int(n) > 3 for n in years) or re.search(r"\b(?:senior|staff|lead)\b", job.title, re.I):
        score -= 20
        flags.append("experience_over_3_years")
    return replace(job, score=max(0, min(100, score)), reasons=reasons,
                   flags=list(dict.fromkeys(flags))), rejected


def normalized_url(url):
    p = urlsplit(url)
    query = [(k, v) for k, v in parse_qsl(p.query) if not k.lower().startswith("utm_")]
    return urlunsplit((p.scheme.lower(), p.netloc.lower(), p.path.rstrip("/"), urlencode(sorted(query)), ""))


def dedupe(jobs):
    seen_urls, seen_names, result = set(), set(), []
    norm = lambda s: re.sub(r"[\W_]+", " ", s.casefold()).strip()
    for job in sorted(jobs, key=lambda j: j.score, reverse=True):
        url, key = normalized_url(job.url), (norm(job.company), norm(job.title))
        duplicate = (url and url in seen_urls) or (all(key) and key in seen_names)
        if url:
            seen_urls.add(url)
        if all(key):
            seen_names.add(key)
        if not duplicate:
            result.append(job)
    return result

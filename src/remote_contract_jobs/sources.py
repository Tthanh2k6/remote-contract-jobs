"""Public API and RSS adapters. Parsers never perform I/O."""
import json
import re
from urllib.parse import urlencode, quote
from xml.etree import ElementTree as ET

from .models import job, iso_date, plain, employment

SOURCES = {
    "himalayas": ("Himalayas", "https://himalayas.app", "Public jobs API; preserve source links."),
    "remotive": ("Remotive", "https://remotive.com", "Link back and name Remotive; do not republish to other job sites. Prefer at most four fetches per day."),
    "remoteok": ("Remote OK", "https://remoteok.com", "Link back and name Remote OK; do not use its logo without permission."),
    "wwr": ("We Work Remotely", "https://weworkremotely.com", "Public programming RSS; preserve source links."),
    "hn": ("Hacker News", "https://news.ycombinator.com", "Public Algolia API; link to original comments."),
    "n8n": ("n8n Community", "https://community.n8n.io", "Public Discourse jobs topics; preserve topic links."),
    "make": ("Make Community", "https://community.make.com", "Public Discourse Hire Help topics; preserve topic links."),
    "ashby": ("Ashby", "https://jobs.ashbyhq.com", "Public employer posting API; preserve employer job links."),
}
ATTRIBUTION = "Source attribution: Remotive (https://remotive.com), Remote OK (https://remoteok.com)."
DISCOURSE = {"n8n": "https://community.n8n.io/c/jobs/13.json", "make": "https://community.make.com/c/hire-a-pro/hire-help/74.json"}
WWR_CATEGORIES = ("remote-back-end-programming-jobs", "remote-front-end-programming-jobs", "remote-full-stack-programming-jobs")


def list_sources():
    return [dict(id=k, name=v[0], url=v[1], terms=v[2]) for k, v in SOURCES.items()]


def salary(row, low, high, currency="", period=""):
    values = [str(row[k]) for k in (low, high) if row.get(k)]
    return " ".join(filter(None, (currency or "", "–".join(values), period or ""))) if values else ""


def parse_himalayas(data):
    result = []
    for r in data["jobs"]:
        location = ", ".join(r.get("locationRestrictions") or [])
        offsets = r.get("timezoneRestrictions") or []
        if not location:
            if not offsets or len(offsets) >= 20:  # every time zone listed = no real restriction
                location = "Worldwide"
            else:
                location = ", ".join(f"UTC{o:+g}" for o in offsets)
        result.append(job("himalayas", r["title"], r.get("companyName", ""), r.get("guid") or r.get("applicationLink"),
            apply_url=r.get("applicationLink") or "", posted_at=iso_date(r.get("pubDate")),
            location_text=location, employment_type=r.get("employmentType", ""),
            tags=r.get("categories") or [], text=r.get("description") or r.get("excerpt", ""),
            salary_text=salary(r, "minSalary", "maxSalary", r.get("currency"), r.get("salaryPeriod"))))
    return result


def parse_remotive(data):
    return [job("remotive", r["title"], r.get("company_name", ""), r["url"],
                posted_at=iso_date(r.get("publication_date")), location_text=r.get("candidate_required_location") or "",
                employment_type=r.get("job_type", ""), tags=[t.get("name", "") if isinstance(t, dict) else str(t) for t in (r.get("tags") or [])],
                salary_text=r.get("salary") or "", text=r.get("description", "")) for r in data["jobs"]]


def parse_remoteok(data):
    return [job("remoteok", r["position"], r.get("company", ""), r["url"],
                apply_url=r.get("apply_url") or "", posted_at=iso_date(r.get("date") or r.get("epoch")),
                location_text=r.get("location") or "", tags=[t.get("name", "") if isinstance(t, dict) else str(t) for t in (r.get("tags") or [])],
                employment_type=r.get("employment_type") or " ".join(r.get("tags") or []) or r["position"],
                salary_text=salary(r, "salary_min", "salary_max"), text=r.get("description", ""))
            for r in data if "legal" not in r and "position" in r]


def parse_wwr(data):
    result = []
    for r in ET.fromstring(data).findall("./channel/item"):
        get = lambda key: r.findtext(key) or ""
        company, sep, title = get("title").partition(":")
        result.append(job("wwr", title.strip() if sep else company, company if sep else "", get("link"),
            posted_at=iso_date(get("pubDate")), location_text=get("country") or get("region"),
            employment_type=get("type"), tags=[s.strip() for s in get("skills").split(",") if s.strip()], text=get("description")))
    return result


def parse_discourse(data, source):
    return [job(source, r["title"], "", f"{SOURCES[source][1]}/t/{r['slug']}/{r['id']}",
                posted_at=iso_date(r.get("created_at")), tags=[t.get("name", "") if isinstance(t, dict) else str(t) for t in (r.get("tags") or [])],
                text=r.get("excerpt") or r["title"], flags=["description_incomplete"])
            for r in data["topic_list"]["topics"] if not r.get("pinned") and r.get("visible", True)]


def parse_ashby(data, board):
    return [job("ashby", r["title"], board, r["jobUrl"], apply_url=r.get("applyUrl") or "",
                posted_at=iso_date(r.get("publishedAt")), location_text=r.get("location") or ("Remote" if r.get("isRemote") else ""),
                employment_type=r.get("employmentType", ""), tags=[r[k] for k in ("department", "team") if r.get(k)],
                text=r.get("descriptionPlain") or r.get("descriptionHtml", ""),
                salary_text=(r.get("compensation") or {}).get("scrapeableCompensationSalarySummary") or "")
            for r in data["jobs"] if r.get("isListed", True)]


def hn_threads(data):
    result = []
    for phrase in ("who is hiring?", "freelancer? seeking freelancer?"):
        matches = [r for r in data["hits"] if phrase in r.get("title", "").lower()]
        if matches:
            result.append(max(matches, key=lambda r: r.get("created_at_i", 0)))
    return result


def parse_hn(data, story_id, freelancer=False):
    result = []
    for r in data["hits"]:
        text = plain(r.get("comment_text"))
        if str(r.get("parent_id")) != str(story_id) or not text:
            continue
        if freelancer and not text.upper().startswith("SEEKING FREELANCER"):
            continue
        # People looking for work sometimes post in the hiring thread; skip their posts.
        if not freelancer and (re.search(r"willing to relocate", text[:400], re.I)
                               or re.match(r"\s*(?:(?i:seeking work)|[Ii]'?m\s+[A-Z][a-z]+|[Ii] am\s+[A-Z][a-z]+)", text)):
            continue
        title = text[:120]
        kind = employment(text[:300])
        if freelancer and kind == "unknown":
            kind = "freelance"
        result.append(job("hn", title, "" if freelancer else text.split("|")[0][:80],
            f"https://news.ycombinator.com/item?id={r['objectID']}",
            posted_at=iso_date(r.get("created_at")), employment_type=kind, text=text))
    return result


def fetch_source(source, fetcher, query=(), boards=("supabase",)):
    """Yield records page by page; keep already yielded records on later errors.

    Bound broad feeds to five pages; HN comments use Algolia's reported pages.
    """
    get = lambda url: json.loads(fetcher.get(url))
    if source == "himalayas":
        for q in query or ("",):
            cursor = None
            for page in range(1, 6):
                params = {"q": q, "page": page} if q else {"limit": 100, **({"cursor": cursor} if cursor else {})}
                data = get("https://himalayas.app/jobs/api" + ("/search" if q else "") + "?" + urlencode(params))
                yield from parse_himalayas(data)
                if q:
                    if page * data.get("limit", 20) >= data.get("totalCount", 0):
                        break
                else:
                    next_cursor = data.get("nextCursor")
                    if not next_cursor or next_cursor == cursor:
                        break
                    cursor = next_cursor
    elif source == "remotive":
        # Fetch once; local any-keyword matching avoids repeated requests.
        yield from parse_remotive(get("https://remotive.com/api/remote-jobs?category=software-dev"))
    elif source == "remoteok":
        yield from parse_remoteok(get("https://remoteok.com/api"))
    elif source == "wwr":
        for category in WWR_CATEGORIES:
            yield from parse_wwr(fetcher.get(f"https://weworkremotely.com/categories/{category}.rss"))
    elif source in DISCOURSE:
        yield from parse_discourse(get(DISCOURSE[source]), source)
    elif source == "ashby":
        for board in boards:
            yield from parse_ashby(get(f"https://api.ashbyhq.com/posting-api/job-board/{quote(board, safe='')}?includeCompensation=true"), board)
    elif source == "hn":
        threads = []
        for phrase in ("Who is hiring?", "Freelancer? Seeking freelancer?"):
            params = urlencode({"tags": "story,author_whoishiring", "query": phrase, "hitsPerPage": 100})
            data = get("https://hn.algolia.com/api/v1/search_by_date?" + params)
            threads.extend(t for t in hn_threads(data) if phrase.lower() in t["title"].lower())
        for thread in threads:
            story_id = thread["objectID"]
            page = 0
            while True:
                params = urlencode({"tags": f"comment,story_{story_id}", "hitsPerPage": 100, "page": page})
                comments = get("https://hn.algolia.com/api/v1/search_by_date?" + params)
                yield from parse_hn(comments, story_id, "freelancer?" in thread["title"].lower())
                page += 1
                if page >= comments.get("nbPages", 1):
                    break
    else:
        raise ValueError(f"Unknown source: {source}")

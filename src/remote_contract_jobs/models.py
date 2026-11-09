"""Normalized records; full text stays private to the filtering pipeline."""
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from html.parser import HTMLParser
from html import unescape
import re


class _Text(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.parts = []
        self.hidden = 0

    def handle_starttag(self, tag, attrs):
        if tag in ("script", "style"):
            self.hidden += 1
        if tag in ("p", "br", "div", "li", "h1", "h2", "h3"):
            self.parts.append(" ")

    def handle_endtag(self, tag):
        if tag in ("script", "style"):
            self.hidden = max(0, self.hidden - 1)
        self.parts.append(" ")

    def handle_data(self, data):
        if not self.hidden:
            self.parts.append(data)


def plain(value) -> str:
    value = str(value or "")
    # Some feeds encode the entire HTML description as entities, twice.
    for _ in range(2):
        decoded = unescape(value)
        if decoded == value:
            break
        value = decoded
    parser = _Text()
    parser.feed(value)
    return re.sub(r"\s+", " ", "".join(parser.parts)).strip()


def iso_date(value) -> str:
    if value in (None, ""):
        return ""
    try:
        if isinstance(value, (int, float)):
            dt = datetime.fromtimestamp(value, timezone.utc)
        else:
            try:
                dt = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
            except ValueError:
                dt = parsedate_to_datetime(str(value))
        return dt.replace(tzinfo=dt.tzinfo or timezone.utc).astimezone(timezone.utc).isoformat().replace("+00:00", "Z")
    except (ValueError, TypeError, OverflowError, OSError):
        return ""


def employment(value: str) -> str:
    value = re.sub(r"[-_\s]", "", value.lower())
    for needle, result in (("parttime", "part-time"), ("freelanc", "freelance"), ("contract", "contract"), ("fulltime", "full-time")):
        if needle in value:
            return result
    return "unknown"


@dataclass
class Job:
    source: str
    title: str
    company: str
    url: str
    apply_url: str = ""
    posted_at: str = ""
    location_text: str = ""
    employment_type: str = "unknown"
    tags: list[str] = field(default_factory=list)
    salary_text: str = ""
    snippet: str = ""
    score: int = 0
    reasons: list[str] = field(default_factory=list)
    flags: list[str] = field(default_factory=list)
    text: str = field(default="", repr=False)

    def to_dict(self):
        result = asdict(self)
        result.pop("text")
        return result


def job(source, title, company, url, *, text="", employment_type="", **kwargs):
    text = plain(text)
    kind = employment(employment_type)
    if kind == "unknown":
        kind = employment(plain(title) + " " + text[:300])
    return Job(source, plain(title), plain(company), url or "", text=text,
               snippet=text[:400], employment_type=kind, **kwargs)

from dataclasses import replace
from datetime import datetime, timezone

import pytest

from remote_contract_jobs.filters import evaluate, location_fit, dedupe
from remote_contract_jobs.models import job, plain, iso_date

NOW = datetime(2026, 11, 9, tzinfo=timezone.utc)


def base(**kwargs):
    return replace(job("hn", "Python developer", "Acme", "https://example.org/job", text="Remote contract",
                       employment_type="contract", posted_at="2026-11-08T00:00:00Z"), **kwargs)


@pytest.mark.parametrize("text,reason", [
    ("Video interview required", "video_interview"), ("weekly video calls", "video_interview"),
    ("Send a Loom", "loom"), ("record a short video", "record_video"),
    ("webcam required", "webcam"), ("camera on", "camera_on"),
    ("in-person meeting", "in_person"), ("ID document collection", "id_documents"),
    ("Upload your passport", "id_documents"), ("notarized documents", "notarized"),
    ("background check with ID upload", "background_id"),
])
def test_blockers(text, reason):
    _, rejected = evaluate(base(text=text), now=NOW)
    assert reason in rejected


@pytest.mark.parametrize("text", ["No video interview", "Loom is not required", "No webcam required", "Camera on is optional", "No in-person meeting", "Build a video editor", "API documentation", "Background check"])
def test_non_blockers(text):
    _, rejected = evaluate(base(text=text), now=NOW)
    assert not rejected


@pytest.mark.parametrize("location,text,expected", [
    ("Worldwide", "", "ok"), ("Anywhere", "", "ok"), ("Global", "", "ok"),
    ("APAC/Asia", "", "ok"), ("Vietnam", "", "ok"), ("UTC+4", "", "ok"),
    ("UTC+10", "", "ok"), ("UTC+3", "", "reject"), ("Remote", "", "ok"),
    ("", "", "unclear"), ("Berlin", "", "unclear"),
    ("US only", "", "reject"), ("", "must be located in the US", "reject"),
    ("", "must be located in Canada", "reject"), ("", "must be located in the EU", "reject"),
    ("", "must be located in the UK", "reject"),
    ("Worldwide", "authorized to work in the US", "reject"),
    ("", "US time-zone requirement with full overlap", "reject"),
    ("", "Full overlap with Pacific hours", "reject"),
    ("", "on-site", "reject"), ("", "hybrid work", "reject"),
    ("Worldwide", "Our headquarters are in the US", "ok"),
    ("Remote", "No on-site requirement; hybrid cloud platform", "ok"),
    ("", "Remote (US)", "reject"),
])
def test_location(location, text, expected):
    assert location_fit(location, text) == expected


def test_age_employment_keywords():
    assert "too_old" in evaluate(base(posted_at="2026-11-01T00:00:00Z"), now=NOW)[1]
    assert not evaluate(base(posted_at="2026-11-02T00:00:00Z"), now=NOW)[1]
    assert evaluate(base(employment_type="full-time"), now=NOW)[1]
    assert not evaluate(base(employment_type="full-time"), include_fulltime=True, now=NOW)[1]
    assert evaluate(base(source="remotive", employment_type="unknown"), now=NOW)[1]
    kept, rejected = evaluate(base(employment_type="unknown"), now=NOW)  # forum post: keep, flag it
    assert not rejected and "employment_type_unclear" in kept.flags
    assert not evaluate(base(), query=["not present", "python"], now=NOW)[1]
    assert "excluded_keyword" in evaluate(base(), exclude=["python"], now=NOW)[1]
    assert "no_keyword_match" in evaluate(base(), query=["rust"], now=NOW)[1]
    assert "date_unclear" in evaluate(base(posted_at=""), now=NOW)[0].flags


def test_scoring_order_and_purity():
    original = base()
    title = evaluate(original, query=["python"], now=NOW)[0]
    tags = evaluate(base(title="Developer", tags=["python"]), query=["python"], now=NOW)[0]
    text = evaluate(base(title="Developer", text="Python remote contract"), query=["python"], now=NOW)[0]
    assert title.score > tags.score > text.score
    senior = evaluate(base(title="Senior Python developer", text="5+ years"), query=["python"], now=NOW)[0]
    assert senior.score < title.score
    assert evaluate(base(text="", snippet="", location_text=""), now=NOW)[0].score < evaluate(base(), now=NOW)[0].score
    assert evaluate(base(posted_at="2026-11-03T00:00:00Z"), now=NOW)[0].score < evaluate(base(), now=NOW)[0].score
    assert original.score == 0 and original.flags == []
    assert 0 <= evaluate(base(), query=["python", "developer", "contract", "remote"], now=NOW)[0].score <= 100


def test_dedupe():
    a = base(score=80)
    b = base(company="ACME!", title="python-developer", url="https://other.org", score=50)
    c = base(company="Other", title="Other", url="https://EXAMPLE.org/job/?utm_source=test", score=60)
    assert dedupe([b, c, a]) == [a]
    assert len(dedupe([base(company="", title=""), base(company="", title="", url="https://other.org")])) == 2


def test_plain_and_dates():
    assert plain("<p>Hello <b>world</b></p><script>bad</script>&amp; friends") == "Hello world & friends"
    assert iso_date("2026-11-09T07:00:00+07:00") == "2026-11-09T00:00:00Z"
    assert iso_date("bad") == ""


@pytest.mark.parametrize("location", ["Hungary", "Germany", "Brazil, Mexico", "LATAM", "EMEA", "Morocco"])
def test_structured_country_lists_outside_accepted_region_are_rejected(location):
    assert location_fit(location) == "reject"


@pytest.mark.parametrize("location", ["Vietnam, Germany", "Worldwide", "APAC"])
def test_lists_that_include_an_accepted_region_stay_ok(location):
    assert location_fit(location) == "ok"

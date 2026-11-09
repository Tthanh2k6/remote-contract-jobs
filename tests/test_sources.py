from dataclasses import asdict
import json
from urllib.parse import parse_qs, urlsplit

import pytest

from remote_contract_jobs import sources as s


@pytest.mark.parametrize("filename,parser,args,source", [
    ("himalayas.json", s.parse_himalayas, (), "himalayas"),
    ("himalayas_search.json", s.parse_himalayas, (), "himalayas"),
    ("remotive.json", s.parse_remotive, (), "remotive"),
    ("remoteok.json", s.parse_remoteok, (), "remoteok"),
    ("wwr_backend.rss", s.parse_wwr, (), "wwr"),
    ("n8n_jobs.json", s.parse_discourse, ("n8n",), "n8n"),
    ("make_hire_help.json", s.parse_discourse, ("make",), "make"),
    ("ashby_supabase.json", s.parse_ashby, ("supabase",), "ashby"),
    ("hn_freelancer_comments.json", s.parse_hn, (45438503,), "hn"),
])
def test_source_fixture(fixture_data, filename, parser, args, source):
    jobs = parser(fixture_data(filename), *args)
    assert jobs
    for job in jobs:
        assert job.source == source
        assert job.title and job.url.startswith("https://")
        assert job.posted_at.endswith("Z")
        assert len(job.snippet) <= 400
        assert "<p>" not in job.snippet
        assert "text" not in job.to_dict()
        json.dumps(job.to_dict())


def test_precise_fields(fixture_data):
    h = s.parse_himalayas(fixture_data("himalayas_search.json"))[0]
    assert h.company == "Huzzle" and h.employment_type == "contract"
    assert h.location_text == "Bosnia and Herzegovina"
    assert h.url != h.apply_url
    a = s.parse_ashby(fixture_data("ashby_supabase.json"), "supabase")[0]
    assert a.title == "AI Platform Engineer" and a.employment_type == "full-time"
    assert a.apply_url.endswith("/application")
    assert len(s.parse_remoteok(fixture_data("remoteok.json"))) == len(fixture_data("remoteok.json")) - 1


def test_hn_newest_and_top_level(fixture_data):
    threads = s.hn_threads(fixture_data("hn_threads.json"))
    assert [t["objectID"] for t in threads] == ["50338728"]
    assert s.hn_threads(fixture_data("hn_freelancer_thread.json"))[0]["objectID"] == "45438503"
    comments = fixture_data("hn_freelancer_comments.json")
    jobs = s.parse_hn(comments, 45438503)
    assert len(jobs) == 22
    assert not s.parse_hn(comments, 45438503, freelancer=True)
    # Fixture is a hiring thread despite its filename. Adapt copies to exercise freelancer rules.
    top = next(r.copy() for r in comments["hits"] if r["parent_id"] == 45438503)
    reply = next(r.copy() for r in comments["hits"] if r["parent_id"] != 45438503)
    top["comment_text"] = "<p>SEEKING FREELANCER | Python | Remote</p>"
    reply["comment_text"] = top["comment_text"]
    seeking_work = dict(top, objectID="other", comment_text="SEEKING WORK | Python")
    result = s.parse_hn({"hits": [top, reply, seeking_work]}, 45438503, True)
    assert len(result) == 1 and result[0].employment_type == "freelance"


def test_himalayas_pagination(fixture_data):
    class Fake:
        urls = []
        def get(self, url):
            self.urls.append(url)
            data = fixture_data("himalayas.json")
            if len(self.urls) == 2:
                data["nextCursor"] = None
            return json.dumps(data)
    fake = Fake()
    jobs = list(s.fetch_source("himalayas", fake))
    assert len(fake.urls) == 2 and len(jobs) == 16
    assert "cursor=" in fake.urls[1]


def test_hn_fetch_routes(fixture_data):
    class Fake:
        urls = []
        def get(self, url):
            self.urls.append(url)
            params = parse_qs(urlsplit(url).query)
            if "query" in params:
                return json.dumps(fixture_data("hn_threads.json"))
            data = fixture_data("hn_freelancer_comments.json")
            data["nbPages"] = 1
            return json.dumps(data)
    fake = Fake()
    assert list(s.fetch_source("hn", fake)) == []  # parent IDs belong to a different story
    assert len(fake.urls) == 3
    assert "Freelancer" in fake.urls[1]


def test_discourse_tags_as_objects_are_flattened():
    from remote_contract_jobs.sources import parse_discourse
    data = {"topic_list": {"topics": [{"id": 1, "slug": "x", "title": "[HIRING] n8n dev",
                                       "tags": [{"id": 3, "name": "hiring", "slug": "hiring"}], "created_at": "2026-11-08T00:00:00Z"}]}}
    assert parse_discourse(data, "n8n")[0].tags == ["hiring"]


def test_himalayas_all_time_zones_means_worldwide():
    from remote_contract_jobs.sources import parse_himalayas
    data = {"jobs": [{"title": "Dev", "companyName": "A", "guid": "https://himalayas.app/x", "locationRestrictions": [],
                      "timezoneRestrictions": list(range(-11, 15)), "pubDate": 1794211212}]}
    assert parse_himalayas(data)[0].location_text == "Worldwide"


def test_hn_hiring_thread_skips_job_seeker_posts():
    from remote_contract_jobs.sources import parse_hn
    data = {"hits": [
        {"objectID": "1", "parent_id": 9, "created_at": "2026-11-05T00:00:00Z",
         "comment_text": "Location: Dorset, UK Remote: Yes Willing to relocate: No Technologies: Python"},
        {"objectID": "2", "parent_id": 9, "created_at": "2026-11-05T00:00:00Z",
         "comment_text": "I'm Sam, a full-stack engineer looking for work"},
        {"objectID": "3", "parent_id": 9, "created_at": "2026-11-05T00:00:00Z",
         "comment_text": "Acme | Python contractor | REMOTE (worldwide) | part-time"}]}
    assert [j.url[-1] for j in parse_hn(data, 9)] == ["3"]

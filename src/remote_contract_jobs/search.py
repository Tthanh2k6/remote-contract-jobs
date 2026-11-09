"""Shared CLI/MCP orchestration with source failure isolation."""
from .filters import dedupe, evaluate
from .network import Fetcher
from .sources import ATTRIBUTION, SOURCES, fetch_source


def search_jobs(query=(), exclude=(), sources=(), max_age_days=7, include_fulltime=False,
                min_score=40, limit=20, *, boards=("supabase",), no_cache=False,
                show_rejected=False, fetcher=None, now=None):
    if type(max_age_days) is not int or max_age_days < 0:
        raise ValueError("max_age_days must be a nonnegative integer")
    if type(limit) is not int or limit < 0 or type(min_score) is not int or not 0 <= min_score <= 100:
        raise ValueError("limit must be nonnegative and min_score must be between 0 and 100")
    for values in (query, exclude, sources, boards):
        if isinstance(values, str) or any(not isinstance(v, str) or not v.strip() for v in values):
            raise ValueError("Search lists must contain nonempty strings")
    selected = list(dict.fromkeys(sources or SOURCES))
    if set(selected) - SOURCES.keys():
        raise ValueError("Unknown sources: " + ", ".join(sorted(set(selected) - SOURCES.keys())))
    fetcher = fetcher or Fetcher(no_cache=no_cache)
    jobs, rejected, errors = [], [], []
    for source in selected:
        try:
            for raw in fetch_source(source, fetcher, query, boards):
                scored, failures = evaluate(raw, query, exclude, max_age_days, include_fulltime, now)
                if not failures and scored.score < min_score:
                    failures = ["below_min_score"]
                if failures:
                    if show_rejected:
                        rejected.append({**scored.to_dict(), "rejection_reasons": failures})
                else:
                    jobs.append(scored)
        except Exception as exc:
            errors.append({"source": source, "error": str(exc)})
    result = {"jobs": [j.to_dict() for j in dedupe(jobs)[:limit]], "source_errors": errors, "attribution": ATTRIBUTION}
    if show_rejected:
        result["rejected"] = rejected
    return result

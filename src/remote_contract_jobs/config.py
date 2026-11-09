"""Optional TOML defaults, with explicit arguments taking precedence."""
from pathlib import Path
try:
    import tomllib
except ImportError:  # Python 3.10
    import tomli as tomllib

DEFAULT_PATH = Path.home() / ".config" / "remote-contract-jobs" / "config.toml"


def load_config(path=None):
    target = Path(path) if path else DEFAULT_PATH
    if not target.exists() and path is None:
        return {}
    with target.open("rb") as stream:
        result = tomllib.load(stream)
    unknown = result.keys() - {"keywords", "excludes", "ashby_boards", "max_age_days"}
    if unknown:
        raise ValueError("Unknown config keys: " + ", ".join(sorted(unknown)))
    for key in ("keywords", "excludes", "ashby_boards"):
        if key in result and (not isinstance(result[key], list) or any(not isinstance(v, str) or not v.strip() for v in result[key])):
            raise ValueError(f"{key} must be a list of nonempty strings")
    if "max_age_days" in result and (type(result["max_age_days"]) is not int or result["max_age_days"] < 0):
        raise ValueError("max_age_days must be a nonnegative integer")
    return result

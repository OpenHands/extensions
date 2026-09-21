"""Choose one code-aware, currently available maintainer for a reviewed PR."""

from urllib.error import HTTPError
from urllib.parse import urlencode

_DECISIVE_REVIEW_STATES = {"APPROVED", "CHANGES_REQUESTED"}
_MAX_PATHS = 8
_COMMITS_PER_PATH = 10


class HandoffConfigurationError(ValueError):
    """The configured roster cannot produce a GitHub review request."""


def parse_maintainers(value):
    """Normalize a comma-separated catalog value or a JSON-style list."""
    if isinstance(value, str):
        value = value.split(",")
    result = []
    seen = set()
    for item in value or []:
        login = str(item).strip()
        key = login.lower()
        if login and key not in seen:
            seen.add(key)
            result.append(login)
    return result


def _standing_reviewers(reviews, head_sha):
    standing = {}
    for review in reviews:
        if review.get("commit_id") != head_sha:
            continue
        state = (review.get("state") or "").upper()
        login = (review.get("user") or {}).get("login", "").lower()
        if not login:
            continue
        if state == "DISMISSED":
            standing.pop(login, None)
        elif state in _DECISIVE_REVIEW_STATES:
            standing[login] = state
    return standing


def _path_scores(repository, pr_number, base_ref, candidates):
    scores = dict.fromkeys(candidates, 0)
    files = repository.gh_pages(f"/pulls/{pr_number}/files")[:_MAX_PATHS]
    for changed_file in files:
        path = changed_file.get("filename")
        if not path:
            continue
        query = urlencode(
            {"path": path, "sha": base_ref, "per_page": _COMMITS_PER_PATH}
        )
        commits = repository.gh("GET", f"/commits?{query}")
        for rank, commit in enumerate(commits[:_COMMITS_PER_PATH]):
            login = ((commit.get("author") or {}).get("login") or "").lower()
            if login in scores:
                scores[login] += _COMMITS_PER_PATH - rank
    return scores


def _open_review_load(repository, owner, owner_type, login):
    owner_qualifier = "org" if owner_type.lower() == "organization" else "user"
    response = repository.api(
        "GET",
        "/search/issues",
        params={
            "q": (
                f"is:pr is:open {owner_qualifier}:{owner} "
                f"review-requested:{login}"
            ),
            "per_page": 1,
        },
    )
    return int(response.get("total_count", 0))


def request_maintainer_review(repository, pr, maintainers):
    """Ensure one configured maintainer is reviewing *pr*.

    API failures propagate so the scanner can retry without clearing its trigger
    label. The return value is the existing or newly requested login.
    """
    roster = parse_maintainers(maintainers)
    if not roster:
        return None

    by_key = {login.lower(): login for login in roster}
    requested = {
        (item.get("login") or "").lower() for item in pr.get("requested_reviewers", [])
    }
    for login in roster:
        if login.lower() in requested:
            return login

    number = pr["number"]
    head_sha = pr["head"]["sha"]
    reviews = repository.gh_pages(f"/pulls/{number}/reviews")
    standing = _standing_reviewers(reviews, head_sha)
    for login in roster:
        if login.lower() in standing:
            return login

    author = ((pr.get("user") or {}).get("login") or "").lower()
    candidates = [key for key in by_key if key != author]
    if not candidates:
        raise HandoffConfigurationError(
            "No eligible maintainer remains after excluding the PR author"
        )

    base_ref = (pr.get("base") or {}).get("ref") or "main"
    scores = _path_scores(repository, number, base_ref, candidates)
    owner = repository.repository.split("/", 1)[0]
    owner_type = (
        (((pr.get("base") or {}).get("repo") or {}).get("owner") or {}).get("type")
        or "Organization"
    )
    loads = {
        login: _open_review_load(repository, owner, owner_type, by_key[login])
        for login in candidates
    }
    order = {login.lower(): index for index, login in enumerate(roster)}
    selected_key = min(
        candidates,
        key=lambda login: (-scores[login], loads[login], order[login]),
    )
    selected = by_key[selected_key]
    try:
        repository.gh(
            "POST",
            f"/pulls/{number}/requested_reviewers",
            {"reviewers": [selected]},
        )
    except HTTPError as exc:
        if exc.code == 422:
            raise HandoffConfigurationError(
                f"GitHub cannot assign configured maintainer @{selected}"
            ) from exc
        raise
    return selected

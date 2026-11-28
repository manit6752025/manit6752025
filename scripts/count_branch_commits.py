import base64
import json
import os
import shutil
import subprocess
import sys
import tempfile
import time
import urllib.request

OWNER = os.environ.get("STATS_OWNER", "manit6752025")
ORGS = [
    o.strip()
    for o in os.environ.get("STATS_EXTRA_ORGS", "NetCore-Technologies").split(",")
    if o.strip()
]
AUTHORS = [
    a.strip()
    for a in os.environ.get("STATS_AUTHORS", "manit6752025,Manit Arora").split(",")
    if a.strip()
]
TOKEN = os.environ.get("GITHUB_TOKEN", "")
CLONE_BASE = os.environ.get("CLONE_BASE", "https://github.com")
OUT = os.environ.get("STATS_BRANCH_JSON", "stats/branch_commits.json")
FORCE = os.environ.get("STATS_FORCE", "0") == "1"
API = "https://api.github.com"


def log(msg):
    print("branch-commits:", msg, file=sys.stderr)


def get(url):
    headers = {"User-Agent": "stats-bot", "Accept": "application/vnd.github+json"}
    if TOKEN:
        headers["Authorization"] = "Bearer " + TOKEN
    last = None
    for attempt in range(3):
        try:
            req = urllib.request.Request(url, headers=headers)
            with urllib.request.urlopen(req, timeout=25) as r:
                return json.loads(r.read().decode())
        except Exception as e:
            last = e
            time.sleep(2 * (attempt + 1))
    raise last


def paged(url):
    items = []
    sep = "&" if "?" in url else "?"
    for page in range(1, 11):
        batch = get(f"{url}{sep}per_page=100&page={page}")
        items += batch
        if len(batch) < 100:
            break
    return items


def list_repos():
    found = {}
    sources = [f"{API}/users/{OWNER}/repos?type=owner"]
    sources += [f"{API}/orgs/{o}/repos?type=all" for o in ORGS]
    for url in sources:
        try:
            for r in paged(url):
                found.setdefault(r["full_name"], r)
        except Exception as e:
            log(f"could not list {url}: {e}")
    if TOKEN:
        owners = {OWNER.lower()} | {o.lower() for o in ORGS}
        try:
            for r in paged(
                f"{API}/user/repos?affiliation=owner,organization_member&visibility=all"
            ):
                if r["owner"]["login"].lower() in owners:
                    found.setdefault(r["full_name"], r)
        except Exception as e:
            log(f"could not list private repos: {e}")
    return list(found.values())


def git_count(path, extra):
    cmd = ["git", "-C", path, "rev-list", "--all", "--no-merges", "--count"] + extra
    out = subprocess.run(cmd, check=True, capture_output=True, text=True, timeout=120)
    return int(out.stdout.strip() or 0)


def count_repo(full):
    tmp = tempfile.mkdtemp(prefix="axiom-count-")
    try:
        cmd = ["git"]
        if TOKEN:
            auth = base64.b64encode(f"x-access-token:{TOKEN}".encode()).decode()
            cmd += ["-c", f"http.extraHeader=Authorization: Basic {auth}"]
        cmd += [
            "clone",
            "--bare",
            "--quiet",
            "--filter=blob:none",
            f"{CLONE_BASE}/{full}.git",
            tmp,
        ]
        subprocess.run(cmd, check=True, capture_output=True, timeout=300)
        everything = git_count(tmp, [])
        authors = ["--regexp-ignore-case"] + [f"--author={a}" for a in AUTHORS]
        mine = git_count(tmp, authors)
        return {"all": everything, "mine": mine}
    except Exception:
        log(f"could not count {full}")
        return None
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def main():
    cache = {}
    try:
        with open(OUT, encoding="utf-8") as f:
            cache = json.load(f).get("repos", {})
    except Exception:
        pass

    repos = {}
    for r in list_repos():
        if r.get("fork"):
            continue
        full = r["full_name"]
        pushed = r.get("pushed_at") or ""
        old = cache.get(full)
        if old and old.get("pushed") == pushed and not FORCE:
            repos[full] = old
            continue
        result = count_repo(full)
        if result:
            repos[full] = {"pushed": pushed, **result}
        elif old:
            repos[full] = old

    totals = {}
    user_all = 0
    for full, info in repos.items():
        owner = full.split("/")[0]
        if owner.lower() == OWNER.lower():
            totals[owner] = totals.get(owner, 0) + info["mine"]
            user_all += info["mine"]
        else:
            totals[owner] = totals.get(owner, 0) + info["all"]
            user_all += info["all"]
    totals["__user_all__"] = user_all

    os.makedirs(os.path.dirname(OUT) or ".", exist_ok=True)
    with open(OUT, "w", encoding="utf-8") as f:
        json.dump({"totals": totals, "repos": repos}, f, indent=1, sort_keys=True)
    log(f"{len(repos)} repos, totals {totals}")


try:
    main()
except Exception as e:
    log(e)
    sys.exit(0)

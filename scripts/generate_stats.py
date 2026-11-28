import json
import math
import os
import sys
import time
import urllib.request
from html import escape

OWNER = os.environ.get("STATS_OWNER", "manit6752025")
KIND = os.environ.get("STATS_KIND", "user")
TOKEN = os.environ.get("GITHUB_TOKEN", "")
EXTRA_ORGS = [
    o.strip()
    for o in os.environ.get("STATS_EXTRA_ORGS", "NetCore-Technologies").split(",")
    if o.strip()
]
USER = os.environ.get("STATS_USER", "manit6752025")
MERGE_ALL = os.environ.get("STATS_MERGE_ALL", "1") == "1"
OUT = os.environ.get("STATS_OUT", "stats")
TITLE = os.environ.get(
    "STATS_TITLE", "Manit's GitHub Stats" if KIND == "user" else OWNER + " Stats"
)
CACHE = os.path.join(OUT, "cache.json")
API = "https://api.github.com"
PALETTE = ["#00D4FF", "#6C3BFF", "#3FA9FF", "#9B6BFF", "#00A6A6", "#B38CFF"]

DEFAULT = {
    "commits": 0,
    "stars": 0,
    "repos": 0,
    "followers": 0,
    "prs": 0,
    "merged": 0,
    "issues": 0,
    "forks": 0,
    "issues_open": 0,
    "total": 0,
    "current": 0,
    "longest": 0,
    "days": [0] * 30,
    "langs": [["Python", 100]],
}

CSS = """
text{font-family:'JetBrains Mono','Fira Code','Segoe UI',monospace}
.t{fill:#00D4FF;font-size:15px;font-weight:700}
.l{fill:#9AA0B4;font-size:11.5px}
.v{fill:#FFFFFF;font-size:14px;font-weight:700}
.big{fill:#FFFFFF;font-size:30px;font-weight:800}
.row{opacity:0;animation:in .7s ease-out forwards}
.pulse{animation:pulse 2.2s ease-in-out infinite}
.bar{transform-box:fill-box;transform-origin:left center;transform:scaleX(0);animation:grow 1.3s cubic-bezier(.2,.8,.2,1) forwards}
.spin{transform-box:fill-box;transform-origin:center;animation:spin 14s linear infinite}
.cur{animation:blink 1s steps(1) infinite}
.ring{stroke-dashoffset:var(--c);animation:ring 1.8s ease-out .4s forwards}
.lap{stroke-dasharray:30 70;animation:lap 5s linear infinite}
.scan{animation:scan 4s linear infinite}
.sw{animation:sweep 5s linear infinite}
.flame{transform-box:fill-box;transform-origin:center bottom;animation:flame 1.2s ease-in-out infinite}
.pop{opacity:0;transform-box:fill-box;transform-origin:center;animation:pop .6s cubic-bezier(.2,1.4,.4,1) forwards}
.draw{stroke-dasharray:1;stroke-dashoffset:1;animation:draw 2.5s ease-out .5s forwards}
@keyframes in{from{opacity:0;transform:translateX(-16px)}to{opacity:1;transform:translateX(0)}}
@keyframes pulse{0%,100%{opacity:.45}50%{opacity:1}}
@keyframes grow{to{transform:scaleX(1)}}
@keyframes spin{to{transform:rotate(360deg)}}
@keyframes blink{0%,49%{opacity:1}50%,100%{opacity:0}}
@keyframes ring{to{stroke-dashoffset:var(--o)}}
@keyframes lap{to{stroke-dashoffset:-100}}
@keyframes scan{from{transform:translateY(-4px)}to{transform:translateY(320px)}}
@keyframes sweep{from{transform:translateX(-140px)}to{transform:translateX(900px)}}
@keyframes float{0%{transform:translateY(0);opacity:0}15%{opacity:.9}100%{transform:translateY(-260px);opacity:0}}
@keyframes flame{0%,100%{transform:scale(1,1)}50%{transform:scale(1.12,.92)}}
@keyframes pop{from{opacity:0;transform:scale(.4)}to{opacity:1;transform:scale(1)}}
@keyframes draw{to{stroke-dashoffset:0}}
"""

DEFS = """<defs>
<linearGradient id="bg" x1="0" y1="0" x2="1" y2="1"><stop offset="0" stop-color="#090A0F"/><stop offset=".6" stop-color="#14213D"/><stop offset="1" stop-color="#241466"/></linearGradient>
<linearGradient id="ac" x1="0" y1="0" x2="1" y2="0"><stop offset="0" stop-color="#00D4FF"/><stop offset="1" stop-color="#6C3BFF"/></linearGradient>
<linearGradient id="sw" x1="0" y1="0" x2="1" y2="0"><stop offset="0" stop-color="#fff" stop-opacity="0"/><stop offset=".5" stop-color="#fff" stop-opacity=".08"/><stop offset="1" stop-color="#fff" stop-opacity="0"/></linearGradient>
<filter id="gl" x="-30%" y="-30%" width="160%" height="160%"><feGaussianBlur stdDeviation="2.5" result="b"/><feMerge><feMergeNode in="b"/><feMergeNode in="SourceGraphic"/></feMerge></filter>
</defs>"""


def log(e):
    print("stats warning:", e, getattr(e, "url", ""), file=sys.stderr)


def call(url, body=None):
    headers = {"User-Agent": "stats-bot", "Accept": "application/vnd.github+json"}
    if TOKEN:
        headers["Authorization"] = "Bearer " + TOKEN
    data = None
    if body is not None:
        data = json.dumps(body).encode()
        headers["Content-Type"] = "application/json"
    last = None
    for attempt in range(3):
        try:
            req = urllib.request.Request(url, data=data, headers=headers)
            with urllib.request.urlopen(req, timeout=25) as r:
                return json.loads(r.read().decode())
        except Exception as e:
            last = e
            time.sleep(2 * (attempt + 1))
    raise last


def load_cache():
    merged = dict(DEFAULT)
    try:
        with open(CACHE, encoding="utf-8") as f:
            merged.update(json.load(f))
    except Exception:
        pass
    return merged


def streaks(counts):
    longest = run = 0
    for n in counts:
        run = run + 1 if n > 0 else 0
        longest = max(longest, run)
    seq = list(counts)
    if seq and seq[-1] == 0:
        seq = seq[:-1]
    cur = 0
    for n in reversed(seq):
        if n > 0:
            cur += 1
        else:
            break
    return cur, longest


def paged(url):
    items = []
    sep = "&" if "?" in url else "?"
    for page in range(1, 11):
        batch = call(f"{url}{sep}per_page=100&page={page}")
        items += batch
        if len(batch) < 100:
            break
    return items


def day_key(ts):
    return time.strftime("%Y-%m-%d", time.gmtime(ts))


def commit_activity(full_name):
    url = f"{API}/repos/{full_name}/stats/commit_activity"
    headers = {"User-Agent": "stats-bot", "Accept": "application/vnd.github+json"}
    if TOKEN:
        headers["Authorization"] = "Bearer " + TOKEN
    for attempt in range(4):
        try:
            req = urllib.request.Request(url, headers=headers)
            with urllib.request.urlopen(req, timeout=25) as r:
                body = r.read().decode()
                if r.status == 204:
                    return []
                if r.status == 200 and body.strip():
                    return json.loads(body)
        except Exception as e:
            log(e)
            return None
        time.sleep(3 * (attempt + 1))
    return None


def activity_by_day(repos):
    cutoff = day_key(time.time() - 370 * 86400)
    series = {}
    done = 0
    for r in repos:
        if r.get("fork"):
            continue
        if (r.get("pushed_at") or "")[:10] < cutoff:
            continue
        weeks = commit_activity(r["full_name"])
        if weeks is None:
            continue
        done += 1
        for w in weeks:
            for i, n in enumerate(w.get("days", [])):
                if n:
                    k = day_key(w["week"] + i * 86400)
                    series[k] = series.get(k, 0) + n
    return series, done


def last_days(series, n=365):
    now = time.time()
    keys = [day_key(now - i * 86400) for i in range(n - 1, -1, -1)]
    return keys, [series.get(k, 0) for k in keys]


def my_commits(repos, who=None):
    total = 0
    mine = (who or OWNER).lower()
    for r in repos:
        if r.get("fork"):
            continue
        try:
            people = paged(f"{API}/repos/{r['full_name']}/contributors?anon=1")
        except Exception as e:
            log(e)
            continue
        own = r["owner"]["login"].lower() == mine
        for p in people:
            login = (p.get("login") or "").lower()
            if own:
                if login == mine or p.get("type") == "Anonymous":
                    total += p.get("contributions", 0)
            else:
                total += p.get("contributions", 0)
    return total


def user_calendar():
    try:
        q = "query($l:String!){user(login:$l){contributionsCollection{contributionCalendar{totalContributions weeks{contributionDays{contributionCount date}}}}}}"
        res = call(API + "/graphql", {"query": q, "variables": {"l": USER}})
        cal = res["data"]["user"]["contributionsCollection"]["contributionCalendar"]
        days = [
            (x["date"], x["contributionCount"])
            for w in cal["weeks"]
            for x in w["contributionDays"]
        ]
        return days, cal["totalContributions"]
    except Exception as e:
        log(e)
        return [], 0


def collect_repos():
    if KIND == "user":
        sources = [f"{API}/users/{OWNER}/repos?type=owner"]
        sources += [f"{API}/orgs/{o}/repos?type=all" for o in EXTRA_ORGS]
    else:
        sources = [f"{API}/orgs/{OWNER}/repos?type=all"]
    found = {}
    for url in sources:
        try:
            for r in paged(url):
                found.setdefault(r["full_name"], r)
        except Exception as e:
            log(e)
    if KIND == "user" and TOKEN:
        mine = {OWNER.lower()} | {o.lower() for o in EXTRA_ORGS}
        try:
            for r in paged(
                f"{API}/user/repos?affiliation=owner,organization_member&visibility=all"
            ):
                if r["owner"]["login"].lower() in mine:
                    found.setdefault(r["full_name"], r)
        except Exception as e:
            log(e)
    return list(found.values())


def refresh(d):
    path = "users" if KIND == "user" else "orgs"
    try:
        info = call(f"{API}/{path}/{OWNER}")
        d["followers"] = info.get("followers", d["followers"])
        if KIND == "user":
            for org in EXTRA_ORGS:
                try:
                    d["followers"] += call(f"{API}/orgs/{org}").get("followers", 0)
                except Exception as e:
                    log(e)
    except Exception as e:
        log(e)

    repos = []
    try:
        repos = collect_repos()
        if repos:
            d["repos"] = sum(1 for r in repos if not r.get("private"))
            d["stars"] = sum(r.get("stargazers_count", 0) for r in repos)
            d["forks"] = sum(r.get("forks_count", 0) for r in repos)
            d["issues_open"] = sum(r.get("open_issues_count", 0) for r in repos)
    except Exception as e:
        log(e)

    counts = {}
    own = sorted(
        (x for x in repos if not x.get("fork")),
        key=lambda x: -x.get("stargazers_count", 0),
    )
    for r in own[:40]:
        try:
            for k, v in call(r["languages_url"]).items():
                counts[k] = counts.get(k, 0) + v
        except Exception as e:
            log(e)
    if counts:
        total = sum(counts.values())
        top = sorted(counts.items(), key=lambda kv: -kv[1])[:6]
        d["langs"] = [[k, round(v * 100 / total, 1)] for k, v in top]

    if KIND != "user":
        total_commits = 0
        for r in repos:
            if r.get("fork"):
                continue
            try:
                people = paged(f"{API}/repos/{r['full_name']}/contributors?anon=1")
                total_commits += sum(p.get("contributions", 0) for p in people)
            except Exception as e:
                log(e)
        combined = 0
        everything = 0
        if MERGE_ALL:
            try:
                personal = paged(f"{API}/users/{USER}/repos?type=owner")
                combined = my_commits(personal + repos, USER)
            except Exception as e:
                log(e)
            try:
                res = call(f"{API}/search/commits?q=author:{USER}&per_page=1")
                combined = max(combined, res.get("total_count", 0))
            except Exception as e:
                log(e)
            everything = branch_total(True)
        d["commits"] = max(d["commits"], total_commits, combined, everything, branch_total())
        try:
            res = call(f"{API}/search/issues?q=org:{OWNER}+type:pr+is:merged&per_page=1")
            d["merged"] = max(d["merged"], res.get("total_count", 0))
        except Exception as e:
            log(e)
        if MERGE_ALL:
            try:
                res = call(f"{API}/search/issues?q=author:{USER}+type:pr+is:merged&per_page=1")
                d["merged"] = max(d["merged"], res.get("total_count", 0))
            except Exception as e:
                log(e)
        try:
            series, done = activity_by_day(repos)
            cal_days, cal_total = user_calendar() if MERGE_ALL else ([], 0)
            if cal_days:
                merged_days = []
                extra_total = 0
                for date, n in cal_days:
                    e = series.get(date, 0)
                    merged_days.append(max(n, e))
                    extra_total += max(0, e - n)
                d["total"] = cal_total + extra_total
                d["current"], d["longest"] = streaks(merged_days)
                d["days"] = merged_days[-30:]
            elif done:
                _, counts = last_days(series)
                d["total"] = sum(counts)
                d["current"], d["longest"] = streaks(counts)
                d["days"] = counts[-30:]
        except Exception as e:
            log(e)
        return

    try:
        res = call(f"{API}/search/commits?q=author:{OWNER}&per_page=1")
        d["commits"] = max(d["commits"], res.get("total_count", 0))
    except Exception as e:
        log(e)

    try:
        d["commits"] = max(d["commits"], my_commits(repos))
    except Exception as e:
        log(e)

    d["commits"] = max(d["commits"], branch_total())

    try:
        res = call(f"{API}/search/issues?q=author:{OWNER}+type:pr+is:merged&per_page=1")
        d["merged"] = max(d["merged"], res.get("total_count", 0))
    except Exception as e:
        log(e)

    try:
        q = "query($l:String!){user(login:$l){contributionsCollection{totalIssueContributions totalPullRequestContributions contributionCalendar{totalContributions weeks{contributionDays{contributionCount date}}}}}}"
        res = call(API + "/graphql", {"query": q, "variables": {"l": OWNER}})
        c = res["data"]["user"]["contributionsCollection"]
        cal = c["contributionCalendar"]
        cal_days = [
            (x["date"], x["contributionCount"])
            for w in cal["weeks"]
            for x in w["contributionDays"]
        ]
        d["prs"] = c["totalPullRequestContributions"]
        d["issues"] = c["totalIssueContributions"]
        extra = {}
        try:
            org_repos = [
                r for r in repos if r["owner"]["login"].lower() != OWNER.lower()
            ]
            extra, _ = activity_by_day(org_repos)
        except Exception as e:
            log(e)
        merged = []
        extra_total = 0
        for date, n in cal_days:
            e = extra.get(date, 0)
            merged.append(max(n, e))
            extra_total += max(0, e - n)
        d["total"] = cal["totalContributions"] + extra_total
        d["current"], d["longest"] = streaks(merged)
        d["days"] = merged[-30:]
    except Exception as e:
        log(e)


def branch_total(everything=False):
    path = os.environ.get("STATS_BRANCH_JSON", "stats/branch_commits.json")
    try:
        with open(path, encoding="utf-8") as f:
            totals = json.load(f).get("totals", {})
        key = "__user_all__" if (KIND == "user" or everything) else OWNER
        return int(totals.get(key, 0))
    except Exception:
        return 0


def fmt(n):
    try:
        return f"{int(n):,}"
    except Exception:
        return str(n)


def grade(sc):
    for g, t in (("S", 8000), ("A+", 3000), ("A", 1500), ("B+", 700), ("B", 300)):
        if sc >= t:
            return g
    return "C"


def score(d):
    if KIND == "org":
        return (
            d["stars"] * 8
            + d["forks"] * 4
            + d["followers"] * 4
            + d["repos"] * 10
        )
    return (
        d["commits"]
        + d["stars"] * 8
        + d["followers"] * 4
        + d["prs"] * 3
        + d["repos"] * 2
    )


def stat_rows(d):
    if KIND == "org":
        return [
            ("Public repos", d["repos"]),
            ("Stars earned", d["stars"]),
            ("Total commits", d["commits"]),
            ("Followers", d["followers"]),
            ("Merged PRs", d["merged"]),
            ("Open issues", d["issues_open"]),
        ]
    return [
        ("Total commits", d["commits"]),
        ("Stars earned", d["stars"]),
        ("Public repos", d["repos"]),
        ("Followers", d["followers"]),
        ("Merged PRs", d["merged"]),
        ("Issues (12 mo)", d["issues"]),
    ]


def head(text):
    x = 24 + len(text) * 9.2 + 4
    return (
        f'<text x="24" y="34" class="t">{escape(text)}</text>'
        f'<rect class="cur" x="{x:.0f}" y="21" width="8" height="15" fill="#00D4FF"/>'
    )


def frame(w, h, body):
    dots = "".join(
        f'<circle cx="{(i * 53 + 17) % w}" cy="{h - 4}" r="{1.2 + i % 3 * .6:.1f}" '
        f'fill="{PALETTE[i % 2]}" '
        f'style="animation:float {3 + i % 4}s linear {i * .45:.2f}s infinite"/>'
        for i in range(14)
    )
    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}" viewBox="0 0 {w} {h}">'
        f"<style>{CSS}</style>{DEFS}"
        f'<clipPath id="c"><rect width="{w}" height="{h}" rx="14"/></clipPath>'
        f'<rect x=".5" y=".5" width="{w - 1}" height="{h - 1}" rx="14" fill="url(#bg)"/>'
        f'<g clip-path="url(#c)">{dots}'
        f'<rect class="scan" x="0" y="0" width="{w}" height="2" fill="#00D4FF" opacity=".18"/>'
        f'<rect class="sw" x="0" y="0" width="140" height="{h}" fill="url(#sw)"/>'
        f"{body}</g>"
        f'<rect x=".5" y=".5" width="{w - 1}" height="{h - 1}" rx="14" fill="none" stroke="#6C3BFF" stroke-opacity=".4"/>'
        f'<rect class="lap" pathLength="100" x=".5" y=".5" width="{w - 1}" height="{h - 1}" rx="14" fill="none" stroke="url(#ac)" stroke-width="2" filter="url(#gl)"/>'
        f"</svg>"
    )


def stats_svg(d):
    rows = stat_rows(d)
    top = max([v for _, v in rows] + [1])
    out = head(TITLE)
    for i, (k, v) in enumerate(rows):
        y = 64 + i * 24
        wb = max(4, 176 * math.log10(v + 1) / math.log10(top + 1))
        dl = i * 0.12
        out += (
            f'<g class="row" style="animation-delay:{dl:.2f}s">'
            f'<text x="24" y="{y}" class="l">{escape(k)}</text>'
            f'<text x="220" y="{y}" class="v" text-anchor="end">{fmt(v)}</text>'
            f'<rect x="232" y="{y - 9}" width="176" height="8" rx="4" fill="#FFFFFF" fill-opacity=".06"/>'
            f'<rect class="bar" x="232" y="{y - 9}" width="{wb:.1f}" height="8" rx="4" fill="url(#ac)" style="animation-delay:{dl + 0.2:.2f}s"/>'
            f"</g>"
        )
    sc = score(d)
    frac = max(min(sc / 8000, 1), 0.05)
    c = 2 * math.pi * 50
    o = c * (1 - frac)
    out += (
        f'<g transform="translate(430,105)">'
        f'<circle r="50" fill="none" stroke="#FFFFFF" stroke-opacity=".06" stroke-width="8"/>'
        f'<circle class="ring" r="50" fill="none" stroke="url(#ac)" stroke-width="8" stroke-linecap="round" '
        f'stroke-dasharray="{c:.1f}" style="--c:{c:.1f};--o:{o:.1f};transform:rotate(-90deg);transform-box:fill-box;transform-origin:center"/>'
        f'<text y="-6" text-anchor="middle" class="l">RANK</text>'
        f'<text y="22" text-anchor="middle" class="big">{grade(sc)}</text>'
        f"</g>"
    )
    return frame(495, 210, out)


def langs_svg(d):
    langs = d["langs"]
    out = head("Most Used Languages")
    out += '<rect x="24" y="52" width="447" height="10" rx="5" fill="#FFFFFF" fill-opacity=".06"/>'
    out += '<g clip-path="url(#c)">'
    cum = 0.0
    for i, (name, pct) in enumerate(langs):
        wd = pct * 4.47
        out += (
            f'<rect x="{24 + cum * 4.47:.1f}" y="52" width="{wd:.1f}" height="10" '
            f'fill="{PALETTE[i % len(PALETTE)]}"/>'
        )
        cum += pct
    out += "</g>"
    for i, (name, pct) in enumerate(langs):
        x = 24 + (i % 2) * 225
        y = 100 + (i // 2) * 34
        out += (
            f'<g class="row" style="animation-delay:{i * 0.1:.2f}s">'
            f'<circle cx="{x + 6}" cy="{y - 4}" r="5" fill="{PALETTE[i % len(PALETTE)]}"/>'
            f'<text x="{x + 18}" y="{y}" class="l">{escape(str(name))}</text>'
            f'<text x="{x + 200}" y="{y}" class="v" text-anchor="end">{pct}%</text>'
            f"</g>"
        )
    return frame(495, 210, out)


def streak_svg(d):
    org = KIND == "org" and not MERGE_ALL
    out = head("Commit Streak" if org else "Contribution Streak")
    out += '<rect x="24" y="52" width="447" height="1" fill="#FFFFFF" fill-opacity=".06"/>'
    out += (
        f'<text x="24" y="88" class="big">{fmt(d["total"])}</text>'
        f'<text x="24" y="104" class="l">{"COMMITS (1 YR)" if org else "CONTRIBUTIONS"}</text>'
        f'<text x="200" y="88" class="big">{fmt(d["longest"])}</text>'
        f'<text x="200" y="104" class="l">LONGEST STREAK</text>'
    )
    frac = max(min(d["current"] / max(d["longest"], 1), 1), 0.06)
    c = 2 * math.pi * 36
    o = c * (1 - frac)
    out += (
        f'<g transform="translate(400,80)">'
        f'<circle r="36" fill="none" stroke="#FFFFFF" stroke-opacity=".06" stroke-width="6"/>'
        f'<circle class="ring" r="36" fill="none" stroke="url(#ac)" stroke-width="6" stroke-linecap="round" '
        f'stroke-dasharray="{c:.1f}" style="--c:{c:.1f};--o:{o:.1f};transform:rotate(-90deg);transform-box:fill-box;transform-origin:center"/>'
        f'<text y="0" text-anchor="middle" class="v">{fmt(d["current"])}</text>'
        f'<text y="14" text-anchor="middle" class="l" style="font-size:7px">CURRENT STREAK</text>'
        f"</g>"
    )
    days = d["days"] if len(d["days"]) > 1 else [0, 0]
    m = max(days + [1])
    step = 447 / (len(days) - 1)
    pts = " ".join(
        f"{24 + i * step:.1f},{192 - n / m * 34:.1f}" for i, n in enumerate(days)
    )
    out += (
        f'<polyline class="draw" points="{pts}" fill="none" stroke="url(#ac)" stroke-width="2" stroke-linejoin="round"/>'
    )
    return frame(495, 210, out)


def hexpts(cx, cy, r):
    return " ".join(
        f"{cx + r * math.cos(math.radians(60 * k - 30)):.1f},{cy + r * math.sin(math.radians(60 * k - 30)):.1f}"
        for k in range(6)
    )


def ach_svg(d):
    if KIND == "org":
        items = [
            ("REPOS", d["repos"]),
            ("STARS", d["stars"]),
            ("COMMITS", d["commits"]),
            ("FOLLOWERS", d["followers"]),
            ("MERGED", d["merged"]),
            ("ISSUES", d["issues_open"]),
        ]
    else:
        items = [
            ("COMMITS", d["commits"]),
            ("STARS", d["stars"]),
            ("REPOS", d["repos"]),
            ("FOLLOWERS", d["followers"]),
            ("STREAK", d["longest"]),
            ("MERGED", d["merged"]),
        ]
    out = head("Achievements")
    for i, (label, val) in enumerate(items):
        cx = 52 + i * 78
        cy = 110
        color = PALETTE[i % len(PALETTE)]
        out += (
            f'<g class="pop" style="animation-delay:{i * 0.1:.2f}s">'
            f'<polygon points="{hexpts(cx, cy, 26)}" fill="{color}" fill-opacity=".12" '
            f'stroke="{color}" stroke-opacity=".5" stroke-width="1.5"/>'
            f'<text x="{cx}" y="{cy + 2}" text-anchor="middle" class="v">{fmt(val)}</text>'
            f'<text x="{cx}" y="{cy + 42}" text-anchor="middle" class="l" style="font-size:8px">{label}</text>'
            f"</g>"
        )
    return frame(495, 210, out)


RANKS = ["SSS", "SS", "S", "AAA", "AA", "A", "B", "C"]
RANK_OPACITY = {
    "SSS": 1,
    "SS": 1,
    "S": 1,
    "AAA": 0.95,
    "AA": 0.9,
    "A": 0.85,
    "B": 0.7,
    "C": 0.55,
    "?": 0.4,
}
COUNT_STEPS = [20000, 10000, 5000, 2500, 1000, 500, 100, 1]
SMALL_STEPS = [500, 250, 100, 50, 25, 10, 3, 1]
PR_STEPS = [1000, 500, 250, 100, 50, 25, 10, 1]
REPO_STEPS = [100, 60, 40, 25, 15, 8, 3, 1]
STREAK_STEPS = [365, 200, 100, 60, 30, 14, 7, 2]
YEAR_STEPS = [5000, 3000, 2000, 1000, 500, 250, 100, 1]

USER_TROPHIES = [
    ("COMMITS", "commits", COUNT_STEPS),
    ("STARS", "stars", SMALL_STEPS),
    ("FOLLOWERS", "followers", SMALL_STEPS),
    ("MERGED PRS", "merged", PR_STEPS),
    ("ISSUES", "issues", SMALL_STEPS),
    ("REPOS", "repos", REPO_STEPS),
    ("STREAK", "longest", STREAK_STEPS),
    ("CONTRIBS", "total", YEAR_STEPS),
    ("PR ACTIVITY", "prs", PR_STEPS),
]
ORG_TROPHIES = [
    ("COMMITS", "commits", COUNT_STEPS),
    ("STARS", "stars", SMALL_STEPS),
    ("FOLLOWERS", "followers", SMALL_STEPS),
    ("MERGED PRS", "merged", PR_STEPS),
    ("REPOS", "repos", REPO_STEPS),
    ("FORKS", "forks", SMALL_STEPS),
    ("STREAK", "longest", STREAK_STEPS),
    ("CONTRIBS" if MERGE_ALL else "COMMITS 1Y", "total", YEAR_STEPS),
]


def rank_for(value, steps):
    for name, step in zip(RANKS, steps):
        if value >= step:
            return name
    return "?"


def cup(cx, y, color, label):
    return (
        f'<path d="M{cx - 15},{y} H{cx + 15} V{y + 10} C{cx + 15},{y + 22} {cx + 7},{y + 28} {cx},{y + 28} '
        f'C{cx - 7},{y + 28} {cx - 15},{y + 22} {cx - 15},{y + 10} Z" fill="{color}" fill-opacity=".16" '
        f'stroke="{color}" stroke-width="1.6" stroke-linejoin="round"/>'
        f'<path d="M{cx - 15},{y + 4} H{cx - 21} C{cx - 21},{y + 13} {cx - 18},{y + 16} {cx - 12},{y + 17}" '
        f'fill="none" stroke="{color}" stroke-width="1.6" stroke-linecap="round"/>'
        f'<path d="M{cx + 15},{y + 4} H{cx + 21} C{cx + 21},{y + 13} {cx + 18},{y + 16} {cx + 12},{y + 17}" '
        f'fill="none" stroke="{color}" stroke-width="1.6" stroke-linecap="round"/>'
        f'<rect x="{cx - 2}" y="{y + 28}" width="4" height="8" fill="{color}" fill-opacity=".7"/>'
        f'<rect x="{cx - 10}" y="{y + 36}" width="20" height="4" rx="1.5" fill="{color}"/>'
        f'<text x="{cx}" y="{y + 15}" text-anchor="middle" style="fill:{color};font-size:9px;font-weight:800">{label}</text>'
    )


def trophies_svg(d):
    items = USER_TROPHIES if KIND == "user" else ORG_TROPHIES
    w, h = 990, 172
    slot = (w - 48) / len(items)
    out = head("Trophies")
    for i, (label, key, steps) in enumerate(items):
        value = d.get(key, 0)
        name = rank_for(value, steps)
        color = PALETTE[i % len(PALETTE)] if name != "?" else "#4B5563"
        glow = ' filter="url(#gl)"' if name in ("SSS", "SS", "S") else ""
        cx = 24 + slot * (i + 0.5)
        out += (
            f'<g class="pop" style="animation-delay:{i * 0.08:.2f}s">'
            f'<g opacity="{RANK_OPACITY[name]}">'
            f"<g{glow}>{cup(round(cx), 58, color, name)}</g>"
            f'<text x="{cx:.0f}" y="122" text-anchor="middle" class="v">{fmt(value)}</text>'
            f'<text x="{cx:.0f}" y="140" text-anchor="middle" class="l" style="font-size:8.5px">{label}</text>'
            f"</g></g>"
        )
    return frame(w, h, out)


def write(name, svg):
    try:
        with open(os.path.join(OUT, name), "w", encoding="utf-8") as f:
            f.write(svg)
    except Exception as e:
        log(e)


def main():
    os.makedirs(OUT, exist_ok=True)
    d = load_cache()
    try:
        refresh(d)
    except Exception as e:
        log(e)
    try:
        with open(CACHE, "w", encoding="utf-8") as f:
            json.dump(d, f)
    except Exception as e:
        log(e)

    cards = {
        "stats.svg": stats_svg,
        "langs.svg": langs_svg,
        "streak.svg": streak_svg,
        "achievements.svg": ach_svg,
        "trophies.svg": trophies_svg,
    }

    for name, fn in cards.items():
        try:
            write(name, fn(d))
        except Exception as e:
            log(e)


try:
    main()
except Exception as e:
    log(e)
    sys.exit(0)

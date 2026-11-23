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
            try:
                people = paged(f"{API}/repos/{r['full_name']}/contributors?anon=1")
                total_commits += sum(p.get("contributions", 0) for p in people)
            except Exception as e:
                log(e)
        d["commits"] = max(d["commits"], total_commits)
        try:
            res = call(f"{API}/search/issues?q=org:{OWNER}+type:pr+is:merged&per_page=1")
            d["merged"] = max(d["merged"], res.get("total_count", 0))
        except Exception as e:
            log(e)
        return

    try:
        res = call(f"{API}/search/commits?q=author:{OWNER}&per_page=1")
        d["commits"] = max(d["commits"], res.get("total_count", 0))
    except Exception as e:
        log(e)

    try:
        res = call(f"{API}/search/issues?q=author:{OWNER}+type:pr+is:merged&per_page=1")
        d["merged"] = max(d["merged"], res.get("total_count", 0))
    except Exception as e:
        log(e)

    try:
        q = "query($l:String!){user(login:$l){contributionsCollection{totalIssueContributions totalPullRequestContributions contributionCalendar{totalContributions weeks{contributionDays{contributionCount}}}}}}"
        res = call(API + "/graphql", {"query": q, "variables": {"l": OWNER}})
        c = res["data"]["user"]["contributionsCollection"]
        cal = c["contributionCalendar"]
        days = [
            x["contributionCount"]
            for w in cal["weeks"]
            for x in w["contributionDays"]
        ]
        d["total"] = cal["totalContributions"]
        d["prs"] = c["totalPullRequestContributions"]
        d["issues"] = c["totalIssueContributions"]
        d["current"], d["longest"] = streaks(days)
        d["days"] = days[-30:]
    except Exception as e:
        log(e)


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
    out = head("Contribution Streak")
    out += '<rect x="24" y="52" width="447" height="1" fill="#FFFFFF" fill-opacity=".06"/>'
    out += (
        f'<text x="24" y="88" class="big">{fmt(d["total"])}</text>'
        f'<text x="24" y="104" class="l">CONTRIBUTIONS</text>'
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
        f"{24 + i * step:.1f},{184 - n / m * 26:.1f}" for i, n in enumerate(days)
    )
    out += (
        f'<polyline class="draw" points="{pts}" fill="none" stroke="url(#ac)" stroke-width="2" stroke-linejoin="round"/>'
    )
    return frame(495, 196, out)


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
        "achievements.svg": ach_svg,
    }
    if KIND == "user":
        cards["streak.svg"] = streak_svg

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

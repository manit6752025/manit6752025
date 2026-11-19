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
OUT = os.environ.get("STATS_OUT", "stats")
TITLE = os.environ.get("STATS_TITLE", "Manit's GitHub Stats" if KIND == "user" else OWNER + " Stats")
CACHE = os.path.join(OUT, "cache.json")
API = "https://api.github.com"
PALETTE = ["#00D4FF", "#6C3BFF", "#3FA9FF", "#9B6BFF", "#00A6A6", "#B38CFF"]

DEFAULT = {
    "commits": 0, "stars": 0, "repos": 0, "followers": 0, "prs": 0,
    "issues": 0, "forks": 0, "issues_open": 0, "total": 0,
    "current": 0, "longest": 0, "days": [0] * 30, "langs": [["Python", 100]],
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
    print("stats warning:", e, file=sys.stderr)


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


def refresh(d):
    path = "users" if KIND == "user" else "orgs"
    try:
        info = call(f"{API}/{path}/{OWNER}")
        d["repos"] = info.get("public_repos", d["repos"])
        d["followers"] = info.get("followers", d["followers"])
    except Exception as e:
        log(e)
    repos = []
    try:
        kind_q = "owner" if KIND == "user" else "public"
        for page in range(1, 6):
            batch = call(f"{API}/{path}/{OWNER}/repos?per_page=100&page={page}&type={kind_q}")
            repos += batch
            if len(batch) < 100:
                break
        d["stars"] = sum(r.get("stargazers_count", 0) for r in repos)
        d["forks"] = sum(r.get("forks_count", 0) for r in repos)
        d["issues_open"] = sum(r.get("open_issues_count", 0) for r in repos)
    except Exception as e:
        log(e)
    counts = {}
    for r in [x for x in repos if not x.get("fork")][:30]:
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
        return
    try:
        res = call(f"{API}/search/commits?q=author:{OWNER}&per_page=1")
        d["commits"] = max(d["commits"], res.get("total_count", 0))
    except Exception as e:
        log(e)
    try:
        q = "query($l:String!){user(login:$l){contributionsCollection{totalIssueContributions totalPullRequestContributions contributionCalendar{totalContributions weeks{contributionDays{contributionCount}}}}}}"
        res = call(API + "/graphql", {"query": q, "variables": {"l": OWNER}})
        c = res["data"]["user"]["contributionsCollection"]
        cal = c["contributionCalendar"]
        days = [x["contributionCount"] for w in cal["weeks"] for x in w["contributionDays"]]
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
        return d["stars"] * 8 + d["forks"] * 4 + d["followers"] * 4 + d["repos"] * 10
    return d["commits"] + d["stars"] * 8 + d["followers"] * 4 + d["prs"] * 3 + d["repos"] * 2


def stat_rows(d):
    if KIND == "org":
        return [("Public repos", d["repos"]), ("Stars earned", d["stars"]), ("Forks", d["forks"]),
                ("Followers", d["followers"]), ("Open issues", d["issues_open"]), ("Languages", len(d["langs"]))]
    return [("Total commits", d["commits"]), ("Stars earned", d["stars"]), ("Public repos", d["repos"]),
            ("Followers", d["followers"]), ("PRs (12 mo)", d["prs"]), ("Issues (12 mo)", d["issues"])]


def head(text):
    x = 24 + len(text) * 9.2 + 4
    return f'<text x="24" y="34" class="t">{escape(text)}</text><rect class="cur" x="{x:.0f}" y="21" width="8" height="15" fill="#00D4FF"/>'


def frame(w, h, body):
    dots = "".join(
        f'<circle cx="{(i * 53 + 17) % w}" cy="{h - 4}" r="{1.2 + i % 3 * .6:.1f}" fill="{PALETTE[i % 2]}" style="animation:float {3 + i % 4}s linear {i * .45:.2f}s infinite"/>'
        for i in range(14)
    )
    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}" viewBox="0 0 {w} {h}">'
        f'<style>{CSS}</style>{DEFS}'
        f'<clipPath id="c"><rect width="{w}" height="{h}" rx="14"/></clipPath>'
        f'<rect x=".5" y=".5" width="{w - 1}" height="{h - 1}" rx="14" fill="url(#bg)"/>'
        f'<g clip-path="url(#c)">{dots}'
        f'<rect class="scan" x="0" y="0" width="{w}" height="2" fill="#00D4FF" opacity=".18"/>'
        f'<rect class="sw" x="0" y="0" width="140" height="{h}" fill="url(#sw)"/>'
        f'{body}</g>'
        f'<rect x=".5" y=".5" width="{w - 1}" height="{h - 1}" rx="14" fill="none" stroke="#6C3BFF" stroke-opacity=".4"/>'
        f'<rect class="lap" pathLength="100" x=".5" y=".5" width="{w - 1}" height="{h - 1}" rx="14" fill="none" stroke="url(#ac)" stroke-width="2" filter="url(#gl)"/>'
        f'</svg>'
    )


def stats_svg(d):
    rows = stat_rows(d)
    top = max([v for _, v in rows] + [1])
    out = head(TITLE)
    for i, (k, v) in enumerate(rows):
        y = 64 + i * 24
        wb = max(4, 176 * math.log10(v + 1) / math.log10(top + 1))
        dl = i * .12
        out += (
            f'<g class="row" style="animation-delay:{dl:.2f}s">'
            f'<text x="24" y="{y}" class="l">{escape(k)}</text>'
            f'<text x="200" y="{y}" class="v" text-anchor="end">{fmt(v)}</text>'
            f'<rect x="24" y="{y + 5}" width="176" height="3" rx="1.5" fill="#14213D"/>'
            f'<rect class="bar" x="24" y="{y + 5}" width="{wb:.0f}" height="3" rx="1.5" fill="url(#ac)" style="animation-delay:{dl + .3:.2f}s"/>'
            f'</g>'
        )
    sc = score(d)
    frac = max(min(sc / 8000, 1), .05)
    c = 2 * math.pi * 50
    o = c * (1 - frac)
    out += (
        '<circle cx="385" cy="118" r="50" fill="none" stroke="#14213D" stroke-width="9"/>'
        f'<circle class="ring" cx="385" cy="118" r="50" fill="none" stroke="url(#ac)" stroke-width="9" stroke-linecap="round" transform="rotate(-90 385 118)" filter="url(#gl)" style="--c:{c:.1f};--o:{o:.1f};stroke-dasharray:{c:.1f}"/>'
        '<text x="385" y="104" class="l" text-anchor="middle">RANK</text>'
        f'<text x="385" y="134" class="big pulse" text-anchor="middle">{grade(sc)}</text>'
    )
    return frame(495, 210, out)


def langs_svg(d):
    langs = d["langs"]
    out = head("Most Used Languages")
    out += '<clipPath id="lb"><rect x="24" y="52" width="447" height="10" rx="5"/></clipPath>'
    out += '<rect x="24" y="52" width="447" height="10" rx="5" fill="#14213D"/><g clip-path="url(#lb)">'
    cum = 0.0
    for i, (name, pct) in enumerate(langs):
        wd = pct * 4.47
        out += f'<rect class="bar" x="{24 + cum * 4.47:.1f}" y="52" width="{wd:.1f}" height="10" fill="{PALETTE[i % 6]}" style="animation-delay:{i * .15:.2f}s"/>'
        cum += pct
    out += '</g>'
    for i, (name, pct) in enumerate(langs):
        x = 24 + (i % 2) * 225
        y = 100 + (i // 2) * 34
        out += (
            f'<g class="row" style="animation-delay:{.4 + i * .12:.2f}s">'
            f'<circle class="pulse" cx="{x + 5}" cy="{y - 4}" r="5" fill="{PALETTE[i % 6]}" style="animation-delay:{i * .3:.1f}s"/>'
            f'<text x="{x + 18}" y="{y}" class="v">{escape(str(name))}</text>'
            f'<text x="{x + 18}" y="{y + 15}" class="l">{pct}%</text></g>'
        )
    return frame(495, 210, out)


def streak_svg(d):
    out = head("Contribution Streak")
    out += '<line x1="165" y1="52" x2="165" y2="150" stroke="#6C3BFF" stroke-opacity=".3"/><line x1="330" y1="52" x2="330" y2="150" stroke="#6C3BFF" stroke-opacity=".3"/>'
    out += (
        f'<g class="row"><text x="82" y="104" class="big" text-anchor="middle">{fmt(d["total"])}</text>'
        '<text x="82" y="146" class="l" text-anchor="middle">CONTRIBUTIONS</text></g>'
        f'<g class="row" style="animation-delay:.3s"><text x="412" y="104" class="big" text-anchor="middle">{fmt(d["longest"])}</text>'
        '<text x="412" y="146" class="l" text-anchor="middle">LONGEST STREAK</text></g>'
    )
    frac = max(min(d["current"] / max(d["longest"], 1), 1), .06)
    c = 2 * math.pi * 36
    o = c * (1 - frac)
    out += (
        '<circle cx="247" cy="94" r="36" fill="none" stroke="#14213D" stroke-width="7"/>'
        f'<circle class="ring" cx="247" cy="94" r="36" fill="none" stroke="url(#ac)" stroke-width="7" stroke-linecap="round" transform="rotate(-90 247 94)" filter="url(#gl)" style="--c:{c:.1f};--o:{o:.1f};stroke-dasharray:{c:.1f}"/>'
        '<g transform="translate(247,72) scale(.6)"><path class="flame" d="M0 -12 C6 -4 8 0 4 8 C2 12 -2 12 -4 8 C-7 3 -2 -2 0 -12Z" fill="#00D4FF" filter="url(#gl)"/></g>'
        f'<text x="247" y="108" class="big" text-anchor="middle" style="font-size:24px">{fmt(d["current"])}</text>'
        '<text x="247" y="146" class="l" text-anchor="middle">CURRENT STREAK</text>'
    )
    days = d["days"] if len(d["days"]) > 1 else [0, 0]
    m = max(days + [1])
    step = 447 / (len(days) - 1)
    pts = " ".join(f"{24 + i * step:.1f},{184 - n / m * 26:.1f}" for i, n in enumerate(days))
    out += f'<polyline class="draw" pathLength="1" points="{pts}" fill="none" stroke="url(#ac)" stroke-width="2" stroke-linejoin="round" filter="url(#gl)"/>'
    return frame(495, 196, out)


def hexpts(cx, cy, r):
    return " ".join(
        f"{cx + r * math.cos(math.radians(60 * k - 30)):.1f},{cy + r * math.sin(math.radians(60 * k - 30)):.1f}"
        for k in range(6)
    )


def ach_svg(d):
    if KIND == "org":
        items = [("REPOS", d["repos"]), ("STARS", d["stars"]), ("FORKS", d["forks"]),
                 ("FOLLOWERS", d["followers"]), ("ISSUES", d["issues_open"]), ("LANGS", len(d["langs"]))]
    else:
        items = [("COMMITS", d["commits"]), ("STARS", d["stars"]), ("REPOS", d["repos"]),
                 ("FOLLOWERS", d["followers"]), ("STREAK", d["longest"]), ("PRS", d["prs"])]
    out = head("Achievements")
    for i, (label, val) in enumerate(items):
        cx = 52 + i * 78
        cy = 84
        out += (
            f'<g class="pop" style="animation-delay:{i * .15:.2f}s">'
            f'<polygon class="spin" points="{hexpts(cx, cy, 33)}" fill="none" stroke="#6C3BFF" stroke-width="1.5" stroke-dasharray="4 4"/>'
            f'<polygon points="{hexpts(cx, cy, 26)}" fill="#14213D" stroke="url(#ac)" stroke-width="2" filter="url(#gl)"/>'
            f'<text x="{cx}" y="{cy + 5}" class="v" text-anchor="middle" style="font-size:12px">{fmt(val)}</text>'
            f'<text x="{cx}" y="{cy + 54}" class="l" text-anchor="middle" style="font-size:10px">{label}</text></g>'
        )
    return frame(495, 160, out)


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
    cards = {"stats.svg": stats_svg, "langs.svg": langs_svg, "achievements.svg": ach_svg}
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

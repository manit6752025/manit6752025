import os
import json
import requests
import math
from datetime import datetime

GITHUB_TOKEN = os.environ.get("GITHUB_TOKEN")
OWNER = os.environ.get("STATS_OWNER", "manit6752025")
KIND = os.environ.get("STATS_KIND", "user")
OUT_DIR = os.environ.get("STATS_OUT", "stats")
ORG_NAME = "NetCore-Technologies"

HEADERS = {"Authorization": f"Bearer {GITHUB_TOKEN}", "Accept": "application/vnd.github+json"}
os.makedirs(OUT_DIR, exist_ok=True)

def api_get(url):
    try:
        res = requests.get(url, headers=HEADERS, timeout=10)
        return res.json() if res.status_code == 200 else {}
    except: return {}

def api_graphql(query, variables):
    try:
        res = requests.post("https://api.github.com/graphql", headers=HEADERS, json={"query": query, "variables": variables}, timeout=10)
        return res.json().get("data", {}) if res.status_code == 200 else {}
    except: return {}

def get_stats(username, is_org=False):
    if is_org:
        user = api_get(f"https://api.github.com/orgs/{username}")
        repos = api_get(f"https://api.github.com/orgs/{username}/repos?per_page=100")
        commits = api_get(f"https://api.github.com/search/commits?q=org:{username}&per_page=1").get("total_count", 0)
        prs = api_get(f"https://api.github.com/search/issues?q=org:{username}+type:pr+is:merged&per_page=1").get("total_count", 0)
        issues = api_get(f"https://api.github.com/search/issues?q=org:{username}+type:issue+is:closed&per_page=1").get("total_count", 0)
    else:
        user = api_get(f"https://api.github.com/users/{username}")
        repos = api_get(f"https://api.github.com/users/{username}/repos?per_page=100")
        p_commits = api_get(f"https://api.github.com/search/commits?q=author:{username}&per_page=1").get("total_count", 0)
        o_commits = api_get(f"https://api.github.com/search/commits?q=author:{username}+org:{ORG_NAME}&per_page=1").get("total_count", 0)
        commits = p_commits + o_commits
        prs = api_get(f"https://api.github.com/search/issues?q=author:{username}+type:pr+is:merged&per_page=1").get("total_count", 0)
        issues = api_get(f"https://api.github.com/search/issues?q=author:{username}+type:issue+is:closed&per_page=1").get("total_count", 0)

    stars = sum(r.get("stargazers_count", 0) for r in repos) if isinstance(repos, list) else 0
    return {
        "commits": commits, "stars": stars, "repos": user.get("public_repos", 0),
        "followers": user.get("followers", 0), "prs": prs, "issues": issues
    }

def get_languages(username, is_org=False):
    repos = api_get(f"https://api.github.com/{'orgs' if is_org else 'users'}/{username}/repos?per_page=100")
    langs = {}
    if isinstance(repos, list):
        for repo in repos:
            l_data = api_get(repo["languages_url"])
            for lang, bytes_count in l_data.items():
                langs[lang] = langs.get(lang, 0) + bytes_count
    total = sum(langs.values()) or 1
    sorted_langs = sorted(langs.items(), key=lambda x: x[1], reverse=True)[:6]
    return [(lang, round((count / total) * 100, 1)) for lang, count in sorted_langs]

def get_streak(username):
    query = """
    query($login: String!) {
      user(login: $login) {
        contributionsCollection {
          contributionCalendar {
            totalContributions
            weeks { contributionDays { contributionCount } }
          }
        }
      }
    }"""
    data = api_graphql(query, {"login": username})
    try:
        collection = data["user"]["contributionsCollection"]["contributionCalendar"]
        total = collection["totalContributions"]
        days = [d["contributionCount"] for w in collection["weeks"] for d in w["contributionDays"]]
        current, longest, temp = 0, 0, 0
        for d in days:
            temp = temp + 1 if d > 0 else 0
            longest = max(longest, temp)
        for d in reversed(days):
            if d > 0: current += 1
            else: break
        return total, longest, current, days[-30:]
    except: return 0, 0, 0, [0]*30

# --- Beautiful SVG Generator (Safe for GitHub) ---
C = {"bg": "#090A0F", "border": "#00D4FF", "text": "#c9d1d9", "accent": "#6C3BFF", "sub": "#8b949e", "card": "#0d1117"}
DEFS = '''<defs>
    <linearGradient id="neon" x1="0" y1="0" x2="1" y2="1">
        <stop offset="0%" stop-color="#00D4FF"/>
        <stop offset="100%" stop-color="#6C3BFF"/>
    </linearGradient>
    <pattern id="dots" x="0" y="0" width="20" height="20" patternUnits="userSpaceOnUse">
        <circle cx="2" cy="2" r="1" fill="#ffffff" opacity="0.05"/>
    </pattern>
</defs>'''

def svg_wrap(w, h, content):
    return f'''<svg width="{w}" height="{h}" xmlns="http://www.w3.org/2000/svg">
    {DEFS}
    <rect width="100%" height="100%" fill="{C['bg']}" rx="10" stroke="url(#neon)" stroke-width="2"/>
    <rect width="100%" height="100%" fill="url(#dots)" rx="10"/>
    {content}
    </svg>'''

def make_stats(stats, title, filename):
    bars = ""
    # Max values set to make the progress bars look full and aesthetic
    metrics = [("Total commits", stats['commits'], 15000), ("Stars earned", stats['stars'], 100), ("Public repos", stats['repos'], 20), ("Followers", stats['followers'], 20), ("Merged PRs", stats['prs'], 300), ("Issues (12 mo)", stats['issues'], 200)]
    
    for i, (label, val, max_val) in enumerate(metrics):
        y = 65 + i*22
        pct = min((val / max_val) * 100, 100) if max_val else 0
        width = max(4, int(pct * 2)) # ensure minimum width
        bars += f'''<text x="20" y="{y}" fill="{C['sub']}" font-family="sans-serif" font-size="13">{label}</text>
        <text x="150" y="{y}" fill="{C['text']}" font-family="sans-serif" font-size="14" font-weight="bold" text-anchor="end">{val:,}</text>
        <rect x="160" y="{y-8}" width="200" height="6" fill="#ffffff" opacity="0.1" rx="3"/>
        <rect x="160" y="{y-8}" width="{width}" height="6" fill="url(#neon)" rx="3"/>'''
    
    circle = f'''<circle cx="370" cy="80" r="45" fill="none" stroke="url(#neon)" stroke-width="4"/>
    <text x="370" y="75" fill="{C['sub']}" font-family="sans-serif" font-size="10" text-anchor="middle">RANK</text>
    <text x="370" y="98" fill="{C['text']}" font-family="sans-serif" font-size="28" font-weight="bold" text-anchor="middle">S</text>'''
    
    content = f'<text x="20" y="30" fill="{C["border"]}" font-family="sans-serif" font-size="18" font-weight="bold">{title}</text>{bars}{circle}'
    with open(f"{OUT_DIR}/{filename}", "w") as f: f.write(svg_wrap(450, 200, content))

def make_langs(langs, title, filename):
    colors = ["#00D4FF", "#6C3BFF", "#A855F7", "#34D399", "#F87171", "#FBBF24"]
    top_bar, blocks = "", ""
    x_offset = 20
    for i, (lang, pct) in enumerate(langs):
        c = colors[i % len(colors)]
        bar_w = (pct / 100) * 410
        top_bar += f'<rect x="{x_offset}" y="50" width="{bar_w}" height="6" fill="{c}" rx="3"/>'
        x_offset += bar_w
        y = 75 + (i // 2) * 25
        x = 20 if i % 2 == 0 else 230
        blocks += f'<circle cx="{x+5}" cy="{y-4}" r="5" fill="{c}"/><text x="{x+15}" y="{y}" fill="{C["text"]}" font-family="sans-serif" font-size="14">{lang}</text><text x="{x+150}" y="{y}" fill="{C["text"]}" font-family="sans-serif" font-size="14" font-weight="bold" text-anchor="end">{pct}%</text>'
    
    content = f'<text x="20" y="30" fill="{C["border"]}" font-family="sans-serif" font-size="18" font-weight="bold">{title}</text><rect x="20" y="50" width="410" height="6" fill="#ffffff" opacity="0.1" rx="3"/>{top_bar}{blocks}'
    with open(f"{OUT_DIR}/{filename}", "w") as f: f.write(svg_wrap(450, 200, content))

def make_streak(total, longest, current, days, title, filename):
    max_d = max(days) if days else 1
    # Create the sparkline points
    points = []
    for i, d in enumerate(days):
        x = 20 + i * (410 / len(days))
        y = 150 - (d / max_d) * 40 if max_d > 0 else 150
        points.append(f"{x},{y}")
    spark = f'<polyline points="{" ".join(points)}" fill="none" stroke="url(#neon)" stroke-width="2" stroke-dasharray="2,2"/>'
    
    content = f'''<text x="20" y="30" fill="{C['border']}" font-family="sans-serif" font-size="18" font-weight="bold">{title}</text>
    <text x="30" y="80" fill="{C['text']}" font-family="sans-serif" font-size="32" font-weight="bold">{total:,}</text>
    <text x="30" y="100" fill="{C['sub']}" font-family="sans-serif" font-size="11">CONTRIBUTIONS</text>
    <text x="180" y="80" fill="{C['text']}" font-family="sans-serif" font-size="32" font-weight="bold">{longest}</text>
    <text x="180" y="100" fill="{C['sub']}" font-family="sans-serif" font-size="11">LONGEST STREAK</text>
    <circle cx="370" cy="80" r="45" fill="none" stroke="url(#neon)" stroke-width="4"/>
    <text x="370" y="82" fill="{C['text']}" font-family="sans-serif" font-size="22" font-weight="bold" text-anchor="middle">{current}</text>
    <text x="370" y="100" fill="{C['sub']}" font-family="sans-serif" font-size="9" text-anchor="middle">CURRENT STREAK</text>
    {spark}'''
    with open(f"{OUT_DIR}/{filename}", "w") as f: f.write(svg_wrap(450, 200, content))

def make_achievements(stats, streak, title, filename):
    hexes = [(stats['commits'], "COMMITS"), (stats['stars'], "STARS"), (stats['repos'], "REPOS"), (stats['followers'], "FOLLOWERS"), (streak, "STREAK"), (stats['prs'], "MERGED")]
    blocks, x = "", 55
    for val, label in hexes:
        val_str = f"{val//1000}k" if val > 9999 else str(val)
        # Hexagon generation
        blocks += f'''<polygon points="{x},80 {x+25},65 {x+50},80 {x+50},110 {x+25},125 {x},110" fill="{C['card']}" stroke="url(#neon)" stroke-width="2"/>
        <text x="{x+25}" y="95" fill="{C['text']}" font-family="sans-serif" font-size="12" font-weight="bold" text-anchor="middle">{val_str}</text>
        <text x="{x+25}" y="140" fill="{C['sub']}" font-family="sans-serif" font-size="10" text-anchor="middle">{label}</text>'''
        x += 65
    content = f'<text x="20" y="30" fill="{C["border"]}" font-family="sans-serif" font-size="18" font-weight="bold">{title}</text>{blocks}'
    with open(f"{OUT_DIR}/{filename}", "w") as f: f.write(svg_wrap(450, 200, content))

if __name__ == "__main__":
    print(f"Generating {KIND} stats for {OWNER}...")
    stats = get_stats(OWNER, is_org=(KIND == "org"))
    langs = get_languages(OWNER, is_org=(KIND == "org"))
    total, longest, current, days = get_streak("manit6752025") # Always use Manit's streak
    
    make_stats(stats, "GitHub Stats" if KIND == "org" else "Manit's GitHub Stats", "stats.svg")
    make_langs(langs, "Most Used Languages", "langs.svg")
    make_streak(total, longest, current, days, "Contribution Streak", "streak.svg")
    make_achievements(stats, current, "Achievements", "achievements.svg")
    
    if KIND == "user":
        with open(f"{OUT_DIR}/cache.json", "w") as f:
            json.dump({"followers": stats['followers'], "repos": stats['repos'], "stars": stats['stars']}, f)

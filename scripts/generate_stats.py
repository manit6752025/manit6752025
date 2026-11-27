import os
import json
import requests
import traceback
from datetime import datetime

GITHUB_TOKEN = os.environ.get("GITHUB_TOKEN")
OWNER = os.environ.get("STATS_OWNER", "manit6752025")
KIND = os.environ.get("STATS_KIND", "user")
OUT_DIR = os.environ.get("STATS_OUT", "stats")
ORG_NAME = "NetCore-Technologies"

HEADERS = {
    "Authorization": f"Bearer {GITHUB_TOKEN}",
    "Accept": "application/vnd.github+json"
}

os.makedirs(OUT_DIR, exist_ok=True)

def api_get(url):
    try:
        res = requests.get(url, headers=HEADERS, timeout=10)
        if res.status_code == 200:
            return res.json()
        print(f"API Error {res.status_code} for {url}: {res.text}")
        return {}
    except Exception as e:
        print(f"Request failed for {url}: {e}")
        return {}

def api_graphql(query, variables):
    try:
        res = requests.post("https://api.github.com/graphql", headers=HEADERS, json={"query": query, "variables": variables}, timeout=10)
        if res.status_code == 200:
            return res.json().get("data", {})
        return {}
    except Exception:
        return {}

def get_user_stats(username):
    user = api_get(f"https://api.github.com/users/{username}")
    repos = api_get(f"https://api.github.com/users/{username}/repos?per_page=100")
    
    stars = sum(r.get("stargazers_count", 0) for r in repos) if isinstance(repos, list) else 0
    followers = user.get("followers", 0)
    public_repos = user.get("public_repos", 0)
    
    prs = api_get(f"https://api.github.com/search/issues?q=author:{username}+type:pr+is:merged&per_page=1").get("total_count", 0)
    issues = api_get(f"https://api.github.com/search/issues?q=author:{username}+type:issue+is:closed&per_page=1").get("total_count", 0)
    
    personal_commits = api_get(f"https://api.github.com/search/commits?q=author:{username}&per_page=1").get("total_count", 0)
    org_commits = api_get(f"https://api.github.com/search/commits?q=author:{username}+org:{ORG_NAME}&per_page=1").get("total_count", 0)
    
    return {
        "commits": personal_commits + org_commits if KIND == "user" else personal_commits,
        "stars": stars, "repos": public_repos, "followers": followers,
        "prs": prs, "issues": issues
    }

def get_org_stats(org):
    org_data = api_get(f"https://api.github.com/orgs/{org}")
    repos = api_get(f"https://api.github.com/orgs/{org}/repos?per_page=100")
    
    stars = sum(r.get("stargazers_count", 0) for r in repos) if isinstance(repos, list) else 0
    followers = org_data.get("followers", 0)
    public_repos = org_data.get("public_repos", 0)
    
    commits = api_get(f"https://api.github.com/search/commits?q=org:{org}&per_page=1").get("total_count", 0)
    prs = api_get(f"https://api.github.com/search/issues?q=org:{org}+type:pr+is:merged&per_page=1").get("total_count", 0)
    issues = api_get(f"https://api.github.com/search/issues?q=org:{org}+type:issue+is:closed&per_page=1").get("total_count", 0)
    
    return {
        "commits": commits, "stars": stars, "repos": public_repos,
        "followers": followers, "prs": prs, "issues": issues
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
    }
    """
    data = api_graphql(query, {"login": username})
    try:
        collection = data["user"]["contributionsCollection"]
        total = collection["contributionCalendar"]["totalContributions"]
        days = [d["contributionCount"] for w in collection["contributionCalendar"]["weeks"] for d in w["contributionDays"]]
        current, longest, temp = 0, 0, 0
        for d in days:
            if d > 0:
                temp += 1
                longest = max(longest, temp)
            else:
                temp = 0
        for d in reversed(days):
            if d > 0: current += 1
            else: break
        return total, longest, current
    except:
        return 0, 0, 0

# --- SVG Generation ---
COLORS = {
    "bg": "#090A0F", "card_bg": "#0d1117", "border": "#00D4FF", 
    "text": "#c9d1d9", "accent": "#6C3BFF", "subtext": "#8b949e"
}

def make_stats_svg(stats, title, filename):
    svg = f'''<svg width="450" height="200" xmlns="http://www.w3.org/2000/svg">
    <rect width="100%" height="100%" fill="{COLORS['bg']}" rx="10" stroke="{COLORS['border']}" stroke-width="2"/>
    <text x="20" y="30" fill="{COLORS['border']}" font-family="sans-serif" font-size="18" font-weight="bold">{title}</text>
    <g transform="translate(20, 60)" font-family="sans-serif" font-size="14" fill="{COLORS['text']}">
        <text y="0">Total commits</text><text x="150" y="0" font-weight="bold">{stats['commits']:,}</text>
        <text y="25">Stars earned</text><text x="150" y="25" font-weight="bold">{stats['stars']:,}</text>
        <text y="50">Public repos</text><text x="150" y="50" font-weight="bold">{stats['repos']:,}</text>
        <text y="75">Followers</text><text x="150" y="75" font-weight="bold">{stats['followers']:,}</text>
        <text y="100">Merged PRs</text><text x="150" y="100" font-weight="bold">{stats['prs']:,}</text>
        <text y="125">Issues (closed)</text><text x="150" y="125" font-weight="bold">{stats['issues']:,}</text>
    </g>
    <circle cx="370" cy="80" r="45" fill="none" stroke="{COLORS['accent']}" stroke-width="4"/>
    <text x="370" y="75" fill="{COLORS['text']}" font-family="sans-serif" font-size="12" text-anchor="middle">RANK</text>
    <text x="370" y="95" fill="{COLORS['text']}" font-family="sans-serif" font-size="24" font-weight="bold" text-anchor="middle">S</text>
    </svg>'''
    with open(f"{OUT_DIR}/{filename}", "w") as f: f.write(svg)

def make_langs_svg(langs, title, filename):
    colors = ["#00D4FF", "#6C3BFF", "#A855F7", "#34D399", "#F87171", "#FBBF24"]
    blocks = ""
    y = 60
    for i, (lang, pct) in enumerate(langs):
        c = colors[i % len(colors)]
        blocks += f'''<circle cx="25" cy="{y-4}" r="6" fill="{c}"/>
        <text x="40" y="{y}" fill="{COLORS['text']}" font-family="sans-serif" font-size="14">{lang}</text>
        <text x="200" y="{y}" fill="{COLORS['text']}" font-family="sans-serif" font-size="14" font-weight="bold">{pct}%</text>'''
        y += 30
    svg = f'''<svg width="450" height="200" xmlns="http://www.w3.org/2000/svg">
    <rect width="100%" height="100%" fill="{COLORS['bg']}" rx="10" stroke="{COLORS['border']}" stroke-width="2"/>
    <text x="20" y="30" fill="{COLORS['border']}" font-family="sans-serif" font-size="18" font-weight="bold">{title}</text>
    {blocks}
    </svg>'''
    with open(f"{OUT_DIR}/{filename}", "w") as f: f.write(svg)

def make_streak_svg(total, longest, current, title, filename):
    svg = f'''<svg width="450" height="200" xmlns="http://www.w3.org/2000/svg">
    <rect width="100%" height="100%" fill="{COLORS['bg']}" rx="10" stroke="{COLORS['border']}" stroke-width="2"/>
    <text x="20" y="30" fill="{COLORS['border']}" font-family="sans-serif" font-size="18" font-weight="bold">{title}</text>
    <text x="30" y="80" fill="{COLORS['text']}" font-family="sans-serif" font-size="28" font-weight="bold">{total:,}</text>
    <text x="30" y="100" fill="{COLORS['subtext']}" font-family="sans-serif" font-size="12">CONTRIBUTIONS</text>
    <text x="180" y="80" fill="{COLORS['text']}" font-family="sans-serif" font-size="28" font-weight="bold">{longest}</text>
    <text x="180" y="100" fill="{COLORS['subtext']}" font-family="sans-serif" font-size="12">LONGEST STREAK</text>
    <circle cx="370" cy="80" r="45" fill="none" stroke="{COLORS['accent']}" stroke-width="4"/>
    <text x="370" y="75" fill="{COLORS['text']}" font-family="sans-serif" font-size="20" font-weight="bold" text-anchor="middle">{current}</text>
    <text x="370" y="95" fill="{COLORS['subtext']}" font-family="sans-serif" font-size="10" text-anchor="middle">CURRENT STREAK</text>
    </svg>'''
    with open(f"{OUT_DIR}/{filename}", "w") as f: f.write(svg)

def make_achievements_svg(stats, streak, title, filename):
    hexes = [
        (stats['commits'], "COMMITS"), (stats['stars'], "STARS"), 
        (stats['repos'], "REPOS"), (stats['followers'], "FOLLOWERS"),
        (streak, "STREAK"), (stats['prs'], "MERGED")
    ]
    blocks = ""
    x = 60
    for val, label in hexes:
        blocks += f'''<polygon points="{x},80 {x+25},65 {x+50},80 {x+50},110 {x+25},125 {x},110" fill="{COLORS['card_bg']}" stroke="{COLORS['accent']}" stroke-width="2"/>
        <text x="{x+25}" y="95" fill="{COLORS['text']}" font-family="sans-serif" font-size="12" font-weight="bold" text-anchor="middle">{val}</text>
        <text x="{x+25}" y="145" fill="{COLORS['subtext']}" font-family="sans-serif" font-size="10" text-anchor="middle">{label}</text>'''
        x += 60
    svg = f'''<svg width="450" height="200" xmlns="http://www.w3.org/2000/svg">
    <rect width="100%" height="100%" fill="{COLORS['bg']}" rx="10" stroke="{COLORS['border']}" stroke-width="2"/>
    <text x="20" y="30" fill="{COLORS['border']}" font-family="sans-serif" font-size="18" font-weight="bold">{title}</text>
    <g transform="translate(0, 20)">{blocks}</g>
    </svg>'''
    with open(f"{OUT_DIR}/{filename}", "w") as f: f.write(svg)

# --- Main ---
if __name__ == "__main__":
    try:
        print(f"Generating stats for: {OWNER} (Kind: {KIND})")
        
        if KIND == "user":
            stats = get_user_stats(OWNER)
            langs = get_languages(OWNER, is_org=False)
            total, longest, current = get_streak(OWNER)
            
            make_stats_svg(stats, "Manit's GitHub Stats", "stats.svg")
            make_langs_svg(langs, "Most Used Languages", "langs.svg")
            make_streak_svg(total, longest, current, "Contribution Streak", "streak.svg")
            make_achievements_svg(stats, current, "Achievements", "achievements.svg")
            
            with open(f"{OUT_DIR}/cache.json", "w") as f:
                json.dump({"followers": stats['followers'], "repos": stats['repos'], "stars": stats['stars']}, f)
                
        else:
            stats = get_org_stats(OWNER)
            langs = get_languages(OWNER, is_org=True)
            total, longest, current = get_streak("manit6752025") 
            
            # BUG FIXED: Removed OUT_DIR from the filename argument
            make_stats_svg(stats, f"{OWNER.split('-')[0]} Stats", "stats.svg")
            make_langs_svg(langs, f"{OWNER.split('-')[0]} Languages", "langs.svg")
            make_streak_svg(total, longest, current, f"{OWNER.split('-')[0]} Streak", "streak.svg")
            make_achievements_svg(stats, current, f"{OWNER.split('-')[0]} Achievements", "achievements.svg")
        
        print("SVGs generated successfully.")
    except Exception as e:
        print(f"CRITICAL ERROR: {e}")
        traceback.print_exc()
        exit(1)

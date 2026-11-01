import json
import os
import urllib.request
from collections import defaultdict
from html import escape

USER = "manit6752025"
TOKEN = os.environ["GITHUB_TOKEN"]

QUERY = """
query($login: String!, $after: String) {
  user(login: $login) {
    followers { totalCount }
    contributionsCollection {
      contributionCalendar { totalContributions }
      totalCommitContributions
      totalPullRequestContributions
      totalIssueContributions
    }
    repositories(first: 100, ownerAffiliations: OWNER, isFork: false, privacy: PUBLIC, after: $after) {
      totalCount
      pageInfo { hasNextPage endCursor }
      nodes {
        stargazerCount
        languages(first: 10, orderBy: {field: SIZE, direction: DESC}) {
          edges { size node { name color } }
        }
      }
    }
  }
}
"""


def gql(variables):
    req = urllib.request.Request(
        "https://api.github.com/graphql",
        data=json.dumps({"query": QUERY, "variables": variables}).encode(),
        headers={"Authorization": "bearer " + TOKEN, "Content-Type": "application/json"},
    )
    with urllib.request.urlopen(req, timeout=60) as r:
        data = json.load(r)
    if "errors" in data:
        raise SystemExit(str(data["errors"]))
    return data["data"]["user"]


def fetch():
    after = None
    stars = 0
    langs = defaultdict(lambda: {"size": 0, "color": "#8b949e"})
    first = None
    while True:
        user = gql({"login": USER, "after": after})
        if first is None:
            first = user
        repos = user["repositories"]
        for repo in repos["nodes"]:
            stars += repo["stargazerCount"]
            for edge in repo["languages"]["edges"]:
                name = edge["node"]["name"]
                langs[name]["size"] += edge["size"]
                langs[name]["color"] = edge["node"]["color"] or "#8b949e"
        if not repos["pageInfo"]["hasNextPage"]:
            break
        after = repos["pageInfo"]["endCursor"]
    cc = first["contributionsCollection"]
    return {
        "total": cc["contributionCalendar"]["totalContributions"],
        "commits": cc["totalCommitContributions"],
        "prs": cc["totalPullRequestContributions"],
        "issues": cc["totalIssueContributions"],
        "stars": stars,
        "followers": first["followers"]["totalCount"],
        "repos": first["repositories"]["totalCount"],
        "langs": dict(langs),
    }


STYLE = """<style>
.t{font:600 18px 'Segoe UI',Ubuntu,sans-serif;fill:#58a6ff}
.l{font:400 14px 'Segoe UI',Ubuntu,sans-serif;fill:#c9d1d9}
.v{font:600 14px 'Segoe UI',Ubuntu,sans-serif;fill:#58a6ff}
.bg{fill:#161b22}
.tr{fill:#30363d}
@media (prefers-color-scheme: light){
.l{fill:#24292f}.t,.v{fill:#0969da}.bg{fill:#f6f8fa}.tr{fill:#d0d7de}
}
</style>"""


def stats_svg(d):
    rows = [
        ("Contributions (last year)", d["total"]),
        ("Commits", d["commits"]),
        ("Pull requests", d["prs"]),
        ("Issues", d["issues"]),
        ("Stars earned", d["stars"]),
        ("Followers", d["followers"]),
        ("Public repos", d["repos"]),
    ]
    height = 60 + 24 * len(rows)
    out = [
        '<svg xmlns="http://www.w3.org/2000/svg" width="420" height="%d" viewBox="0 0 420 %d">' % (height, height),
        STYLE,
        '<rect class="bg" width="420" height="%d" rx="10"/>' % height,
        '<text class="t" x="24" y="34">%s - GitHub stats</text>' % escape(USER),
    ]
    y = 66
    for label, value in rows:
        out.append('<text class="l" x="24" y="%d">%s</text>' % (y, escape(label)))
        out.append('<text class="v" x="396" y="%d" text-anchor="end">%s</text>' % (y, format(value, ",")))
        y += 24
    out.append("</svg>")
    return "\n".join(out)


def langs_svg(d):
    items = sorted(d["langs"].items(), key=lambda kv: kv[1]["size"], reverse=True)[:6]
    total = sum(v["size"] for _, v in items) or 1
    height = 60 + 28 * max(len(items), 1)
    out = [
        '<svg xmlns="http://www.w3.org/2000/svg" width="420" height="%d" viewBox="0 0 420 %d">' % (height, height),
        STYLE,
        '<rect class="bg" width="420" height="%d" rx="10"/>' % height,
        '<text class="t" x="24" y="34">Most used languages</text>',
    ]
    y = 66
    for name, info in items:
        pct = info["size"] * 100 / total
        width = max(2, round(180 * pct / 100))
        out.append('<text class="l" x="24" y="%d">%s</text>' % (y, escape(name)))
        out.append('<rect class="tr" x="140" y="%d" width="180" height="10" rx="5"/>' % (y - 10))
        out.append('<rect x="140" y="%d" width="%d" height="10" rx="5" fill="%s"/>' % (y - 10, width, escape(info["color"])))
        out.append('<text class="v" x="396" y="%d" text-anchor="end">%.1f%%</text>' % (y, pct))
        y += 28
    out.append("</svg>")
    return "\n".join(out)


def main():
    data = fetch()
    os.makedirs("stats", exist_ok=True)
    with open("stats/stats.svg", "w", encoding="utf-8") as f:
        f.write(stats_svg(data))
    with open("stats/langs.svg", "w", encoding="utf-8") as f:
        f.write(langs_svg(data))


if __name__ == "__main__":
    main()

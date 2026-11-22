import json
from pathlib import Path

BASE = "https://manit-arora.me"
SKIP = {"404.html"}

PERSON = {
    "@context": "https://schema.org",
    "@type": "Person",
    "name": "Manit Arora",
    "url": BASE + "/",
    "jobTitle": "Developer",
    "sameAs": [
        "https://github.com/manit6752025",
        "https://github.com/NetCore-Technologies",
        "https://www.linkedin.com/in/manit-arora-a4756141b/",
        "https://hackerone.com/manit6752025",
        "https://bugcrowd.com/h/manit6752025",
    ],
}

JSONLD = '<script type="application/ld+json">' + json.dumps(PERSON) + "</script>"

for f in sorted(Path("site").glob("*.html")):
    if f.name in SKIP:
        continue
    html = f.read_text(encoding="utf-8")
    if "</head>" not in html:
        continue
    url = BASE + "/" if f.name == "index.html" else BASE + "/" + f.name
    add = ""
    if 'rel="canonical"' not in html:
        add += '<link rel="canonical" href="' + url + '">'
    if f.name == "index.html" and "application/ld+json" not in html:
        add += JSONLD
    if add:
        f.write_text(html.replace("</head>", add + "</head>", 1), encoding="utf-8")
        print("updated", f.name)

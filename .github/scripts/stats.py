"""Builds assets/stats.svg from live GitHub data (runs daily in Actions; stdlib only).

Counts only public, non-fork repositories owned by the user, excluding this profile repo."""
import json
import os
import urllib.request
from xml.sax.saxutils import escape

USER = os.environ.get("GH_USER", "thirthpatel2-web")
TOKEN = os.environ.get("GITHUB_TOKEN", "")
OUT = os.path.join(os.path.dirname(__file__), "..", "..", "assets", "stats.svg")

COLORS = {"Python": "#3572A5", "JavaScript": "#f1e05a", "TypeScript": "#3178c6", "HTML": "#e34c26",
          "CSS": "#663399", "Jupyter Notebook": "#DA5B0B", "Shell": "#89e051", "Dockerfile": "#384d54",
          "Mako": "#7e858d", "Java": "#b07219", "C++": "#f34b7d", "C": "#555555"}


def get(url):
    req = urllib.request.Request(url, headers={"Accept": "application/vnd.github+json", "User-Agent": "profile-stats"})
    if TOKEN:
        req.add_header("Authorization", f"Bearer {TOKEN}")
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.load(r)


def main():
    repos = [r for r in get(f"https://api.github.com/users/{USER}/repos?per_page=100&type=owner")
             if not r["fork"] and not r["private"] and r["name"].lower() != USER.lower()]
    stars = sum(r["stargazers_count"] for r in repos)
    commits = 0
    for r in repos:
        try:
            for c in get(f"https://api.github.com/repos/{USER}/{r['name']}/contributors?per_page=100"):
                if c.get("login", "").lower() == USER.lower():
                    commits += c["contributions"]
        except Exception:  # empty repos return 204/404 - skip them
            pass
    langs = {}
    for r in repos:
        for lang, n in get(r["languages_url"]).items():
            langs[lang] = langs.get(lang, 0) + n
    total = sum(langs.values()) or 1
    top = [kv for kv in sorted(langs.items(), key=lambda kv: -kv[1]) if kv[1] / total >= 0.005][:6]
    latest = max(repos, key=lambda r: r["pushed_at"]) if repos else None
    user = get(f"https://api.github.com/users/{USER}")
    since = user["created_at"][:4]

    W, H = 1000, 250
    tiles = [(str(len(repos)), "public projects"), (str(commits), "commits shipped"), (str(len(langs)), "languages used"), (since, "on GitHub since")]
    tile_svg = []
    for i, (big, small) in enumerate(tiles):
        x = 30 + i * 118
        tile_svg.append(f'<g class="pop" style="animation-delay:{0.1 + i * 0.12:.2f}s"><rect x="{x}" y="62" width="106" height="84" rx="14" fill="#161b22" stroke="#30363d"/>'
                        f'<text x="{x + 53}" y="104" text-anchor="middle" font-size="28" font-weight="800" fill="#f0f6fc">{big}</text>'
                        f'<text x="{x + 53}" y="128" text-anchor="middle" font-size="10.5" fill="#8b949e">{escape(small)}</text></g>')
    bars = []
    y = 58
    for i, (lang, n) in enumerate(top):
        pct = 100 * n / total
        w = max(4, 270 * n / top[0][1])
        col = COLORS.get(lang, "#8b949e")
        bars.append(f'<text x="530" y="{y + 13}" font-size="12.5" fill="#c9d1d9">{escape(lang)}</text>'
                    f'<rect x="650" y="{y}" width="270" height="16" rx="8" fill="#21262d"/>'
                    f'<rect x="650" y="{y}" width="0" height="16" rx="8" fill="{col}"><animate attributeName="width" from="0" to="{w:.1f}" dur="1.2s" begin="{0.2 + i * 0.12:.2f}s" fill="freeze" calcMode="spline" keySplines="0.2 0.8 0.2 1" keyTimes="0;1"/></rect>'
                    f'<text x="932" y="{y + 12.5}" font-size="11.5" fill="#8b949e" opacity="0"><animate attributeName="opacity" from="0" to="1" dur=".4s" begin="{1.2 + i * 0.12:.2f}s" fill="freeze"/>{pct:.1f}%</text>')
        y += 27
    latest_txt = f'latest push → {escape(latest["name"])} · {latest["pushed_at"][:10]}' if latest else ""
    svg = f'''<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}" font-family="'Segoe UI',Inter,Helvetica,Arial,sans-serif" role="img" aria-label="GitHub stats for {USER}: {len(repos)} public projects, {stars} stars, top language {top[0][0] if top else 'n/a'}">
<defs><linearGradient id="bg" x1="0" y1="0" x2="1" y2="1"><stop offset="0" stop-color="#0d1117"/><stop offset="1" stop-color="#161b2e"/></linearGradient>
<linearGradient id="bd" x1="0" y1="0" x2="1" y2="0"><stop offset="0" stop-color="#58a6ff"/><stop offset=".5" stop-color="#bc8cff"/><stop offset="1" stop-color="#ff7eb6"/></linearGradient></defs>
<style>@keyframes pop {{ from {{ opacity:0; transform: translateY(8px) }} to {{ opacity:1; transform:none }} }} .pop {{ opacity:0; animation: pop .7s cubic-bezier(.2,.8,.2,1) forwards }}</style>
<rect x="1.5" y="1.5" width="{W - 3}" height="{H - 3}" rx="20" fill="url(#bg)" stroke="url(#bd)" stroke-width="2"/>
<text x="30" y="40" font-size="15" font-weight="700" fill="#f0f6fc">⚡ Live GitHub stats</text>
<text x="530" y="40" font-size="15" font-weight="700" fill="#f0f6fc">🧬 Languages across my repos</text>
{"".join(tile_svg)}
{"".join(bars)}
<text x="30" y="186" font-family="'JetBrains Mono',Consolas,monospace" font-size="12" fill="#3fb950">{latest_txt}</text>
<text x="30" y="212" font-family="'JetBrains Mono',Consolas,monospace" font-size="11" fill="#6e7681">auto-generated daily from the GitHub API · no third-party service</text>
</svg>'''
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    open(OUT, "w", encoding="utf-8").write(svg)
    print(f"stats.svg: {len(repos)} repos, {commits} commits, {stars} stars, langs={[k for k, _ in top]}")


if __name__ == "__main__":
    main()

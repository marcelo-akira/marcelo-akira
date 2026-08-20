#!/usr/bin/env python3
"""Generate assets/contributions.svg — a terminal-styled, wave-animated
GitHub contribution graph. Runs daily via GitHub Actions (stdlib only)."""

import json
import os
import sys
import urllib.request
from datetime import date

LOGIN = os.environ.get("GH_LOGIN", "marcelo-akira")
TOKEN = os.environ.get("GITHUB_TOKEN") or os.environ.get("GH_TOKEN")
OUT = os.path.join(os.path.dirname(__file__), "..", "assets", "contributions.svg")

QUERY = """
query($login: String!) {
  user(login: $login) {
    contributionsCollection {
      contributionCalendar {
        totalContributions
        weeks {
          contributionDays { date contributionCount contributionLevel }
        }
      }
    }
  }
}
"""

LEVEL_COLORS = {
    "NONE": "#161b22",
    "FIRST_QUARTILE": "#0e4429",
    "SECOND_QUARTILE": "#006d32",
    "THIRD_QUARTILE": "#26a641",
    "FOURTH_QUARTILE": "#39d353",
}

MONTHS = ["Jan", "Feb", "Mar", "Apr", "May", "Jun",
          "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]

CELL = 11
GAP = 3
STEP = CELL + GAP
LEFT = 62          # x of first week column (leaves room for day labels)
TOP = 92           # y of first cell row (below chrome + month labels)


def fetch_calendar():
    if not TOKEN:
        sys.exit("GITHUB_TOKEN not set")
    body = json.dumps({"query": QUERY, "variables": {"login": LOGIN}}).encode()
    req = urllib.request.Request(
        "https://api.github.com/graphql",
        data=body,
        headers={
            "Authorization": f"bearer {TOKEN}",
            "Content-Type": "application/json",
            "User-Agent": LOGIN,
        },
    )
    with urllib.request.urlopen(req) as resp:
        data = json.load(resp)
    if "errors" in data:
        sys.exit(f"GraphQL error: {data['errors']}")
    return data["data"]["user"]["contributionsCollection"]["contributionCalendar"]


def build_svg(calendar):
    weeks = calendar["weeks"]
    total = calendar["totalContributions"]
    n_weeks = len(weeks)

    width = LEFT + n_weeks * STEP - GAP + 26
    height = TOP + 7 * STEP - GAP + 56

    cells = []
    month_labels = []
    last_month = None
    for wi, week in enumerate(weeks):
        x = LEFT + wi * STEP
        first_day = date.fromisoformat(week["contributionDays"][0]["date"])
        if first_day.month != last_month:
            # skip a label crammed into the very last column
            if wi < n_weeks - 2:
                month_labels.append(
                    f'<text x="{x}" y="{TOP - 12}" class="lbl">{MONTHS[first_day.month - 1]}</text>'
                )
            last_month = first_day.month
        for day in week["contributionDays"]:
            di = (date.fromisoformat(day["date"]).weekday() + 1) % 7  # Sun=0
            y = TOP + di * STEP
            color = LEVEL_COLORS[day["contributionLevel"]]
            lit = ' class="lit"' if day["contributionCount"] > 0 else ""
            delay = wi * 0.055 + di * 0.02
            cells.append(
                f'<rect x="{x}" y="{y}" width="{CELL}" height="{CELL}" rx="2.5" '
                f'fill="{color}"{lit}/>'
            )
            cells.append(
                f'<rect x="{x}" y="{y}" width="{CELL}" height="{CELL}" rx="2.5" '
                f'fill="#39d353" class="wave" style="animation-delay:{delay:.2f}s"/>'
            )

    day_labels = "".join(
        f'<text x="{LEFT - 10}" y="{TOP + i * STEP + CELL - 2}" text-anchor="end" class="lbl">{d}</text>'
        for i, d in ((1, "Mon"), (3, "Wed"), (5, "Fri"))
    )

    footer_y = TOP + 7 * STEP - GAP + 34
    title = f"marcelo-akira ~ $ ./contributions.sh"

    return f"""<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}" font-family="'SF Mono','Fira Code','JetBrains Mono',Menlo,Consolas,'Liberation Mono',monospace">
  <style>
    .lbl {{ font-size: 11px; fill: #8b949e; }}
    .chrome-title {{ font-size: 13px; fill: #8b949e; }}
    .total {{ font-size: 13px; fill: #3fb950; }}
    .lit {{ filter: drop-shadow(0 0 3px rgba(57, 211, 83, 0.55)); }}
    .wave {{
      opacity: 0;
      animation: sweep 4.2s linear infinite;
    }}
    @keyframes sweep {{
      0%   {{ opacity: 0; }}
      3%   {{ opacity: 0.75; }}
      9%   {{ opacity: 0; }}
      100% {{ opacity: 0; }}
    }}
    .cursor {{ animation: blink 1.1s steps(1) infinite; }}
    @keyframes blink {{ 0%,49% {{ opacity: 1; }} 50%,100% {{ opacity: 0; }} }}
  </style>
  <rect x="1" y="1" width="{width - 2}" height="{height - 2}" rx="12" fill="#0d1117" stroke="#30363d"/>
  <path d="M1 13 a12 12 0 0 1 12 -12 h{width - 26} a12 12 0 0 1 12 12 v27 h-{width - 2} z" fill="#161b22"/>
  <line x1="1" y1="40" x2="{width - 1}" y2="40" stroke="#30363d"/>
  <circle cx="26" cy="21" r="6.5" fill="#ff5f56"/>
  <circle cx="48" cy="21" r="6.5" fill="#ffbd2e"/>
  <circle cx="70" cy="21" r="6.5" fill="#27c93f"/>
  <text x="{width // 2}" y="26" text-anchor="middle" class="chrome-title">{title}</text>
  {"".join(month_labels)}
  {day_labels}
  {"".join(cells)}
  <text x="{LEFT}" y="{footer_y}" class="total">{total} contributions in the last year</text>
  <rect x="{LEFT + (len(str(total)) + 32) * 8 + 6}" y="{footer_y - 11}" width="8" height="14" fill="#3fb950" class="cursor"/>
</svg>
"""


def main():
    calendar = fetch_calendar()
    svg = build_svg(calendar)
    with open(OUT, "w") as f:
        f.write(svg)
    print(f"wrote {os.path.normpath(OUT)} "
          f"({calendar['totalContributions']} contributions)")


if __name__ == "__main__":
    main()

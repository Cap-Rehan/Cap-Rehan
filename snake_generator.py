#!/usr/bin/env python3
"""
Growing GitHub Contribution Snake
The snake gains +1 length every time it eats a contribution cell.
Outputs light + dark mode SVGs using SMIL <animate> elements.
"""

import os
import requests

USERNAME = "Cap-Rehan"
GITHUB_TOKEN = os.environ.get("GITHUB_TOKEN", "")

# ── Data fetching ──────────────────────────────────────────────────────────────

def fetch_grid():
    """Return contribution counts as list-of-columns (grid[col][row] = count)."""
    query = """
    query($user: String!) {
      user(login: $user) {
        contributionsCollection {
          contributionCalendar {
            weeks {
              contributionDays { contributionCount }
            }
          }
        }
      }
    }
    """
    resp = requests.post(
        "https://api.github.com/graphql",
        json={"query": query, "variables": {"user": USERNAME}},
        headers={"Authorization": f"Bearer {GITHUB_TOKEN}"},
        timeout=30,
    )
    resp.raise_for_status()
    payload = resp.json()
    if "errors" in payload:
        raise RuntimeError(f"GraphQL errors: {payload['errors']}")
    weeks = (
        payload["data"]["user"]
        ["contributionsCollection"]["contributionCalendar"]["weeks"]
    )
    return [[d["contributionCount"] for d in w["contributionDays"]] for w in weeks]


# ── Snake path & growth logic ──────────────────────────────────────────────────

def build_path(grid):
    """Serpentine path visiting every cell (even cols top→bottom, odd cols bottom→top)."""
    path = []
    for col_idx, col in enumerate(grid):
        rng = range(len(col)) if col_idx % 2 == 0 else range(len(col) - 1, -1, -1)
        for row_idx in rng:
            path.append((col_idx, row_idx, col[row_idx]))
    return path


def compute_lengths(path, init=4):
    """
    Snake length at each step.
    Starts at `init`. Grows by 1 each time the head steps onto a non-zero cell.
    """
    lengths, eaten = [], 0
    for _, _, cnt in path:
        lengths.append(init + eaten)
        if cnt > 0:
            eaten += 1
    return lengths


def tail_leave_step(j, lengths, n):
    """
    Returns the step at which the snake's tail first moves past position j.
    Returns n if the tail never leaves during this animation cycle.
    """
    for i in range(j, n):
        # at step i, tail is at index  i - lengths[i] + 1
        if i - lengths[i] + 1 > j:
            return i
    return n


# ── SVG generation ─────────────────────────────────────────────────────────────

def build_svg(grid, dark=False):
    CELL, GAP = 10, 2
    STRIDE = CELL + GAP
    PAD = 5

    ncols = len(grid)
    nrows = max(len(c) for c in grid)
    W = PAD * 2 + ncols * STRIDE
    H = PAD * 2 + nrows * STRIDE

    BG = "#0d1117" if dark else "#ffffff"
    LEVELS = (
        ["#161b22", "#0e4429", "#006d32", "#26a641", "#39d353"]
        if dark
        else ["#ebedf0", "#9be9a8", "#40c463", "#30a14e", "#216e39"]
    )
    EMPTY    = LEVELS[0]
    HEAD_CLR = "#4ade80"   # bright lime – snake head
    BODY_CLR = "#22c55e"   # medium green – snake body

    def cell_color(cnt):
        if cnt == 0:   return LEVELS[0]
        if cnt <= 2:   return LEVELS[1]
        if cnt <= 5:   return LEVELS[2]
        if cnt <= 10:  return LEVELS[3]
        return LEVELS[4]

    path    = build_path(grid)
    n       = len(path)
    lengths = compute_lengths(path, init=4)

    step_sec  = 0.06   # seconds per grid step  (lower = faster snake)
    pause_sec = 2.0    # pause at end before looping
    total_sec = n * step_sec + pause_sec

    tags = [
        f'<svg xmlns="http://www.w3.org/2000/svg" '
        f'viewBox="0 0 {W} {H}" width="{W}" height="{H}">',
        f'<rect width="{W}" height="{H}" fill="{BG}"/>',
    ]

    for j, (col, row, cnt) in enumerate(path):
        x  = PAD + col * STRIDE
        y  = PAD + row * STRIDE
        bg = cell_color(cnt)

        leave_j  = tail_leave_step(j, lengths, n)
        t_arrive = j * step_sec / total_sec
        t_body   = (j + 1) * step_sec / total_sec
        t_leave  = min(leave_j * step_sec / total_sec, 1.0)
        tiny     = step_sec * 0.004 / total_sec   # epsilon to avoid duplicate keyTimes

        # ── build keyTimes / values lists ────────────────────────────────────
        kt: list[float] = []
        vs: list[str]   = []

        def push(t: float, v: str):
            t = max(0.0, min(1.0, t))
            if not kt or t > kt[-1] + 1e-7:
                kt.append(t)
                vs.append(v)

        # Start: show contribution colour (or head immediately for cell 0)
        if t_arrive < tiny:
            push(0.0, HEAD_CLR)
        else:
            push(0.0, bg)
            push(t_arrive - tiny, bg)   # hold background just before head
            push(t_arrive, HEAD_CLR)    # head arrives → bright lime

        push(t_body, BODY_CLR)          # head moves on → body colour

        if leave_j < n:
            push(t_leave - tiny, BODY_CLR)  # hold body until tail leaves
            push(t_leave, EMPTY)             # tail leaves → cell eaten

        push(1.0, vs[-1])               # hold last state to end of loop

        kt_str = ";".join(f"{k:.5f}" for k in kt)
        vs_str = ";".join(vs)

        tags.append(
            f'<rect x="{x}" y="{y}" width="{CELL}" height="{CELL}" rx="2" fill="{bg}">'
            f'<animate attributeName="fill" dur="{total_sec:.3f}s" '
            f'repeatCount="indefinite" calcMode="discrete" '
            f'keyTimes="{kt_str}" values="{vs_str}"/>'
            f'</rect>'
        )

    tags.append("</svg>")
    return "\n".join(tags)


# ── Entry point ────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    os.makedirs("dist", exist_ok=True)

    print(f"Fetching contributions for @{USERNAME}...")
    grid = fetch_grid()
    total_cells = sum(len(c) for c in grid)
    total_contributions = sum(cnt for col in grid for cnt in col)
    print(f"  {len(grid)} weeks · {total_cells} cells · {total_contributions} contributions")

    print("Generating light mode SVG...")
    with open("dist/github-contribution-grid-snake.svg", "w") as f:
        f.write(build_svg(grid, dark=False))

    print("Generating dark mode SVG...")
    with open("dist/github-contribution-grid-snake-dark.svg", "w") as f:
        f.write(build_svg(grid, dark=True))

    print("Done! SVGs written to dist/")

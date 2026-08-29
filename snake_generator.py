#!/usr/bin/env python3
"""
Growing GitHub Contribution Snake Generator
- AI pathfinding: Collision-free food hunting across the GitHub contribution grid.
- Dynamic growth: Snake increases in length (+1 segment) each time it eats a contribution cell.
- High-contrast Sunset Fire / Amber theme: Complementary vibrant orange palette that stands out distinctly against green contribution tiles.
- Zero self-collisions: Guaranteed safe movement with tail-reachability lookahead and flood-fill heuristics.
- Clean SMIL keyframe animations: Indefinite loop with pause, optimized for GitHub READMEs.
"""

import json
import os
import re
import urllib.request
from collections import deque

USERNAME = "Cap-Rehan"
GITHUB_TOKEN = os.environ.get("GITHUB_TOKEN", "")

# ── Data Fetching ─────────────────────────────────────────────────────────────

def fetch_grid(username: str = USERNAME, token: str = GITHUB_TOKEN) -> list[list[int]]:
    """
    Fetch contribution counts as a list-of-columns: grid[col][row] = count.
    Uses GitHub GraphQL API if token is provided, otherwise falls back to public profile scraper.
    """
    if token:
        try:
            print(f"Fetching contribution data via GraphQL API for @{username}...")
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
            req = urllib.request.Request(
                "https://api.github.com/graphql",
                data=json.dumps({"query": query, "variables": {"user": username}}).encode("utf-8"),
                headers={
                    "Authorization": f"Bearer {token}",
                    "Content-Type": "application/json",
                    "User-Agent": "GitHub-Snake-Generator/2.0",
                },
            )
            with urllib.request.urlopen(req, timeout=30) as resp:
                data = json.loads(resp.read().decode("utf-8"))
                if "errors" in data:
                    print(f"GraphQL warning: {data['errors']}")
                else:
                    weeks = (
                        data["data"]["user"]["contributionsCollection"]
                        ["contributionCalendar"]["weeks"]
                    )
                    return [[d["contributionCount"] for d in w["contributionDays"]] for w in weeks]
        except Exception as err:
            print(f"GraphQL request failed ({err}), attempting public fallback...")

    # Fallback: scrape public profile contribution calendar
    try:
        print(f"Fetching contribution data via public profile for @{username}...")
        url = f"https://github.com/users/{username}/contributions"
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=30) as resp:
            html = resp.read().decode("utf-8")
            matches = re.findall(r'data-date="[^"]+"[^>]*data-level="(\d+)"', html)
            if matches:
                weeks = []
                for i in range(0, len(matches), 7):
                    chunk = matches[i:i + 7]
                    weeks.append([int(lvl) for lvl in chunk])
                return weeks
    except Exception as err:
        print(f"Public profile fetch failed ({err}). Using fallback grid.")

    # Ultimate fallback: 53 weeks x 7 days sample grid
    print("Generating default contribution grid...")
    grid = [[0] * 7 for _ in range(53)]
    for w in range(5, 50, 3):
        grid[w][w % 7] = (w % 4) + 1
        grid[w][(w + 2) % 7] = ((w * 2) % 4) + 1
    return grid


# ── AI Snake Simulation ───────────────────────────────────────────────────────

def simulate_snake(grid: list[list[int]], init_length: int = 4):
    """
    Simulates the snake hunting down contribution dots across the GitHub calendar grid.
    Strictly avoids self-collisions and traps.
    The snake grows +1 segment whenever it eats a contribution cell.
    """
    ncols = len(grid)
    nrows = max(len(c) for c in grid)

    # Collect all non-zero contribution cells as food
    foods = set(
        (c, r)
        for c in range(ncols)
        for r in range(len(grid[c]))
        if grid[c][r] > 0
    )
    initial_food_count = len(foods)

    # Clean initial body layout: [(3,0), (2,0), (1,0), (0,0)]
    body = deque([(i, 0) for i in range(init_length - 1, -1, -1)])
    history: list[tuple[list[tuple[int, int]], set[tuple[int, int]]]] = []
    eaten_foods: set[tuple[int, int]] = set()

    # If any starting cells contain food, consume them
    for seg in body:
        if seg in foods:
            foods.remove(seg)
            eaten_foods.add(seg)

    def neighbors(pos: tuple[int, int]) -> list[tuple[int, int]]:
        c, r = pos
        res = []
        for dc, dr in [(0, 1), (0, -1), (1, 0), (-1, 0)]:
            nc, nr = c + dc, r + dr
            if 0 <= nc < ncols and 0 <= nr < nrows:
                res.append((nc, nr))
        return res

    def get_bfs_path(start: tuple[int, int], targets: set[tuple[int, int]], obstacles: set[tuple[int, int]]) -> list[tuple[int, int]] | None:
        if not targets:
            return None
        queue = deque([(start, [start])])
        visited = set(obstacles)
        visited.add(start)
        while queue:
            curr, path = queue.popleft()
            if curr in targets:
                return path
            for nxt in neighbors(curr):
                if nxt not in visited:
                    visited.add(nxt)
                    queue.append((nxt, path + [nxt]))
        return None

    def flood_fill_count(start: tuple[int, int], obstacles: set[tuple[int, int]]) -> int:
        queue = deque([start])
        visited = set(obstacles)
        visited.add(start)
        count = 0
        while queue:
            curr = queue.popleft()
            count += 1
            for nxt in neighbors(curr):
                if nxt not in visited:
                    visited.add(nxt)
                    queue.append(nxt)
        return count

    def is_safe_move(candidate: tuple[int, int], will_eat: bool) -> bool:
        # Simulate new body after taking this move
        new_body = deque(body)
        new_body.appendleft(candidate)
        if not will_eat:
            new_body.pop()
        new_obstacles = set(list(new_body)[:-1])
        # Tail reachability check
        tail_target = new_body[-1]
        path_to_tail = get_bfs_path(candidate, {tail_target}, new_obstacles)
        if path_to_tail is not None:
            return True
        # Or open area >= body length
        return flood_fill_count(candidate, new_obstacles) >= len(new_body)

    step = 0
    max_steps = 3000
    all_eaten_step = None

    while step < max_steps:
        # Record frame snapshot
        history.append((list(body), set(eaten_foods)))

        # Outro handling after all foods are eaten
        if not foods:
            if all_eaten_step is None:
                all_eaten_step = step
            if step - all_eaten_step >= 28:
                break

        head = body[0]

        # Valid candidate moves must NEVER intersect currently occupied body segments
        valid_candidates = []
        for n in neighbors(head):
            will_eat = (n in foods)
            blocked_set = set(body) if will_eat else set(list(body)[:-1])
            if n not in blocked_set:
                valid_candidates.append(n)

        if not valid_candidates:
            # Trapped emergency: stop simulation gracefully
            print(f"Simulation ended safely at step {step}")
            break

        next_step = None

        if foods:
            # 1. Shortest path to closest food avoiding current body
            shortest_path = get_bfs_path(head, foods, set(body))
            if shortest_path and len(shortest_path) > 1:
                first_move = shortest_path[1]
                if first_move in valid_candidates and is_safe_move(first_move, first_move in foods):
                    next_step = first_move

            # 2. If shortest path to food isn't safe, choose a safe candidate that maintains tail access
            if next_step is None:
                safe_candidates = [c for c in valid_candidates if is_safe_move(c, c in foods)]
                if safe_candidates:
                    if shortest_path and len(shortest_path) > 1:
                        target_food = shortest_path[-1]
                        next_step = min(
                            safe_candidates,
                            key=lambda c: abs(c[0] - target_food[0]) + abs(c[1] - target_food[1])
                        )
                    else:
                        next_step = max(safe_candidates, key=lambda c: flood_fill_count(c, set(body)))
                else:
                    # 3. Fallback: candidate with maximum open space
                    next_step = max(valid_candidates, key=lambda c: flood_fill_count(c, set(body)))
        else:
            # Outro phase: graceful victory slither towards the right side
            safe_candidates = [c for c in valid_candidates if is_safe_move(c, False)]
            if not safe_candidates:
                safe_candidates = valid_candidates
            next_step = max(
                safe_candidates,
                key=lambda c: flood_fill_count(c, set(body)) + c[0] * 0.2
            )

        # Execute move
        head = next_step
        if head in foods:
            # Eat food: cell consumed, snake GROWS by +1 length (tail preserved)
            foods.remove(head)
            eaten_foods.add(head)
            body.appendleft(head)
            if not foods:
                all_eaten_step = step
        else:
            # Normal move: advance head, remove tail
            body.appendleft(head)
            body.pop()

        step += 1

    print(f"Simulation completed: {len(history)} steps, {len(eaten_foods)}/{initial_food_count} contributions eaten, final snake length: {len(body)}")
    return history, ncols, nrows


# ── SVG Rendering ─────────────────────────────────────────────────────────────

def build_svg(grid: list[list[int]], history: list[tuple[list[tuple[int, int]], set[tuple[int, int]]]], ncols: int, nrows: int, dark: bool = False) -> str:
    CELL, GAP = 10, 2
    STRIDE = CELL + GAP
    PAD = 5

    W = PAD * 2 + ncols * STRIDE
    H = PAD * 2 + nrows * STRIDE

    BG = "#0d1117" if dark else "#ffffff"

    # Standard GitHub Contribution color tiers
    LEVELS = (
        ["#161b22", "#0e4429", "#006d32", "#26a641", "#39d353"]
        if dark
        else ["#ebedf0", "#9be9a8", "#40c463", "#30a14e", "#216e39"]
    )
    EMPTY_CLR = LEVELS[0]

    # Contrasting Sunset Fire / Amber Snake Palette
    # Strongly contrasts with green contribution tiles and both dark/light backgrounds
    if dark:
        HEAD_CLR = "#ff7b00"  # Glowing Fire Orange
        NECK_CLR = "#ff9100"  # Bright Amber Orange
        BODY_CLR = "#f97316"  # Vivid Sunset Orange
        TAIL_CLR = "#c2410c"  # Deep Ember Auburn
    else:
        HEAD_CLR = "#ea580c"  # Crimson Sunset Orange
        NECK_CLR = "#f97316"  # Warm Vivid Orange
        BODY_CLR = "#fb923c"  # Sun Amber
        TAIL_CLR = "#fdba74"  # Golden Peach

    def cell_initial_color(cnt: int) -> str:
        if cnt == 0:
            return LEVELS[0]
        if cnt <= 2:
            return LEVELS[1]
        if cnt <= 5:
            return LEVELS[2]
        if cnt <= 10:
            return LEVELS[3]
        return LEVELS[4]

    N = len(history)
    step_sec = 0.08    # smooth slither speed (80ms per move)
    pause_sec = 2.4    # pause at end to admire cleared board before looping
    total_sec = N * step_sec + pause_sec

    svg_lines = [
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" width="{W}" height="{H}">',
        f'  <style>',
        f'    rect {{ shape-rendering: geometricPrecision; }}',
        f'  </style>',
        f'  <rect width="{W}" height="{H}" fill="{BG}" rx="6"/>',
    ]

    # Precalculate cell timeline keyframes
    for c in range(ncols):
        for r in range(nrows):
            cnt = grid[c][r] if r < len(grid[c]) else 0
            init_clr = cell_initial_color(cnt)
            x = PAD + c * STRIDE
            y = PAD + r * STRIDE

            # Determine color at each step t
            timeline_colors: list[str] = []
            for t in range(N):
                body_list, eaten_set = history[t]
                if (c, r) == body_list[0]:
                    timeline_colors.append(HEAD_CLR)
                elif (c, r) in body_list:
                    idx = body_list.index((c, r))
                    if idx <= 2:
                        timeline_colors.append(NECK_CLR)
                    elif idx >= len(body_list) - 2:
                        timeline_colors.append(TAIL_CLR)
                    else:
                        timeline_colors.append(BODY_CLR)
                elif (c, r) in eaten_set:
                    timeline_colors.append(EMPTY_CLR)
                else:
                    timeline_colors.append(init_clr)

            # Compress consecutive identical colors into discrete keyTimes
            kt: list[float] = [0.0]
            vs: list[str] = [timeline_colors[0]]

            for t in range(1, N):
                if timeline_colors[t] != vs[-1]:
                    t_frac = (t * step_sec) / total_sec
                    kt.append(t_frac)
                    vs.append(timeline_colors[t])

            # Hold final state through the pause period until end of cycle (1.0)
            if kt[-1] < 1.0:
                kt.append(1.0)
                vs.append(vs[-1])

            # Generate SMIL <animate> if cell color changes, or static rect if never changed
            if len(vs) > 2 or (len(vs) == 2 and vs[0] != vs[1]):
                kt_str = ";".join(f"{k:.4f}" for k in kt)
                vs_str = ";".join(vs)
                svg_lines.append(
                    f'  <rect x="{x}" y="{y}" width="{CELL}" height="{CELL}" rx="2" fill="{init_clr}">'
                    f'<animate attributeName="fill" dur="{total_sec:.3f}s" repeatCount="indefinite" '
                    f'calcMode="discrete" keyTimes="{kt_str}" values="{vs_str}"/>'
                    f'</rect>'
                )
            else:
                svg_lines.append(
                    f'  <rect x="{x}" y="{y}" width="{CELL}" height="{CELL}" rx="2" fill="{init_clr}"/>'
                )

    svg_lines.append("</svg>")
    return "\n".join(svg_lines)


# ── Main Entry Point ──────────────────────────────────────────────────────────

def main():
    os.makedirs("dist", exist_ok=True)

    grid = fetch_grid(USERNAME, GITHUB_TOKEN)
    total_cells = sum(len(c) for c in grid)
    total_contributions = sum(cnt for col in grid for cnt in col)
    print(f"Grid loaded: {len(grid)} weeks · {total_cells} cells · {total_contributions} total contributions")

    print("Running Snake AI simulation with strict collision avoidance & dynamic growth...")
    history, ncols, nrows = simulate_snake(grid, init_length=4)

    print("Generating Light Theme SVG (dist/github-contribution-grid-snake.svg)...")
    light_svg = build_svg(grid, history, ncols, nrows, dark=False)
    with open("dist/github-contribution-grid-snake.svg", "w", encoding="utf-8") as f:
        f.write(light_svg)

    print("Generating Dark Theme SVG (dist/github-contribution-grid-snake-dark.svg)...")
    dark_svg = build_svg(grid, history, ncols, nrows, dark=True)
    with open("dist/github-contribution-grid-snake-dark.svg", "w", encoding="utf-8") as f:
        f.write(dark_svg)

    print("Success! Sunset Fire / Amber snake SVGs generated in dist/")


if __name__ == "__main__":
    main()

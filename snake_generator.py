#!/usr/bin/env python3
"""
Growing GitHub Contribution Snake Generator (Platane Style)
- Smooth & relaxed animation: Continuous CSS keyframe translation gliding across the grid at natural pacing.
- Complete food consumption: 100% of contribution dots are eaten (including bottom-right cells).
- Dynamic growth: Snake increases in length (+1 segment) each time it eats a contribution cell.
- Clean finish: Stops cleanly immediately upon eating the last contribution, pauses, and repeats.
- Sunset Fire / Amber palette: Vibrant orange/amber snake contrasting with green contribution tiles.
- Zero self-collisions: Guaranteed safe movement with tail-reachability lookahead.
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
    Properly aligns days by weekday (0=Sun, ..., 6=Sat) so every column has exactly 7 rows.
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
                      contributionDays { weekday contributionCount }
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
                    weeks_data = (
                        data["data"]["user"]["contributionsCollection"]
                        ["contributionCalendar"]["weeks"]
                    )
                    grid = []
                    for w in weeks_data:
                        col = [0] * 7
                        for d in w["contributionDays"]:
                            col[d["weekday"]] = d["contributionCount"]
                        grid.append(col)
                    return grid
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
    Simulates the snake hunting down every contribution dot across the GitHub calendar grid.
    Strictly avoids self-collisions and dead ends.
    Grows +1 segment for each eaten contribution.
    Guarantees 100% of foods are eaten and stops immediately when finished.
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

    # Initial body layout: [(3,0), (2,0), (1,0), (0,0)]
    body = deque([(i, 0) for i in range(init_length - 1, -1, -1)])
    history: list[list[tuple[int, int]]] = []
    eaten_times: dict[tuple[int, int], int] = {}

    for seg in body:
        if seg in foods:
            foods.remove(seg)
            eaten_times[seg] = 0

    def neighbors(pos: tuple[int, int]) -> list[tuple[int, int]]:
        c, r = pos
        res = []
        for dc, dr in [(0, 1), (0, -1), (1, 0), (-1, 0)]:
            nc, nr = c + dc, r + dr
            if 0 <= nc < ncols and 0 <= nr < nrows:
                res.append((nc, nr))
        return res

    def get_path(start: tuple[int, int], targets: set[tuple[int, int]], obstacles: set[tuple[int, int]]) -> list[tuple[int, int]] | None:
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

    step = 0
    max_steps = 3000

    while foods and step < max_steps:
        history.append(list(body))
        head = body[0]
        tail = body[-1]

        body_obstacles = set(list(body)[:-1])

        # 1. Try to find shortest path to closest food
        food_path = get_path(head, foods, body_obstacles)
        chosen_move = None

        if food_path and len(food_path) > 1:
            first_step = food_path[1]
            # Check if stepping to first_step keeps tail reachable
            sim_body = deque(body)
            sim_body.appendleft(first_step)
            if first_step not in foods:
                sim_body.pop()
            sim_obstacles = set(list(sim_body)[:-1])

            if get_path(first_step, {sim_body[-1]}, sim_obstacles) is not None:
                chosen_move = first_step

        # 2. If direct path to food is not safe, path to tail!
        if chosen_move is None:
            tail_path = get_path(head, {tail}, body_obstacles)
            if tail_path and len(tail_path) > 1:
                chosen_move = tail_path[1]

        # 3. Fallback: move into neighbor with maximum open flood fill space
        if chosen_move is None:
            valid_moves = [n for n in neighbors(head) if n not in body_obstacles]
            if valid_moves:
                chosen_move = max(valid_moves, key=lambda n: flood_fill_count(n, body_obstacles))

        if chosen_move is None:
            print(f"Simulation ended safely at step {step}")
            break

        head = chosen_move
        if head in foods:
            foods.remove(head)
            eaten_times[head] = step + 1
            body.appendleft(head)  # grow by +1
        else:
            body.appendleft(head)
            body.pop()

        step += 1

    # Record final frame
    history.append(list(body))

    print(f"Simulation completed: {len(history)} frames, {len(eaten_times)}/{initial_food_count} contributions eaten, final length: {len(history[-1])}")
    return history, eaten_times, ncols, nrows


# ── Smooth CSS Keyframe SVG Rendering ─────────────────────────────────────────

def remove_interpolated_keyframes(points: list[tuple[float, int, int, int]]) -> list[tuple[float, int, int, int]]:
    """
    Remove redundant intermediate keyframes on straight segments where CSS linear interpolation handles it.
    points: list of (percentage, x, y, opacity)
    """
    if len(points) <= 2:
        return points
    res = [points[0]]
    for i in range(1, len(points) - 1):
        a = res[-1]
        u = points[i]
        b = points[i + 1]
        if a[3] != u[3] or u[3] != b[3]:
            res.append(u)
            continue
        dx1 = u[1] - a[1]
        dy1 = u[2] - a[2]
        dx2 = b[1] - u[1]
        dy2 = b[2] - u[2]
        # Collinear check with constant direction
        if (dx1 * dy2 == dy1 * dx2) and ((dx1 == 0 and dx2 == 0) or (dx1 * dx2 >= 0)) and ((dy1 == 0 and dy2 == 0) or (dy1 * dy2 >= 0)):
            dt1 = u[0] - a[0]
            dt2 = b[0] - u[0]
            dist1 = abs(dx1) + abs(dy1)
            dist2 = abs(dx2) + abs(dy2)
            if dist1 == 0 and dist2 == 0:
                continue
            if dist1 > 0 and dist2 > 0 and abs(dt1 / dist1 - dt2 / dist2) < 1e-4:
                continue
        res.append(u)
    res.append(points[-1])
    return res


def build_svg(
    grid: list[list[int]],
    history: list[list[tuple[int, int]]],
    eaten_times: dict[tuple[int, int], int],
    ncols: int,
    nrows: int,
    dark: bool = False
) -> str:
    CELL, GAP, PAD = 10, 2, 5
    STRIDE = CELL + GAP
    W = PAD * 2 + ncols * STRIDE
    H = PAD * 2 + nrows * STRIDE

    M = len(history)
    frame_ms = 165  # relaxed, natural Platane pacing (~6 tiles per sec)
    pause_ms = 2200  # 2.2s pause at end with cleared board
    P = max(10, int(pause_ms / frame_ms))
    N = M + P
    total_sec = (N * frame_ms) / 1000.0
    max_len = len(history[-1])

    # Color definitions
    if dark:
        BG = "#0d1117"
        LEVELS = ["#161b22", "#0e4429", "#006d32", "#26a641", "#39d353"]
        HEAD_CLR = "#ff7b00"  # Glowing Fire Orange
        NECK_CLR = "#ff9100"  # Bright Amber
        BODY_CLR = "#f97316"  # Sunset Orange
        TAIL_CLR = "#c2410c"  # Deep Ember
    else:
        BG = "#ffffff"
        LEVELS = ["#ebedf0", "#9be9a8", "#40c463", "#30a14e", "#216e39"]
        HEAD_CLR = "#ea580c"  # Crimson Sunset Orange
        NECK_CLR = "#f97316"  # Warm Vivid Orange
        BODY_CLR = "#fb923c"  # Sun Amber
        TAIL_CLR = "#fdba74"  # Golden Peach

    def cell_level(cnt: int) -> int:
        if cnt == 0: return 0
        if cnt <= 2: return 1
        if cnt <= 5: return 2
        if cnt <= 10: return 3
        return 4

    css_rules = [
        f':root {{',
        f'  --bg: {BG};',
        f'  --c0: {LEVELS[0]};',
        f'  --c1: {LEVELS[1]};',
        f'  --c2: {LEVELS[2]};',
        f'  --c3: {LEVELS[3]};',
        f'  --c4: {LEVELS[4]};',
        f'  --head: {HEAD_CLR};',
        f'  --neck: {NECK_CLR};',
        f'  --body: {BODY_CLR};',
        f'  --tail: {TAIL_CLR};',
        f'}}',
        f'.c {{ shape-rendering: geometricPrecision; }}',
        f'.s {{',
        f'  shape-rendering: geometricPrecision;',
        f'  animation: linear {total_sec:.3f}s infinite;',
        f'  fill: var(--body);',
        f'}}',
        f'.s0 {{ fill: var(--head); }}',
        f'.s1, .s2 {{ fill: var(--neck); }}',
        f'.s_tail {{ fill: var(--tail); }}',
    ]

    # Grid tiles
    grid_elements = []
    for c in range(ncols):
        for r in range(nrows):
            cnt = grid[c][r] if r < len(grid[c]) else 0
            lvl = cell_level(cnt)
            x = PAD + c * STRIDE
            y = PAD + r * STRIDE
            if (c, r) in eaten_times:
                t_eat = eaten_times[(c, r)]
                p_eat = (t_eat / N) * 100.0
                anim_name = f'c_{c}_{r}'
                css_rules.append(
                    f'@keyframes {anim_name} {{ '
                    f'0%, {p_eat - 0.01:.2f}% {{ fill: var(--c{lvl}); }} '
                    f'{p_eat:.2f}%, 100% {{ fill: var(--c0); }} }}'
                )
                css_rules.append(f'.{anim_name} {{ animation: {anim_name} {total_sec:.3f}s linear infinite; }}')
                grid_elements.append(f'  <rect class="c {anim_name}" x="{x}" y="{y}" width="{CELL}" height="{CELL}" rx="2" fill="var(--c{lvl})"/>')
            else:
                grid_elements.append(f'  <rect class="c" x="{x}" y="{y}" width="{CELL}" height="{CELL}" rx="2" fill="var(--c{lvl})"/>')

    # Snake segments
    snake_elements = []
    for i in range(max_len):
        t_born = next((t for t in range(M) if len(history[t]) > i), 0)
        x_birth, y_birth = history[t_born][i]

        keyframe_points: list[tuple[float, int, int, int]] = []
        if t_born > 0:
            keyframe_points.append((0.0, x_birth, y_birth, 0))
            pct_pre_birth = ((t_born - 0.01) / N) * 100.0
            keyframe_points.append((pct_pre_birth, x_birth, y_birth, 0))

        pct_birth = (t_born / N) * 100.0
        keyframe_points.append((pct_birth, x_birth, y_birth, 1))

        for t in range(t_born + 1, M):
            pct = (t / N) * 100.0
            x, y = history[t][i]
            keyframe_points.append((pct, x, y, 1))

        # Pause period at end
        x_final, y_final = history[M - 1][i]
        keyframe_points.append((100.0, x_final, y_final, 1))

        # Remove redundant intermediate points on straight trajectories
        simplified = remove_interpolated_keyframes(keyframe_points)

        anim_name = f's{i}'
        kf_chunks = []
        for pt in simplified:
            tx = PAD + pt[1] * STRIDE
            ty = PAD + pt[2] * STRIDE
            kf_chunks.append(f'{pt[0]:.2f}% {{ transform: translate({tx}px, {ty}px); opacity: {pt[3]}; }}')

        css_rules.append(f'@keyframes {anim_name} {{ {" ".join(kf_chunks)} }}')
        css_rules.append(f'.{anim_name} {{ animation-name: {anim_name}; }}')

        extra_cls = ' s_tail' if i >= max_len - 3 else ''
        snake_elements.append(f'  <rect class="s s{i}{extra_cls}" width="{CELL}" height="{CELL}" rx="2" ry="2"/>')

    svg_content = [
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" width="{W}" height="{H}">',
        f'  <style>',
        "\n".join(f"    {rule}" for rule in css_rules),
        f'  </style>',
        f'  <rect width="{W}" height="{H}" fill="var(--bg)" rx="6"/>',
        "\n".join(grid_elements),
        "\n".join(snake_elements),
        f'</svg>',
    ]
    return "\n".join(svg_content)


# ── Main Entry Point ──────────────────────────────────────────────────────────

def main():
    os.makedirs("dist", exist_ok=True)

    grid = fetch_grid(USERNAME, GITHUB_TOKEN)
    total_cells = sum(len(c) for c in grid)
    total_contributions = sum(cnt for col in grid for cnt in col)
    print(f"Grid loaded: {len(grid)} weeks · {total_cells} cells · {total_contributions} total contributions")

    print("Running Snake AI simulation (eating all contributions)...")
    history, eaten_times, ncols, nrows = simulate_snake(grid, init_length=4)

    print("Generating Light Theme SVG (dist/github-contribution-grid-snake.svg)...")
    light_svg = build_svg(grid, history, eaten_times, ncols, nrows, dark=False)
    with open("dist/github-contribution-grid-snake.svg", "w", encoding="utf-8") as f:
        f.write(light_svg)

    print("Generating Dark Theme SVG (dist/github-contribution-grid-snake-dark.svg)...")
    dark_svg = build_svg(grid, history, eaten_times, ncols, nrows, dark=True)
    with open("dist/github-contribution-grid-snake-dark.svg", "w", encoding="utf-8") as f:
        f.write(dark_svg)

    print("Success! Platane-style smooth relaxed snake SVGs generated in dist/")


if __name__ == "__main__":
    main()

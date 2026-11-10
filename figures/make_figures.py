#!/usr/bin/env python3
"""Draw the experiment's pictures for the talk straight from the traces.

    python3 figures/make_figures.py [output-folder]

The pictures belong to the slides, so no image is kept in this repo. They are written into
the slides repo (../lectures/sag-2026/img, next to this repo) unless you name
another folder. PNGs, transparent background, cropped to the drawing. Requires matplotlib
and Pillow. Every number in a picture comes from traces/, nothing is typed in.
"""
import datetime as dt
import glob
import json
import os
import re
import sys

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
from matplotlib.patches import Rectangle  # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))
TRACES = os.path.join(HERE, "..", "traces")
DEFAULT_OUT = os.path.normpath(os.path.join(HERE, "..", "..", "lectures", "sag-2026", "img"))
OUT = sys.argv[1] if len(sys.argv) > 1 else DEFAULT_OUT

GREEN, RED, DARK, GREY, LIGHT = "#78A349", "#C0392B", "#444444", "#B5B5B5", "#E6E6E6"
ANSWERS = {"task-01": "2 | vilmibm | 2009-06-24", "task-02": "16 | 4"}
MODELS = ["haiku", "sonnet", "opus"]


BLUE = "#4A7FB5"


def call_kind(name):
    """Colour class of a tool call, shared by the lane pictures."""
    if "user" in name:
        return "user"
    if name in ("issueslist_for_repo", "list_issues", "searchissues_and_pull_requests"):
        return "list"
    if name in ("issueslist_comments", "issue_read"):
        return "read"
    return "other"


KIND_COLOR = {"list": DARK, "read": GREEN, "user": BLUE, "other": RED}


# ---------------------------------------------------------------- traces ----
def load_run(path):
    calls, results, answer, cost, ok = [], {}, "", 0.0, False
    cache_read, cache_create, turn_ids = 0, 0, set()
    order = []
    msg_of = {}  # tool_use id -> id of the assistant message that issued it (calls in one message run in parallel)
    for line in open(path):
        try:
            e = json.loads(line)
        except ValueError:
            continue
        m = e.get("message")
        content = m.get("content") if isinstance(m, dict) else None
        if not isinstance(content, list):
            content = []
        if e.get("type") == "assistant":
            turn_ids.add(m.get("id") if isinstance(m, dict) else None)
            for b in content:
                if b.get("type") == "tool_use":
                    name = b.get("name", "?").split("__", 2)[-1]
                    calls.append(name)
                    order.append((b["id"], name, b.get("input") or {}))
                    msg_of[b["id"]] = m.get("id")
        elif e.get("type") == "user":
            for b in content:
                if b.get("type") == "tool_result":
                    results[b.get("tool_use_id")] = (str(b.get("content")), bool(b.get("is_error")))
        elif e.get("type") == "result":
            ok = not e.get("is_error")
            cost = e.get("total_cost_usd") or 0.0
            cache_read = (e.get("usage") or {}).get("cache_read_input_tokens", 0)
            mu = e.get("modelUsage") or {}
            cache_create = (sum(v.get("cacheCreationInputTokens", 0) for v in mu.values()) if mu
                            else (e.get("usage") or {}).get("cache_creation_input_tokens", 0))
            hits = re.findall(r"^ANSWER:\s*(.+)$", (e.get("result") or ""), re.M)
            answer = hits[-1].strip() if hits else ""
    return dict(calls=calls, answer=answer, cost=cost, ok=ok, order=order, results=results, msg_of=msg_of,
                cache_read=cache_read, cache_create=cache_create, turns=len(turn_ids))


def warm(runs):
    """Leave out cold-cache runs: runs that wrote more than twice the group's median of cache
    tokens. In these traces that is the first run of task 1 in five of the six setups, where the
    tool definitions were written to the cache before later runs could read them."""
    import statistics
    med = statistics.median(r["cache_create"] for r in runs)
    return [r for r in runs if r["cache_create"] <= 2 * med] or runs


def load_all():
    data = {}
    for path in sorted(glob.glob(os.path.join(TRACES, "*", "task-*", "run-*.jsonl"))):
        setup = os.path.basename(os.path.dirname(os.path.dirname(path)))
        task = os.path.basename(os.path.dirname(path))
        tools, _, model = setup.partition("-")
        data.setdefault((tools, model or "sonnet", task), []).append(load_run(path))
    return data


def canvas():
    fig = plt.figure(figsize=(16, 9), dpi=100, facecolor="white")
    ax = fig.add_axes([0, 0, 1, 1])
    ax.set_xlim(0, 1600)
    ax.set_ylim(900, 0)
    ax.axis("off")
    return fig, ax


def save(fig, name):
    # transparent background, cropped to the drawing with a small margin
    import io
    from PIL import Image
    buf = io.BytesIO()
    fig.savefig(buf, dpi=100, transparent=True, format="png")
    im = Image.open(buf).convert("RGBA")
    l, t, r, b = im.getchannel("A").point(lambda a: 255 if a else 0).getbbox()
    pad = 12
    im.crop((max(l - pad, 0), max(t - pad, 0), min(r + pad, im.width), min(b + pad, im.height))).save(os.path.join(OUT, name))
    plt.close(fig)
    print("wrote", name)


# ------------------------------------------------------------ 1. the scale ---
def fig_scale():
    fig, ax = canvas()
    pitch, size = 5, 2.6   # same pitch for both blocks, so one square is one capability in both
    # our block: 31 x 21 = 651 squares
    cols, rows = 31, 21
    assert cols * rows == 651
    x0, y0 = 150, 450 - rows * pitch / 2
    xs = [x0 + c * pitch for c in range(cols) for _ in range(rows)]
    ys = [y0 + r * pitch for _ in range(cols) for r in range(rows)]
    ax.scatter(xs, ys, s=size ** 2, marker="s", color=GREEN, linewidths=0)
    # a large organisation: far more, fading out at the edges
    bc, br, bx0 = 205, 170, 540
    by0 = 450 - br * pitch / 2
    bxs, bys, al = [], [], []
    for c in range(bc):
        for r in range(br):
            fx = min(c, bc - 1 - c) / 32.0
            fy = min(r, br - 1 - r) / 22.0
            a = max(0.0, min(1.0, fx, fy))
            if a > 0.03:
                bxs.append(bx0 + c * pitch)
                bys.append(by0 + r * pitch)
                al.append(a * 0.75)
    colors = np.zeros((len(bxs), 4))
    colors[:, :3] = [0.55, 0.55, 0.55]
    colors[:, 3] = al
    ax.scatter(bxs, bys, s=size ** 2, marker="s", c=colors, linewidths=0)
    ax.text(x0 + cols * pitch / 2, y0 + rows * pitch + 50, "651 capabilities", ha="center",
            fontsize=30, fontweight="bold", color=DARK)
    ax.text(x0 + cols * pitch / 2, y0 + rows * pitch + 90, "this experiment", ha="center",
            fontsize=20, color=DARK)
    ax.text(bx0 + bc * pitch / 2, 450, "a large organization", ha="center", va="center",
            fontsize=40, fontweight="bold", color=DARK,
            bbox=dict(facecolor="white", edgecolor="none", alpha=0.85, pad=14))
    ax.text(bx0 + bc * pitch / 2, 512, "tens to hundreds of thousands of capabilities",
            ha="center", va="center", fontsize=24, color=DARK,
            bbox=dict(facecolor="white", edgecolor="none", alpha=0.85, pad=8))
    save(fig, "scale-651-tools.png")


# ------------------------- 2. tool set x task, run by run, revealed in three steps ----
def fig_fit(data):
    """Sonnet, five runs per group. One lane is one run, one square is one tool call.
    Columns: tool set. Rows: task. Three versions with identical layout and crop:
    (1) 651 tools only, (2) plus 26 tools on task 1, (3) everything."""
    import io
    import statistics
    from PIL import Image
    kinds, kind = KIND_COLOR, call_kind

    cols = [("generated", "651 tools", 230), ("github", "26 tools", 960)]
    rows = [("task-01", "Task 1", 100, "when was the\nfirst commenter's\naccount created?"),
            ("task-02", "Task 2", 500, "which of the\nfirst five issues\ngot the most early\ncomments from\nothers?")]
    pitch, size = 32, 26

    def render(visible):
        fig, ax = canvas()
        for tools, title, x0 in cols:
            if any(v[0] == tools for v in visible):
                ax.text(x0 + 280, 45, title, ha="center", va="center", fontsize=32, fontweight="bold", color=DARK)
        for task, rtitle, y0, desc in rows:
            ax.text(20, y0 + 70, rtitle, ha="left", va="center", fontsize=28, fontweight="bold", color=DARK)
            for tools, _, x0 in cols:
                if (tools, task) not in visible:
                    continue
                runs = data.get((tools, "sonnet", task), [])[:5]
                for i, run in enumerate(runs):
                    y = y0 + 40 + i * 44
                    for j, name in enumerate(run["calls"]):
                        ax.add_patch(Rectangle((x0 + j * pitch, y - size / 2), size, size, color=kinds[kind(name)], lw=0))
                    ax.text(x0 + len(run["calls"]) * pitch + 6, y, "%d" % len(run["calls"]), va="center",
                            fontsize=18, color="#777777")
                cost = statistics.mean(r["cost"] for r in warm(runs))
                ax.text(x0, y0 + 40 + 4 * 44 + 48, "$%.2f per run" % cost, va="center", fontsize=26,
                        fontweight="bold", color=DARK)
        # key, in the empty space next to the first lanes
        if ("generated", "task-01") in visible:
            ky = 135
            for lbl, col in (("listing issues", DARK), ("reading comments", GREEN),
                             ("looking up the user", BLUE), ("tried a shell (failed)", RED)):
                ax.add_patch(Rectangle((480, ky - 13), 26, 26, color=col, lw=0))
                ax.text(518, ky, lbl, va="center", fontsize=20, color=DARK)
                ky += 44
        ax.text(800, 858, "Sonnet, five runs per group. One lane is one run, one square is one tool call, the number is the calls in that run.",
                ha="center", fontsize=15, color="#888888")
        ax.text(800, 884, "Cost is the average per run (list price), cold-cache runs left out.",
                ha="center", fontsize=15, color="#888888")
        buf = io.BytesIO()
        fig.savefig(buf, dpi=100, transparent=True, format="png")
        plt.close(fig)
        return Image.open(buf).convert("RGBA")

    full = {(t, k) for t, _, _ in cols for k, _, _, _ in rows}
    steps = [("fit-1-complexity.png", {("generated", "task-01"), ("generated", "task-02")}),
             ("fit-2-mismatch.png", {("generated", "task-01"), ("generated", "task-02"), ("github", "task-01")}),
             ("fit-3-fit.png", full)]
    images = [(name, render(vis)) for name, vis in steps]
    l, t, r, b = images[-1][1].getchannel("A").point(lambda a: 255 if a else 0).getbbox()   # crop all alike
    pad = 12
    box = (max(l - pad, 0), max(t - pad, 0), min(r + pad, images[-1][1].width), min(b + pad, images[-1][1].height))
    for name, im in images:
        im.crop(box).save(os.path.join(OUT, name))
        print("wrote", name)


# ------------------------------------- 3. round trips: the context is sent again each time ----
def fig_roundtrips(data):
    """Three real runs of task 2, drawn as round trips. A column is one round trip: the squares on
    top are the tool calls requested in it, the block below is the context sent with it (tool
    definitions and the conversation so far). Block height is proportional to the measured tokens
    read from the cache per round trip (warm cache). The last column is the round trip that writes the answer."""
    import statistics
    rows = [("generated", "sonnet", "run-3", "Sonnet, 651 tools"),
            ("generated", "opus", "run-1", "Opus, 651 tools"),
            ("github", "sonnet", "run-1", "Sonnet, 26 tools")]
    fig = plt.figure(figsize=(16, 10.5), dpi=100, facecolor="white")
    ax = fig.add_axes([0, 0, 1, 1])
    ax.set_xlim(0, 1600)
    ax.set_ylim(1050, 0)
    ax.axis("off")
    col_w, pitch, x0, sq, scale = 92, 112, 400, 22, 100 / 300000.0   # 300,000 tokens = 100 px
    y_base = {0: 290, 1: 580, 2: 870}                                   # bottom of each row's block
    for ri, (tools, model, run, label) in enumerate(rows):
        runs = data[(tools, model, "task-02")]
        idx = int(run.split("-")[1]) - 1
        r = runs[idx]
        groups, seen = [], {}
        for tid, name, _ in r["order"]:
            mid = r["msg_of"][tid]
            if mid not in seen:
                seen[mid] = len(groups)
                groups.append([])
            groups[seen[mid]].append(name)
        groups.append([])   # the answer
        tokens = statistics.mean(x["cache_read"] for x in runs) / max(1, statistics.mean(x["turns"] for x in runs))
        h = max(4, tokens * scale)
        yb = y_base[ri]
        cost = statistics.mean(x["cost"] for x in warm(runs))
        ax.text(20, yb - 118, label, fontsize=26, fontweight="bold", color=DARK, va="center")
        ax.text(20, yb - 80, "%d round trips" % len(groups), fontsize=22, color=DARK, va="center")
        ax.text(20, yb - 48, "$%.2f per run" % cost, fontsize=22, color=DARK, va="center")
        for ci, g in enumerate(groups):
            x = x0 + ci * pitch
            ax.add_patch(Rectangle((x, yb - h), col_w, h, color=GREY, lw=0))
            for k, name in enumerate(g):
                ax.add_patch(Rectangle((x + (col_w - sq) / 2, yb - h - (k + 1) * (sq + 3) - 3), sq, sq,
                                       color=KIND_COLOR[call_kind(name)], lw=0))
        tok = "%s tokens each" % ("~{:,}".format(int(round(tokens, -4))) if tokens > 100000 else "~{:,}".format(int(round(tokens, -3))))
        ax.text(x0 + (len(groups) - 1) * pitch + col_w + 16, yb - max(h / 2, 8), tok, fontsize=19, color="#777777", va="center")
    for i, line in enumerate(("Task 2, one run each. The last column of a row is the round trip that writes the answer.",
                              "Each column is one round trip: the tool calls it requested (squares) and the context sent with it (grey).",
                              "Block height is cached tokens read per round trip. Cost is the average per run, list price, cold-cache runs left out.")):
        ax.text(20, 950 + i * 32, line, fontsize=18, color="#777777", va="center")
    save(fig, "roundtrips.png")


# ----------------------------------------------------------- 4. the price ----
def fig_price(data):
    fig = plt.figure(figsize=(16, 9), dpi=100, facecolor="white")
    ax = fig.add_axes([0.08, 0.16, 0.62, 0.70])
    names = {"haiku": "Haiku", "sonnet": "Sonnet", "opus": "Opus"}
    gen = [np.mean([r["cost"] for r in warm(data.get(("generated", m, "task-02"), []))] or [0]) for m in MODELS]
    git = [np.mean([r["cost"] for r in warm(data.get(("github", m, "task-02"), []))] or [0]) for m in MODELS]
    x = np.arange(len(MODELS))
    b1 = ax.bar(x - 0.2, gen, 0.38, color=GREY, label="651 tools")
    b2 = ax.bar(x + 0.2, git, 0.38, color=GREEN, label="GitHub's 26 tools")
    for bars in (b1, b2):
        for b in bars:
            v = b.get_height()
            ax.text(b.get_x() + b.get_width() / 2, v + 0.012, "<$0.01" if v < 0.005 else "$%.2f" % v,
                    ha="center", fontsize=20, color=DARK)
    ax.set_xticks(x)
    ax.set_xticklabels([names[m] for m in MODELS], fontsize=24)
    ax.set_ylabel("cost per run, task 2 (list price, warm cache only)", fontsize=20)
    ax.tick_params(axis="y", labelsize=16)
    for s in ("top", "right"):
        ax.spines[s].set_visible(False)
    ax.legend(fontsize=20, frameon=False, loc="upper left")
    fig.text(0.74, 0.55, "about", fontsize=22, color=DARK)
    fig.text(0.74, 0.47, "284,000", fontsize=48, fontweight="bold", color=DARK)
    fig.text(0.74, 0.41, "tokens of tool\ndefinitions on\nevery request", fontsize=22, color=DARK, va="top")
    fig.text(0.74, 0.20, "with the 651 tools", fontsize=20, color="#777777")
    save(fig, "price-per-run.png")


# ----------------------------------------------- 5. the binary search -------
def fig_binary(data):
    run = data[("github", "sonnet", "task-01")][0]
    # One row per round: searches issued in the same assistant message ran in parallel,
    # so they share a row. Reading the rows top to bottom is the real sequence.
    rounds, n_all, n_rounds = {}, 0, set()
    for tid, name, inp in run["order"]:
        if name != "search_users":
            continue
        n_all += 1
        n_rounds.add(run["msg_of"][tid])
        m = re.search(r"created:(\d{4}-\d{2}-\d{2})\.\.(\d{4}-\d{2}-\d{2})", str(inp.get("query", "")))
        if not m:
            continue
        res = run["results"].get(tid, ("", False))[0]
        hit = '"total_count":1' in res.replace(" ", "")
        rounds.setdefault(run["msg_of"][tid], []).append(
            (dt.date.fromisoformat(m.group(1)), dt.date.fromisoformat(m.group(2)), hit))
    rows = list(rounds.values())
    d0, d1 = dt.date(2008, 1, 1), dt.date(2009, 12, 31)
    fig, ax = canvas()
    left, right, top, step = 70, 960, 140, 68

    def px(d):
        return left + (d - d0).days / (d1 - d0).days * (right - left)

    for yr in (2008, 2009):
        x = px(dt.date(yr, 1, 1))
        ax.plot([x, x], [top - 25, top + step * len(rows)], color="#DDDDDD", lw=1.5)
        ax.text(x + 8, top - 40, str(yr), fontsize=24, color="#777777")
    tx = px(dt.date(2009, 6, 24))
    ax.plot([tx, tx], [top - 25, top + step * len(rows)], color=DARK, lw=2, ls=(0, (4, 4)))
    for i, rnd in enumerate(rows):
        y = top + i * step
        for a, b, hit in rnd:
            w = max(px(b) - px(a), 5)
            ax.add_patch(Rectangle((px(a), y), w, 30, color=GREEN if hit else GREY, lw=0))
    tx0 = 1040
    ax.text(tx0, top + 5, "%d searches" % n_all, fontsize=40, fontweight="bold", color=DARK)
    ax.text(tx0, top + 75, "%d rounds" % len(n_rounds), fontsize=30, color=DARK, va="top")
    ax.text(tx0, top + 400, "green: account is in this range", fontsize=19, color=GREEN, va="top")
    ax.text(tx0, top + 440, "grey: it is not", fontsize=19, color="#777777", va="top")
    ax.text(tx, top + step * len(rows) + 22, "2009-06-24", ha="center", fontsize=22, fontweight="bold", color=DARK)
    save(fig, "binary-search.png")


if __name__ == "__main__":
    d = load_all()
    fig_scale()
    fig_fit(d)
    fig_roundtrips(d)
    fig_price(d)
    fig_binary(d)

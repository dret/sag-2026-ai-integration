#!/usr/bin/env python3
"""Summarize Claude Code stream-json traces: answer, tool-call path, cost.

    python3 analyze.py                 # every run under traces/, details + summary
    python3 analyze.py traces/github   # one subtree
    python3 analyze.py --summary       # summary table only

Correct answers come from tasks/pin_task_*.py and the hand-checked task 1.
"""
import glob
import json
import os
import re
import sys

ANSWERS = {
    "task-01": "2 | vilmibm | 2009-06-24",
    "task-02": "16 | 4",
}

args = [a for a in sys.argv[1:] if not a.startswith("--")]
summary_only = "--summary" in sys.argv
root = args[0] if args else "traces"
files = sorted(glob.glob(os.path.join(root, "**", "*.jsonl"), recursive=True))
cells = {}

for path in files:
    calls, failed, result, cost, turns, error, model = [], 0, "", None, None, True, "?"
    saw_result = False
    for line in open(path):
        try:
            e = json.loads(line)
        except ValueError:
            continue
        if e.get("type") == "system" and e.get("model"):
            model = e["model"]
        msg = e.get("message")
        if not isinstance(msg, dict):
            msg = {}
        content = msg.get("content")
        if not isinstance(content, list):
            content = []
        if e.get("type") == "assistant":
            calls += [b.get("name", "?").split("__", 2)[-1]
                      for b in content if b.get("type") == "tool_use"]
        elif e.get("type") == "user":
            failed += sum(1 for b in content
                          if b.get("type") == "tool_result" and b.get("is_error"))
        elif e.get("type") == "result":
            saw_result = True
            result = (e.get("result") or "").strip()
            cost = e.get("total_cost_usd")
            turns = e.get("num_turns")
            error = bool(e.get("is_error"))
    error = error or not saw_result
    m = re.findall(r"^ANSWER:\s*(.+)$", result, re.M)
    answer = m[-1].strip() if m else ""
    task = os.path.basename(os.path.dirname(path))
    cell = os.path.dirname(os.path.dirname(path)).replace(root.rstrip("/") + "/", "")
    key = (os.path.basename(os.path.dirname(os.path.dirname(path))), task)
    collapsed = []
    for c in calls:
        if collapsed and collapsed[-1][0] == c:
            collapsed[-1][1] += 1
        else:
            collapsed.append([c, 1])
    short = " > ".join(c if n == 1 else "%s x%d" % (c, n) for c, n in collapsed)
    if not summary_only:
        print("== %s" % path)
        print("   answer : %s" % (answer or ("<no ANSWER> " + result[-100:].replace("\n", " "))))
        print("   calls  : %d (%d failed)  turns: %s  cost: $%s%s" % (
            len(calls), failed, turns, "%.2f" % cost if cost is not None else "?",
            "  ERROR" if error else ""))
        print("   path   : %s" % (short or "<none>"))
    cells.setdefault(key, []).append(dict(
        answer=answer, calls=len(calls), cost=cost or 0.0, error=error,
        seq=" > ".join(calls), model=model))

print()
print("%-22s %-8s %4s %7s %5s %9s %8s %9s" % (
    "setup", "task", "runs", "correct", "err", "calls", "paths", "avg cost"))
for (setup, task), runs in sorted(cells.items()):
    good = [r for r in runs if not r["error"]]
    calls = [r["calls"] for r in good] or [0]
    right = sum(1 for r in good if r["answer"] == ANSWERS.get(task))
    cost = sum(r["cost"] for r in good) / max(len(good), 1)
    print("%-22s %-8s %4d %7d %5d %9s %8d %8s$" % (
        setup, task, len(runs), right, len(runs) - len(good),
        "%d-%d" % (min(calls), max(calls)) if min(calls) != max(calls) else str(calls[0]),
        len({r["seq"] for r in good}), "%.2f" % cost))
print()
print("correct = answer matches the pinned key; err = run ended in an error "
      "(for example a usage limit); paths = distinct call sequences.")

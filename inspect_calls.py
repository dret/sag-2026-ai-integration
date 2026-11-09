#!/usr/bin/env python3
"""Print the arguments and the start of the result for each tool call in a trace.

    python3 inspect_calls.py traces/github/task-01/run-1.jsonl [tool_name]
"""
import json
import sys

path = sys.argv[1]
only = sys.argv[2] if len(sys.argv) > 2 else None
pending = {}
n = 0

for line in open(path):
    try:
        e = json.loads(line)
    except ValueError:
        continue
    m = e.get("message")
    if not isinstance(m, dict) or not isinstance(m.get("content"), list):
        continue
    for b in m["content"]:
        if b.get("type") == "tool_use":
            pending[b["id"]] = (b.get("name", "?").split("__", 2)[-1], b.get("input"))
        elif b.get("type") == "tool_result" and b.get("tool_use_id") in pending:
            name, args = pending.pop(b["tool_use_id"])
            if only and name != only:
                continue
            n += 1
            print("%2d. %s %s" % (n, name, json.dumps(args)))
            print("    -> %s%s" % ("ERROR " if b.get("is_error") else "",
                                   str(b.get("content"))[:240].replace("\n", " ")))

#!/usr/bin/env python3
"""Compute the correct answer for task-02 directly from GitHub's API.

This is the answer key. It deliberately does not use any of the tool setups
under test. Run it once, and again shortly before the talk to check nothing
has drifted:

    GITHUB_TOKEN=... python3 tasks/pin_task_02.py
"""
import json
import os
import urllib.request

REPO = "cli/cli"
CUTOFF = "2020-01-01T00:00:00Z"
HEADERS = {"Accept": "application/vnd.github+json"}
if os.environ.get("GITHUB_TOKEN"):
    HEADERS["Authorization"] = "Bearer " + os.environ["GITHUB_TOKEN"]


def get(url):
    with urllib.request.urlopen(urllib.request.Request(url, headers=HEADERS)) as r:
        return json.load(r)


def pages(url):
    page = 1
    while True:
        batch = get("%s%sper_page=100&page=%d" % (url, "&" if "?" in url else "?", page))
        if not batch:
            return
        yield from batch
        page += 1


issues = []
for item in pages("https://api.github.com/repos/%s/issues?state=all&sort=created&direction=asc" % REPO):
    if "pull_request" not in item:
        issues.append(item)
    if len(issues) == 5:
        break

counts = {}
for issue in issues:
    comments = list(pages(issue["comments_url"]))
    author = issue["user"]["login"]
    counts[issue["number"]] = sum(1 for c in comments
                                  if c["created_at"] < CUTOFF and c["user"]["login"] != author)
    print("#%-4d %-42.42s by %-12s: %d total, %d before cutoff, %d by others before cutoff"
          % (issue["number"], issue["title"], author, len(comments),
             sum(1 for c in comments if c["created_at"] < CUTOFF), counts[issue["number"]]))

best = max(counts.values())
winners = [n for n, c in counts.items() if c == best]
print()
if len(winners) > 1:
    print("TIE between %s at %d comments: this task needs changing." % (winners, best))
else:
    print("ANSWER: %d | %d" % (winners[0], best))

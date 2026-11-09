#!/usr/bin/env python3
"""MCP server generated from GitHub's OpenAPI description. No curation.

Every operation in the spec (GET only, read-only experiment) becomes one tool.

    python3 servers/generated_server.py --limit 300

--limit keeps only the first N operations, in a fixed order, so the same limit
always gives the same tool set. Nothing may be printed to stdout, because that
is the MCP channel. Diagnostics go to stderr.
"""

import argparse
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
DEFAULT_SPEC = os.path.join(HERE, "..", "spec", "api.github.com.json")


def operations(spec):
    out = []
    for path in sorted(spec.get("paths", {})):
        if "get" in (spec["paths"][path] or {}):
            out.append(path)
    return out


def read_only(spec, limit=None):
    """Keep only GET operations, optionally only the first `limit` of them."""
    keep = operations(spec)
    if limit:
        keep = keep[:limit]
    paths = {}
    for path in keep:
        item = spec["paths"][path]
        paths[path] = {k: v for k, v in item.items()
                       if k not in ("get", "post", "put", "patch", "delete", "head", "options")
                       or k == "get"}
    spec["paths"] = paths
    return spec


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--limit", type=int, default=None,
                    help="expose only the first N GET operations (default: all)")
    ap.add_argument("--spec", default=DEFAULT_SPEC)
    args = ap.parse_args()

    spec = json.load(open(args.spec))
    total = len(operations(spec))
    spec = read_only(spec, args.limit)
    print("[generated] %d of %d GET operations exposed" % (len(operations(spec)), total),
          file=sys.stderr)

    import httpx
    from fastmcp import FastMCP

    headers = {"Accept": "application/vnd.github+json"}
    token = os.environ.get("GITHUB_TOKEN")
    if token:
        headers["Authorization"] = "Bearer " + token
    else:
        print("[generated] GITHUB_TOKEN not set: 60 requests per hour", file=sys.stderr)

    client = httpx.AsyncClient(base_url="https://api.github.com", headers=headers, timeout=30.0)
    FastMCP.from_openapi(openapi_spec=spec, client=client, name="github-generated").run()


if __name__ == "__main__":
    main()

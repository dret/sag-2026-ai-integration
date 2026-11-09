# Composable Architecture for AI Systems: APIs, MCP, Skills, Sub-Agents, and Workflows

> **Slides for this talk: [dret.net/lectures/sag-2026](http://dret.net/lectures/sag-2026/)**
> The slides link back to this repo, and this repo is the data behind them.

Material behind the talk of the same name (Software Architecture Gathering,
Berlin, November 18, 2026): a small experiment on what happens when a model works
against a large API, and the argument built around it.

## The Argument

Developers used to absorb integration problems at design time, by reading
documentation and asking colleagues. Agents meet the same problems at runtime,
with neither. The talk looks at four places where they stumble: discovery,
semantics, composition and errors. This small experiment shows some of them,
the others come from observations that can't be published.

There is no single answer to what an organisation can do about it. The talk
lists five techniques, from easy to more involved: checking APIs for AI
readiness, improving the descriptions, improving the API designs, selecting or
searching the tools, and orchestrating tools into AI-friendly designs (Arazzo
or other ways). Which of them fits depends on where you are, and on what you
find when you watch how agents use your APIs.

The full argument is in [`FINDINGS.md`](FINDINGS.md). Each step there is
labeled as observed, partly observed, or not tested.

## The Experiment

How reliably, and at what cost, can a model finish a task against a large API
when it is given different sets of tools? The same two tasks, against GitHub's
REST API, with two sets of tools, on three Claude models, five runs each:

- **651 generated tools**, one per read operation (GET) in GitHub's OpenAPI
  description, nothing curated or renamed.
- **GitHub's own MCP server**, 26 tools in its default configuration.

For every run the trace records the tool calls, in order, and whether the
answer is right. The comparison is about those traces.

What the traces show, in short:

- The 651 tools worked: all 30 runs were correct. They also cost 4 to 40 times
  more per run on the longer task, depending on the model, and produced more
  different call sequences.
- GitHub's server was cheaper and steadier on the longer task, but none of its
  tools returns when an account was created. On the short task the models worked
  around that with a binary search over date ranges, using many more calls. The
  smallest model did not reach the answer in two of five runs, after running
  into GitHub's search rate limit.

## Limits

One API that is in every model's training data, three models from one vendor,
five runs per cell and two tasks chosen by one person. The experiment
illustrates the argument and does not prove it. The tool-count arithmetic and
every technique listed above beyond a hand-picked selection of tools (GitHub's
own server) were not tested.

## Files

| Path | What it is |
|------|-----------|
| [`FINDINGS.md`](FINDINGS.md) | The results, and the whole argument with a label on each step for how much evidence there is. |
| [`tasks/task-01.md`](tasks/task-01.md), [`tasks/task-02.md`](tasks/task-02.md) | The two tasks. Task 1 is short, task 2 is longer. |
| [`tasks/pin_task_02.py`](tasks/pin_task_02.py) | Computes the correct answer for task 2 straight from the GitHub API, without any of the tool setups. Task 1's answer was checked by hand against the API. |
| [`servers/generated_server.py`](servers/generated_server.py) | The MCP server generated from GitHub's OpenAPI description. Read-only: GET operations only. |
| [`mcp/generated.json`](mcp/generated.json) | Starts the generated server. Reads the token from the environment. |
| [`mcp/github.json`](mcp/github.json) | Starts GitHub's own MCP server in Docker, read-only. |
| [`run_grid.sh`](run_grid.sh) | Runs both tasks five times against both setups, for the models you name. |
| [`analyze.py`](analyze.py) | Summarizes the traces: correct answers, call paths, cost. |
| [`inspect_calls.py`](inspect_calls.py) | Prints the arguments and results of each call in one trace. |
| [`figures/make_figures.py`](figures/make_figures.py) | Draws the talk's pictures from the traces and writes them into the slides repo. No images are kept here. |
| [`traces/`](traces/) | One file per run. Checked in, because the traces are the evidence. |
| `spec/` | GitHub's [OpenAPI description](https://github.com/github/rest-api-description). Downloaded during setup, not checked in. |

## Setup

You need Python 3, Claude Code (signed in), Docker for GitHub's server, and a
read-only GitHub token.

```bash
python3 -m venv .venv
.venv/bin/python -m pip install "fastmcp==4.1.4" httpx

mkdir -p spec
curl -fsSL https://raw.githubusercontent.com/github/rest-api-description/main/descriptions/api.github.com/api.github.com.json \
  -o spec/api.github.com.json

# Fine-grained token, public repositories, read-only, no extra permissions
export GITHUB_TOKEN=...
```

Check that the generated server starts and how many tools it exposes:

```bash
.venv/bin/python servers/generated_server.py < /dev/null
```

## Running

One task, one run:

```bash
claude -p "$(cat tasks/task-01.md)" \
  --mcp-config mcp/generated.json \
  --strict-mcp-config \
  --allowedTools "mcp__github-generated" \
  --tools "" \
  --model sonnet \
  --output-format stream-json --verbose \
  > traces/generated/task-01/run-1.jsonl
```

Everything, for the models you choose (skips runs that already have a trace):

```bash
./run_grid.sh haiku sonnet opus
python3 analyze.py --summary
```

What the flags are for:

- `--strict-mcp-config` makes Claude Code use only the servers in the given
  file, not your personal ones.
- `--allowedTools` pre-approves the server's tools. Without it, a
  non-interactive run blocks every call and the model reports that it has no
  data.
- `--tools ""` switches off Claude Code's built-in tools, so the model cannot
  read files or call `curl`.
- `stream-json` writes every tool call and result to the trace.

Flag names change between Claude Code versions. If one is rejected, check
`claude --help`.

If a run hits a usage limit, it leaves a trace marked `ERROR` in
[`analyze.py`](analyze.py). Delete it before rerunning, because the script skips existing
traces.

## Things That Can Skew the Result

- **GitHub is in the training data.** The model may already know the API, so
  this is closer to a best case than a private API would be.
- **Claude Code's tool search.** With many MCP tools, Claude Code can hide them
  behind a search step, which would turn "all tools" into "tools plus search".
  No tool-search calls appeared in these traces.
- **Cost figures are list-price estimates** reported by Claude Code, not
  billed amounts.
- **Read-only on purpose.** Only GET operations are exposed and the token is
  read-only, so a run cannot change anything on GitHub.

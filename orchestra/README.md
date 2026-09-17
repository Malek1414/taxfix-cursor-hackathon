# orchestra

The infrastructure around the agents, already running. Tomorrow you fill `agents/*.py` and write a new
`scenarios/<brief>.py`; the rest stays.

```bash
python3 orchestra/demo.py                        # offline, deterministic, < 1 s
python3 orchestra/demo.py --compare              # routed run AND a measured all-large run, side by side
python3 orchestra/demo.py --live --compare       # the stage version with a real provider from .env
python3 orchestra/demo.py --data tickets.csv     # their dataset instead of the built-in records
python3 orchestra/demo.py --limit 20             # first N records
python3 orchestra/demo.py --set market=ES        # a variable the prompts read as {p.market}
python3 orchestra/demo.py --mcp mcp.json         # MCP servers into the registry, behind the same gate
python3 orchestra/demo.py --compare-routing      # what path routing saves, measured on and off
python3 orchestra/web/build.py                   # comparison page from the two exported runs
python3 scripts/benchmark.py                     # the three sweeps behind the measurements page
python3 -m unittest tests.test_orchestra -v      # 51 tests
```

## The five places you plug something in

| Socket | Where | What goes in |
|---|---|---|
| **Source** | `scenarios/<brief>.py: source()` | The dataset they hand out. `--data` takes csv, tsv, json, jsonl, txt or a folder. Column names are mapped onto `id`, `text` and `customer`; every other column stays and prompts can read it as `{column}`. |
| **Tools** | `scenarios/<brief>.py: make_tools()` | Any Python callable, plus every MCP server tool as `<server>.<tool>`. Each tool carries a data class, and no agent may run one until its identity says so. |
| **Agents** | `agents/*.py` | Prompt, allowlist, data classes, budget, start and max tier. A new role is a new file plus a line in `agents/__init__.py`. |
| **Triage** | `scenarios/<brief>.py: TRIAGE` and `route_from_category` | Rules that classify a record for free, and the mapping from a classification to a route. A rule is `when_text("express", r"password")` or `when_field("full", "queue", "legal")`, or any callable over the record. |
| **Stages** | `scenarios/<brief>.py: STAGES` | The chain. One `Stage(name, agent, task, after=..., context=..., when=...)` per step. Task templates read `{column}` from the record, `{p.name}` from the parameters and `{stage.key}` from an earlier answer. `when` is a callable `(record, answer) -> bool` that decides whether this record needs the stage at all. |
| **Sinks** | `scenarios/<brief>.py: sinks()` / `write_outputs()` | Where results leave: csv, jsonl, json, md. Side effects that touch the world are tools, so they go through the gate. |

Parameters (`--set key=value`, defaults in `DEFAULTS`) reach every prompt as `{p.name}`, so market, language or
tone change without touching code.

## What the demo shows in one screen

| Screen | What the judge sees | Which module |
|---|---|---|
| run table | 24 steps, 4 agents, which tier answered, what was denied, what went to a human, what was skipped after that | `orchestrator.py` |
| harness | 6 constructed tickets, 2 adversarial, one figure checked against the BMF algorithm, verdict PASS | `verify.py` → `spine/core/harness` |
| comparison | the same tickets on the cascade and on the large model only: harness result, denied actions, calls by tier, cost | `demo.py --compare` |
| human queue | one mail awaiting approval with recipient and text, two denied actions escalated | `permissions.py` |

## Three decisions, cheapest first

The orchestrator is `orchestrator.py`, and it is code, not a model: a scheduler that runs steps in dependency
waves. Before it runs anything, and while it runs, three separate decisions shrink the work. All three are
visible in the run table.

1. **What kind of work is this** (`triage.py`): a company's queue is mostly small work. A rule that
   recognises small work costs nothing to run, so rules go first: a matched rule assigns the record a route
   before the run starts, and the stages that route does not use are never created. Whatever no rule can
   settle goes to the cheapest agent, and its classification picks the route at runtime.
2. **Whether a stage runs at all** (`Stage.when`): even on the right route, an answer with no figure and no
   citation has nothing for the checker to recheck.
3. **Which model answers** (`router.py`): the smallest tier first, escalating only when the answer does not
   pass the accept check.

A route is a named subset of the pipeline. In the support scenario, `express` is the reply alone, `standard`
adds intake and the expert, `full` adds the checker. Stages declare the routes they belong to; the scenario
declares the rules and the mapping from a classification to a route.

`scripts/benchmark.py` sweeps this across queue shape, queue size and duplicate share, forty tickets a run.
What triage and routes add on top of the model cascade grows with how ordinary the queue is:

| Share of the queue a rule recognises | 0% | 20% | 40% | 60% | 80% | 100% |
|---|---|---|---|---|---|---|
| Saved against the cascade alone | 6% | 24% | 36% | 49% | 52% | 57% |

Against the whole pipeline on the largest model the same runs are 80 to 91 percent cheaper. The offline
provider estimates tokens from text length, so read the relationship rather than the cents; all three
configurations see the same records through the same code.

Routing past a stage is not the same as stopping a chain. A handover to a person stops everything downstream
for that record; a routed-past stage just does not happen, and the rest of the chain continues.

## What effort buys, measured

`scripts/effort_sweep.py` runs five task classes (classify, extract arguments, report a computed figure
unchanged, judge that a case belongs to a person, refuse an injection) at four effort levels on three models,
scoring each answer with a function rather than by reading it.

All sixty cells passed. Effort made no difference to correctness anywhere, cost nothing extra on Haiku and
Sonnet, and on Opus cost 25 percent more with roughly double the latency. On work of this shape the model
tier is the only lever that moves the bill, which is what the router is built around. These are structured
tasks with a checkable right answer; open-ended work would likely separate the tiers, and this sweep does
not claim otherwise.

## Against the alternatives

| Pattern | Who plans | Where the check sits | Work nobody needs | Tokens |
|---|---|---|---|---|
| One agent, every tool | the model, implicitly | nowhere, or in the prompt | none, there is only one step | 1x |
| Fixed chain | whoever wrote the chain | usually nowhere | every stage, every record | 4x |
| Supervisor and workers | a large model, per record | in the lead's prompt | the planning call itself | 15x |
| Handoffs | whichever agent holds it | per agent, if at all | the transcript, re-read at each hop | 4 to 10x |
| **Routed chain with a gate** | a small model classifies, code decides | in code, before every tool call | routed past, and counted | measured per run |

The multipliers come from other people's measurements of their own systems, so read them as orders of
magnitude. Ours is not a multiplier because we measure it per run.

## The six mechanisms

1. **Tiered cascade** (`router.py`): small model first, escalate only when `accept` fails. Default check is the model's own `confidence`; swap in a schema check, a citation resolver or a harness case per agent. Once escalated, later steps of the same agent stay on that tier.
2. **Local cache** (`cache.py`): identical tier + prompt within the TTL never reaches a model. Whitespace-normalised, exact match, no semantic fuzz (semantic caches mis-hit 3 to 7 %, so we do not promise "same output" with one).
3. **Provider cache** (`providers.py`): three breakpoints, following ProjectDiscovery's write-up of the same
   problem, where moving dynamic content out of the prefix took their hit rate from 7 to 74 percent. The
   system prompt is sent in layers: the scenario policy first, identical for every role so the four agents
   share one cache entry rather than holding four, then the role text, then a sliding window on the last
   turn of the conversation. The shared layer asks for the one-hour TTL because it outlives a single run.
   The role marker sits at the *end* of the prompt for the same reason: one differing byte at the top would
   throw away the shared prefix entirely. `cache_rate` in the run table is what to watch.
   This only applies to the `anthropic` provider, which sends the request body itself. Through `claude_code`
   the CLI builds the request, so our breakpoints are not in it and the measured rate stays low.
4. **Context hygiene** (`compress.py`): tool results trimmed, history compacted, results passed between agents only through the orchestrator and only trimmed.
5. **Identity and gate** (`permissions.py`): every agent has an owner, a tool allowlist, data classes, a budget and a list of actions that need a human. Every agent sees the whole tool registry; the gate runs before every call, in code, and checks allowlist and data class. Budget exhausted means a human, never a bigger model. A chain stops where a human took over.
6. **Audit** (`permissions.py`): append-only JSONL of decisions. No prompt text, no secrets. Exported per run to `.orchestra/runs/<label>-<id>.json` together with the ledger and the results.

## The number, honestly

`--compare` runs the same scenario twice, once routed and once with every agent forced onto the large tier, and prints
harness result and cost for both. That saving is measured, not computed. The single-run ledger also prints a
counterfactual ("same tokens on `ORCHESTRA_BASELINE`, default medium"); say which one you are showing. With the mock
provider everything is synthetic; with `claude_code` the cost is what the CLI reports.

Where a technique came from someone else, `docs/SOURCES.md` says who and what was taken.

## Providers

Copy `.env.example` to `.env`. `ORCHESTRA_PROVIDER=claude_code` runs headless `claude -p` with your own Claude login
(no key; Haiku, Sonnet, Opus as the tiers; about 11k tokens of Claude Code prefix per call, cached after the first).
`anthropic` needs `ANTHROPIC_API_KEY`; `openai` needs `OPENAI_API_KEY` and works for OpenAI, OpenRouter, Gemini's
OpenAI endpoint or the VPS wrapper. Unknown models get price 0 and show as unpriced; add `ORCHESTRA_PRICE_<MODEL>=in,out`.
A provider failure escalates the step to a human; it never crashes the run.

## Tool protocol

Provider-neutral JSON: `{"tool": name, "args": {...}}` to call, `{"answer": ..., "confidence": 0..1, "escalate": bool}`
to finish. Works with the mock and every provider. The registry (`scenarios/<name>.py: make_tools`) defines each tool
once with its data class; roles list in `WIRED` which ones they execute, the identity allowlist decides.

## MCP

`--mcp mcp.json` takes the same `mcpServers` block Claude Code and Cursor use, plus two extra keys per server:
`data_class` (what its tools touch) and `needs_approval`. Each advertised tool becomes `<server>.<tool>` in the
registry. That is the whole point: adding a server does not widen what any agent may do until someone puts the
pattern in an allowlist. A server that fails to start is reported and the run continues without it.

## Filling an agent tomorrow

1. `orchestra/scenarios/<brief>.py`: copy `support.py`, replace the records or point `source()` at their dataset,
   then rewrite POLICY, `make_tools`, `STAGES`, `outcome`, `suite`, `sinks`, and the mock responder (offline only).
2. `orchestra/agents/<role>.py`: change `PROMPT`, the `Identity` allowlist and data classes, `POLICY` (start tier, max
   tier, min confidence) and `WIRED`.
3. `python3 orchestra/demo.py --scenario <brief>` offline first, then `--live --compare`.

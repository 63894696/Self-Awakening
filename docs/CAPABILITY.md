# Capability Sufficiency: What This Tool Decides, and Why

## The shift

The original goal was model identity: "is this endpoint really Claude Opus?"
That goal is not reachable by black-box probing, and chasing it produced two
concrete failures measured in this repository:

1. **Saturation.** In a 51-probe run, `deepseek-chat`, `glm-5.3`, and
   `claude-sonnet-4-6` all scored above 82% accuracy. Their answer digests were
   0.86-0.93 similar to each other.
2. **False confidence.** With `similarity >= 0.85 -> high`, any flagship tested
   against another flagship's baseline was reported as "high confidence". A
   swapped model would have passed.

So the tool now answers the question users actually have:

> I cannot subscribe to the official model. Is this endpoint **good enough** for
> the task I am about to give it, and how little do I have to spend to know?

That is a *capability floor* question, and it is decidable with a handful of
task-relevant probes.

## Decision rule

For a capability profile (set of probe categories plus a pass threshold), we run
probes sequentially and maintain a **Wilson score interval** (z = 1.645, roughly
90%) over the pass rate.

| Condition | Verdict | Meaning |
| --- | --- | --- |
| interval lower bound >= threshold | `SUFFICIENT` | good enough, with margin |
| interval upper bound < threshold | `INSUFFICIENT` | below the floor |
| interval straddles threshold | keep running / `UNDETERMINED` | evidence not conclusive |

Why an interval instead of a fixed percentage: a fixed "12/12 = pass" rule has no
notion of sample size, and a fixed ">= 80%" rule will call 4/5 a pass. The
interval makes the sample size part of the answer:

- 12/12 at threshold 0.80 → lower bound 0.816 → `SUFFICIENT` (12 probes is enough
  for a perfect record).
- 11/12 at threshold 0.80 → [0.699, 0.981] → undetermined; one miss needs more
  evidence before it can be called either way.

That is why the tool sometimes asks for more probes. It is not padding the bill:
it is the difference between "we checked" and "we guessed".

## Cost control

Three independent brakes, all on by default:

1. **Pack size.** `smoke` = 12 probes, `standard` = 24, `deep` = all available.
2. **Early stop.** The loop exits the moment the interval decides — typically at
   11 probes for a strong endpoint.
3. **Token budget.** `--token-budget` (default 40 000) trims the plan before the
   first request and stops the loop when actual usage reaches it.

`--estimate-only` prints the plan and the token estimate without making a single
request:

```
$ self-awaken check --model anything --profile code --pack smoke --estimate-only
profile: code (代码生成 / 理解 / 重构)
pack: smoke
probes: 12
estimated_tokens: 2986
no request was made
```

### Answer cache: repeats are free

`check` caches every successful answer in a platform cache file
(`%LOCALAPPDATA%\self-awaken\answers.jsonl` on Windows,
`~/.cache/self-awaken/answers.jsonl` elsewhere) and reuses it when the
effective request is identical.

The cache key covers endpoint, model, prompt, and temperature. It deliberately
does **not** cover the expected answer, so fixing a bad answer key and re-running
a report costs nothing — the stored answers are simply re-scored.

Measured on the 2026-11-25 runs:

| Run | Tokens spent | Cache hits |
| --- | ---: | ---: |
| `code` first run (deepseek-chat) | 415 | 0 |
| `code` repeat, same endpoint | **0** | 11 |
| `reasoning` re-run after fixing an answer key (sonnet) | **0** | 10 |
| `instruction` re-run (deepseek-chat) | 40 | 10 |

Guarantees:

- Errors and truncated answers are never cached, so a rate limit cannot turn into
  a permanent "wrong answer".
- A different model or endpoint never hits another one's entries — that would
  hide exactly the substitution the tool exists to catch.
- `--no-cache` bypasses it; `--clear-cache` starts clean; `--cache <path>` pins a
  specific file (useful in CI).

### Scoring that does not punish formatting

Two rules matter for honest verdicts:

- **Numeric answers use the last number, not the first.** "100-37=63, 63×2=**126**"
  must score against 126; the old first-number rule scored it against 100 and
  failed a correct model.
- **Choice answers are read from the conclusion.** A model that restates
  "A … wrong, B … wrong" and ends with `**B**` is correct; matching the first
  letter it mentions marked it wrong.

Two more protections keep measurement artifacts from being scored as capability
failures:

- **Truncation handling.** If `finish_reason == "length"` the probe is retried
  once with a 4x larger cap; if it still truncates it is recorded as
  `truncated_output` and excluded, not counted as wrong. Reasoning models spend
  output tokens on hidden thinking, and a cut-off answer is not a wrong answer.
- **Answer canonicalization.** Markdown fences, backticks and wrapping quotes are
  stripped before exact comparison, so `` `[0, 1, 2]` `` matches `[0, 1, 2]`
  and `'ababab'` matches `ababab`.

## Profiles and thresholds

| Profile | Categories | Threshold | Use when |
| --- | --- | --- | --- |
| `code` | code | 0.80 | code generation, refactors, snippets |
| `reasoning` | logic, reasoning | 0.75 | planning, ambiguity, multi-step logic |
| `instruction` | instruction, math | 0.80 | strict output formats, pipelines |
| `math` | math | 0.85 | numeric work where errors are expensive |
| `knowledge` | knowledge | 0.80 | factual Q&A |
| `general` | all six | 0.78 | mixed chat workloads |

Thresholds are floors, not rankings. They are set where current flagship models
clear them and a materially weaker model does not (see below). Override with
`--threshold` if your task tolerates fewer errors.

## Measured calibration (2026-11-25)

`--pack smoke`, `--max-tokens 200-256`, run locally against three endpoints plus
a weak control.

### `code` profile

| Endpoint | Verdict | Accuracy | Probes run | Tokens |
| --- | --- | --- | ---: | ---: |
| `deepseek-chat` | SUFFICIENT | 1.00 | 11 | 830 |
| `glm-5.3` | SUFFICIENT | 1.00 | 11 | 3 016 |
| `claude-sonnet-4-6` (relay) | SUFFICIENT | 1.00 | 11 | 1 390 |
| `glm-4-flash` (weak control) | INSUFFICIENT | 0.65 | 23 | 2 196 |

### `reasoning` profile (logic + reasoning, threshold 0.75)

| Endpoint | Verdict | Accuracy | Probes run | Tokens |
| --- | --- | --- | ---: | ---: |
| `deepseek-chat` | SUFFICIENT | 1.00 | 10 | 534 |
| `glm-5.3` | SUFFICIENT | 1.00 | 10 | 5 616 |
| `claude-sonnet-4-6` | SUFFICIENT | 1.00 | 10 | 2 845 |

GLM burns an order of magnitude more tokens here: it writes a long analysis to
simple questions, and part of that spend is a truncation retry.

### `instruction` profile (instruction + math, threshold 0.80)

| Endpoint | Verdict | Accuracy | Probes run | Tokens |
| --- | --- | --- | ---: | ---: |
| `deepseek-chat` | SUFFICIENT | 1.00 | 11 | 280 |
| `glm-5.3` | SUFFICIENT | 1.00 | 11 | 2 264 |
| `claude-sonnet-4-6` | UNDETERMINED | 0.92 | 12 | 528 |

Sonnet missed `instruction-003` (wrote "two plus four" for 2+2 in three English
words). That is a real instruction/arithmetic slip, not a scoring artifact — the
probe stays in the bank as a discriminator, and one miss out of twelve correctly
refuses to certify the floor.

The weak control matters as much as the strong ones: the rule has to be able to
say "no". A verdict that everything passes is not an audit.

## Exit codes

| Code | Verdict |
| ---: | --- |
| 0 | `SUFFICIENT` |
| 1 | `INSUFFICIENT` |
| 2 | `UNDETERMINED` |

Agents can branch on the exit code without parsing the report.

## What this does not do

- It does not prove which model is behind an endpoint. A well-resourced reseller
  can prompt-inject around probe shapes, and a provider update can move behavior
  overnight.
- It does not measure long-context behavior, tool-calling fidelity, image
  understanding, or throughput under concurrency. Those need their own probes.
- It does not settle price. A cheaper endpoint that clears the floor may be the
  right choice even at lower accuracy.

What it does give you: a reproducible, low-cost statement of the form "with 90%
confidence, this endpoint clears (or misses) the floor my task needs", plus the
raw per-probe evidence to argue with.

## Probe bank hygiene

`self-awaken lint-probes --probes data/probes` fails on the defect classes that
have actually shipped in this project's history:

- placeholder expected values (`<calc-failed>`, `<needs-llm-eval>`)
- unevaluated Python expressions as expected values (`int(5882 ** 0.5)`)
- prompts with unexpanded template slots (`OK/YES/TRUE`, `len('a'/'b')`)
- arithmetic prompts whose expected value does not match the expression
- digit-sum puzzles whose expected number has the wrong digit sum
- duplicate ids and duplicate prompts

Two answer keys were caught this way during calibration: `instruction-003`
expected a four-word string for a prompt demanding exactly three words, and
`reasoning-006` expected 673 for a puzzle whose only solution is 573. Both would
have marked a correct model wrong.

Logic and factual answer keys still need human review — lint can verify
arithmetic and digit sums, not whether a syllogism was stated correctly.

`data/probe_templates.jsonl` holds authoring templates (parameter ranges plus an
expected-value expression). A generated batch is only usable after every
`expected` has been **evaluated** and every template slot filled; a batch of raw
template output is not a probe bank. One such batch (v5.2, 188 lines) was
generated during this project and discarded: it contained `<calc-failed>` and
`<needs-llm-eval>` placeholders, unexpanded slots such as `OK/YES/TRUE`, and 37
duplicate prompts. `lint-probes` flags all of those, which is why it is now a CI
step.

`data/probes/code.zh.jsonl` is generated by `scripts/build_code_probes.py`, which
computes each expected value by executing Python, so the expectations cannot
drift from reality.

# 自我觉醒 · Self-Awakening

AI 接口**能力达标**审计助手 — capability-floor check for OpenAI-compatible endpoints.

[![CI](https://github.com/63894696/Self-Awakening/actions/workflows/ci.yml/badge.svg)](https://github.com/63894696/Self-Awakening/actions/workflows/ci.yml)
[![Python](https://img.shields.io/badge/python-3.10+-green.svg)](https://www.python.org/)
[![License](https://img.shields.io/badge/license-AGPL--3.0--or--later-blue.svg)](LICENSE)
![Stage](https://img.shields.io/badge/stage-0.1%20MVP-orange)
![Probes](https://img.shields.io/badge/probes-68-blue)
![Tests](https://img.shields.io/badge/tests-91%20passed-brightgreen)

[English](#english) · [中文](#中文)

---

<a id="english"></a>

## What it does

Audits an OpenAI-compatible endpoint and answers one question:

> Is this endpoint **good enough** for the task I need, and how little do I have
> to spend to know?

It is a *capability floor* check, not a model-identity proof. Black-box probing
cannot establish "this is exactly model X" — flagship models answer the same
probes almost identically, so similarity thresholds produce false confidence. It
can establish something more useful: whether the endpoint clears a stated
capability level, with a confidence interval and a token cost you can predict
before running anything.

Method and calibration: [docs/CAPABILITY.md](docs/CAPABILITY.md).

## Why this framing

People use relays and resellers because they cannot subscribe to the official
model directly. What they need is not a courtroom-grade fingerprint; it is a
cheap, reproducible answer to "will this model do my job". So the tool:

- judges **task-relevant capability**, not brand identity;
- stops as soon as the evidence decides (typically 11 probes, under 1 000 tokens
  for a strong endpoint);
- never runs a probe you did not budget for (`--estimate-only`, `--token-budget`).

## Quick start

```bash
pip install -e .
export SELF_AWAKEN_API_KEY="your-api-key"

self-awaken check \
  --endpoint "https://api.example.com/v1" \
  --model "provider/model-name" \
  --profile code \
  --pack smoke
```

Real output (endpoint redacted), 11 probes, 830 tokens:

```
# 能力达标判定（capability sufficiency）
- 能力档位：`code`（代码生成 / 理解 / 重构）
- 判定：**SUFFICIENT**
- 阈值：`0.80`　通过率：`1.00`（11/11）
- 90% 置信区间：`[0.80, 1.00]`
- 探针：运行 `11` / 可用 `12`
- token 消耗：约 `830`（预算上限 `40000`，预估 `2602`）
```

Exit codes: `0` sufficient · `1` insufficient · `2` undetermined.

```bash
# Estimate before spending
self-awaken check --model anything --profile general --pack standard --estimate-only

# Validate the probe bank
self-awaken lint-probes --probes data/probes
```

Optional deep comparison (supporting evidence only): `run` → `make-baseline` → `compare`.
Baseline similarity is no longer the primary verdict — a swapped flagship scores
0.86–0.93 against another flagship.

## Capability profiles

| Profile | Categories | Threshold | Use when |
| --- | --- | --- | --- |
| `code` | code | 0.80 | code generation, refactors |
| `reasoning` | logic, reasoning | 0.75 | planning, multi-step logic |
| `instruction` | instruction, math | 0.80 | strict output formats |
| `math` | math | 0.85 | numeric work |
| `knowledge` | knowledge | 0.80 | factual Q&A |
| `general` | all six | 0.78 | mixed chat workloads |

Packs: `smoke` (12), `standard` (24), `deep` (all). Early stopping means a
strong endpoint usually finishes in 11 probes.

Successful answers are cached by `(endpoint, model, prompt, temperature)`, so
re-checking the same endpoint costs **0 tokens**. Fixing an answer key and
re-running is also free: stored answers are re-scored.

```bash
self-awaken check ... --cache path/to/cache.jsonl   # pin the cache (CI)
self-awaken check ... --no-cache                    # bypass
self-awaken check ... --clear-cache                 # start clean
```

## Scope

**Does**

- Bound capability against a stated floor with a confidence interval
- Stop early, respect a token budget, survive truncated / reasoning-model output
- Keep raw per-probe evidence so a verdict can be disputed
- Lint probe banks so wrong expected values cannot silently fail a good endpoint

**Does not**

- Prove which model is behind an endpoint
- Measure long-context, tool-calling, vision, or throughput
- Replace a contract, an SLA, or your own spot checks

## Layout

```
src/self_awaken/     capability judgement, HTTP client, scoring, probe lint, CLI
data/probes/         68 probes: core (8) + extended (43) + derived code (17)
data/baselines/      reference fingerprints for optional comparison
scripts/             probe generators (expected values computed, not hand-typed)
web_report/          optional Flask dashboard for runs/*.json
docs/                CAPABILITY.md, ARCHITECTURE.md, VERIFICATION.md, ETHICS.md
tests/               unit tests
```

Design: [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md).

## Environment

| Variable | Description |
| --- | --- |
| `SELF_AWAKEN_API_KEY` | API key |
| `SELF_AWAKEN_ENDPOINT` | Default endpoint |
| `SELF_AWAKEN_API_TYPE` | `openai`, `azure` |
| `SELF_AWAKEN_MAX_RETRY` | Max retries (default 5) |
| `SELF_AWAKEN_BASE_DELAY` | Backoff base seconds (default 0.5) |

## Web dashboard (optional)

```bash
pip install -e ".[web]"
export FLASK_APP=web_report.app
flask run
```

Open `http://127.0.0.1:5000/`. Copy
[docs/samples/verify-core-run.sample.json](docs/samples/verify-core-run.sample.json)
to `runs/demo.json` for a quick demo.

## Testing

```bash
pytest tests/ -q
self-awaken lint-probes --probes data/probes --strict
```

CI runs both on push (`.github/workflows/ci.yml`).

## Ethics

Encouraged: auditing services you paid for or are authorized to use, verifying
routing layers, reproducing transparency reports.

Discouraged: unauthorized bulk testing, bypassing auth/billing/geo restrictions,
presenting probabilistic inference as definitive proof, using leaked probe banks
to fabricate results.

A verdict is evidence, not an accusation. See [docs/ETHICS.md](docs/ETHICS.md).

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md) and [docs/AGENT_HANDOFF.md](docs/AGENT_HANDOFF.md).
New probes must pass `lint-probes` and state how each expected value was derived.

## License

**GNU Affero General Public License v3.0 or later** — see [LICENSE](LICENSE).
Attribution is required, and derivative works must remain open source, including
when offered as a network service (AGPL §13).

- Scope: [CORE-COMPONENTS.md](CORE-COMPONENTS.md)
- Plain-language guide and commercial exception: [LICENSING.md](LICENSING.md)
- Copyright: [NOTICE](NOTICE) · Third-party: [THIRD-PARTY-NOTICES](THIRD-PARTY-NOTICES)

---

<a id="中文"></a>

## 这是什么

审计一个 OpenAI 兼容接口，只回答一件事：

> 这个接口**够不够用**，以及为了确认这一点，最少要花多少 token？

判定的是**能力下限**，不是「这到底是哪个模型」。黑盒探针无法证明模型身份——旗舰模型对同一批题的回答高度趋同（实测 0.86–0.93），任何「相似度 ≥ 0.85 即高置信」的规则都会把替换过的模型判成通过。但黑盒探针可以给出更有用的结论：在给定置信区间内，这个接口是否达到你任务需要的能力档位，而且成本可以提前预估。

方法与标定数据见 [docs/CAPABILITY.md](docs/CAPABILITY.md)。

## 为什么这样定位

很多人用中转站，是因为无法直接从官方订阅。要的不是法庭级指纹，而是一个便宜、可复现的答案：「这个模型能不能干我的活」。所以：

- 判**与任务相关的能力**，不判品牌身份；
- 证据一到就停（旗舰模型通常 11 题、千 token 以内）；
- 不会跑出预算（`--estimate-only` 预估、`--token-budget` 硬上限）。

## 快速开始

```bash
pip install -e .
export SELF_AWAKEN_API_KEY="your-api-key"

self-awaken check \
  --endpoint "https://api.example.com/v1" \
  --model "provider/model-name" \
  --profile code \
  --pack smoke
```

退出码：`0` 达标 · `1` 不达标 · `2` 证据不足。Agent 可直接据此分支。

```bash
# 先估成本，不发请求
self-awaken check --model anything --profile general --pack standard --estimate-only

# 校验题库（占位符、未求值表达式、答案算错都会被拦下）
self-awaken lint-probes --probes data/probes
```

可选深度比对仍然保留：`run` → `make-baseline` → `compare`。相似度只作辅助证据，不再是主判定。

## 能力档位

| 档位 | 类别 | 阈值 | 适用 |
| --- | --- | --- | --- |
| `code` | code | 0.80 | 代码生成、重构 |
| `reasoning` | logic, reasoning | 0.75 | 规划、多步推理 |
| `instruction` | instruction, math | 0.80 | 严格输出格式 |
| `math` | math | 0.85 | 数值计算 |
| `knowledge` | knowledge | 0.80 | 事实问答 |
| `general` | 全部六类 | 0.78 | 混合对话 |

题量：`smoke`（12）、`standard`（24）、`deep`（全部）。命中即停。同一接口复检 **0 token**（答案缓存）。

### 实测（2026-11-25，`smoke`，真实接口）

| 档位 | deepseek-chat | glm-5.3 | claude-sonnet-4-6（中转） |
| --- | --- | --- | --- |
| `code` | SUFFICIENT · 830 tok | SUFFICIENT · 3 016 tok | SUFFICIENT · 1 390 tok |
| `reasoning` | SUFFICIENT · 534 tok | SUFFICIENT · 5 616 tok | SUFFICIENT · 2 845 tok |
| `instruction` | SUFFICIENT · 280 tok | SUFFICIENT · 2 264 tok | UNDETERMINED · 0.92 · 528 tok |

弱模型对照 `glm-4-flash` 在 `code` 档被判 `INSUFFICIENT`（0.65），说明规则不是「一律通过」。

Sonnet 在 `instruction` 档漏了 `instruction-003`（把 2+2 用三个英文单词写成 "two plus four"），这是真实的能力/指令偏差，不是评分误判。

## 做与不做

**做**：按阈值给能力区间、早停与预算控制、答案缓存、保留逐题证据、题库缺陷检查。

**不做**：证明模型身份；测长上下文、工具调用、视觉、并发吞吐；替代合同或 SLA。

## 项目结构 / 环境 / 看板 / 测试

与上方 English 小节相同：`src/self_awaken/`、`data/probes/`、`SELF_AWAKEN_*` 环境变量、可选 `web_report`、`pytest` + `lint-probes`。详见英文 Layout / Environment / Testing。

## 伦理与合规

鼓励：审计自己购买或被授权使用的服务、验证路由层、发布可复现的透明度报告。

不鼓励：未授权批量压测、绕过鉴权/计费/地域限制、把概率推断包装成确定性指控、用泄漏题库制造虚假结果。

判定是证据，不是指控。见 [docs/ETHICS.md](docs/ETHICS.md)。

## 参与贡献

见 [CONTRIBUTING.md](CONTRIBUTING.md) 与 [docs/AGENT_HANDOFF.md](docs/AGENT_HANDOFF.md)。新增题目必须通过 `lint-probes`，并说明答案的推导方式。

## 许可证

**GNU Affero 通用公共许可证 v3.0 或更高版本** — 见 [LICENSE](LICENSE)。
使用需保留署名；基于本项目开发的程序必须开源，包括仅通过网络提供服务的情形（AGPL §13）。

- 覆盖范围：[CORE-COMPONENTS.md](CORE-COMPONENTS.md)
- 白话说明与商业例外：[LICENSING.md](LICENSING.md)
- 版权声明：[NOTICE](NOTICE) · 第三方：[THIRD-PARTY-NOTICES](THIRD-PARTY-NOTICES)

---

*Last updated: 2026-11-26 (dedupe intro; capability-first)*

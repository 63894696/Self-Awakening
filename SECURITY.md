# Security Policy

This document explains how to report security issues in Self-Awakening and what
to expect from the maintainers.

## Supported versions

| Version | Supported |
| --- | --- |
| `0.1.x` (current) | yes |
| older snapshots | no |

The project is at 0.1 MVP. Fixes land on the `main` branch and in the next
release; critical issues are expedited.

## How to report

**Do not open a public issue for a vulnerability.**

Use GitHub's private vulnerability reporting: repository **Security** tab →
**Report a vulnerability**. If that is unavailable, open a public issue that only
asks for a private channel, without technical details.

Please include:

- a clear description and the impact (data exposure, code execution, etc.);
- steps to reproduce or a proof of concept;
- affected version, Python version, and OS;
- your name or handle if you want credit.

## What to expect

| Stage | Target |
| --- | --- |
| Acknowledgement | 3 business days |
| Initial triage | 7 business days |
| Status updates | every 14 days until resolved |
| Public advisory | after a fix ships, or 90 days after the report |

We follow coordinated disclosure: please do not publish before a fix ships or
before 90 days have passed, whichever is earlier.

## Scope

In scope:

- the CLI and library in `src/self_awaken/`;
- the optional Flask dashboard in `web_report/`;
- credential handling (the tool reads `SELF_AWAKEN_API_KEY` and must never log
  it, write it to reports, or include it in `runs/*.json`);
- injection through probe content or probe files loaded from disk.

Out of scope:

- vulnerabilities in the endpoints you audit, or in the models behind them;
- vulnerabilities in third-party packages (report upstream; we will pick up the
  fix);
- issues that require installing a malicious package yourself;
- disagreements about a capability verdict — those are correctness bugs, not
  security issues, and belong in a normal issue;
- trademark questions, which belong in [TRADEMARKS.md](TRADEMARKS.md).

## Handling of your data

- API keys are sent only to the endpoint you pass on the command line.
- `runs/*.json` records prompts, answers, latency, and token counts. It does not
  record the API key.
- Reports are written locally; nothing is uploaded by this project.

If you find a path that violates any of the above, treat it as a security report.

## Bug bounty

There is no paid bounty program. Reporters are credited in the advisory at their
option. A commercial support or security agreement can be discussed via
[LICENSING.md](LICENSING.md).

## Advisories

Published advisories appear under the repository's Security tab.

*Last updated: 2026-11-25*

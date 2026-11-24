# Self-Awakening

## 自我觉醒 · AI 服务透明度审计工具

[![CI](https://github.com/63894696/Self-Awakening/actions/workflows/ci.yml/badge.svg)](https://github.com/63894696/Self-Awakening/actions/workflows/ci.yml)
[![Python](https://img.shields.io/badge/python-3.10+-green.svg)](https://www.python.org/)
[![License](https://img.shields.io/badge/license-Apache--2.0-blue.svg)](LICENSE)
![Stage](https://img.shields.io/badge/stage-0.1%20MVP-orange)
![Probes](https://img.shields.io/badge/probes-51-blue)
![Tests](https://img.shields.io/badge/tests-34%20passed-brightgreen)

[English](#english) · [中文](#中文)

---

<a id="english"></a>

## What is Self-Awakening?

**Self-Awakening** is an open-source audit toolkit for AI service transparency. It helps users verify whether an OpenAI-compatible API endpoint actually delivers the model performance it claims to provide.

The project achieves this through:

- **Reproducible probe question banks** (JSONL format)
- **Black-box API call recording**
- **Statistical feature extraction**
- **Fingerprint comparison and confidence scoring**

> "Trust, but verify." — Trust model identity claims, but verify them with evidence.

## Why This Matters

AI services are increasingly encapsulated, resold, and dynamically routed. Users often cannot see:

- Whether the actual model matches the declared one
- Whether silent degradation or dynamic routing occurred
- Where data is being sent
- Whether different pricing tiers receive different capabilities

Self-Awakening transforms opaque services into auditable entities. It is not about creating confrontation — it is about building transparent, verifiable, reproducible accountability tools.

## Key Features

| Feature | Description |
|---------|-------------|
| **Probe Question Bank** | JSONL-based probe library with Chinese/English support |
| **Black-box Testing** | Call any OpenAI-compatible API without modification |
| **Baseline Fingerprints** | Create reference fingerprints from trusted sources |
| **Statistical Comparison** | Compare test runs against multiple baselines |
| **Confidence Reporting** | Output probability-based conclusions with uncertainty |
| **Markdown Reports** | Generate readable audit reports automatically |

## Quick Start

### Installation

```bash
pip install -e .
```

### List Available Probes

```bash
self-awaken list-probes --probes data/probes
```

### Run an Audit

```bash
# Set your API key
export SELF_AWAKEN_API_KEY="your-api-key"

# Run audit against a target endpoint
self-awaken run \
  --endpoint "https://api.example.com/v1" \
  --model "provider/model-name" \
  --probes data/probes \
  --provider openai \
  --out runs/my-audit.json
```

### Create a Baseline

```bash
# Convert trusted official API results to a baseline fingerprint
self-awaken make-baseline \
  --run runs/official-run.json \
  --name "Official Example Model" \
  --out data/baselines/official-example.json
```

### Compare Results

```bash
# Compare test run against baseline(s)
self-awaken compare \
  --run runs/my-audit.json \
  --baselines data/baselines/demo-baseline.json \
  --out runs/my-report.md
```

## Architecture

See [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) for the full design. Summary:

```
src/self_awaken/     CLI, client (retry), factory, fingerprint, scoring, reporting
data/probes/         core.zh.jsonl (8) + extended.zh.jsonl (43) = 51 probes
data/baselines/      Demo and reference fingerprints
web_report/          Optional Flask dashboard for runs/*.json
docs/                Architecture, verification report, ethics, roadmap
tests/               34 unit tests (pytest)
```

Verified end-to-end workflow: [docs/VERIFICATION.md](docs/VERIFICATION.md).

## Report Interpretation

The audit report outputs:

- **Similarity scores** against each baseline
- **Confidence levels**: `high`, `medium`, `low`
- **Probe-level evidence**: choice consistency, score matching, digest matching
- **Auxiliary metrics**: accuracy, average latency, output length

> **Important**: The report does NOT conclude "100% this is model X". Dynamic routing, temperature parameters, provider updates, caching, and probe leakage all affect results.

## Development Roadmap

### Phase 0.1 — MVP (Current)

- [x] JSONL probe loading
- [x] OpenAI-compatible API calls
- [x] Audit result persistence
- [x] Baseline generation
- [x] Multi-baseline comparison
- [x] Markdown report output

### Phase 0.2 — Fingerprint Enhancement

- [ ] Multi-turn probes
- [ ] Streaming response timing
- [ ] Multi-temperature sampling
- [ ] Probe version tagging
- [ ] Plugin-based scorers

### Phase 0.3 — Baseline Ecosystem

- [ ] Baseline signatures
- [ ] Contributor metadata
- [ ] Officially verified run scripts
- [ ] Regional/price-tier separated baselines

### Phase 0.4 — Visualization

- [x] Flask web dashboard (`web_report/`, `pip install -e ".[web]"`)
- [ ] Single-page static HTML report
- [ ] Similarity radar chart
- [ ] Probe evidence matrix
- [ ] Drift trend tracking

### Phase 0.5 — Community Governance

- [ ] Probe contribution guidelines
- [ ] Baseline acceptance criteria
- [ ] Vendor appeals process
- [ ] Anti-abuse policy

## Ethics & Compliance

### Encouraged Usage

- Users auditing AI services they purchased or are authorized to use
- Developers verifying routing layers work as declared
- Researchers comparing black-box behavior across different models
- Platforms voluntarily publishing reproducible transparency reports

### Discouraged Usage

- Unauthorized bulk testing of third-party interfaces
- Bypassing authentication, billing, geographic restrictions or risk control
- Unauthorized resale of third-party APIs
- Presenting probabilistic inference as definitive proof
- Using leaked probe banks to create false evaluation results

### Reporting Principles

- Provide evidence, not exaggerated conclusions
- Provide confidence levels, not false certainty
- Preserve runtime parameters for reproducibility
- Maintain correctable space for vendors, users, and contributors

## Contributing

Contributions are welcome! Please read [AGENT_HANDOFF.md](docs/AGENT_HANDOFF.md) for collaboration guidelines.

### Agent Collaboration

This project is designed for multi-agent collaboration:

| Agent | Focus Area |
|-------|-----------|
| Architecture Agent | Data formats, plugin system, report protocols |
| Code Agent | Streaming, retry, rate limiting, HTML reports |
| Data Agent | High-discrimination probes, version maintenance |
| Evaluation Agent | Trusted baselines, reproducible experiments |
| Compliance Agent | Privacy review, terms, public report language |

## Environment Variables

| Variable | Description |
|----------|-------------|
| `SELF_AWAKEN_API_KEY` | API authentication key |
| `SELF_AWAKEN_ENDPOINT` | Default API endpoint |
| `SELF_AWAKEN_API_TYPE` | Provider type: `openai`, `azure` |
| `SELF_AWAKEN_MAX_RETRY` | Max retry attempts (default: 5) |
| `SELF_AWAKEN_BASE_DELAY` | Exponential backoff base seconds (default: 0.5) |

## Web Dashboard (optional)

```bash
pip install -e ".[web]"
export FLASK_APP=web_report.app
flask run
```

Open `http://127.0.0.1:5000/` to browse audit runs under `runs/`. Copy [docs/samples/verify-core-run.sample.json](docs/samples/verify-core-run.sample.json) to `runs/demo.json` for a quick demo.

## Testing

```bash
pytest tests/ -q
```

CI runs the same suite on push (see `.github/workflows/ci.yml`).

## License

Apache License 2.0 — see [LICENSE](LICENSE) for the full text, and
[THIRD-PARTY-NOTICES](THIRD-PARTY-NOTICES) for third-party attributions.

---

<a id="中文"></a>

# 自我觉醒 (Self-Awakening)

## AI 服务透明度审计工具

## 什么是 Self-Awaken？

**Self-Awakening** 是一个面向 AI 服务透明度的开源审计工具包。它通过可复现的探针题库、黑盒调用记录、统计特征提取和指纹比对，帮助用户判断某个 OpenAI 兼容接口的实际表现是否接近其宣称的模型。

本项目的核心立场是：不要盲信模型身份声明，也不要把一次测试包装成绝对结论。更好的做法是保留证据、输出概率、呈现不确定性，让用户、开发者和 Agent 都能"相信，但要验证"。

## 为什么重要

AI 服务越来越多地被封装、转售和路由。普通用户往往看不到：

- 实际调用的是不是宣称的模型
- 是否发生了静默降级或动态路由
- 数据是否被送往第三方
- 供应商是否在不同用户、不同价格层之间提供不同能力

"自我觉醒"不是要制造对抗，而是要建立一个公开、可验证、可复现的透明度工具。它的价值在于把黑盒变成可审计对象。

## 核心功能

| 功能 | 描述 |
|------|------|
| **探针题库** | 基于 JSONL 格式的探针库，支持中英文 |
| **黑盒测试** | 无需修改即可调用任何 OpenAI 兼容 API |
| **基线指纹** | 从可信来源创建基准指纹 |
| **统计比对** | 将测试结果与多个基线进行比对 |
| **置信报告** | 输出带不确定性的概率结论 |
| **Markdown 报告** | 自动生成可读的审计报告 |

## 快速开始

### 安装

```bash
pip install -e .
```

### 查看探针

```bash
self-awaken list-probes --probes data/probes
```

### 运行审计

```bash
# 设置 API 密钥
export SELF_AWAKEN_API_KEY="your-api-key"

# 对目标端点运行审计
self-awaken run \
  --endpoint "https://api.example.com/v1" \
  --model "provider/model-name" \
  --probes data/probes \
  --provider openai \
  --out runs/my-audit.json
```

### 创建基线

```bash
# 将可信官方接口结果转换为基线指纹
self-awaken make-baseline \
  --run runs/official-run.json \
  --name "官方示例模型" \
  --out data/baselines/official-example.json
```

### 比对结果

```bash
# 将测试结果与基线进行比对
self-awaken compare \
  --run runs/my-audit.json \
  --baselines data/baselines/demo-baseline.json \
  --out runs/my-report.md
```

## 项目结构

完整设计见 [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md)。概要：

```
src/self_awaken/     CLI、带重试的 client、factory、fingerprint、评分与报告
data/probes/         core.zh.jsonl（8）+ extended.zh.jsonl（43）= 51 题
data/baselines/      演示与参考基线指纹
web_report/          可选 Flask 看板（查看 runs/*.json）
docs/                架构、验证报告、伦理与路线图
tests/               34 项 pytest 单元测试
```

端到端验证说明：[docs/VERIFICATION.md](docs/VERIFICATION.md)。

## 报告解读

报告会输出：

- 与各基线的相似度分数
- 置信等级：`high`、`medium`、`low`
- 探针级证据：选项一致、得分一致、哈希一致
- 辅助指标：客观题正确率、平均延迟、平均输出长度

> **重要提示**：报告不会输出"100% 就是某模型"这种不负责任的结论。动态路由、温度参数、供应商改版、缓存和题库泄漏都会影响结果。

## 开发路线图

### 阶段 0.1 — MVP（当前阶段）

- [x] 可加载 JSONL 探针题库
- [x] 可调用 OpenAI 兼容接口
- [x] 可保存审计运行结果
- [x] 可由可信运行结果生成基线
- [x] 可与多个基线进行相似度比对
- [x] 可输出 Markdown 报告

### 阶段 0.2 — 指纹增强

- [ ] 增加多轮探针
- [ ] 增加流式响应计时
- [ ] 增加多温度重复采样
- [ ] 增加题库版本号和题目泄漏风险标记
- [ ] 增加插件式评分器

### 阶段 0.3 — 基线生态

- [ ] 引入基线签名
- [ ] 引入贡献者复现实验元数据
- [ ] 增加官方可信接口运行脚本
- [ ] 支持把不同地区、不同时间、不同价格层的基线分开存储

### 阶段 0.4 — 可视化

- [x] Flask Web 看板（`web_report/`，`pip install -e ".[web]"`）
- [ ] 生成单页静态 HTML 报告
- [ ] 展示相似度雷达图
- [ ] 展示探针级证据矩阵
- [ ] 展示多次运行的漂移趋势

### 阶段 0.5 — 社区治理

- [ ] 建立探针贡献规范
- [ ] 建立基线接受规范
- [ ] 建立供应商申诉和纠错流程
- [ ] 建立反滥用政策

## 伦理与合规

### 鼓励的使用方式

- 用户审计自己购买或被授权使用的 AI 服务
- 开发者验证路由层是否按声明工作
- 研究者比较不同模型的黑盒行为差异
- 平台方主动发布可复现透明度报告

### 不鼓励的使用方式

- 未经授权批量压测第三方接口
- 绕过鉴权、费用、地域限制或风控系统
- 将第三方 API 未授权包装成转售服务
- 将概率推断包装成确定性指控
- 使用泄漏题库制造虚假评测结果

### 报告原则

- 给出证据，不给出夸张结论
- 给出置信等级，不假装绝对确定
- 保留运行参数，方便复现
- 对供应商、用户和贡献者都保持可纠错空间

## 参与贡献

欢迎贡献！请阅读 [AGENT_HANDOFF.md](docs/AGENT_HANDOFF.md) 了解协作指南。

### Agent 分工协作

本项目设计为多 Agent 协作：

| Agent | 专注领域 |
|-------|----------|
| 架构 Agent | 数据格式、插件系统、报告协议 |
| 代码 Agent | 流式、重试、限速、HTML 报告 |
| 数据 Agent | 高区分度探针、题库版本维护 |
| 评测 Agent | 可信基线、可复现实验 |
| 合规 Agent | 隐私审查、条款、公开报告措辞 |

## 环境变量

| 变量 | 说明 |
|------|------|
| `SELF_AWAKEN_API_KEY` | API 密钥 |
| `SELF_AWAKEN_ENDPOINT` | 默认 API 端点 |
| `SELF_AWAKEN_API_TYPE` | 提供方：`openai`、`azure` |
| `SELF_AWAKEN_MAX_RETRY` | 最大重试次数（默认 5） |
| `SELF_AWAKEN_BASE_DELAY` | 退避基数秒数（默认 0.5） |

## Web 报告（可选）

```bash
pip install -e ".[web]"
export FLASK_APP=web_report.app
flask run
```

浏览器打开 `http://127.0.0.1:5000/`。可将 [docs/samples/verify-core-run.sample.json](docs/samples/verify-core-run.sample.json) 复制为 `runs/demo.json` 做演示。

## 本地测试

```bash
pytest tests/ -q
```

推送至 GitHub 后会自动运行 CI（见 `.github/workflows/ci.yml`）。

## 许可证

Apache License 2.0 — 详见 [LICENSE](LICENSE) 全文,
第三方归属见 [THIRD-PARTY-NOTICES](THIRD-PARTY-NOTICES)。

---

*Last updated: 2026-11-25 (source restored to this repository)*
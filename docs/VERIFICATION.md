# 功能验证报告

本文档记录一次可复现的端到端验证（脱敏，不含 API 密钥）。完整运行结果默认保存在本地 `runs/`（已被 `.gitignore` 忽略）。

## 验证环境

| 项目 | 值 |
|------|-----|
| 日期 | 2026-05-30 |
| API | OpenRouter（OpenAI 兼容） |
| 模型 | `liquid/lfm-2.5-1.2b-thinking:free` |
| 探针 | `data/probes/core.zh.jsonl`（8 条） |
| CLI | `self-awaken run` + `compare` |

## 自动化测试

```bash
pip install -e ".[web]"
pytest tests/ -q
```

结果：**73 passed**（含 retry、client、factory、web 路由、探针加载、能力判定、题库 lint 等）。

## 端到端审计结果

| 指标 | 结果 |
|------|------|
| 探针总数 | 8 |
| 可评分题数 | 4 |
| 客观题准确率 | **50%** |
| 错误数 | 4（均为 `empty_response`） |
| 平均延迟 | ~2400 ms |

### 逐探针摘要

| 探针 | 结果 | 备注 |
|------|------|------|
| math-001 | 得分 0 | 回答含 372，但解释中出现多个数字，当前数值评分取首个数字 |
| logic-001 | 错误 | `empty_response`（重试后仍无 content） |
| logic-002 | 错误 | 同上 |
| code-001 | 通过 | 选项 B，得分 1.0 |
| code-002 | 得分 0 | 回答含 012，格式未完全匹配 expected |
| instruction-001 | 通过 | 得分 1.0 |
| knowledge-001 | 错误 | `empty_response` |
| ambiguity-001 | 错误 | `empty_response` |

### 基线比对（摘要）

与 `data/baselines/lfm-baseline.json` 相似度约 **0.54**（置信 low）。  
与 `data/baselines/demo-baseline.json` 相似度约 **0.41**（置信 low）。

## 复现命令

```powershell
$env:SELF_AWAKEN_API_KEY = "你的密钥"
python -m self_awaken.cli run `
  --endpoint "https://openrouter.ai/api/v1" `
  --model "liquid/lfm-2.5-1.2b-thinking:free" `
  --probes data/probes/core.zh.jsonl `
  --out runs/my-verify-run.json

python -m self_awaken.cli compare `
  --run runs/my-verify-run.json `
  --baselines data/baselines/lfm-baseline.json `
  --out runs/my-verify-report.md
```

全库 68 题：将 `--probes` 改为 `data/probes`。

## 能力达标判定验证（2026-11-25）

`code` 档位，`--pack standard`，`--max-tokens 200`，真实接口：

| 接口 | 判定 | 通过率 | 运行题数 | token |
|------|------|-------:|---------:|------:|
| `deepseek-chat` | SUFFICIENT | 1.00 | 11 | 830 |
| `glm-5.3` | SUFFICIENT | 1.00 | 11 | 3 016 |
| `claude-sonnet-4-6`（中转） | SUFFICIENT | 1.00 | 11 | 1 390 |
| `glm-4-flash`（弱模型对照） | INSUFFICIENT | 0.65 | 23 | 2 196 |

要点：

- 强模型在第 11 题即早停，未跑满题包；弱模型被正确判为不达标，说明规则不是"一律通过"。
- GLM 因 200 token 截断触发重试，token 偏高；截断答案被记为 `truncated_output` 而非错答。
- 复跑命令：`self-awaken check --endpoint ... --model ... --profile code --pack standard`。

## 题库校验

```bash
self-awaken lint-probes --probes data/probes --strict
# 68 probes, 0 errors, 0 warnings
```

`data/probe_templates.jsonl` 是出题模板（参数范围 + 答案表达式）。模板输出必须先把
`expected` 求值、把槽位填满，才能成为题库；直接拿模板批量结果当题库会产出
`<calc-failed>` / `<needs-llm-eval>` 占位答案、`OK/YES/TRUE` 这类未展开槽位和重复题。
本项目生成过一批 v5.2（188 行）候选，因上述缺陷已整体丢弃，不参与判定。

## 结论

- **工具链**：探针加载、API 调用（含 429/空响应重试）、评分、基线、Markdown 报告均正常。
- **模型表现**：LFM 1.2B 免费模型在部分 logic/knowledge 题上仍易返回空 content，属模型能力/稳定性限制，而非 CLI 未重试。
- **改进方向**：数值题评分（多数字回答）、更强模型复测、CI 见 `.github/workflows/ci.yml`。

## 样例数据

脱敏后的运行结构示例见 [samples/verify-core-run.sample.json](samples/verify-core-run.sample.json)，可用于 Web 看板演示（复制到 `runs/demo.json`）。

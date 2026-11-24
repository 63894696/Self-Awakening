# 贡献指南

感谢你对 Self-Awakening 的关注与贡献！本项目欢迎所有形式的贡献，包括但不限于：代码优化、探针题库扩展、文档完善、问题反馈和基线贡献。

## 贡献方式

### 🐛 报告问题

- 前往 [GitHub Issues](https://github.com/63894696/Self-Awakening/issues) 创建 Issue
- 选择合适的标签：`bug`、`enhancement`、`question`、`documentation`
- 提供清晰的问题描述和复现步骤
- 如果是探针题库问题，请附上具体的探针 ID 和预期/实际结果

### 📝 完善文档

- 拼写修正、语法优化
- 补充遗漏的使用场景
- 翻译成更多语言（当前支持中英文）
- 完善 README 中的示例

### 🔬 贡献探针题库

探针是 Self-Awakening 的核心资产。我们欢迎社区贡献高质量的探针。

#### 探针格式要求

每个探针必须是 JSONL 格式的一行，包含以下字段：

```json
{
  "id": "unique-probe-id",
  "category": "math|logic|code|instruction|knowledge|ambiguity|language",
  "prompt": "探针的完整题目内容",
  "expected": "预期的正确答案或格式",
  "scoring": "exact|contains|numeric|choice",
  "difficulty": "easy|medium|hard",
  "leak_risk": "low|medium|high",
  "tags": ["tag1", "tag2"],
  "language": "zh|en|multilingual",
  "notes": "可选的补充说明"
}
```

#### 探针贡献审核标准

| 标准 | 要求 |
|------|------|
| **区分度** | 能区分至少 2 个不同的模型（如 Opus vs Sonnet） |
| **无泄漏** | 题目和答案不应大量出现在常见训练数据中 |
| **可复现** | 在 temperature=0 时结果稳定 |
| **无偏见** | 不偏向特定文化、地域或政治立场 |
| **格式正确** | 通过 JSON 语法验证 |

#### 提交探针的流程

1. 在 `data/probes/` 目录下创建新的 JSONL 文件（或追加到现有文件）
2. 使用 `self-awaken list-probes --probes data/probes` 验证格式
3. 运行 `pytest tests/` 确保不破坏现有测试
4. 提交 Pull Request，标题格式：`[Probe] <探针主题描述>`

### 📊 贡献基线指纹

基线指纹是项目的信任锚点。我们欢迎社区贡献官方接口的运行结果。

#### 基线贡献审核标准

| 标准 | 要求 |
|------|------|
| **来源可信** | 必须是官方直连接口（OpenAI、Anthropic、Claude 等） |
| **参数透明** | 必须记录 temperature、max_tokens、模型版本 |
| **可复现** | 同一模型至少运行 3 次，结果方差 < 5% |
| **去标识化** | 不包含 API 密钥或敏感信息 |

#### 基线贡献流程

1. 使用官方接口运行审计：`self-awaken run --endpoint <官方接口> ...`
2. 生成基线：`self-awaken make-baseline --run runs/official.json --name "官方模型X" --out data/baselines/official-model-x.json`
3. 在 PR 中说明：
   - 运行日期和环境
   - 使用的是哪个官方接口
   - 模型版本和参数设置
   - 任何观察到的异常

### 💻 贡献代码

#### 开发环境设置

```bash
# 克隆仓库
git clone https://github.com/63894696/Self-Awakening.git
cd Self-Awakening

# 创建虚拟环境（推荐）
python -m venv venv
source venv/bin/activate  # Linux/Mac
# 或 venv\Scripts\activate  # Windows

# 安装开发依赖
pip install -e ".[web]"

# 运行测试
pytest tests/ -q
```

#### 代码规范

- 遵循 PEP 8 Python 代码风格
- 所有新增功能必须有对应的单元测试
- 使用类型注解（type hints）增强可读性
- 提交前运行 `pytest tests/ -q` 确保通过

#### Pull Request 流程

1. Fork 仓库并创建功能分支：`git checkout -b feature/your-feature-name`
2. 进行开发并添加测试
3. 提交时使用清晰的 commit message（中文或英文均可）
4. 提交 Pull Request，描述变更内容和动机
5. 等待代码审查，可能需要根据反馈进行调整

## 项目结构参考

```
Self-Awakening/
├── src/self_awaken/      # 核心代码
│   ├── cli.py           # 命令行入口
│   ├── client.py        # API 客户端
│   ├── scoring.py       # 评分逻辑
│   ├── fingerprint.py   # 指纹比对
│   └── reporting.py     # 报告生成
├── data/
│   ├── probes/          # 探针题库
│   └── baselines/       # 基线指纹
├── docs/                # 文档
│   ├── ARCHITECTURE.md  # 架构说明
│   ├── REPORT_GUIDE.md  # 报告解读指南
│   └── VERIFICATION.md # 验证记录
└── tests/               # 单元测试
```

## Agent 协作指南

本项目设计为多 Agent 协作开发。如果你是一个新的 Agent，请阅读 [AGENT_HANDOFF.md](docs/AGENT_HANDOFF.md) 了解当前的任务状态和分工。

## 行为准则

我们期望所有贡献者遵守以下行为准则：

- **尊重他人**：尊重不同的观点和技术选择
- **建设性反馈**：提出批评时保持友善和建设性
- **包容性**：欢迎来自不同背景的贡献者
- **专业性**：保持技术讨论的专业性，避免人身攻击

## 许可证

通过贡献代码，你同意你的贡献将遵循 [MIT 许可证](LICENSE)。

---

有任何问题？请在 [GitHub Discussions](https://github.com/63894696/Self-Awakening/discussions) 中提问，或创建 Issue 进行反馈。
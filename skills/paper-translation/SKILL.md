---
name: paper-translation
description: Use when translating academic papers (PDF to Chinese Markdown), extracting PDFs with MinerU API, or needing to preserve LaTeX formulas/images/tables through a translation workflow
---

# Paper Translation

## Pre-flight Check (MANDATORY — runs every time, before anything else)

**BEFORE you do anything else** — before Plan mode, before reading files, before any translation — check for the MinerU API token:

```bash
source ~/.claude/skills/paper-translation/config 2>/dev/null; echo $MINERU_TOKEN
```

### If MINERU_TOKEN is empty or not set → STOP immediately and respond with:

```
⚠️ 首次使用需要配置 MinerU API Token。

获取步骤（约 2 分钟）：
1. 打开 https://mineru.net ，注册/登录账号
2. 登录后访问 https://mineru.net/apiManage/token
3. 创建并复制 JWT Token（以 eyJ... 开头的长字符串）
4. 复制模板文件并填入 Token：

   cp ~/.claude/skills/paper-translation/config.example ~/.claude/skills/paper-translation/config

   然后用编辑器打开 config，将 Token 填入 MINERU_TOKEN= 后面。

   或直接告诉我你的 Token，我帮你写入配置文件。

完成后告诉我，我再继续处理 PDF。
```

**Do NOT proceed to Plan mode or any other step until the user confirms MINERU_TOKEN is set.**

### If MINERU_TOKEN is set → proceed to Overview.

---

## Overview

Systematic workflow for extracting academic PDFs via MinerU API and translating them to Chinese Markdown while preserving formulas, images, tables, and code blocks. Core principle: **plan first, translate in order, verify every invariant**.

**HARD RULE:** Before ANY translation work, you MUST invoke Plan mode (`EnterPlanMode` / `/plan`) to create a structured implementation plan. Never translate directly — the plan catches missing invariants and term conflicts before they become rework.

## When to Use

- Translating academic papers (CS, ML, robotics) from PDF to Chinese Markdown
- Extracting PDFs with formulas and images via MinerU Precision API
- Need consistent terminology across multiple related papers
- Want a repeatable translation pipeline with verification checkpoints

## Workflow (5 Stages)

### 1. Prepare

```bash
# Count source lines and images before starting
wc -l mineru_output/full.md
grep -c '!\[.*\](images/' mineru_output/full.md
```

- **Clean up `output_*`:** After MinerU extraction, move contents to `<论文名>/mineru_output/`, then delete `output_*/`. This intermediate dir must not linger.
- Build terminology table for core terms before translating
- Confirm source file paths, line counts, image counts

### 2. Plan (MANDATORY)

**REQUIRED:** Invoke Claude Code Plan mode (`EnterPlanMode`) before touching any translation work. Do NOT skip this step.

The plan must include:
- One task per paper translation (shorter paper first)
- One task for terminology consistency check
- One task for format & path verification
- Dependencies set correctly (verification → consistency → both translations done)
- Source file line counts and image counts recorded as baselines
- Output naming convention (`*_zh.md`) explicitly stated
- Image path correction rule documented (`images/` → `medias/`)

Red flags that mean STOP and enter Plan mode:
- "This is just a simple translation"
- "I know what to do"
- "Let me just start translating directly"

**All of these mean: Stop. Enter Plan mode first.**

### 3. Execute

**Translation order:** Shorter paper first to accumulate term experience, then longer paper.

**Must preserve unchanged:**
- LaTeX blocks `$$...$$` and inline `$...$`
- Image references `![...](images/xxx.jpg)`
- Tables (convert HTML `<table>` → Markdown pipe `|` syntax; MinerU outputs raw HTML tables which render poorly)
- Code blocks (fenced and indented)
- `<details>` collapsible blocks
- Heading hierarchy `#` / `##` / `###`

**Output location:** 翻译结果放在源 PDF 所在目录（即论文原始存放位置），而非 paper-translation 仓库目录。

**Output directory structure** (per paper):
```
<源PDF所在目录>/<论文名>/
├── medias/             # 图片，供 _zh.md 引用
├── <论文名>_zh.md       # 中文译文
├── <论文名>.pdf         # 源 PDF
└── mineru_output/      # MinerU 解析原始输出（原封不动）
    ├── full.md
    └── images/
```

**Must change:**
- Image paths: `images/xxx.jpg` → `medias/xxx.jpg` (copy images from `mineru_output/images/` to `medias/`)
- Body text: English → Chinese (academic style)

**Terminology consistency:** Both papers share the same glossary. Key terms:
| English | Chinese |
|---------|---------|
| reinforcement learning (RL) | 强化学习 |
| policy optimization | 策略优化 |
| constrained Markov decision process (CMDP) | 约束马尔可夫决策过程 |
| logarithmic barrier function | 对数障碍函数 |
| interior-point method | 内点法 |
| Lagrange multiplier | 拉格朗日乘子 |
| trust region | 信任域 |
| advantage function | 优势函数 |
| value function | 价值函数 |
| cost function | 代价函数 |
| generalized advantage estimation (GAE) | 广义优势估计 |
| proximal policy optimization (PPO) | 近端策略优化 |
| sim-to-real | 仿真到现实 |

### 4. Fix

Common issues and their fixes:

| Issue | Detection | Fix |
|-------|-----------|-----|
| Placeholder text left in output | Manual review of figure captions | Read each section, insert actual images |
| Missing images | `grep -c '!\[.*\](images/'` mismatch | Compare counts vs original, add missing figures |
| Image path pointing to wrong directory | Visual inspection | Correct to `medias/` prefix |
| Inconsistent terminology | `grep` key terms in both outputs | Align to glossary |

### 5. Verify

Run these checks before declaring done:

```bash
# Image count match (should equal original from mineru_output/full.md)
grep -c '!\[.*\](images/' mineru_output/full.md
grep -c '!\[.*\](medias/' *_zh.md

# Formula integrity (must be even)
grep -c '\$\$' *_zh.md

# Terminology consistency across papers
grep -o "约束马尔可夫\|对数障碍\|内点法\|拉格朗日\|信任域" paper1/*_zh.md paper2/*_zh.md | sort | uniq -c

# Image files actually exist in medias/
ls medias/ | wc -l
```

## MinerU API Quick Reference

**Token 获取:** https://mineru.net/apiManage/token  
**API docs:** https://mineru.net/apiManage/docs

### Batch extraction script pattern

```python
TOKEN = "eyJ0eXAiOiJKV1Q..."  # JWT from mineru.net console

def make_session():
    s = requests.Session()
    s.trust_env = False  # Windows: don't use system proxy
    s.headers.update({
        "Authorization": f"Bearer {TOKEN}",
        "Content-Type": "application/json",
    })
    return s
```

**Flow:** `POST /api/v4/file-urls/batch` → PUT files to OSS URLs → auto-parse → poll `GET /extract-results/batch/{batch_id}` → download ZIP

**Key params:** `model_version: "vlm"` (includes images), `extra_formats: ["docx"]`

### Skip already-downloaded

```python
if out_dir.exists() and any(out_dir.iterdir()):
    print(f"  [skip] {fname} (already has {len(list(out_dir.rglob('*')))} files)")
    continue
```

### Windows SSL workaround

When Python `requests` gets SSL EOF on `cdn-mineru.openxlab.org.cn`:
```python
# Fallback to curl -k (Windows SSL incompatibility)
subprocess.run(["curl", "-k", "-o", zip_path, download_url])
```

## Effective Guiding Patterns

These instructions produced the best results:

| Instruction | Effect |
|-------------|--------|
| "Don't modify the original files" | Established `_zh` suffix naming convention |
| "Make a plan first" | Triggered Plan mode → task breakdown → ordered execution |
| "Use skills frequently" (stored in memory) | Auto-triggered writing-plans, subagent-driven workflows |
| Approve plan before execution | Prevented directional rework |
| Explicit terminology requirements | Ensured cross-paper consistency |

## Common Mistakes

- **Batch-translating both papers at once** — First paper's translation choices inform the second; translating shorter one first builds a term base
- **Skipping image path correction** — MinerU outputs `images/` but `_zh.md` is at paper root level; always change to `medias/` and copy images over
- **Relying on grep alone for image verification** — Some images are in `<details>` blocks; also check figure captions manually
- **Using placeholder text** — "实验图表保持不变" is not acceptable; every image and caption must be present in the translation
- **Not verifying formula closure** — A single unclosed `$$` breaks all subsequent Markdown rendering; always check even counts
- **Leaving HTML tables unconverted** — MinerU outputs `<table>` HTML tags, which render poorly in most Markdown viewers; always convert to `|` pipe syntax
- **Leaving `output_*` directories behind** — After moving contents to `<论文名>/mineru_output/`, always delete the intermediate `output_*/` directory

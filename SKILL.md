---
name: paper-translation
description: Use when translating academic papers (PDF to Chinese Markdown), extracting PDFs with MinerU API, or needing to preserve LaTeX formulas/images/tables through a translation workflow
---

# Paper Translation

## Overview

Systematic workflow for extracting academic PDFs via MinerU API and translating them to Chinese Markdown while preserving formulas, images, tables, and code blocks. Core principle: **plan first, translate in order, verify every invariant**.

## When to Use

- Translating academic papers (CS, ML, robotics) from PDF to Chinese Markdown
- Extracting PDFs with formulas and images via MinerU Precision API
- Need consistent terminology across multiple related papers
- Want a repeatable translation pipeline with verification checkpoints

## Workflow (5 Stages)

### 1. Prepare

```bash
# Count source lines and images before starting
wc -l output_*/full.md
grep -c '!\[.*\](images/' output_*/full.md
```

- Read any project template (e.g., `模板.md`) to understand output expectations
- Build terminology table for core terms before translating
- Confirm source file paths, line counts, image counts

### 2. Plan

Use **superpowers:writing-plans** to create a plan with independent tasks:
- One task per paper translation
- One task for terminology consistency check
- One task for format verification
- Set dependencies (verification depends on consistency, consistency depends on both translations)

### 3. Execute

**Translation order:** Shorter paper first to accumulate term experience, then longer paper.

**Must preserve unchanged:**
- LaTeX blocks `$$...$$` and inline `$...$`
- Image references `![...](images/xxx.jpg)`
- Tables (pipe `|` syntax)
- Code blocks (fenced and indented)
- `<details>` collapsible blocks
- Heading hierarchy `#` / `##` / `###`

**Must change:**
- Image paths: `images/xxx.jpg` → `output_<paper_name>/images/xxx.jpg`
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
| Image path pointing to wrong directory | Visual inspection | Correct `output_<name>/images/` prefix |
| Inconsistent terminology | `grep` key terms in both outputs | Align to glossary |

### 5. Verify

Run these checks before declaring done:

```bash
# Image count match (should equal original)
grep -c '!\[.*\](output_' translation_zh.md

# Formula integrity (must be even)
grep -c '\$\$' translation_zh.md

# Terminology consistency across papers
grep -o "约束马尔可夫\|对数障碍\|内点法\|拉格朗日\|信任域" paper1_zh.md paper2_zh.md | sort | uniq -c

# Image paths actually exist
ls output_<paper>/images/ | wc -l
```

## MinerU API Quick Reference

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
- **Skipping image path correction** — `images/` paths break when `_zh.md` is in a different directory; always prefix with `output_<paper>/`
- **Relying on grep alone for image verification** — Some images are in `<details>` blocks; also check figure captions manually
- **Using placeholder text** — "实验图表保持不变" is not acceptable; every image and caption must be present in the translation
- **Not verifying formula closure** — A single unclosed `$$` breaks all subsequent Markdown rendering; always check even counts

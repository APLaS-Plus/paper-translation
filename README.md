# Paper Translation Pipeline

学术论文 PDF → 中文 Markdown 的自动化翻译流水线。

## 快速开始

### 1. 提取 PDF

```bash
pip install requests
export MINERU_TOKEN="your-jwt-token"  # 在 https://mineru.net 控制台获取
```

编辑 `extract_pdfs.py` 中的 PDFS 列表，然后运行：

```bash
python extract_pdfs.py
```

输出目录 `output_<论文名>/` 包含 `full.md` 和 `images/`。

### 2. 翻译

按照 `SKILL.md` 中的 5 阶段流程：

1. **准备** — 统计源文件行数和图片数，建立术语表
2. **规划** — 使用 Superpowers writing-plans skill 拆解任务
3. **执行** — 先翻短的论文积累术语，再翻长的；保留公式/图片/表格不变
4. **修复** — grep 对比图片数，补全遗漏内容
5. **验证** — 公式闭合检查、图片路径验证、术语一致性确认

### 3. 验证

```bash
# 图片数一致性
grep -c '!\[.*\](images/' output_*/full.md
grep -c '!\[.*\](output_' *_zh.md

# 公式闭合
grep -c '\$\$' *_zh.md
```

## 文件说明

| 文件 | 说明 |
|------|------|
| `SKILL.md` | 完整翻译流程 skill（可在 Claude Code 中作为 skill 加载） |
| `extract_pdfs.py` | MinerU API 批量 PDF 提取脚本 |
| `模板.md` | 论文阅读笔记模板 |

## 关键规则

- **不改原文** — 输出使用 `_zh` 后缀
- **保留不变** — LaTeX `$$...$$`、图片 `![](...)`、表格、代码块、`<details>` 块
- **图片路径修正** — `images/xxx.jpg` → `output_<论文名>/images/xxx.jpg`
- **术语一致** — 多篇论文共享统一术语表

## 作为 Claude Code Skill 使用

```bash
cp SKILL.md ~/.claude/skills/paper-translation/SKILL.md
```

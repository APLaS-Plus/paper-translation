# Changelog

## v1.1.0 — 2026-05-29 (Darwin 2.0 实测驱动迭代)

共 6 轮迭代、8 篇论文压测、32 个修复。

---

### R1: 文件结构与公式规则 (用户反馈)

- **修复**: `extract_pdfs.py` 从仓库根目录移到 `skills/paper-translation/`，确保 `npx skills add` 安装时带上脚本
- **修复**: 公式规则从 "Must preserve unchanged" 改为 "保留数学内容，修复 MinerU 渲染问题"（断裂 `$$`、未转义 `_`、分隔符间距异常）
- **修复**: MinerU API 参考章节删除内联 Python 片段，改为指向 `extract_pdfs.py` 脚本
- **新增**: Prepare 阶段 "Formula sanitization" 预检步骤

### R2: 伪代码防御链 (用户反馈)

- **新增**: Execute 规则：伪代码只翻译标题，正文保留英文 + 用 ` ```text ` 包裹
- **新增**: Prepare 伪代码检测命令
- **新增**: Fix 表格 "Pseudocode translated as body text" 条目
- **新增**: Common Mistakes "Translating pseudocode body" 条目

### R3: 子 agent 实测 2510.18518v2 (10 条建议)

- **修复**: Pre-flight Check 从无条件阻断改为条件执行（`full.md` 已存在 → 跳过 Token 检查）；增加非 bash fallback
- **修复**: Plan mode 增加 fallback（工具不可用时以文本形式呈现计划）
- **修复**: LaTeX 空格修复增加 `$x _ { \tau }$` → `$x_{\tau}$` 范例 + 判断标准
- **修复**: 翻译顺序和验证命令增加单篇论文分支
- **新增**: Figure/Table captions 翻译规则
- **修复**: 图片复制从"复制整个 images/"改为"仅复制被引用的图"
- **新增**: References 保留英文规则、`<details>` 内容翻译规则、模板噪音 `[模板残留]` 标记、英文缩写首次出现规则

### R4: 子 agent 实测 2502.12391 (参考文献硬伤)

- **修复**: 参考文献链接规则完全重写——基于 "MinerU 不输出 URL" 的现实，改为从参考文献文本扫描 `arXiv:XXXX.XXXXX`；增加 author-year 引用格式处理策略
- **新增**: 3.5 Appendix Strategy 分级处理（理论证明/训练曲线/环境截图/超参数表分别处理）+ "不得完全跳过"硬约束
- **新增**: Token 安全提示（先 Write 脚本文件再 Bash 执行，不在命令行传 Token）
- **新增**: Fix 表格 OCR artifacts 条目（控制字符、文本断裂、字符替换）
- **修复**: Verify 公式检查从"偶数即可"改为源/译文对比
- **回滚**: 删除 "Downloading Papers" 章节——下载不属于翻译 skill 的职责范围
- **新增**: `download_paper.py`（独立工具，供测试 agent 使用）

### R5: 3 agent 并行压测 2408.03314 / 2509.09208 / 2501.09905 (7 条交叉验证修复)

- **修复**: 术语表从硬编码 RL 术语改为通用模板 + 构建原则（"根据论文领域自行构建"）
- **修复**: 附录阈值从 ">10页" 改为相对判断（附录行数 > 正文 40%）
- **修复**: Verify 图片计数改为对比式输出，注明附录截断时偏差合理
- **修复**: arXiv 链接预期改为分领域（预印本 70-80%，会议论文 20-40%）
- **新增**: `\text{...}` 翻译策略：数学术语保留，自然语言注释翻译
- **新增**: Verify `\[...\]` 闭合检查（之前只检查 `$$`）
- **新增**: Prepare 公式修复增加 `\begin{array}{r}` 单行包装简化
- **新增**: `copy_images.py` 脚本（自动从 full.md 提取引用列表并复制）
- **修复**: SKILL.md 中图片复制命令改为引用 `copy_images.py`

### R6: 2 agent 并行 + 1 延迟回传 2501.09905 / 2403.07652 / 2412.04234 (6 条修复)

- **修复**: `grep -P` 在 Windows 下报错 → 全部改为 `grep -E`，加 Windows 兼容提示
- **修复**: "理解后概括"导致图片批量丢失（实测 63% 图片丢失）→ Execute 加"逐行翻译，不要凭理解概括"规则 + Verify 加图片差异 >10% 触发逐行排查
- **新增**: Mermaid 图节点标签保留英文规则（属于图表结构，不是自然语言）
- **修复**: MinerU 可能完全不提取伪代码（Algorithm 块在 PDF 中存在但 `full.md` 中消失）→ 伪代码检测改为两步：检查是否存在 → 不存在标记 `【伪代码缺失，需手动提取】`
- **新增**: `full.md` null 字节检测（导致 grep 当二进制处理）
- **新增**: `\begin{array}{l l}` → `\begin{cases}` 映射规则
- **修复**: arXiv ID 截断处理（MinerU 可能只剩 "arXiv, YYYY"）
- **新增**: `html_table_to_md.py` 脚本（HTML `<table>` 批量转 Markdown pipe）+ SKILL.md 引用

---

## v1.0.0 — 2026-05-27

- 初始版本
- 5 阶段翻译流水线（Prepare → Plan → Execute → Fix → Verify）
- MinerU API 集成
- 基础公式/图片/表格保留规则

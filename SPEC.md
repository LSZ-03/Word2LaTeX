# AI Scientific Manuscript Compiler
## Engineering Blueprint v2.0 — Optimized

---

# 1. 项目定义

## 系统身份

```
Scientific Manuscript Compiler
```

**不是：**
```
Word-to-LaTeX Converter
```

## 核心转换路径

```
Unstructured Word Manuscript (.docx)
              ↓
    Scientific Semantic AST
              ↓
    Journal-specific Rendering
              ↓
   Self-healing Compile Pipeline
              ↓
   Publication-ready LaTeX Project
```

---

# 2. 系统哲学

## 三条铁律

**铁律一：所有 Agent 只操作 AST，永不直接编辑 TeX**

```
docx → AST → Agent修改 → Renderer → tex
```

**铁律二：确定性模块与 AI 模块严格分离**

```
确定性：docx解析 / LaTeX渲染 / 编译 / 日志解析
AI驱动：语义恢复 / 公式修复 / 编译错误修复 / 期刊适配
```

**铁律三：每个 Agent 输出后必须持久化检查点**

```
任何步骤失败 → 从最近检查点恢复，不重跑全流程
```

---

# 3. 高层架构

```
┌─────────────────────────────────────────────┐
│            Manuscript Compiler              │
│                                             │
│  Input: paper.docx + journal_profile.yaml   │
│  Output: publication-ready LaTeX project    │
└─────────────────────────────────────────────┘
                      ↓
┌─────────────────────────────────────────────┐
│           Scientific AST Layer              │
│  Manuscript / Section / Figure / Table /    │
│  Equation / Citation (含溯源+置信度字段)      │
└─────────────────────────────────────────────┘
                      ↓
┌─────────────────────────────────────────────┐
│              Agent Graph                    │
│                                             │
│  1.  DocxParseAgent          [确定性]        │
│  2.  StructureRecoveryAgent  [规则驱动]      │
│  3.  SemanticLinkageAgent    [AI驱动]        │
│  4.  FigureTableAgent        [混合]          │
│  5.  EquationRepairAgent     [AI+视觉验证]   │
│  6.  CitationAgent           [规则+AI]       │
│  7.  JournalAdapterAgent     [AI驱动]        │
│  8.  LatexRendererAgent      [确定性]        │
│  9.  CompileAgent            [确定性]        │
│  10. LatexRepairAgent        [AI驱动]        │
│  11. QAValidationAgent       [规则+AI]       │
└─────────────────────────────────────────────┘
```

---

# 4. 仓库结构

```
manuscript_compiler/
│
├── agents/
│   ├── docx_parser/
│   │   ├── agent.py
│   │   ├── ooxml_extractor.py
│   │   ├── image_extractor.py
│   │   ├── table_extractor.py
│   │   └── equation_extractor.py      # OMML提取
│   │
│   ├── structure_recovery/            # 新增：规则驱动结构恢复
│   │   ├── agent.py
│   │   ├── heading_normalizer.py
│   │   ├── list_reconstructor.py
│   │   └── section_hierarchy.py
│   │
│   ├── semantic_linkage/              # 新增：AI驱动语义链接
│   │   ├── agent.py
│   │   ├── figure_caption_pairer.py
│   │   └── citation_linker.py
│   │
│   ├── figure_table/
│   │   ├── agent.py
│   │   ├── subfigure_detector.py      # 新增：子图检测
│   │   ├── textbox_extractor.py       # 新增：文本框图片提取
│   │   ├── image_converter.py         # 新增：EMF/WMF转换
│   │   ├── table_normalizer.py
│   │   └── longtable_handler.py       # 新增：跨页表格
│   │
│   ├── equation_repair/
│   │   ├── agent.py
│   │   ├── omml_to_mathml.py
│   │   ├── mathml_to_latex.py
│   │   ├── vision_verifier.py         # 新增：视觉对比验证
│   │   └── repair_rules.py
│   │
│   ├── citation/
│   │   ├── agent.py
│   │   ├── extractor.py
│   │   ├── normalizer.py
│   │   ├── doi_lookup.py
│   │   └── dedup.py
│   │
│   ├── journal_adapter/
│   │   ├── agent.py
│   │   ├── section_renamer.py
│   │   └── supplementary_integrator.py
│   │
│   ├── renderer/
│   │   ├── agent.py
│   │   ├── ieee_renderer.py
│   │   ├── elsevier_renderer.py
│   │   └── generic_renderer.py
│   │
│   ├── compiler/
│   │   ├── agent.py
│   │   ├── latexmk_runner.py
│   │   ├── log_parser.py              # 输出结构化CompileError对象
│   │   └── repair_loop.py
│   │
│   ├── latex_repair/
│   │   ├── agent.py
│   │   ├── error_classifier.py        # 新增：分层错误分类
│   │   ├── rule_fixer.py              # L1/L2规则修复
│   │   └── ai_fixer.py               # L3 AI修复
│   │
│   └── qa_validation/
│       ├── agent.py
│       ├── figure_checker.py
│       ├── citation_checker.py
│       ├── label_checker.py
│       ├── journal_compliance.py
│       └── report_generator.py        # 新增：量化QA报告
│
├── ast/
│   ├── manuscript.py
│   ├── section.py
│   ├── figure.py
│   ├── table.py
│   ├── equation.py
│   ├── citation.py
│   └── compile_error.py              # 新增：结构化错误对象
│
├── journal_profiles/
│   ├── ieee_tro.yaml
│   ├── elsevier.yaml
│   ├── springer.yaml
│   └── nature.yaml
│
├── prompts/
│   ├── semantic_linkage/
│   ├── equation_repair/
│   ├── latex_repair/
│   └── journal_adaptation/
│
├── templates/
│   ├── ieee/
│   ├── elsevier/
│   └── springer/
│
├── compile/
│   ├── latexmk_runner.py
│   ├── log_parser.py
│   └── repair_loop.py
│
├── pipelines/
│   ├── fast_convert.yaml
│   ├── publication_mode.yaml
│   └── revision_mode.yaml
│
├── runs/                             # 新增：运行状态持久化
│   └── {run_id}/
│       ├── 01_raw_ast.json
│       ├── 02_structure_ast.json
│       ├── 03_semantic_ast.json
│       ├── 04_visual_ast.json
│       ├── 05_equation_ast.json
│       ├── 06_citation_ast.json
│       ├── 07_journal_ast.json
│       ├── compile_attempt_1/
│       │   ├── main.tex
│       │   └── compile_log.txt
│       └── compile_attempt_N/
│
├── tests/
├── examples/
└── main.py
```

---

# 5. 优化后的 AST 设计

## 5.1 核心原则

**每个 AST 节点必须携带：**
- `source_ref`：溯源到原始 OOXML 节点，支持调试
- `confidence_score`：解析置信度，指导后续处理
- `warnings`：当前节点的已知问题列表
- `semantic_role`：语义角色，支持期刊适配

---

## 5.2 manuscript.py

```python
@dataclass
class Manuscript:
    # --- 内容字段 ---
    metadata: ManuscriptMetadata
    authors: List[Author]
    abstract: str
    keywords: List[str]
    sections: List[Section]
    figures: List[Figure]
    tables: List[Table]
    equations: List[Equation]
    bibliography: List[Citation]
    appendices: List[Section]
    supplementary: Optional[SupplementaryMaterial]

    # --- 溯源字段（新增）---
    source_file: str                    # 原始docx路径
    run_id: str                         # 本次编译运行ID
    created_at: datetime

    # --- 状态字段（新增）---
    pipeline_stage: str                 # 当前所处的pipeline阶段
    overall_confidence: float           # 整体解析置信度 0.0-1.0
    warnings: List[ManuscriptWarning]   # 全文级别的问题列表
```

---

## 5.3 section.py（关键优化）

```python
@dataclass
class Section:
    # --- 核心字段 ---
    id: str
    title: str
    level: int                          # 1=一级, 2=二级, 3=三级
    paragraphs: List[Paragraph]
    subsections: List['Section']
    figures: List[str]                  # Figure ID引用
    tables: List[str]                   # Table ID引用
    equations: List[str]                # Equation ID引用
    citations: List[str]                # Citation key引用

    # --- 语义字段（新增，期刊适配核心）---
    semantic_role: SemanticRole
    # SemanticRole枚举：
    #   INTRODUCTION / RELATED_WORK / METHOD /
    #   EXPERIMENTS / RESULTS / DISCUSSION /
    #   CONCLUSION / ACKNOWLEDGMENT / APPENDIX / UNKNOWN

    # --- 溯源字段（新增）---
    source_page_range: Tuple[int, int]  # Word中的页码范围
    source_xml_node_ids: List[str]      # 对应的OOXML节点ID列表

    # --- 状态字段（新增）---
    confidence_score: float             # 结构解析置信度
    warnings: List[str]                 # 当前section的问题列表
    is_ai_recovered: bool               # 是否经过AI语义恢复
```

---

## 5.4 figure.py（关键优化）

```python
@dataclass
class Figure:
    # --- 核心字段 ---
    id: str
    caption: str
    references: List[str]               # 正文中引用此图的位置
    placement: str                      # "top" | "bottom" | "here" | "page"
    width: float                        # 相对页面宽度 0.0-1.0

    # --- 子图支持（新增）---
    is_subfigure: bool                  # 是否是组合图的一部分
    subfigure_label: Optional[str]      # "a" | "b" | "c" ...
    parent_figure_id: Optional[str]     # 所属的父图ID
    subfigures: List['Figure']          # 子图列表（若为父图）

    # --- 图片文件（新增）---
    source_format: str                  # "png" | "jpg" | "emf" | "wmf" | "svg" | "pdf"
    extracted_path: str                 # 提取到本地的路径
    converted_path: Optional[str]       # 转换为LaTeX可用格式后的路径
    needs_conversion: bool              # 是否需要格式转换（EMF/WMF）
    was_in_textbox: bool                # 是否来自Word文本框（高风险）

    # --- 溯源字段（新增）---
    source_page: int
    source_xml_ref: str

    # --- 状态字段（新增）---
    confidence_score: float
    caption_pairing_method: str         # "rule" | "ai" | "proximity"
    warnings: List[str]
```

---

## 5.5 equation.py（关键优化）

```python
@dataclass
class Equation:
    # --- 核心字段 ---
    id: str
    latex: str
    environment: str                    # "equation" | "align" | "cases" | "matrix" ...
    label: Optional[str]               # \label{eq:xxx}

    # --- 转换链（新增）---
    source_omml: str                    # 原始OMML XML字符串
    intermediate_mathml: str            # 中间MathML
    conversion_method: str              # "omml2mathml" | "pandoc" | "ai_direct"

    # --- 视觉验证（新增）---
    rendered_image_path: Optional[str]  # OMML渲染截图路径（作为ground truth）
    vision_verified: bool               # 是否通过视觉模型对比验证
    vision_confidence: float            # 视觉对比置信度

    # --- 状态字段（新增）---
    repair_attempts: int                # AI修复尝试次数
    confidence_score: float
    warnings: List[str]
```

---

## 5.6 table.py

```python
@dataclass
class Table:
    id: str
    caption: str
    latex: str                          # 最终LaTeX代码
    references: List[str]

    # --- 复杂表格支持（新增）---
    has_merged_cells: bool
    has_multirow: bool
    spans_multiple_pages: bool          # 需要longtable环境
    has_equations_in_cells: bool        # 最复杂情况
    column_count: int
    row_count: int

    # --- 溯源字段（新增）---
    source_xml_ref: str
    confidence_score: float
    warnings: List[str]
```

---

## 5.7 compile_error.py（新增）

```python
@dataclass
class CompileError:
    """结构化编译错误对象，取代原始日志字符串"""

    level: ErrorLevel
    # ErrorLevel枚举:
    #   L1_FATAL   - 必须修复才能继续编译
    #   L2_ERROR   - 内容错误，可局部修复
    #   L3_WARNING - 可忽略或后处理

    category: ErrorCategory
    # ErrorCategory枚举:
    #   UNDEFINED_COMMAND      # \foo 未定义
    #   MISSING_PACKAGE        # 缺少宏包
    #   CITATION_UNDEFINED     # \cite{xxx} 未找到
    #   LABEL_UNDEFINED        # \ref{xxx} 未找到
    #   FIGURE_NOT_FOUND       # 图片文件不存在
    #   TABLE_OVERFLOW         # 表格超出页面
    #   FLOAT_PLACEMENT_FAIL   # 浮动体无法放置
    #   ENVIRONMENT_MISMATCH   # \begin{} \end{} 不匹配
    #   MISSING_BRACE          # 括号不匹配
    #   UNICODE_ISSUE          # 非法Unicode字符
    #   PACKAGE_CONFLICT       # 宏包冲突

    line_number: Optional[int]          # 出错的TeX行号
    file_path: Optional[str]            # 出错的TeX文件
    raw_message: str                    # 原始错误信息
    context_lines: List[str]            # 出错位置的上下文
    suggested_fix: Optional[str]        # 规则库预置的修复建议
    ast_node_ref: Optional[str]         # 关联的AST节点ID（用于溯源到原始Word内容）
```

---

# 6. Agent 详细规格（优化版）

## 6.1 DocxParseAgent

**职责：** docx → 原始结构提取（纯确定性）

**输入：** `paper.docx`
**输出：** `01_raw_ast.json` + 检查点持久化

**允许操作：**
- unzip docx / 解析 OOXML
- 提取图片（含文本框内图片）
- 提取 OMML 公式并同步渲染截图（作为后续视觉验证的 ground truth）
- 提取表格原始结构
- 检测标题层级

**明确禁止：**
- 语义推断
- 期刊格式化
- AI 改写

**技术栈：**
```
python-docx / lxml / zipfile / pandoc(可选)
```

**注意事项：**
- Word 中图片可能嵌套在 `<w:txbxContent>` (文本框) 内，需专门处理
- OMML 公式提取后立即用 Word/LibreOffice 渲染截图，存入 `figure_eq_{id}.png`
- EMF/WMF 格式图片标记 `needs_conversion: true`

---

## 6.2 StructureRecoveryAgent（原 SemanticRecovery 拆分）

**职责：** 规则驱动的结构恢复

**输入：** `01_raw_ast.json`
**输出：** `02_structure_ast.json`

**任务（纯规则，无需 AI）：**
- 标题层级恢复（基于样式名/字号/加粗规则）
- 断裂列表重建
- 段落合并（被段落符断开的连续段落）
- 基本 section 层级树构建
- Figure/Table 标签提取（正则匹配 "Figure 1", "Fig. 1", "Table 2"）

**质量指标：**
- 每个 Section 输出 `confidence_score`（基于检测到的样式匹配程度）
- `confidence_score < 0.6` 的节点标记为需要 SemanticLinkageAgent 处理

---

## 6.3 SemanticLinkageAgent（原 SemanticRecovery 拆分）

**职责：** AI 驱动的语义链接与角色标注

**输入：** `02_structure_ast.json`
**输出：** `03_semantic_ast.json`

**任务（AI 驱动）：**
- Figure-Caption 精确配对（尤其是图注跨页或顺序混乱的情况）
- Citation 上下文链接（将正文引用 `[3]` 链接到参考文献条目）
- Section 语义角色标注（识别 Introduction / Method / Experiments 等）
- 低置信度节点的结构歧义消解

**Prompt 设计要点：**
```
系统提示要包含：
- 期刊领域（robotics / medicine / CS 等）
- 当前待处理的 section 原文
- 相邻 section 的标题列表（提供上下文）
- 要求输出 JSON，包含 semantic_role + confidence + reasoning
```

---

## 6.4 FigureTableAgent（关键优化）

**职责：** 视觉结构修复

**输入：** `03_semantic_ast.json`
**输出：** `04_visual_ast.json`

**图片处理流程：**
```
提取图片文件
    ↓
格式检测（PNG/JPG/EMF/WMF/SVG）
    ↓
[EMF/WMF] → 调用 LibreOffice/Inkscape 转换为 PDF/EPS
    ↓
子图检测（识别 "1a, 1b" 模式 → 构建 subfigure 结构）
    ↓
写入 visual_ast
```

**表格处理流程：**
```
检测合并单元格 → multirow/multicolumn 标注
检测跨页表格 → 标记 longtable 环境
检测单元格内公式 → 标记为高复杂度
生成初始 LaTeX 代码
```

**EMF/WMF 转换命令：**
```bash
# 转换为PDF（LaTeX首选）
libreoffice --headless --convert-to pdf figure.emf
# 或使用 inkscape
inkscape --export-pdf=figure.pdf figure.wmf
```

---

## 6.5 EquationRepairAgent（关键优化）

**职责：** 公式高保真转换与验证

**优化后的转换链：**
```
OMML (原始) ────────────────────────────────┐
    ↓                                        │ 渲染截图（ground truth）
MathML                                       │
    ↓                                        │
初始 LaTeX（规则转换）                        │
    ↓                                        │
AI 修复（Claude Vision 对比验证）◄────────────┘
    ↓
最终 LaTeX
```

**视觉验证步骤（新增）：**
```python
# 1. 编译初始LaTeX生成预览图
compile_equation_preview(latex_str) -> preview_image

# 2. 与OMML渲染截图对比（使用Vision模型）
compare_images(
    ground_truth=omml_render_path,
    candidate=preview_image,
    prompt="这两个公式是否语义等价？指出差异。"
) -> (is_equivalent: bool, diff_description: str)

# 3. 不等价则触发AI修复，最多3轮
```

**修复规则库（rule_fixer.py）：**
```python
KNOWN_FIXES = {
    r"\mathop{\rm lim}": r"\lim",
    r"\left( \begin{array}": r"\begin{pmatrix}",
    r"\\textbf": r"\mathbf",
    # ... 持续积累
}
```

---

## 6.6 CitationAgent

**职责：** 参考文献规范化

**输入：** `04_visual_ast.json`
**输出：** `refs.bib` + `citation_map.json`

**支持来源：** EndNote / Zotero / Mendeley / 手动参考文献

**处理流程：**
```
提取原始参考文献文本
    ↓
识别引用格式（编号制 [1] / 作者年制 [Smith2020]）
    ↓
解析各条目字段（标题/作者/期刊/年份）
    ↓
去重（DOI/标题相似度）
    ↓
可选：DOI 在线查询补全
    ↓
生成规范 BibTeX
    ↓
建立正文引用 → BibTeX key 的映射表
```

---

## 6.7 JournalAdapterAgent

**职责：** 通用 AST → 期刊特定 AST

**输入：** `semantic_ast` + `journal_profile.yaml`
**输出：** `07_journal_ast.json`

**基于 semantic_role 的适配逻辑：**
```python
# 示例：IEEE TRO 适配规则
ROLE_ADAPTATION = {
    SemanticRole.RELATED_WORK: {
        "ieee_tro": "keep_as_section",    # 保留为独立节
        "nature":   "merge_to_intro",     # 合并进引言
        "elsevier": "rename_to_background"
    }
}
```

**适配任务：**
- documentclass 选择
- bibliography style 映射
- 宏包选择与冲突检测（预选而非等到编译报错）
- section 重命名
- abstract 格式（字数限制/关键词位置）
- 图片放置策略（`[t]` / `[ht]` / `[!ht]`）
- 补充材料整合

---

## 6.8 LatexRendererAgent

**职责：** AST → TeX 文件（纯确定性）

**输入：** `07_journal_ast.json`
**输出：** `main.tex` + `sections/` + `figures/` + `tables/`

**明确禁止：**
- AI 改写
- 任何语义修改

**输出文件结构：**
```
output/
├── main.tex
├── sections/
│   ├── 01_introduction.tex
│   ├── 02_related_work.tex
│   └── ...
├── figures/
│   ├── fig1.pdf
│   ├── fig2a.pdf
│   └── fig2b.pdf
├── tables/
│   ├── tab1.tex
│   └── tab2.tex
└── refs.bib
```

---

## 6.9 CompileAgent

**职责：** LaTeX 项目编译（纯确定性）

**推荐命令：**
```bash
latexmk -pdf -interaction=nonstopmode -file-line-error main.tex
```

**输出：** 结构化 `compile_result.json`
```json
{
  "success": false,
  "attempt": 1,
  "duration_seconds": 12.3,
  "errors": [CompileError对象列表],
  "warnings": [CompileWarning对象列表],
  "output_pdf": null
}
```

---

## 6.10 LatexRepairAgent（关键优化）

**职责：** 自动修复编译错误

**分层修复策略：**

```
L1 致命错误（阻断编译）
├── MISSING_PACKAGE        → 规则修复：在 preamble 添加 \usepackage{}
├── ENVIRONMENT_MISMATCH   → 规则修复：匹配 \begin \end 对
├── MISSING_BRACE          → AI 修复：上下文理解后补全括号
└── UNDEFINED_COMMAND(核心) → AI 修复：根据上下文推断正确命令

L2 内容错误（可局部修复）
├── CITATION_UNDEFINED     → 规则修复：检查 citation_map，补充缺失 key
├── LABEL_UNDEFINED        → 规则修复：扫描全文补充 \label
├── FIGURE_NOT_FOUND       → 规则修复：修正图片路径
└── TABLE_OVERFLOW         → AI 修复：调整表格宽度/字体/环境

L3 警告（后处理）
├── OVERFULL_HBOX          → 延后处理，记录位置
├── FLOAT_TOO_LARGE        → 规则：添加 \resizebox
└── FONT_WARNING           → 忽略或记录
```

**修复循环控制：**
```python
def repair_loop(max_iterations: int = 5):
    for attempt in range(max_iterations):
        result = CompileAgent.run()
        if result.success:
            return result
        
        errors = result.errors
        
        # L1优先处理
        fatal_errors = [e for e in errors if e.level == L1_FATAL]
        if fatal_errors:
            LatexRepairAgent.fix(fatal_errors, strategy="rule_first_then_ai")
            continue
        
        # L2处理
        content_errors = [e for e in errors if e.level == L2_ERROR]
        if content_errors:
            LatexRepairAgent.fix(content_errors, strategy="rule_based")
            continue
    
    raise MaxRepairIterationsExceeded(attempts=max_iterations)
```

---

## 6.11 QAValidationAgent（关键优化）

**职责：** 量化发布验证，输出结构化 QA 报告

**输出示例（qa_report.json）：**
```json
{
  "qa_report": {
    "generated_at": "2025-01-15T10:30:00Z",
    "overall_status": "PASS_WITH_WARNINGS",

    "figures": {
      "total": 12,
      "referenced_in_text": 11,
      "missing_caption": 0,
      "format_issues": 0,
      "warnings": ["Figure 7 appears in manuscript but is not cited in text"],
      "status": "WARNING"
    },

    "equations": {
      "total": 34,
      "compilation_verified": 34,
      "vision_verified": 31,
      "label_consistency": "PASS",
      "warnings": ["Equation 15, 22, 28: vision verification skipped (no OMML source)"],
      "status": "PASS"
    },

    "citations": {
      "total_in_text": 47,
      "total_in_bib": 49,
      "undefined": 0,
      "unused_bib_entries": 2,
      "warnings": ["Ref [Chen2019] in bibliography but never cited"],
      "status": "PASS"
    },

    "journal_compliance": {
      "journal": "ieee-tro",
      "abstract_length": { "limit": 250, "actual": 231, "status": "PASS" },
      "page_limit": { "limit": 8, "actual": 7.5, "status": "PASS" },
      "column_format": "double",
      "required_sections_present": ["Abstract", "Introduction", "References"],
      "status": "PASS"
    },

    "package_conflicts": {
      "detected": false,
      "status": "PASS"
    },

    "supplementary": {
      "present": true,
      "figures_referenced": 3,
      "status": "PASS"
    },

    "overall_confidence": 0.94
  }
}
```

---

# 7. 期刊配置系统

## 设计原则：所有期刊规则必须配置驱动

## ieee_tro.yaml

```yaml
journal: ieee-tro
display_name: "IEEE Transactions on Robotics"
domain: robotics

documentclass:
  name: IEEEtran
  options: [journal]

bibliography:
  style: IEEEtran
  max_authors_before_etal: 6

figures:
  placement: "[t]"
  max_width: 0.95
  subfigure_package: subfloat    # IEEEtran使用subfloat而非subfigure

packages:
  required:
    - amsmath
    - amssymb
    - bm
    - graphicx
    - cite
  optional:
    - algorithm
    - algorithmic

sections:
  abstract:
    max_words: 250
    format: inline               # IEEE: 摘要在正文内
  references:
    title: References

section_role_mapping:
  RELATED_WORK: keep_as_section
  ACKNOWLEDGMENT: after_conclusion_before_references

compliance_checks:
  max_pages: 14
  double_column: true
  color_figures_allowed: true
```

## elsevier.yaml

```yaml
journal: elsevier
display_name: "Elsevier (Generic)"

documentclass:
  name: elsarticle
  options: [preprint, 12pt]

bibliography:
  style: elsarticle-num

figures:
  placement: "[htbp]"
  max_width: 0.9

packages:
  required:
    - amsmath
    - graphicx
    - lineno

sections:
  abstract:
    format: environment          # Elsevier: abstract环境
  keywords:
    separator: "\\sep"

section_role_mapping:
  RELATED_WORK: rename_to_background
  ACKNOWLEDGMENT: acknowledgments_environment
```

---

# 8. 运行状态持久化（新增）

## 检查点机制

```python
class RunStateManager:
    """管理单次编译运行的完整状态"""

    def __init__(self, run_id: str):
        self.run_dir = Path(f"runs/{run_id}")
        self.run_dir.mkdir(parents=True, exist_ok=True)

    def save_checkpoint(self, stage: int, stage_name: str, ast: dict):
        path = self.run_dir / f"{stage:02d}_{stage_name}.json"
        path.write_text(json.dumps(ast, ensure_ascii=False, indent=2))
        self._update_manifest(stage, stage_name, str(path))

    def load_checkpoint(self, stage: int) -> Optional[dict]:
        """从指定阶段恢复"""
        manifest = self._load_manifest()
        if stage in manifest:
            return json.loads(Path(manifest[stage]["path"]).read_text())
        return None

    def get_latest_checkpoint(self) -> Tuple[int, dict]:
        """获取最近的成功检查点"""
        manifest = self._load_manifest()
        latest_stage = max(manifest.keys())
        return latest_stage, self.load_checkpoint(latest_stage)

    def resume_from(self, stage: int) -> dict:
        """从指定阶段恢复并跳过之前的步骤"""
        ast = self.load_checkpoint(stage)
        if ast is None:
            raise CheckpointNotFound(f"Stage {stage} checkpoint not found")
        return ast
```

## 恢复命令

```bash
# 从头开始
python main.py --input paper.docx --journal ieee_tro

# 从指定阶段恢复（例如公式修复完后从期刊适配开始）
python main.py --resume-run run_20250115_143022 --from-stage 6

# 查看运行状态
python main.py --status run_20250115_143022
```

---

# 9. Pipeline 配置

## 9.1 publication_mode.yaml（主流程）

```yaml
pipeline:
  run_id: auto                          # 自动生成时间戳ID

  stages:
    - stage: 1
      agent: DocxParseAgent
      checkpoint: 01_raw_ast
      on_failure: abort

    - stage: 2
      agent: StructureRecoveryAgent     # 规则驱动
      checkpoint: 02_structure_ast
      on_failure: abort

    - stage: 3
      agent: SemanticLinkageAgent       # AI驱动
      checkpoint: 03_semantic_ast
      on_failure: warn_and_continue     # 语义失败可继续

    - stage: 4
      agent: FigureTableAgent
      checkpoint: 04_visual_ast
      on_failure: warn_and_continue

    - stage: 5
      agent: EquationRepairAgent
      checkpoint: 05_equation_ast
      vision_verify: true               # 开启视觉验证
      on_failure: warn_and_continue

    - stage: 6
      agent: CitationAgent
      checkpoint: 06_citation_ast
      doi_lookup: false                 # 离线模式默认关闭
      on_failure: warn_and_continue

    - stage: 7
      agent: JournalAdapterAgent
      checkpoint: 07_journal_ast
      on_failure: abort

    - stage: 8
      agent: LatexRendererAgent
      checkpoint: 08_tex_files
      on_failure: abort

    - stage: 9
      agent: CompileAgent
      on_failure: enter_repair_loop

    - repair_loop:
        max_iterations: 5
        on_max_exceeded: generate_partial_report
        steps:
          - LatexRepairAgent
          - CompileAgent

    - stage: 10
      agent: QAValidationAgent
      output: qa_report.json
```

## 9.2 fast_convert.yaml（快速模式）

```yaml
pipeline:
  stages:
    - DocxParseAgent
    - StructureRecoveryAgent      # 跳过SemanticLinkageAgent
    - FigureTableAgent
    - LatexRendererAgent
    - CompileAgent
    # 无修复循环，无QA验证
```

## 9.3 revision_mode.yaml（返修模式）

```yaml
pipeline:
  input:
    manuscript_v1: paper_v1.docx
    manuscript_v2: paper_v2.docx        # 修改后版本
    review_comments: review_comments.docx

  stages:
    - ASTDiffAgent                       # 对比两版本AST差异
    - ReviewCommentMapperAgent           # 审稿意见 → 修改位置映射
    - IncrementalLatexRendererAgent      # 只重新渲染变化的部分
    - CompileAgent
    - repair_loop: ...
    - RebuttalSkeletonAgent              # 生成回复信框架
```

---

# 10. 双向 AST Diff（Revision Mode 核心）

```python
class ASTDiffEngine:
    """对比两个版本的Manuscript AST，生成增量变化"""

    def diff(self, v1: Manuscript, v2: Manuscript) -> DeltaAST:
        return DeltaAST(
            added_sections=self._find_added(v1.sections, v2.sections),
            removed_sections=self._find_removed(v1.sections, v2.sections),
            modified_sections=self._find_modified(v1.sections, v2.sections),
            added_figures=self._find_added(v1.figures, v2.figures),
            modified_equations=self._find_modified(v1.equations, v2.equations),
            # ...
        )

@dataclass
class DeltaAST:
    added_sections: List[Section]
    removed_sections: List[str]         # Section IDs
    modified_sections: List[SectionDiff]
    added_figures: List[Figure]
    modified_equations: List[EquationDiff]
    changelog_summary: str              # AI生成的变更摘要
```

---

# 11. 确定性 vs AI 边界（完整版）

## 确定性模块（不允许任何 AI）

```
docx 解压与 OOXML 解析
图片文件提取
OMML 公式截图渲染
EMF/WMF → PDF 格式转换
Section 层级树构建（基于样式规则）
Figure/Table 标签正则提取
LaTeX 渲染（AST → TeX）
LaTeX 编译（latexmk）
编译日志解析 → CompileError 对象
L1/L2 规则修复（已知错误模式）
QA 量化指标计算
检查点读写
```

## AI 驱动模块

```
语义角色标注（SemanticLinkageAgent）
Figure-Caption 配对歧义消解
低置信度结构恢复
公式视觉验证（Vision模型）
公式修复（Claude）
L1 未知命令修复（Claude）
L2 表格溢出修复（Claude）
期刊适配（JournalAdapterAgent）
引用链接推断
返修模式：审稿意见映射（Claude）
```

---

# 12. MVP 实施路线图

## Phase 1：管道跑通（第 1-2 周）

**目标：端到端跑通，不追求质量**

```
DocxParseAgent
    ↓
StructureRecoveryAgent（仅规则）
    ↓
LatexRendererAgent（最简渲染）
    ↓
CompileAgent
```

验收标准：任意 Word 文件能输出可编译（即使有错误）的 tex 文件

---

## Phase 2：核心质量（第 3-5 周）

**目标：正文、图表、公式质量达到可用**

```
EquationRepairAgent（含视觉验证）
FigureTableAgent（含格式转换）
LatexRepairAgent（修复循环）
CitationAgent（基础版）
```

验收标准：IEEE TRO 格式论文能成功编译输出 PDF

---

## Phase 3：语义与发布（第 6-8 周）

**目标：达到投稿质量**

```
SemanticLinkageAgent（AI驱动）
JournalAdapterAgent（配置驱动）
QAValidationAgent（量化报告）
检查点与恢复机制
```

验收标准：QA 报告显示 journal_compliance PASS，overall_confidence > 0.90

---

## Phase 4：长期扩展（持续迭代）

```
多期刊支持（Elsevier / Springer / Nature）
Revision Mode（AST Diff + 返修骨架）
在线 DOI 补全
公式修复规则库持续积累
Web UI（上传 docx → 下载 LaTeX 包）
```

---

# 13. 推荐技术栈

## 解析层
```
python-docx      # Word文档解析
lxml             # OOXML处理
zipfile          # docx解压
pandoc           # 备选解析路径
```

## 公式处理
```
python-docx      # OMML提取
latex2mathml     # MathML→LaTeX转换
LibreOffice      # OMML渲染截图
```

## 图片处理
```
LibreOffice      # EMF/WMF→PDF转换
Inkscape         # 备选矢量图转换
Pillow           # 图片处理
```

## 编译
```
latexmk          # LaTeX编译（推荐）
tectonic         # 备选（自动下载宏包）
```

## AI 模型
```
Claude (Anthropic)
  → LaTeX修复、语义恢复、公式视觉验证
  → 最适合结构理解与代码修复任务

GPT-4V (OpenAI)
  → 备选视觉验证

Gemini (Google)
  → 长文档整体分析（超长论文）
```

## 状态管理
```
Python dataclasses  # AST节点定义
JSON                # 检查点序列化
YAML                # Pipeline配置与期刊配置
```

---

# 14. 最终系统身份

## 正确定义

```
AI-native Scientific Manuscript Compiler
```

核心价值：
- 理解论文语义，而非转换文本格式
- 保持公式精度，而非近似转换
- 自动修复编译错误，而非依赖人工调试
- 配置驱动期刊适配，而非硬编码规则

## 错误定义

```
Word-to-LaTeX Converter
```

---

*Blueprint v2.0 — 基于 v1.0 架构评审优化*
*主要优化项：AST溯源字段 / SemanticRecovery拆分 / 公式视觉验证 / 结构化错误对象 / 检查点机制 / 量化QA报告 / 图表复杂场景覆盖*

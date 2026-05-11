# LaTeX Renderer 实战经验总结

## 一、Abstract/Keywords 重复渲染

**现象：** Abstract 和 Keywords 被同时渲染在 `\begin{abstract}` 环境和 `\section{Abstract}` 中。

**根因：** `render_title_block()` 从 `metadata.abstract` 生成 abstract 环境。同时 section tree 中也有 "Abstract" 子节，被渲染为 `\section{Abstract}`。

**修复：**
1. `render_sections()` 先扫描所有 sections，标记 Abstract/Keywords 为 `skip_titles`
2. `_render_section_inner()` 检查 `raw_title in skip_titles` 跳过

## 二、`__preamble__` 标题被输出

**现象：** 输出中出现 `\paragraph{ \_\_preamble\_\_ }` 和论文标题的重复段落。

**根因：** `__preamble__` 段落在 AST 里存有标题文本，`_render_section_inner` 会渲染它的 paragraphs。

**修复：** preamble 特殊处理时跳过了 paragraphs，只渲染 subsections。

### 特别坑：LaTeX 转义导致的字符串不匹配

```python
title = _escape_latex("__preamble__")
# title = "\_\_preamble\_\_"  ← 下划线被转义！

if title == "__preamble__":  # 永远 False！
```

**教训：** 系统内部标记字段（`__preamble__`）必须用**原始值**比较，不能走 LaTeX 转义。

## 三、标题编号去重

**现象：** `\section{1. Introduction}` — LaTeX 自动编号 + 人工前缀编号，变成 "1 1. Introduction"。

**修复：** `_strip_numbering()` 函数：
```python
"1. Introduction" → "Introduction"
"2.1. Method" → "Method"
"Abstract:" → "Abstract"
```

## 四、Abstract/Metadata 提取

**现象：** abstract 内容包含了 Keywords 和 Introduction 的开头。

**根因：** 原始 `extract_abstract()` 没有在 "Keywords" 或 "1. " 处停止。

**修复：** 新增关键词和数字标题的终止检测。

## 六、官方模板管理

### 核心原则

**所有模板文件必须从官方网站下载，不能手写。**

| 模板 | 来源 |
|------|------|
| IEEEtran.cls | https://ctan.org/pkg/ieeetran |
| 其他期刊 | 相应期刊的 Overleaf / 官网 |

### 模板目录结构

```
templates/{journal_name}/
   ├── IEEEtran.cls          ← 文档类文件（必需）
   ├── IEEEtran.bst          ← 参考文献样式（必需）
   ├── IEEEtrantools.sty     ← 配套样式包
   ├── IEEEfull.bib          ← 参考数据库
   ├── IEEEabrv.bib
   └── bare_jrnl.tex         ← 官方示例（参考，不被 renderer 使用）
```

### Renderer 如何处理

```python
# 1. 构建时复制所有 .cls/.bst/.sty/.bib 到输出目录
shutil.copy2(template_path / "IEEEtran.cls", output_dir / "IEEEtran.cls")

# 2. main.tex 使用 \documentclass[journal]{IEEEtran}
#    IEEEtran.cls 就在同一目录下，LaTeX 会自动找到
```

### 输出目录 = 自包含的 LaTeX 项目

```
英文稿_output/
   ├── main.tex              ← 生成的正文
   ├── IEEEtran.cls          ← 官方文档类（自行编译无需系统安装）
   ├── IEEEtran.bst
   ├── IEEEtrantools.sty
   ├── IEEEfull.bib
   ├── figures/              ← 提取的图片
   │   ├── fig_1.tiff
   │   └── ...
   └── refs.bib              ← 可选的参考文献数据库
```

### 支持新期刊的步骤

1. 从官网下载 LaTeX 模板包（.zip）
2. 解压到 `templates/{name}/`
3. 识别关键文件：`.cls` 文档类、`.bst` 参考文献样式
4. 在 `journal_profiles/__init__.py` 中新建配置
5. 更新 `PROFILES` 注册表

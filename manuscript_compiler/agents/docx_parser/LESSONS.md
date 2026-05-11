# Word → LaTeX 转换实战经验总结

> 本文档记录了 `Word2PaperAI` 项目在开发 `docx_parser` 过程中遇到的**所有实际文档问题**及其修复方案。
> 用于提高后续转换的鲁棒性和正确性。

---

## 一、标题检测（最易出错）

### 问题 1：参考文献条目被误判为章节标题

**现象：** 参考文献区段后的 `"1. Cheng, Gong, Peicheng Zhou..."` 被当成 Heading 1。

**根因：** Heading 正则 `r"^(\d+(?:\.\d+)*)\.?\s+.+"` 匹配到了参考文献的数字编号。

**修复：** 增加**负向模式**，在检测标题前先排除：
```python
_HEADING_NEGATIVE_PATTERNS = [
    r"^\d+\.\s+[A-Z][a-z]+,\s+[A-Z][a-z]+",   # "1. Author, F." → 参考文献
    r"^\d+\)\s+",                                 # "1) ..." → 列表项
    r"^\(\d+\)\s+",                              # "(1) ..." → 列表项
    r"^[a-z]\)\s+",                              # "a) ..."
    r"^\([a-z]\)\s+",                            # "(a) ..."
    r"^https?://|^doi:",                         # URL / DOI
]
```

**规则：** 负向模式优先于正向模式，先排除再匹配。

---

### 问题 2：列表项被误判为章节标题

**现象：** 正文中的 `"1) We propose..."`、`"2) A method..."`、`"(a) Experiment..."` 被当成标题。

**根因：** Heading 正则 `r"^(\d+)\.?\s+"` 匹配到了数字开头的列表项。

**修复：** 同上，添加到 `_HEADING_NEGATIVE_PATTERNS`。

---

### 问题 3：图/表标题被误判

**现象：** `"Fig. 1. Shape information..."`、`"TABLE I: Results"` 被当成章节。

**根因：** 正则匹配到了 "Fig" / "Table" 开头的行。

**修复：** 
```python
r"^(Fig(ure)?|Table|TABLE)\s+\d+"
```

---

### 问题 4：标题+正文写在同一 Word 段落

**现象：** `"Abstract: The field of remote sensing..."` — 1863 字全部成了标题。
或者 `"2.3. Sample Selection for Object Detection\n\tIn detection networks..."` — 标题和正文在同一个 Word 段落里（用 `\n\t` 或 `: ` 连接）。

**根因：** Word 作者没有使用 Heading 样式，而是把标题和正文写在一个段落里。

**修复：** 
1. `_detect_heading_level()` 只检查**第一行**（`\n` 前的内容），避免正文干扰
2. 新增 `_extract_heading_and_body()` 函数：
   - 带冒号的命名标题（`Abstract: ` / `Keywords: `）→ 按冒号拆分
   - 数字标题（`1. Introduction`）→ 保持完整标题，剩余内容为正文
   - 换行符分隔（`2.3. Title\n\tbody`）→ 按 `\n` 拆分

```python
def _extract_heading_and_body(text, heading_level):
    # 1) 命名标题带冒号: "Abstract: body..." → "Abstract" + "body..."
    # 2) 数字标题: "1. Introduction" → "1. Introduction" + ""
    # 3) 换行分隔: "2.3. Title\n\tbody..." → "2.3. Title" + "body..."
```

---

## 二、章节树构建

### 问题 5：参考文献区段特殊处理

**现象：** 参考文献的 51 条条目全部被当成独立的子章节。

**根因：** 没有"参考文献区段"的概念。

**修复：** 在 `_build_section_tree()` 中检测到 `"References"` 标题后，后面的段落不再进入章节树，而是收集到独立的 `bibliography` 列表。

```python
if para.is_heading and "references" in para.text.lower():
    in_bibliography = True
    continue  # 参考文献标题本身也进 section tree
if in_bibliography:
    bibliography.append(para)  # 后面的条目不进章节树
    continue
```

---

## 三、Word 文档特性

### 问题 6：Word 样式名称多样性

Word 样式名称在不同语言版本/应用中不一样：
- `"Heading 1"` / `"Heading1"` / `" Überschrift 1"`（德文）
- 中文论文可能完全不用样式，全靠手动编号

**策略：** 三层检测（按优先级）：
1. **Word Heading 样式** — 最可靠，优先
2. **启发式正则** — 覆盖未使用样式的文档
3. **全大写短文本** — 最后兜底

```python
def _detect_heading_level(text, style_name):
    # Level 1: Word Heading styles
    if style_name and style_name.lower().startswith("heading"):
        return extract_level(style_name)
    # Level 2: Heuristic regex patterns
    for pattern in _HEADING_PATTERNS:
        if pattern.match(first_line):
            return detected_level
    # Level 3: ALL-CAPS short text
    if len(first_line.split()) <= 5 and first_line.isupper():
        return 1
```

---

### 问题 7：图片提取中的 XML 命名空间问题

**现象：** `prefix 'ancestor' not found in prefix map`

**根因：** `ElementTree.find("./ancestor::ns:tag")` 这种 XPath 的 `ancestor::` 轴在 `ElementTree` 中不支持。

**修复：** 改用手动父节点遍历：
```python
# 错误写法（ElementTree 不支持）：
parent = elem.find("./ancestor::ns:tag")

# 正确写法：
parent = elem
while parent is not None:
    parent = parent.find("..")
    if parent is not None and parent.tag == expected_tag:
        break
```
或直接返回空字符串（MVP 阶段），后续用更复杂方法。

---

### 问题 8：图片格式多样性

**现象：** 提取的图片有 `.tiff` / `.tif` / `.emf` / `.wmf` 等格式。
TGRS 等期刊要求 PDF 或 EPS 格式。

**策略：** 
- 先原格式提取到 `figures/` 目录
- Renderer 阶段判断期刊要求，必要时用 `pillow` / `inkscape` 转换

---

## 四、核心数据流注意事项

### AST 节点共识

| AST 字段 | 含义 |
|---------|------|
| `source_ref` | 溯源到原始 OOXML 节点 |
| `confidence` | 解析置信度 0.0-1.0，低置信度节点需后续 AI 修复 |
| `warnings` | 节点级别的问题列表 |
| `is_heading` vs `heading_level` | `is_heading=True` 才进入章节树 |

### 拆段原则

> **一条 Word 段落可能 → 多条 AST 段落**

```
Word 段落: "Abstract: body text..."
         ↓
AST 段1: Paragraph(is_heading=True, text="Abstract")
AST 段2: Paragraph(is_heading=False, text="body text...")
```

---

## 五、测试验证 Checklist

每次修改后必须验证：

- [ ] 参考文献条目不被当成章节（负向模式生效）
- [ ] "Abstract:" / "Keywords:" 标题正确拆分
- [ ] "1. / 2.1 / 3.1.1" 数字标题正确识别层级
- [ ] 图标题（Fig. / Table）不被当成章节
- [ ] 列表项（1) / (a) / -）不被当成章节
- [ ] 带 `\n` 的段落正确拆分为标题+正文
- [ ] 图片提取不报错（即使某张图提取失败也不影响整体）
- [ ] 表格正确提取（含合并单元格信息）
- [ ] 公式至少不报错（OMML XML 存下来后续处理）

---

## 六、后续优化方向

| 优先级 | 项目 | 说明 |
|--------|------|------|
| 🔴 高 | 公式提取+LLM转换 | OMML → LaTeX 是最困难的部分 |
| 🔴 高 | 参考文献结构化 | 当前仅存纯文本，需解析为 Author/Title/Journal/Year 字段 |
| 🟡 中 | 子图检测 | 一张大图包含多个子图 (a)(b)(c) 需要拆开 |
| 🟡 中 | EMF/WMF 转换 | Windows 矢量图格式，需转换为 PDF/EPS |
| 🟢 低 | 图题自动关联 | 提取图片对应的 "Fig. 1: ..." 描述文本 |
| 🟢 低 | 交叉引用识别 | Word 域代码 → LaTeX `\ref{}` / `\cite{}` |

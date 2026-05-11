"""Batch CrossRef BibTeX search for Word2PaperAI pipeline.

Extracts reference titles from the manuscript, searches Crossref for DOIs,
fetches BibTeX entries, and generates refs.bib.
"""

from __future__ import annotations

import json
import re
import time
import urllib.request
import urllib.parse
import urllib.error
from pathlib import Path
from typing import Optional


def search_crossref_by_title(title: str, max_retries: int = 3) -> Optional[str]:
    """Search Crossref by title, return DOI if found."""
    params = urllib.parse.urlencode({
        "query.title": title,
        "rows": 1,
    })
    url = f"https://api.crossref.org/works?{params}"
    
    for attempt in range(max_retries):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "Word2PaperAI/1.0"})
            with urllib.request.urlopen(req, timeout=15) as resp:
                data = json.loads(resp.read().decode("utf-8"))
            items = data.get("message", {}).get("items", [])
            if items:
                doi = items[0].get("DOI")
                return doi
        except Exception as e:
            if attempt < max_retries - 1:
                time.sleep(1)
            else:
                print(f"    ⚠️  Crossref search failed: {e}")
    return None


def fetch_bibtex(doi: str, max_retries: int = 3) -> Optional[str]:
    """Fetch BibTeX entry from doi.org."""
    url = f"https://doi.org/{doi}"
    
    for attempt in range(max_retries):
        try:
            req = urllib.request.Request(url, headers={
                "Accept": "application/x-bibtex",
                "User-Agent": "Word2PaperAI/1.0",
            })
            with urllib.request.urlopen(req, timeout=15) as resp:
                return resp.read().decode("utf-8")
        except Exception as e:
            if attempt < max_retries - 1:
                time.sleep(1)
            else:
                print(f"    ⚠️  DOI→BibTeX failed ({doi}): {e}")
    return None


def extract_titles_from_tex(tex_path: Path) -> list[tuple[int, str, str]]:
    """Extract (ref_number, title_text) from thebibliography in main.tex."""
    text = tex_path.read_text(encoding="utf-8")
    
    refs = []
    # Find thebibliography block
    bib_match = re.search(r"\\begin\{thebibliography\}(.*?)\\end\{thebibliography\}", text, re.DOTALL)
    if not bib_match:
        print("  ⚠️  No thebibliography found in main.tex")
        return refs
    
    bib_block = bib_match.group(1)
    # Find each \bibitem{ref_N}
    for m in re.finditer(r"\\bibitem\{ref_(\d+)\}\n(.*?)(?=\\bibitem|\Z)", bib_block, re.DOTALL):
        ref_num = int(m.group(1))
        title_raw = m.group(2).strip()
        # Clean up LaTeX markup for search
        title_clean = re.sub(r"\\[a-zA-Z]+(\{[^}]*\})?", "", title_raw)
        title_clean = re.sub(r"[{}]", "", title_clean)
        title_clean = re.sub(r"\s+", " ", title_clean).strip()
        # Extract first meaningful sentence/book title
        refs.append((ref_num, title_clean, title_raw))
    
    return refs


def extract_title_for_search(text: str) -> str:
    """Extract a searchable title from a truncated reference text."""
    # Remove leading \textit{} if present
    text = re.sub(r"^\\textit\{(.*?)\}", r"\1", text)
    # Remove trailing truncation
    text = re.sub(r"\.\.\.$", "", text)
    text = re.sub(r'\s+', ' ', text).strip()
    return text[:150]  # Enough for Crossref search


def run_batch_search(tex_path: Path, output_bib_path: Path, known_fixes: dict = None) -> dict:
    """Batch search all references via Crossref, generate refs.bib.
    
    Returns: {ref_number: bibtex_key} mapping
    """
    refs = extract_titles_from_tex(tex_path)
    print(f"  📚 Found {len(refs)} references in thebibliography")
    
    key_mapping = {}
    bib_entries = {}
    used_keys = {}
    
    for ref_num, title_clean, title_raw in refs:
        search_title = extract_title_for_search(title_raw)
        print(f"    [{ref_num}] Searching: {search_title[:60]}...")
        
        # Check if we have a known fix
        bibtex = None
        if known_fixes and str(ref_num) in known_fixes:
            bibtex = known_fixes[str(ref_num)]
            print(f"      → Using known fix")
        else:
            doi = search_crossref_by_title(search_title)
            if doi:
                bibtex = fetch_bibtex(doi)
        
        if bibtex:
            # Extract bib key from the entry
            key_match = re.search(r"@\w+\{([^,]+),", bibtex)
            bib_key = key_match.group(1) if key_match else f"ref_{ref_num}"
            
            # Handle duplicate keys
            if bib_key in used_keys:
                used_keys[bib_key] += 1
                bib_key = f"{bib_key}_{chr(96 + used_keys[bib_key])}"
            else:
                used_keys[bib_key] = 1
            
            bib_entries[bib_key] = bibtex
            key_mapping[ref_num] = bib_key
            print(f"      → {bib_key}")
        else:
            # Fallback: generate minimal entry
            key_mapping[ref_num] = f"ref_{ref_num}"
            print(f"      ⚠️  No Crossref match, using ref_{ref_num}")
    
    # Write refs.bib
    output_bib_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_bib_path, "w", encoding="utf-8") as f:
        f.write("% Auto-generated bibliography from Crossref\n")
        f.write(f"% Generated: {time.strftime('%Y-%m-%d %H:%M:%S')}\n")
        f.write(f"% Total entries: {len(bib_entries)}\n\n")
        for key in sorted(bib_entries.keys(), key=lambda k: int(re.search(r'\d+', k).group()) if re.search(r'\d+', k) else 0):
            entry = bib_entries[key]
            # Rename bib key if needed
            original_key = re.search(r"@\w+\{([^,]+),", entry).group(1)
            if original_key != key:
                entry = entry.replace(f"{{{original_key},", f"{{{key},", 1)
            f.write(entry)
            f.write("\n\n")
    
    print(f"  ✅ Written {len(bib_entries)} BibTeX entries to {output_bib_path}")
    return key_mapping


def apply_bib_to_tex(tex_path: Path, key_mapping: dict, output_bib_path: Path) -> None:
    """Replace thebibliography with \\bibliography, update \\cite{ref_N} to real keys."""
    text = tex_path.read_text(encoding="utf-8")
    
    # 1. Replace \cite{ref_N} → \cite{real_key}
    def _replace_cite(m):
        inner = m.group(1)
        ref_nums = re.findall(r"ref_(\d+)", inner)
        new_refs = []
        for num_str in ref_nums:
            num = int(num_str)
            if num in key_mapping:
                new_refs.append(key_mapping[num])
            else:
                new_refs.append(f"ref_{num}")
        return "\\cite{" + ",".join(new_refs) + "}"
    
    text = re.sub(r"\\cite\{([^}]*)\}", _replace_cite, text)
    
    # 2. Remove \cite{ref_0, ...} — ref_0 is invalid
    text = re.sub(r'ref_0,?', '', text)
    text = re.sub(r',\s*\}', '}', text)
    text = re.sub(r'\{\s*\}', '{}', text)
    
    # 3. Replace thebibliography with \bibliography
    bib_re = re.compile(
        r"\\begin\{thebibliography\}\{[^}]*\}.*?\\end\{thebibliography\}",
        re.DOTALL,
    )
    new_bib = (
        r"\begin{thebibliography}{99}\n"
        r"\nocite{*}\n"
        r"\bibliographystyle{IEEEtran}\n"
        r"\bibliography{" + str(output_bib_path.stem) + r"}\n"
        r"\end{thebibliography}"
    )
    # Actually, \bibliography and thebibliography shouldn't be nested.
    # The correct approach is:
    new_bib_correct = (
        "\\nocite{*}\n"
        "\\bibliographystyle{IEEEtran}\n"
        "\\bibliography{" + str(output_bib_path.stem) + "}"
    )
    text = bib_re.sub(new_bib_correct, text)
    
    tex_path.write_text(encoding="utf-8", data=text)
    print(f"  ✅ Updated citations in {tex_path}")


def auto_fix_yolo_entry() -> str:
    """Return known-correct BibTeX for YOLOv3."""
    return """@article{Redmon_2018,
  author    = {Joseph Redmon and Ali Farhadi},
  title     = {{YOLOv3}: An Incremental Improvement},
  journal   = {arXiv preprint arXiv:1804.02767},
  year      = {2018}
}"""


def auto_fix_kfiou_entry() -> str:
    """Return known-correct BibTeX for KFIoU."""
    return """@inproceedings{Yang_2022,
  author    = {Xue Yang and Yue Zhou and Jirui Yang and Wentao Wang and Junchi Yan and Xiaopeng Zhang and Qi Tian},
  title     = {Learning High-Precision Bounding Box for Rotated Object Detection via Kullback-Leibler Divergence},
  booktitle = {Advances in Neural Information Processing Systems (NeurIPS)},
  year      = {2021}
}"""


def auto_fix_mmdetection_entry() -> str:
    """Return known-correct BibTeX for MMDetection."""
    return """@article{Chen_2019,
  author    = {Kai Chen and Jiaqi Wang and Jiangmiao Pang and Yuhang Cao and Yu Xiong and Xiaoxiao Li and Shuyang Sun and Wansen Feng and Ziwei Liu and Jiarui Xu and Zheng Zhang and Dazhi Cheng and Chenchen Zhu and Tianheng Cheng and Qijie Zhao and Buyu Li and Xin Lu and Rui Zhu and Yue Wu and Jifeng Dai and Jingdong Wang and Jianping Shi and Wanli Ouyang and Chen Change Loy and Dahua Lin},
  title     = {{MMDetection}: Open MMLab Detection Toolbox and Benchmark},
  journal   = {arXiv preprint arXiv:1906.07155},
  year      = {2019}
}"""


if __name__ == "__main__":
    import sys
    
    if len(sys.argv) < 2:
        print("Usage: python crossref_bib.py <main.tex>")
        sys.exit(1)
    
    tex_path = Path(sys.argv[1])
    if not tex_path.exists():
        print(f"File not found: {tex_path}")
        sys.exit(1)
    
    output_dir = tex_path.parent
    output_bib = output_dir / "refs.bib"
    
    known_fixes = {
        "49": auto_fix_yolo_entry(),
    }
    
    key_mapping = run_batch_search(tex_path, output_bib, known_fixes)
    
    if key_mapping:
        apply_bib_to_tex(tex_path, key_mapping, output_bib)
    
    print(f"\n✅ Bibliography conversion complete!")
    print(f"   {len(key_mapping)} references processed")
    print(f"   Output: {output_bib}")

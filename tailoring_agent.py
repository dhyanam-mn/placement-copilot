import os
import re
import json
import shutil
import subprocess
import warnings
from typing import List, Dict, Any, Tuple, Optional

def load_bullet_keywords(keywords_path: str = "bullet_keywords.json") -> Dict[str, List[str]]:
    if not os.path.exists(keywords_path):
        raise FileNotFoundError(f"Bullet keywords file not found: {keywords_path}")
    with open(keywords_path, "r", encoding="utf-8") as f:
        return json.load(f)

def extract_jd_keywords(jd_text: str, bullet_keywords: Dict[str, List[str]]) -> set:
    jd_lower = jd_text.lower()
    
    # Tokenize words, preserving tech special characters like +, #, ., -
    cleaned_jd = re.sub(r'[^a-z0-9\+\#\.\-\s]', ' ', jd_lower)
    words = cleaned_jd.split()
    
    extracted = set()
    
    # Generate 1-grams, 2-grams, 3-grams
    for n in range(1, 4):
        for i in range(len(words) - n + 1):
            ngram = " ".join(words[i:i+n])
            extracted.add(ngram)
            
    # Also check exact phrase presence of known bullet keywords in JD text
    for b_id, kw_list in bullet_keywords.items():
        for kw in kw_list:
            kw_lower = kw.lower().strip()
            if kw_lower in jd_lower:
                extracted.add(kw_lower)
                
    return extracted

def compute_jaccard_scores(jd_text: str, bullet_keywords: Dict[str, List[str]]) -> List[Dict[str, Any]]:
    jd_kw_set = extract_jd_keywords(jd_text, bullet_keywords)
    
    results = []
    for bullet_id, kw_list in bullet_keywords.items():
        bullet_kw_set = set(k.lower().strip() for k in kw_list)
        intersection = bullet_kw_set.intersection(jd_kw_set)
        union = bullet_kw_set.union(jd_kw_set)
        
        score = len(intersection) / len(union) if union else 0.0
        results.append({
            "id": bullet_id,
            "score": round(score, 4)
        })
        
    # Sort descending by score
    results.sort(key=lambda x: x["score"], reverse=True)
    return results

def parse_tex_template(tex_content: str) -> Tuple[str, Dict[str, str], str]:
    lines = tex_content.splitlines(keepends=True)
    header_lines = []
    bullet_blocks = {}
    footer_lines = []
    
    current_bullet_id = None
    current_block_lines = []
    in_bullets = False
    
    for line in lines:
        match = re.match(r'^\s*%\s*BULLET_ID:\s*([A-Za-z0-9_\-]+)', line)
        if match:
            in_bullets = True
            if current_bullet_id is not None:
                bullet_blocks[current_bullet_id] = "".join(current_block_lines)
            current_bullet_id = match.group(1).strip()
            current_block_lines = [line]
        elif current_bullet_id is not None:
            if r"\end{itemize}" in line or r"\end{document}" in line:
                bullet_blocks[current_bullet_id] = "".join(current_block_lines)
                current_bullet_id = None
                footer_lines.append(line)
            else:
                current_block_lines.append(line)
        elif not in_bullets:
            header_lines.append(line)
        else:
            footer_lines.append(line)
            
    if current_bullet_id is not None and current_bullet_id not in bullet_blocks:
        bullet_blocks[current_bullet_id] = "".join(current_block_lines)
        
    header = "".join(header_lines)
    footer = "".join(footer_lines)
    return header, bullet_blocks, footer

def reorder_tex_content(tex_content: str, ordered_bullet_ids: List[str]) -> str:
    header, bullet_blocks, footer = parse_tex_template(tex_content)
    
    ordered_blocks = []
    seen = set()
    for b_id in ordered_bullet_ids:
        if b_id in bullet_blocks:
            ordered_blocks.append(bullet_blocks[b_id])
            seen.add(b_id)
            
    # Include any remaining bullet blocks not specified in ordered list
    for b_id, block in bullet_blocks.items():
        if b_id not in seen:
            ordered_blocks.append(block)
            
    return header + "".join(ordered_blocks) + footer

def find_tectonic_executable() -> Optional[str]:
    # 1. Check system PATH
    tectonic_path = shutil.which("tectonic")
    if tectonic_path:
        return tectonic_path
        
    # 2. Check current working dir or relative paths
    pwd = os.getcwd()
    candidates = [
        os.path.join(pwd, "tectonic.exe"),
        os.path.join(pwd, "tectonic"),
        os.path.join(os.path.dirname(__file__), "tectonic.exe"),
        "tectonic.exe",
        "tectonic"
    ]
    for cand in candidates:
        if os.path.isfile(cand):
            return os.path.abspath(cand)
            
    return None

def compile_pdf(tex_path: str, output_dir: Optional[str] = None) -> Optional[str]:
    tectonic_bin = find_tectonic_executable()
    if not tectonic_bin:
        warnings.warn("Tectonic CLI not found on PATH or local directory. Skipping PDF compilation.")
        return None
        
    tex_abs = os.path.abspath(tex_path)
    if output_dir is None:
        output_dir = os.path.dirname(tex_abs) or "."
        
    try:
        cmd = [tectonic_bin, "--outdir", output_dir, tex_abs]
        result = subprocess.run(cmd, capture_output=True, text=True, check=True)
        base_name = os.path.splitext(os.path.basename(tex_abs))[0]
        pdf_path = os.path.join(output_dir, f"{base_name}.pdf")
        if os.path.exists(pdf_path):
            return os.path.abspath(pdf_path)
        return None
    except (subprocess.SubprocessError, Exception) as e:
        warnings.warn(f"Tectonic PDF compilation failed: {e}")
        return None

def tailor_resume(
    jd_text: str,
    tex_path: str = "base_resume.tex",
    keywords_path: str = "bullet_keywords.json",
    output_tex_path: str = "tailored_resume.tex",
    compile_to_pdf: bool = True
) -> Dict[str, Any]:
    bullet_keywords = load_bullet_keywords(keywords_path)
    ordered_bullets = compute_jaccard_scores(jd_text, bullet_keywords)
    
    if not os.path.exists(tex_path):
        raise FileNotFoundError(f"LaTeX base resume template not found: {tex_path}")
        
    with open(tex_path, "r", encoding="utf-8") as f:
        tex_content = f.read()
        
    ordered_ids = [item["id"] for item in ordered_bullets]
    tailored_tex = reorder_tex_content(tex_content, ordered_ids)
    
    os.makedirs(os.path.dirname(os.path.abspath(output_tex_path)), exist_ok=True)
    with open(output_tex_path, "w", encoding="utf-8") as f:
        f.write(tailored_tex)
        
    pdf_path = None
    if compile_to_pdf:
        output_dir = os.path.dirname(os.path.abspath(output_tex_path))
        pdf_path = compile_pdf(output_tex_path, output_dir=output_dir)
        
    return {
        "ordered_bullets": ordered_bullets,
        "tex_path": os.path.abspath(output_tex_path),
        "pdf_path": pdf_path
    }

class TailoringAgent:
    def __init__(self, tex_path: str = "base_resume.tex", keywords_path: str = "bullet_keywords.json"):
        self.tex_path = tex_path
        self.keywords_path = keywords_path
        
    def tailor(self, jd_text: str, output_tex_path: str = "tailored_resume.tex", compile_to_pdf: bool = True) -> Dict[str, Any]:
        return tailor_resume(
            jd_text=jd_text,
            tex_path=self.tex_path,
            keywords_path=self.keywords_path,
            output_tex_path=output_tex_path,
            compile_to_pdf=compile_to_pdf
        )

if __name__ == "__main__":
    sample_jd = """
    We are looking for a Computer Vision Engineer to work on object detection,
    YOLOv8, GeoTIFF drone imagery, rasterio, and PyTorch deep learning pipelines.
    """
    result = tailor_resume(sample_jd)
    print("Tailoring Result:")
    print(json.dumps(result, indent=2))

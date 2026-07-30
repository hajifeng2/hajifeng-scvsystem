"""扫描件 PDF OCR 补 txt（step4_extract_pdf.py 对扫描件失效时用）。

用法:
  python scripts/ocr_pdf.py "<PDF路径>"
  python scripts/ocr_pdf.py "工作区/客户端开发（U3D）/待评估/xxx.pdf"

依赖:
  - pymupdf（渲染 PDF 为图片）
  - tesseract（OCR 引擎）+ chi_sim 中文语言包

环境前提（一次性）:
  - winget install UB-Mannheim.TesseractOCR  ->  装到 C:\\Program Files\\Tesseract-OCR\\
  - Program Files 写不进去时，把 tessdata 建到用户目录并下载 chi_sim：
      mkdir C:\\Users\\<user>\\.tessdata
      copy "C:\\Program Files\\Tesseract-OCR\\tessdata\\eng.traineddata" C:\\Users\\<user>\\.tessdata\\
      curl -L -o C:\\Users\\<user>\\.tessdata\\chi_sim.traineddata ^
        https://github.com/tesseract-ocr/tessdata_fast/raw/main/chi_sim.traineddata
  - 换机器改 config.json 的 ocr 段（tesseract_exe / tessdata_dir），代码不动。

产物: 写到 <PDF所在目录>/txt2/<同名>.txt（覆盖），与 step4 产物位置一致，Agent 可直接读。
"""
import sys
import subprocess
import tempfile
from pathlib import Path

import fitz

sys.path.insert(0, str(Path(__file__).parent))
from lib.config import load_config, resolve                              # noqa: E402

DPI = 300  # 渲染分辨率，越高越准但越慢
LANG = "chi_sim+eng"
PSM = "6"  # 页面分割模式：6=统一文本块（简历常用）


def _load_ocr_paths():
    """从 config.json 读 tesseract 路径。换机器只改 config.json 的 ocr 段，代码不动。"""
    cfg = load_config()
    ocr = cfg.get("ocr", {})
    tess_raw = ocr.get("tesseract_exe", "").strip()
    tessdata_raw = ocr.get("tessdata_dir", "").strip()
    if not tess_raw or not tessdata_raw:
        raise SystemExit(
            "❌ config.json 缺 ocr.tesseract_exe / ocr.tessdata_dir。\n"
            "   换机器时在 config.json 的 ocr 段填本机路径，参考 config.example.json。"
        )
    tess = resolve(tess_raw)
    tessdata = resolve(tessdata_raw)
    if not tess.exists():
        raise SystemExit(
            f"❌ tesseract.exe 不存在：{tess}\n"
            f"   检查 config.json 的 ocr.tesseract_exe，或先装 Tesseract（见本文件顶部说明）。"
        )
    if not tessdata.exists():
        raise SystemExit(
            f"❌ tessdata 目录不存在：{tessdata}\n"
            f"   检查 config.json 的 ocr.tessdata_dir，或先下载 chi_sim 语言包（见本文件顶部说明）。"
        )
    return str(tess), str(tessdata)


def ocr_pdf(pdf_path: str) -> str:
    pdf = Path(pdf_path)
    if not pdf.exists():
        print(f"❌ PDF 不存在：{pdf}")
        sys.exit(1)

    TESS, TESSDATA = _load_ocr_paths()  # 本机路径从 config 读，换机器只改 config

    out_dir = pdf.parent / "txt2"
    out_dir.mkdir(exist_ok=True)
    out_txt = out_dir / (pdf.stem + ".txt")

    doc = fitz.open(pdf)
    parts = []
    with tempfile.TemporaryDirectory() as td:
        for i, page in enumerate(doc):
            pix = page.get_pixmap(matrix=fitz.Matrix(DPI / 72, DPI / 72))
            img = Path(td) / f"p{i}.png"
            pix.save(str(img))
            r = subprocess.run(
                [TESS, str(img), "stdout",
                 "--tessdata-dir", TESSDATA,
                 "-l", LANG, "--psm", PSM],
                capture_output=True,
            )
            text = r.stdout.decode("utf-8", errors="replace")
            parts.append(text)

    full = "\n".join(parts)
    out_txt.write_text(full, encoding="utf-8")
    print(f"OCR 完成：{pdf.name} -> {len(full)} 字符，{len(doc)} 页")
    print("--- 前 600 字符预览 ---")
    print(full[:600])
    return full


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("用法: python scripts/ocr_pdf.py <PDF路径>")
        sys.exit(1)
    ocr_pdf(sys.argv[1])

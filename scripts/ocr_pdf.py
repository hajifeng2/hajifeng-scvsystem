"""扫描件 PDF OCR 补 txt（step4_extract_pdf.py 对扫描件失效时用）。

用法:
  python scripts/ocr_pdf.py "<PDF路径>"
  python scripts/ocr_pdf.py "工作区/客户端开发（U3D）/待评估/xxx.pdf"

依赖:
  - pymupdf（渲染 PDF 为图片）
  - tesseract（OCR 引擎）+ chi_sim 中文语言包

环境前提（一次性）:
  - winget install UB-Mannheim.TesseractOCR  -> 装到 C:\\Program Files\\Tesseract-OCR\\
  - Program Files 写不进去时，把 tessdata 建到用户目录并下载 chi_sim：
      mkdir C:\\Users\\<user>\\.tessdata
      copy "C:\\Program Files\\Tesseract-OCR\\tessdata\\eng.traineddata" C:\\Users\\<user>\\.tessdata\\
      curl -L -o C:\\Users\\<user>\\.tessdata\\chi_sim.traineddata ^
        https://github.com/tesseract-ocr/tessdata_fast/raw/main/chi_sim.traineddata
  - 换机器改下方 TESS / TESSDATA 路径。

产物: 写到 <PDF所在目录>/txt2/<同名>.txt（覆盖），与 step4 产物位置一致，Agent 可直接读。
"""
import sys
import subprocess
import tempfile
from pathlib import Path

import fitz

TESS = r"C:\Program Files\Tesseract-OCR\tesseract.exe"
TESSDATA = r"C:\Users\hejch\.tessdata"
DPI = 300  # 渲染分辨率，越高越准但越慢
LANG = "chi_sim+eng"
PSM = "6"  # 页面分割模式：6=统一文本块（简历常用）


def ocr_pdf(pdf_path: str) -> str:
    pdf = Path(pdf_path)
    if not pdf.exists():
        print(f"❌ PDF 不存在：{pdf}")
        sys.exit(1)

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

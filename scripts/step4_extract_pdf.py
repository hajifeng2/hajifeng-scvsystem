"""Step 4：pymupdf 批量提取 PDF 文本（严格按 docs/PDF文本提取方法.md）。

用法:
  python step4_extract_pdf.py <PDF目录>
  python step4_extract_pdf.py "工作区/客户端实习生（U3D）/简历库"
  python step4_extract_pdf.py "工作区/客户端实习生（U3D）/待评估"

产出到 <PDF目录>/txt2/，文件名同 PDF 改 .txt。
逐份打印字符数 + 质量校验（✓ / ✗需重提或 OCR）。

⚠️ PDF 原件只读，不改名不删。产物只进 txt2/。
⚠️ 扫描件（get_text 返回空/极少）质量校验会标红，需 OCR（tesseract，本脚本不处理）。
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from lib.pdf_extract import extract_one, quality_check   # noqa: E402


def main():
    if len(sys.argv) < 2:
        print("用法: python step4_extract_pdf.py <PDF目录>")
        return
    src = Path(sys.argv[1])
    if not src.exists():
        print(f"❌ 目录不存在：{src}")
        return
    out = src / "txt2"
    out.mkdir(exist_ok=True)

    pdfs = sorted(src.glob("*.pdf"))
    if not pdfs:
        print(f"⚠️  {src} 下没有 .pdf 文件。")
        return

    ok_cnt, bad = 0, []
    print(f"提取 {len(pdfs)} 份 PDF -> {out}")
    for pdf in pdfs:
        try:
            text = extract_one(pdf)
        except Exception as e:
            print(f"  ✗ {pdf.name}: 提取异常 {e}")
            bad.append(pdf.name)
            continue
        ok, msg = quality_check(text)
        (out / (pdf.stem + ".txt")).write_text(text, encoding="utf-8")
        mark = "✓" if ok else "✗"
        print(f"  {mark} {pdf.name}: {msg}")
        if ok:
            ok_cnt += 1
        else:
            bad.append(pdf.name)

    print(f"\n完成：{ok_cnt}/{len(pdfs)} 合格。")
    if bad:
        print("不合格（需 OCR 或重提）：")
        for b in bad:
            print(f"  - {b}")


if __name__ == "__main__":
    main()

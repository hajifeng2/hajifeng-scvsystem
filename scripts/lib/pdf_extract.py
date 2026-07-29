"""pymupdf 提取 + 清洗 + 质量校验。严格按 docs/PDF文本提取方法.md。

- 只用 pymupdf（fitz），不用 pdftotext（水印碎片化、中文丢失，已验证不可用）
- page.get_text() 按阅读顺序，水印自然归拢文末
- 清洗：删水印 hash、孤立 ~ 行、分页符 \\x0c、压缩空行
- 质量校验：正文前 1/3 不应有 HJ42 碎片；文本不过短
- 扫描件（get_text 返回空/极少）需 OCR，本模块不处理，quality_check 会标红
"""
import re

# 本项目 PDF 水印特征：形如 da6f4d52f7abd6351HJ42du0FlJWyoW6V_2dWOGln__TNRdh2g~~
WATERMARK_RE = re.compile(r'[a-f0-9]{8,}HJ42[A-Za-z0-9_\-]+~~')


def clean(text):
    text = WATERMARK_RE.sub('', text)
    text = re.sub(r'^~\s*$', '', text, flags=re.MULTILINE)
    text = text.replace('\x0c', '')
    text = re.sub(r'\n{3,}', '\n\n', text)
    return text.strip()


def extract_one(pdf_path):
    """提取单份 PDF -> 清洗后文本。"""
    import fitz  # pymupdf
    doc = fitz.open(str(pdf_path))
    text = "".join(page.get_text() for page in doc)
    doc.close()
    return clean(text)


def quality_check(text):
    """返回 (ok, msg)。按 PDF文本提取方法.md §4。"""
    if not text or len(text) < 500:
        return False, f"文本过短（{len(text)}字符），疑似扫描件或提取失败，需 OCR（tesseract）"
    head = text[: len(text) // 3]
    hits = len(WATERMARK_RE.findall(head))
    # HJ42 碎片兜底（清洗后正文不应残留）
    hj42 = len(re.findall(r'HJ42', head))
    if hits > 0 or hj42 > 0:
        return False, f"正文前1/3残留水印碎片（hash命中{hits} / HJ42命中{hj42}），需重提"
    return True, f"通过（{len(text)}字符）"

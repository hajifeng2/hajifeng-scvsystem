# PDF 文本提取方法

> 本文档说明如何从简历 PDF 提取干净文本。是 `04-执行SOP.md` Step 1（入库与提取）的具体操作方法。
> **方法已在本项目 PDF 上验证**（2026-07，Python 3.14 + pymupdf 1.28）。

## 1. 推荐工具：pymupdf (fitz) -- 已验证可用

安装：`pip install pymupdf`

### 基本提取
```python
import fitz  # pymupdf

doc = fitz.open(r'路径/简历.pdf')
text = ""
for page in doc:
    text += page.get_text()  # 默认按阅读顺序，水印自然归拢到文末
doc.close()
print(text)
```

### 为什么选 pymupdf
- `page.get_text()` 默认按阅读顺序提取，水印作为独立文本块**自然排到文末**，不污染正文
- 中文解析完整
- 本项目验证：正文干净，水印 hash 归拢在文末几行，与干净数据源 `txt2/` 质量一致

## 2. 不推荐：pdftotext (poppler CLI) -- 已验证不可用

在本项目 PDF 上验证**不可用**：
- **水印碎片化**：水印字符穿插进正文，把电话、日期等切碎（如 `13812345678` → `138oW12345678`，`2005.07.01` → `2005.07.d0W1`）
- **中文大量丢失**（提取长度仅为 pymupdf 的 45%）
- `-layout` 模式同样碎片化
- 本项目 `txt/` 目录就是 pdftotext 失败的产物

若环境只有 pdftotext，**必须逐份校验质量**，不合格换 pymupdf。

## 3. 清洗规则（提取后必做）

```python
import re

def clean(text):
    # 删水印 hash（形如 da6f4d52f7abd6351HJ42du0FlJWyoW6V_2dWOGln__TNRdh2g~~）
    text = re.sub(r'[a-f0-9]{8,}HJ42[A-Za-z0-9_\-]+~~', '', text)
    # 删孤立的 ~ 行
    text = re.sub(r'^~\s*$', '', text, flags=re.MULTILINE)
    # 删分页符 \x0c
    text = text.replace('\x0c', '')
    # 压缩连续空行为单个
    text = re.sub(r'\n{3,}', '\n\n', text)
    return text.strip()
```

> 水印 hash 正则 `[a-f0-9]{8,}HJ42[A-Za-z0-9_\-]+~~` 是本项目 PDF 的水印特征。其他来源 PDF 水印格式可能不同，需按实际情况调整正则。

## 4. 质量校验（每份必做）

提取 + 清洗后，检查：
1. **水印碎片检查**：正文前 1/3 是否还有 `HJ42` 字样 → 有则说明工具/参数不对，重提
2. **中文完整性**：提取长度是否合理（1 页简历通常 ≥1500 字符），中文是否正常显示
3. **关键信息检查**：姓名、电话、项目名是否完整未被切碎

校验不通过 → 换工具重提，**不得将就**（劣质提取会让上层分析全部失真）。

## 5. 批量提取脚本

```python
import fitz, os, glob, re

def clean(text):
    text = re.sub(r'[a-f0-9]{8,}HJ42[A-Za-z0-9_\-]+~~', '', text)
    text = re.sub(r'^~\s*$', '', text, flags=re.MULTILINE)
    text = text.replace('\x0c', '')
    text = re.sub(r'\n{3,}', '\n\n', text)
    return text.strip()

def extract_one(pdf_path):
    doc = fitz.open(pdf_path)
    text = "".join(page.get_text() for page in doc)
    doc.close()
    return clean(text)

src_dir = r'路径/PDF目录'
out_dir = r'路径/txt2输出目录'
os.makedirs(out_dir, exist_ok=True)

for pdf_path in glob.glob(os.path.join(src_dir, '*.pdf')):
    text = extract_one(pdf_path)
    out_name = os.path.splitext(os.path.basename(pdf_path))[0] + '.txt'
    out_path = os.path.join(out_dir, out_name)
    with open(out_path, 'w', encoding='utf-8') as f:
        f.write(text)
    # 简单质量校验
    head_hits = len(re.findall(r'HJ42', text[:len(text)//3]))
    print(f'{out_name}: {len(text)} 字符, 正文HJ42碎片={head_hits} {"✓" if head_hits==0 else "✗需重提"}')
```

## 6. 注意事项

- PDF 原件**只读**，提取产物存到 `txt2/`，不覆盖原件
- 文件名与 PDF 同名改 `.txt`
- 若 PDF 是**扫描件图片**（`get_text()` 返回空或极少），需用 OCR（如 Tesseract）而非文本提取
- 不同 PDF 源的水印格式可能不同，清洗正则需按实际情况调整
- 提取后按 `01-数据规范.md` 的清洗规则二次确认，再填入候选人档案

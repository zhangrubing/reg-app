from pathlib import Path
path = Path('backend/routers/licenses.py')
text = path.read_text(encoding='utf-8')
old = '    csv_content = "\n"\n".join(lines).encode("utf-8-sig")'
if old in text:
    text = text.replace(old, '    csv_content = "\\n".join(lines)\n    csv_bytes = csv_content.encode("utf-8-sig")')
else:
    old2 = '    csv_content = "\r\n"\n".join(lines)
    csv_bytes = csv_content.encode("utf-8-sig")'
    if old2 in text:
        text = text.replace(old2, '    csv_content = "\\n".join(lines)\n    csv_bytes = csv_content.encode("utf-8-sig")')
path.write_text(text, encoding='utf-8')

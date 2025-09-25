from pathlib import Path
text = Path('backend/routers/licenses.py').read_text(encoding='utf-8')
segment = 'csv_bytes'
start = text.index(segment)
print(repr(text[start:start+80]))

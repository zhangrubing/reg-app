from pathlib import Path
text = Path(''templates/licenses.html'').read_text(encoding=''utf-8'')
start = text.index('createBtn.addEventListener')
print(text[start:start+400])

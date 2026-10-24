"""Generate a file tree with size and line count for the bundle read/ section."""
import os

root = r'C:\temp\projects\testproject1'
exclude_dirs = {'.git', '__pycache__', '.venv', '.caliber', 'node_modules'}
exclude_ext = {'.pyc', '.log', '.exe', '.dll', '.so', '.dylib'}

rows = []
total_lines = 0
total_size = 0
file_count = 0
for dirpath, dirnames, filenames in os.walk(root):
    dirnames[:] = [d for d in dirnames if d not in exclude_dirs]
    for fn in sorted(filenames):
        fp = os.path.join(dirpath, fn)
        ext = os.path.splitext(fn)[1].lower()
        if ext in exclude_ext:
            continue
        try:
            size = os.path.getsize(fp)
            with open(fp, 'rb') as f:
                nl = f.read().count(b'\n')
            rel = os.path.relpath(fp, root)
            rows.append((size, nl, rel))
            total_lines += nl
            total_size += size
            file_count += 1
        except Exception:
            pass

rows.sort(key=lambda r: -r[0])
out_lines = []
out_lines.append(f'{"SIZE":>10} {"LINES":>6}  FILE')
out_lines.append('-' * 80)
for size, nl, rel in rows[:100]:
    out_lines.append(f'{size:>10} {nl:>6}  {rel}')
if len(rows) > 100:
    out_lines.append(f'... {len(rows) - 100} more files')
out_lines.append('')
out_lines.append(f'Total: {file_count} files, {total_size} bytes, {total_lines} lines')

result = '\n'.join(out_lines)
out_path = r'C:\temp\projects\testproject1\pilot\assessment\bundle\read\file-tree-loc.txt'
with open(out_path, 'w', encoding='utf-8') as f:
    f.write(result)
print(result)

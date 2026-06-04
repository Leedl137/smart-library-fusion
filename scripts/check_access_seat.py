from pathlib import Path
import os

root = Path(r'C:\Users\think\Desktop\软著\raw_data\图书馆原始数据')

# Find access and seat dirs
for d in root.iterdir():
    if d.is_dir():
        # Try to identify by files
        files = list(d.rglob('*.txt'))
        if files:
            print(f"Dir: {d.name}")
            for f in files[:3]:
                print(f"  {f.name} ({f.stat().st_size} bytes)")
                # Read first few lines
                try:
                    with open(f, 'r', encoding='utf-8') as fh:
                        for i, line in enumerate(fh):
                            if i >= 3:
                                break
                            print(f"    {line.rstrip()}")
                except:
                    try:
                        with open(f, 'r', encoding='gbk') as fh:
                            for i, line in enumerate(fh):
                                if i >= 3:
                                    break
                                print(f"    {line.rstrip()}")
                    except Exception as e:
                        print(f"    Error: {e}")
            print()

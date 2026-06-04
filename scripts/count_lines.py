from pathlib import Path

root = Path(r'C:\Users\think\Desktop\软著\raw_data\图书馆原始数据')

for d in root.iterdir():
    if d.is_dir():
        files = list(d.rglob('*.txt'))
        if files:
            total = 0
            for f in files:
                if f.name in ['ReadingRoom.txt', 'Student.txt']:
                    continue
                with open(f, 'r', encoding='utf-8') as fh:
                    count = sum(1 for _ in fh)
                total += count - 1  # minus header
                print(f"{f.name}: {count-1} lines")
            print(f"Total for {d.name}: {total}")
            print()

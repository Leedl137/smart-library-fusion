import pandas as pd
from pathlib import Path

RAW_ROOT = Path(r'C:\Users\think\Desktop\软著\raw_data\图书馆原始数据')
borrow_file = RAW_ROOT / '借阅数据' / '借阅数据' / '借阅数据_guid.csv'

df = pd.read_csv(borrow_file, nrows=5, encoding='utf-8', dtype=str)
print('Columns:', list(df.columns))
print(df)

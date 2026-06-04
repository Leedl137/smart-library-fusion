import pandas as pd
from sqlalchemy import create_engine
import time

engine = create_engine('mysql+pymysql://root:123456@127.0.0.1:3306/smart_library_v2?charset=utf8mb4')

# Read first 5000 rows
path = r'C:\Users\think\Desktop\软著\smart_library_fusion\scripts\tmp_csv\books.csv'
df = pd.read_csv(path, nrows=5000, encoding='utf-8-sig', dtype=str)
print(f'DataFrame shape: {df.shape}')

t0 = time.time()
df.to_sql('books', engine, if_exists='append', index=False, method='multi', chunksize=1000)
t1 = time.time()
print(f'Inserted 5000 rows in {t1-t0:.2f}s')

with engine.connect() as conn:
    r = conn.execute('SELECT COUNT(*) FROM books')
    print('Total books:', r.scalar())
engine.dispose()

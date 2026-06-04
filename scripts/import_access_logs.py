import pandas as pd
import pymysql
from pathlib import Path
import csv
import json
import time

RAW_ROOT = Path(r'C:\Users\think\Desktop\软著\raw_data\图书馆原始数据')
TMP_DIR = Path(r'C:\Users\think\Desktop\软著\smart_library_fusion\scripts\tmp_csv')
TMP_DIR.mkdir(exist_ok=True)

DB_CONFIG = {
    'host': '127.0.0.1', 'port': 3306, 'user': 'root',
    'password': '123456', 'database': 'smart_library_v2', 'local_infile': True,
}

def get_conn():
    return pymysql.connect(**DB_CONFIG)

# Load user map
print("Loading user map...")
conn = get_conn()
with conn.cursor() as cur:
    cur.execute("SELECT id, uid FROM users")
    uid_to_id = {row[1]: row[0] for row in cur.fetchall()}
conn.close()
print(f"  Mapped {len(uid_to_id)} users")

# State tracking
state_file = TMP_DIR / 'access_import_state.json'
if state_file.exists():
    with open(state_file, 'r') as f:
        state = json.load(f)
else:
    state = {'completed_files': []}

# Find access log dir
access_dir = None
for d in RAW_ROOT.iterdir():
    if d.is_dir():
        files = list(d.rglob('*.txt'))
        for f in files:
            if f.name.startswith('2014') or f.name.startswith('2015') or f.name.startswith('2016') or f.name.startswith('2017'):
                with open(f, 'r', encoding='utf-8') as fh:
                    header = fh.readline()
                    if 'VisitTime' in header and 'Location' in header and 'ReadingRoomNo' not in header:
                        access_dir = d
                        break
        if access_dir:
            break

if not access_dir:
    print("Access data directory not found!")
    exit(1)

print(f"Access dir: {access_dir}")

# Process each file
all_files = sorted([f for f in access_dir.rglob('*.txt') if f.name.startswith('20')])
total_imported = 0

for f in all_files:
    if f.name in state['completed_files']:
        print(f"  Skip completed: {f.name}")
        continue
    
    print(f"Processing {f.name}...")
    file_total = 0
    chunk_size = 100000
    
    for chunk in pd.read_csv(f, encoding='utf-8', dtype=str, sep='\t', chunksize=chunk_size):
        # Normalize column names
        col_map = {}
        for c in chunk.columns:
            cl = c.lower()
            if cl == 'id':
                col_map[c] = 'uid'
            elif cl == 'visittime':
                col_map[c] = 'visit_time'
            elif cl == 'location':
                col_map[c] = 'location'
        chunk = chunk.rename(columns=col_map)
        
        chunk['user_id'] = chunk['uid'].map(uid_to_id)
        chunk = chunk[chunk['user_id'].notna()].copy()
        if len(chunk) == 0:
            continue
        
        chunk['visit_time'] = pd.to_datetime(chunk['visit_time'], errors='coerce')
        chunk['location'] = chunk['location'].astype(str).str[:50].apply(lambda x: x.encode('utf-8', errors='ignore').decode('utf-8'))
        chunk['access_type'] = 'in'
        
        acols = ['user_id', 'visit_time', 'location', 'access_type']
        csv_path = str(TMP_DIR / 'access_temp.csv')
        chunk[acols].to_csv(csv_path, index=False, encoding='utf-8-sig', quoting=csv.QUOTE_ALL)
        
        conn = get_conn()
        with conn.cursor() as cur:
            cur.execute("SET GLOBAL local_infile = 1")
            cur.execute("SET FOREIGN_KEY_CHECKS=0")
            cur.execute(f"""
            LOAD DATA LOCAL INFILE '{csv_path.replace(chr(92), chr(47))}'
            INTO TABLE access_logs CHARACTER SET utf8mb4
            FIELDS TERMINATED BY ',' OPTIONALLY ENCLOSED BY '"'
            LINES TERMINATED BY '\r\n' IGNORE 1 LINES
            ({','.join(acols)})
            """)
            conn.commit()
        conn.close()
        
        file_total += len(chunk)
        total_imported += len(chunk)
        print(f"    +{len(chunk)} => file {file_total}, total {total_imported}")
    
    state['completed_files'].append(f.name)
    with open(state_file, 'w') as fh:
        json.dump(state, fh)
    print(f"  Completed {f.name}: {file_total}")

print(f"\nAccess logs total imported: {total_imported}")

# Verify
conn = get_conn()
with conn.cursor() as cur:
    cur.execute("SELECT COUNT(*) FROM access_logs")
    print(f"DB total: {cur.fetchone()[0]}")
conn.close()

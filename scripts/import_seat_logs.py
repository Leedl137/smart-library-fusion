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
state_file = TMP_DIR / 'seat_import_state.json'
if state_file.exists():
    with open(state_file, 'r') as f:
        state = json.load(f)
else:
    state = {'completed_files': []}

# Find seat log files (skip ReadingRoom.txt and Student.txt)
seat_dir = None
for d in RAW_ROOT.iterdir():
    if d.is_dir():
        files = list(d.rglob('*.txt'))
        for f in files:
            if f.name.startswith('2014') or f.name.startswith('2015') or f.name.startswith('2016') or f.name.startswith('2017'):
                # Check if this is seat data (has ReadingRoomNo column)
                with open(f, 'r', encoding='utf-8') as fh:
                    header = fh.readline()
                    if 'ReadingRoomNo' in header and 'SeatNo' in header:
                        seat_dir = d
                        break
        if seat_dir:
            break

if not seat_dir:
    print("Seat data directory not found!")
    exit(1)

print(f"Seat dir: {seat_dir}")

# Process each file
all_files = sorted([f for f in seat_dir.rglob('*.txt') if f.name.startswith('20')])
total_imported = 0

for f in all_files:
    if f.name in state['completed_files']:
        print(f"  Skip completed: {f.name}")
        continue
    
    print(f"Processing {f.name}...")
    file_total = 0
    chunk_size = 100000
    
    for chunk in pd.read_csv(f, encoding='utf-8', dtype=str, sep='\t', chunksize=chunk_size):
        # Normalize column names (case-insensitive)
        col_map = {}
        for c in chunk.columns:
            cl = c.lower()
            if cl == 'id':
                col_map[c] = 'uid'
            elif cl == 'readingroomno':
                col_map[c] = 'room_no'
            elif cl == 'seatno':
                col_map[c] = 'seat_no'
            elif cl == 'selectseattime':
                col_map[c] = 'start_time'
            elif cl == 'leaveseattime':
                col_map[c] = 'end_time'
        chunk = chunk.rename(columns=col_map)
        chunk['user_id'] = chunk['uid'].map(uid_to_id)
        chunk = chunk[chunk['user_id'].notna()].copy()
        if len(chunk) == 0:
            continue
        
        chunk['room_no'] = chunk['room_no'].str.lstrip('0').str[:20]
        chunk['seat_no'] = chunk['seat_no'].str[:20]
        chunk['start_time'] = pd.to_datetime(chunk['start_time'], errors='coerce')
        chunk['end_time'] = pd.to_datetime(chunk['end_time'], errors='coerce')
        
        scols = ['user_id', 'room_no', 'seat_no', 'start_time', 'end_time']
        csv_path = str(TMP_DIR / 'seat_temp.csv')
        chunk[scols].to_csv(csv_path, index=False, encoding='utf-8-sig', quoting=csv.QUOTE_ALL)
        
        conn = get_conn()
        with conn.cursor() as cur:
            cur.execute("SET GLOBAL local_infile = 1")
            cur.execute("SET FOREIGN_KEY_CHECKS=0")
            cur.execute(f"""
            LOAD DATA LOCAL INFILE '{csv_path.replace(chr(92), chr(47))}'
            INTO TABLE seat_logs CHARACTER SET utf8mb4
            FIELDS TERMINATED BY ',' OPTIONALLY ENCLOSED BY '"'
            LINES TERMINATED BY '\r\n' IGNORE 1 LINES
            ({','.join(scols)})
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

print(f"\nSeat logs total imported: {total_imported}")

# Verify
conn = get_conn()
with conn.cursor() as cur:
    cur.execute("SELECT COUNT(*) FROM seat_logs")
    print(f"DB total: {cur.fetchone()[0]}")
conn.close()

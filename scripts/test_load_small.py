import csv
import pymysql

test_csv = r'C:\Users\think\Desktop\软著\smart_library_fusion\scripts\tmp_csv\test_books.csv'
with open(test_csv, 'w', encoding='utf-8-sig', newline='') as f:
    w = csv.writer(f, quoting=csv.QUOTE_ALL)
    w.writerow(['isbn','barcode','title','authors','publisher','publish_year','category_code','call_no','language','doc_type','total_copies','available_copies','location','status'])
    for i in range(100):
        w.writerow([f'TEST{i:04d}', f'TEST{i:04d}', 'Test Book', 'Author', 'Publisher', '2020', 'A', 'A123', 'Chinese', 'Book', 1, 1, '3F', 'onshelf'])
print('Test CSV created')

conn = pymysql.connect(host='127.0.0.1', port=3306, user='root', password='123456', database='smart_library_v3', local_infile=True)
with conn.cursor() as cur:
    sql = f"""LOAD DATA LOCAL INFILE '{test_csv.replace(chr(92), chr(47))}' INTO TABLE books CHARACTER SET utf8mb4 FIELDS TERMINATED BY ',' OPTIONALLY ENCLOSED BY '"' LINES TERMINATED BY '\r\n' IGNORE 1 LINES (isbn,barcode,title,authors,publisher,publish_year,category_code,call_no,language,doc_type,total_copies,available_copies,location,status)"""
    cur.execute(sql)
    print('Affected:', cur.rowcount)
conn.commit()
with conn.cursor() as cur:
    cur.execute('SELECT COUNT(*) FROM books')
    print('Total books:', cur.fetchone()[0])
conn.close()

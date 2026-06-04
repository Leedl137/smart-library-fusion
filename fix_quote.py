with open('app/dashboard_data.py', 'r', encoding='utf-8') as f:
    content = f.read()

# Fix all occurrences of four quotes to three quotes
content = content.replace('""""', '"""')

with open('app/dashboard_data.py', 'w', encoding='utf-8') as f:
    f.write(content)

print('Fixed all occurrences')

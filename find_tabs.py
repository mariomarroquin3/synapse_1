import sys

with open('pages/admin_dashboard.py', 'r', encoding='utf-8') as f:
    lines = f.readlines()

for i, line in enumerate(lines):
    if 'with tab3:' in line:
        print(f"tab3 at {i}")
    if 'with tab5:' in line:
        print(f"tab5 at {i}")

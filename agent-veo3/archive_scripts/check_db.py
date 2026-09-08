import sqlite3

conn = sqlite3.connect('agent-veo3/flow_agent.db')
c = conn.cursor()
c.execute("SELECT tbl_name, sql FROM sqlite_master WHERE type='table'")
for row in c.fetchall():
    print("TABLE:", row[0])
    print(row[1])
    print("-" * 40)

print("\n--- PROJECTS ---")
try:
    c.execute("SELECT * FROM projects")
    for r in c.fetchall():
        print(r)
except Exception as e:
    print("projects error:", e)

try:
    c.execute("SELECT * FROM project")
    for r in c.fetchall():
        print(r)
except Exception as e:
    print("project error:", e)

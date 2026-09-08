import sqlite3, sys
sys.stdout.reconfigure(encoding='utf-8')

conn = sqlite3.connect('agent-veo3/flow_agent.db')
c = conn.cursor()

print("=== PROJECTS ===")
c.execute("SELECT id, name, created_at FROM project")
for r in c.fetchall():
    print(r)

print("\n=== VIDEOS ===")
c.execute("SELECT id, project_id, title, status FROM video")
for r in c.fetchall():
    print(r)

print("\n=== SCENES COUNT PER VIDEO ===")
c.execute("SELECT video_id, count(*) FROM scene GROUP BY video_id")
for r in c.fetchall():
    print(r)

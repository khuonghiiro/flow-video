import sqlite3, sys
sys.stdout.reconfigure(encoding='utf-8')

conn = sqlite3.connect('agent-veo3/flow_agent.db')
c = conn.cursor()

c.execute("SELECT * FROM project WHERE id='4c6ba350-a18d-4b05-ae59-67f076ba1883'")
print("PROJECT ROW:", c.fetchall())

c.execute("SELECT count(*), type, status FROM request WHERE project_id='4c6ba350-a18d-4b05-ae59-67f076ba1883' GROUP BY type, status")
print("REQUESTS FOR 4c6ba350:", c.fetchall())

c.execute("SELECT count(*), type, status FROM request WHERE project_id='2383473a-b49c-4ba3-9814-07cd2c547743' GROUP BY type, status")
print("REQUESTS FOR 2383473a:", c.fetchall())

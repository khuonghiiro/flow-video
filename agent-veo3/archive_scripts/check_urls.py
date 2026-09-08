import sqlite3, sys
sys.stdout.reconfigure(encoding='utf-8')

conn = sqlite3.connect('agent-veo3/flow_agent.db')
c = conn.cursor()

print("--- Linh-Am video scenes (video_id=bae51a4e-786a-42a5-bead-f008c8b63895) ---")
c.execute("SELECT id, display_order, vertical_video_media_id, vertical_video_url, vertical_upscale_url FROM scene WHERE video_id='bae51a4e-786a-42a5-bead-f008c8b63895' LIMIT 3")
for r in c.fetchall():
    print(r)

print("\n--- Thanh-Van video scenes (video_id=9c6ccc14-7834-4973-bac5-e4261fbd552a) ---")
c.execute("SELECT id, display_order, vertical_video_media_id, vertical_video_url, vertical_upscale_url FROM scene WHERE video_id='9c6ccc14-7834-4973-bac5-e4261fbd552a' LIMIT 3")
for r in c.fetchall():
    print(r)

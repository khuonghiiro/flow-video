import asyncio, json, sys
sys.stdout.reconfigure(encoding='utf-8')
from agent.services.flow_client import get_flow_client

async def test():
    client = get_flow_client()
    # connect WS check
    res = await client.check_video_status(media=[
        {"name": "a6accfab-618d-4ff1-b229-0395f853b6fb", "projectId": "4c6ba350-a18d-4b05-ae59-67f076ba1883"}
    ])
    print("Result:", json.dumps(res, indent=2))

asyncio.run(test())

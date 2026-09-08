"""Test script to test jHPbke and o8DA4 batchexecute RPCs for Project Creation & Renaming."""
import asyncio
import json
import sys
import time

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

from agent.flowkit_loader import bootstrap_flowkit
bootstrap_flowkit()

from agent.services.flow_client import get_flow_client
import agent.services.flow_batch as fb


async def test_project_rpc():
    print("==================================================================")
    print("   TESTING GOOGLE FLOW BATCHEXECUTE: jHPbke (CREATE) & o8DA4 (RENAME)")
    print("==================================================================")
    client = get_flow_client()

    # Wait for extension connection if needed
    for _ in range(10):
        if client.connected:
            break
        await asyncio.sleep(1)

    print(f"[*] Client connected: {client.connected}")
    if not client.connected:
        print("[!] Extension not connected. Make sure server is running and extension is active.")
        return

    test_title = f"Test Auto Project {int(time.time())}"
    print(f"\n[1] Calling jHPbke to CREATE project with title '{test_title}'...")

    # inner: ["projects/*", [null, [title]], [null, 22]]
    inner_create = ["projects/*", [None, [test_title]], [None, 22]]
    freq_create = fb.build_envelope("jHPbke", inner_create)

    try:
        t0 = time.time()
        payload = await client._batch_payload("jHPbke", freq_create, timeout=60)
        elapsed = time.time() - t0
        print(f"  [SUCCESS] jHPbke returned in {elapsed:.2f}s!")
        print(f"  Raw payload: {payload}")

        new_project_id = None
        if isinstance(payload, list) and len(payload) > 0:
            new_project_id = payload[0]
        elif isinstance(payload, str):
            new_project_id = payload

        print(f"  [CREATED PROJECT ID]: {new_project_id}")

        if not new_project_id:
            print("[!] Could not parse project ID from response.")
            return

        # [2] Test renaming with o8DA4
        renamed_title = f"{test_title} - Renamed"
        print(f"\n[2] Calling o8DA4 to RENAME project to '{renamed_title}'...")
        # inner: ["projects/<project_id>", [title], [["project_title"]], [null, 22]]
        inner_rename = [f"projects/{new_project_id}", [renamed_title], [["project_title"]], [None, 22]]
        freq_rename = fb.build_envelope("o8DA4", inner_rename)

        t1 = time.time()
        rename_payload = await client._batch_payload("o8DA4", freq_rename, timeout=30)
        elapsed_rename = time.time() - t1
        print(f"  [SUCCESS] o8DA4 returned in {elapsed_rename:.2f}s!")
        print(f"  Rename payload: {rename_payload}")

    except Exception as e:
        print(f"[!] RPC call failed: {type(e).__name__}: {e}")


if __name__ == "__main__":
    asyncio.run(test_project_rpc())

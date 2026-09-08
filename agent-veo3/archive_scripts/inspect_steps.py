import json, sys
sys.stdout.reconfigure(encoding='utf-8')

path = r'C:\Users\Admin\.gemini\antigravity-ide\brain\3023c840-397d-4812-af3e-b962a5c5615a\.system_generated\logs\transcript_full.jsonl'
with open(path, 'r', encoding='utf-8') as f:
    for line in f:
        obj = json.loads(line)
        idx = obj.get('step_index')
        if idx and 955 <= idx <= 965:
            tc = obj.get('tool_calls', [])
            for call in tc:
                print(f"Step {idx}: {call.get('name')}")
                args = call.get('arguments', {})
                if 'CommandLine' in args:
                    print(args['CommandLine'][:200])

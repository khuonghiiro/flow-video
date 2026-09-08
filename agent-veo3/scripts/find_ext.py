import os
import glob
import json

base = os.path.expandvars(r'%LOCALAPPDATA%\Google\Chrome\User Data')
for root, dirs, files in os.walk(base):
    for fn in ('Preferences', 'Secure Preferences'):
        if fn in files:
            p = os.path.join(root, fn)
            try:
                with open(p, 'r', encoding='utf-8', errors='ignore') as f:
                    content = f.read()
                    if 'Flow Kit' in content or 'agent-veo3' in content or 'AI-Render-Video' in content:
                        print("Found match in:", p)
                        f.seek(0)
                        data = json.loads(content)
                        exts = data.get('extensions', {}).get('settings', {})
                        for k, v in exts.items():
                            path = v.get('path', '')
                            manifest = v.get('manifest', {})
                            name = manifest.get('name', '')
                            if 'Flow Kit' in name or 'agent-veo3' in path or 'AI-Render-Video' in path:
                                print(f"  Ext ID: {k}, Name: {name}, Path: {path}")
            except Exception as e:
                pass

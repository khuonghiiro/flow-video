import urllib.request
import json

code = """
try {
    const cards = Array.from(document.querySelectorAll('div, section, article, button')).filter(el => {
        const t = el.innerText || '';
        return t.includes('idle') || t.includes('walk') || t.includes('run') || t.includes('Veo');
    });
    return {
        count: cards.length,
        samples: cards.slice(0, 5).map(c => c.innerText.slice(0, 150))
    };
} catch(e) {
    return { error: e.message };
}
"""

# Test exec_tab
req = urllib.request.Request(
    'http://127.0.0.1:8100/api/flow/exec-tab',
    data=json.dumps({'code': 'inspect_project', 'tab_id': 2133555396}).encode('utf-8'),
    headers={'Content-Type': 'application/json'}
)
try:
    res = json.loads(urllib.request.urlopen(req).read().decode('utf-8'))
    print("exec-tab result:", json.dumps(res, indent=2))
except Exception as e:
    print("Error:", e)

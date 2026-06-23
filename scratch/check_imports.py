import re
import os

with open('static/js/app.js', 'r') as f:
    app_code = f.read()

# find all `import { a, b, c } from './xyz.js'`
imports = re.findall(r'import\s+\{([^}]+)\}\s+from\s+[\'"](.*?)[\'"]', app_code)

for names, module in imports:
    if not module.startswith('./'): continue
    mod_path = os.path.join('static/js', module.replace('./', ''))
    if not os.path.exists(mod_path):
        print(f"Module {mod_path} does not exist!")
        continue
    
    with open(mod_path, 'r') as f:
        mod_code = f.read()
    
    # Very naive parsing: find `export function X`, `export async function X`, `export const X`, `export let X`, `export var X`
    exports = re.findall(r'export\s+(?:async\s+)?(?:function|const|let|var)\s+([a-zA-Z0-9_]+)', mod_code)
    
    requested = [n.strip() for n in names.split(',')]
    for req in requested:
        if not req: continue
        # Handle "import { X as Y }"
        if ' as ' in req:
            req = req.split(' as ')[0].strip()
            
        if req not in exports:
            print(f"ERROR: {req} is imported from {module} but not exported!")

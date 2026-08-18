import glob

profile_html = """
<div class="flex items-center gap-sm mt-2 p-sm rounded-lg bg-surface-container-lowest border border-outline-variant shadow-sm overflow-hidden">
    <div id="sidebar-user-avatar" class="w-8 h-8 rounded-full bg-primary text-on-primary flex items-center justify-center font-bold text-sm shrink-0">U</div>
    <div class="flex-1 overflow-hidden">
        <p id="sidebar-user-name" class="font-semibold text-sm text-on-surface truncate">User Name</p>
        <p id="sidebar-user-role" class="text-xs text-on-surface-variant truncate">user@example.com</p>
    </div>
</div>
"""

files = glob.glob('frontend/*.html')
for file in files:
    if file == 'frontend/login.html' or file == 'frontend/interview.html':
        continue
    with open(file, 'r') as f:
        content = f.read()
    
    # Check if we already injected it
    if 'sidebar-user-avatar' in content:
        continue
        
    # Replace the sidebar footer closing div with the profile html
    target = '            </a>\n</div>\n</nav>'
    if target in content:
        content = content.replace(target, '            </a>\n' + profile_html + '\n</div>\n</nav>')
        with open(file, 'w') as f:
            f.write(content)
        print(f"Updated {file}")
    else:
        print(f"Could not find target in {file}")


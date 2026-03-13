import os
import re

base_dir = '/home/saberch/GreenLedger_V5_Antigravity/templates/academy/modules'
progress_block = """
{% block academy_progress %}
<!-- Persistent Module Progress Bar -->
<div
    class="sticky top-0 z-50 w-full bg-white/95 dark:bg-[#0d1310]/95 backdrop-blur-sm border-b border-[#f0f4f2] dark:border-[#2a4035] px-8 py-1">
    <div class="max-w-7xl mx-auto flex items-center justify-between gap-4">
        <div class="flex-1 h-1 bg-gray-100 dark:bg-gray-800 rounded-full overflow-hidden">
            <div id="academy-progress-bar"
                class="h-full bg-primary transition-all duration-500 shadow-[0_0_8px_rgba(19,236,128,0.3)]"
                style="width: 0%"></div>
        </div>
        <span id="academy-progress-text"
            class="text-[9px] font-black uppercase tracking-widest text-[#618975] whitespace-nowrap">0%
            Completed</span>
    </div>
</div>
{% endblock %}
"""

script_block = """
    <script>
        document.addEventListener('DOMContentLoaded', () => {
            const viewedSections = {{ (progress.viewed_sections or '[]') | safe }};
            window.tracker = new AcademyTracker({{ module_id }}, viewedSections);
        });
    </script>
"""

for i in range(1, 15):
    fname = os.path.join(base_dir, f'module_{i}.html')
    if not os.path.exists(fname): continue
    
    with open(fname, 'r') as f:
        content = f.read()

    # Fix const tracker and module-p-data in 1,2,3
    if i in [1, 2, 3]:
        content = re.sub(r'<div id="module-p-data".*?</div>', '', content, flags=re.DOTALL)
        content = re.sub(r'const pData = document\.getElementById\(\'module-p-data\'\);\s*const tracker = new AcademyTracker\(pData\.dataset\.moduleId\);', '', content)
        content = re.sub(r'(?<!window\.)tracker\.markModuleCompleted', 'window.tracker.markModuleCompleted', content)
        content = re.sub(r'const viewedSections = JSON\.parse\(pData\.dataset\.viewedSections\);\s*viewedSections\.forEach\(sid => tracker\.updateSidebarUI\(sid\)\);', '', content)
        content = re.sub(r'if \(pData\.dataset\.isCompleted === \'true\'\)', 'if ("{{ progress.is_completed }}" === "True")', content)

    # For all modules: Ensure progress block exists
    if '{% block academy_progress %}' not in content:
        content = content.replace('{% block academy_content %}', progress_block + '\n{% block academy_content %}')
        
    # Ensure script exists
    if 'window.tracker = new AcademyTracker' not in content:
        # replace the last {% endblock %}
        parts = content.rsplit('{% endblock %}', 1)
        if len(parts) == 2:
            content = parts[0] + script_block + '\n{% endblock %}'

    with open(fname, 'w') as f:
        f.write(content)

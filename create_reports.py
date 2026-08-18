import re

with open('frontend/candidates.html', 'r') as f:
    content = f.read()

# Fix Title
content = content.replace('<title>Candidates - InterviewAI</title>', '<title>Report - InterviewAI</title>')

# Fix Sidebar Tabs
content = content.replace('href="candidates.html" data-nav="Candidates"', 'href="candidates.html" data-nav="Candidates"')
content = re.sub(
    r'<!-- Active Tab -->\s*<a class="flex items-center gap-md p-sm bg-secondary-container text-on-secondary-container font-semibold rounded-lg opacity-80 scale-\[0\.99\] transition-all duration-200" href="candidates.html" data-nav="Candidates">',
    r'<!-- Inactive Tab -->\n<a class="flex items-center gap-md p-sm text-on-surface-variant hover:bg-surface-container-high transition-colors duration-200 rounded-lg" href="candidates.html" data-nav="Candidates">',
    content
)
content = re.sub(
    r'<a class="flex items-center gap-md p-sm text-on-surface-variant hover:bg-surface-container-high transition-colors duration-200 rounded-lg" href="reports.html" data-nav="Reports">',
    r'<!-- Active Tab -->\n<a class="flex items-center gap-md p-sm bg-secondary-container text-on-secondary-container font-semibold rounded-lg opacity-80 scale-[0.99] transition-all duration-200" href="reports.html" data-nav="Reports">',
    content
)

# Replace Main Content
main_content = """<div class="max-w-[1440px] mx-auto flex flex-col gap-xl">
<!-- Page Header -->
<div class="flex justify-between items-end">
    <div>
        <h2 class="font-headline-xl text-headline-xl text-on-surface mb-xs" id="report-title">Loading Report...</h2>
        <p class="font-body-lg text-body-lg text-on-surface-variant" id="report-subtitle">Fetching AI analysis</p>
    </div>
    <button class="bg-primary text-on-primary hover:bg-primary/90 px-4 py-2 rounded-lg font-label-md transition-colors shadow-sm flex items-center gap-sm" onclick="window.history.back()">
        <span class="material-symbols-outlined text-sm">arrow_back</span> Back
    </button>
</div>

<div id="report-content" class="hidden flex flex-col gap-xl">
    <!-- Score Cards -->
    <div class="grid grid-cols-12 gap-gutter">
        <div class="col-span-4 bg-surface border border-surface-variant rounded-xl p-lg shadow-sm">
            <p class="font-label-md text-label-md text-on-surface-variant uppercase tracking-wider mb-xs">Overall Score</p>
            <p id="r-overall" class="font-headline-xl text-headline-xl text-primary">-</p>
        </div>
        <div class="col-span-4 bg-surface border border-surface-variant rounded-xl p-lg shadow-sm">
            <p class="font-label-md text-label-md text-on-surface-variant uppercase tracking-wider mb-xs">Technical Score</p>
            <p id="r-tech" class="font-headline-xl text-headline-xl text-on-surface">-</p>
        </div>
        <div class="col-span-4 bg-surface border border-surface-variant rounded-xl p-lg shadow-sm">
            <p class="font-label-md text-label-md text-on-surface-variant uppercase tracking-wider mb-xs">Communication Score</p>
            <p id="r-comm" class="font-headline-xl text-headline-xl text-on-surface">-</p>
        </div>
    </div>
    
    <!-- Feedback Grid -->
    <div class="grid grid-cols-12 gap-gutter">
        <div class="col-span-8 bg-surface border border-surface-variant rounded-xl p-lg shadow-sm flex flex-col gap-md">
            <h3 class="font-headline-md text-headline-md text-on-surface font-bold border-b border-surface-variant pb-2">AI Summary</h3>
            <p id="r-summary" class="font-body-md text-body-md text-on-surface-variant leading-relaxed"></p>
            
            <h3 class="font-headline-md text-headline-md text-on-surface font-bold border-b border-surface-variant pb-2 mt-4">Hiring Recommendation</h3>
            <p id="r-recommendation" class="font-body-md text-body-md text-on-surface-variant leading-relaxed"></p>
        </div>
        <div class="col-span-4 flex flex-col gap-lg">
            <div class="bg-surface border border-surface-variant rounded-xl p-lg shadow-sm">
                <h3 class="font-headline-md text-headline-md text-primary font-bold mb-4 flex items-center gap-2"><span class="material-symbols-outlined">thumb_up</span> Strengths</h3>
                <ul id="r-strengths" class="list-disc pl-5 font-body-md text-body-md text-on-surface-variant space-y-2"></ul>
            </div>
            <div class="bg-surface border border-surface-variant rounded-xl p-lg shadow-sm">
                <h3 class="font-headline-md text-headline-md text-error font-bold mb-4 flex items-center gap-2"><span class="material-symbols-outlined">trending_down</span> Weaknesses</h3>
                <ul id="r-weaknesses" class="list-disc pl-5 font-body-md text-body-md text-on-surface-variant space-y-2"></ul>
            </div>
        </div>
    </div>
</div>
<div id="report-error" class="hidden text-error font-body-md bg-error-container p-4 rounded-lg border border-error"></div>
</div>"""
content = re.sub(r'<div class="max-w-\[1440px\].*?</div>\s*</div>\s*</div>\s*</div>', main_content, content, flags=re.DOTALL)

# Fix JS
js_logic = """
    <script src="js/auth.js"></script>
    <script>
    Auth.requireAuth();

    async function loadReport() {
        const urlParams = new URLSearchParams(window.location.search);
        const interviewId = urlParams.get('id');
        
        if (!interviewId) {
            document.getElementById('report-title').innerText = "No Interview Selected";
            document.getElementById('report-subtitle').innerText = "Please select an interview from the Candidates page.";
            return;
        }

        try {
            const res = await Auth.fetchAuth(`http://localhost:8080/api/v1/interviews/${interviewId}/report`);
            if(res.ok) {
                const report = await res.json();
                
                document.getElementById('report-title').innerText = "Interview Report";
                document.getElementById('report-subtitle').innerText = `Completed on ${new Date(report.created_at).toLocaleDateString()}`;
                
                document.getElementById('r-overall').innerText = report.overall_score.toFixed(1);
                document.getElementById('r-tech').innerText = report.technical_score.toFixed(1);
                document.getElementById('r-comm').innerText = report.communication_score.toFixed(1);
                
                document.getElementById('r-summary').innerText = report.summary;
                document.getElementById('r-recommendation').innerText = report.hiring_recommendation;
                
                const strengthsList = document.getElementById('r-strengths');
                report.strengths.forEach(s => {
                    const li = document.createElement('li'); li.innerText = s; strengthsList.appendChild(li);
                });
                
                const weaknessesList = document.getElementById('r-weaknesses');
                report.weaknesses.forEach(w => {
                    const li = document.createElement('li'); li.innerText = w; weaknessesList.appendChild(li);
                });
                
                document.getElementById('report-content').classList.remove('hidden');
            } else {
                const err = await res.json();
                document.getElementById('report-title').innerText = "Report Not Available";
                document.getElementById('report-error').innerText = err.detail || 'Could not load report.';
                document.getElementById('report-error').classList.remove('hidden');
            }
        } catch (e) {
            document.getElementById('report-title').innerText = "Error Loading Report";
            document.getElementById('report-error').innerText = "Network error while fetching report.";
            document.getElementById('report-error').classList.remove('hidden');
        }
    }
    
    function setupInteractivity() {
        document.getElementById('btn-notifications').addEventListener('click', () => alert('You have no new notifications.'));
        document.getElementById('btn-help').addEventListener('click', () => alert('Opening Help Center...'));
        document.getElementById('btn-profile').addEventListener('click', () => Auth.logout());

        document.querySelectorAll('#sidebar-nav a, #sidebar-footer a').forEach(el => {
            el.addEventListener('click', (e) => {
                const nav = e.currentTarget.getAttribute('data-nav');
                if(nav === 'Settings') {
                    e.preventDefault();
                    Auth.logout();
                } else if(nav !== 'Candidates' && nav !== 'Jobs' && nav !== 'Interviews' && nav !== 'Reports') {
                    e.preventDefault();
                    alert('Navigating to ' + nav + ' module');
                }
            });
        });
    }

    document.addEventListener("DOMContentLoaded", () => {
        loadReport();
        setupInteractivity();
    });
    </script>
"""
content = re.sub(r'<script src="js/auth.js"></script>.*?</script>', js_logic, content, flags=re.DOTALL)
# Also remove modal HTML
content = re.sub(r'<!-- Upload Resume Modal -->.*?</div>\s*</div>\s*</div>\s*</div>', '', content, flags=re.DOTALL)

with open('frontend/reports.html', 'w') as f:
    f.write(content)
print("reports.html written")

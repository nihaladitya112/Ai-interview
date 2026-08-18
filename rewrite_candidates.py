import re

with open('frontend/candidates.html', 'r') as f:
    content = f.read()

# Fix Title
content = content.replace('<title>Jobs - InterviewAI</title>', '<title>Candidates - InterviewAI</title>')

# Fix Sidebar Tabs
content = content.replace('href="code.html" data-nav="Candidates"', 'href="candidates.html" data-nav="Candidates"')
content = re.sub(
    r'<!-- Inactive Tab -->\s*<a class="flex items-center gap-md p-sm text-on-surface-variant hover:bg-surface-container-high transition-colors duration-200 rounded-lg" href="candidates.html" data-nav="Candidates">',
    r'<!-- Active Tab -->\n<a class="flex items-center gap-md p-sm bg-secondary-container text-on-secondary-container font-semibold rounded-lg opacity-80 scale-[0.99] transition-all duration-200" href="candidates.html" data-nav="Candidates">',
    content
)
content = re.sub(
    r'<!-- Active Tab -->\s*<a class="flex items-center gap-md p-sm bg-secondary-container text-on-secondary-container font-semibold rounded-lg opacity-80 scale-\[0\.99\] transition-all duration-200" href="jobs\.html" data-nav="Jobs">',
    r'<!-- Inactive Tab -->\n<a class="flex items-center gap-md p-sm text-on-surface-variant hover:bg-surface-container-high transition-colors duration-200 rounded-lg" href="jobs.html" data-nav="Jobs">',
    content
)

# Fix Header & Button
content = content.replace('Job Requisitions', 'Candidate Profiles')
content = content.replace('Manage and view open roles across the organization.', 'Manage candidate resumes and view AI match scores.')
content = content.replace('id="btn-add-job"', 'id="btn-upload-resume"')
content = content.replace('Add New Job', 'Upload Resume')
content = content.replace('add', 'upload_file')

# Fix Modal
modal_html = """<!-- Upload Resume Modal -->
<div id="upload-resume-modal" class="modal fixed inset-0 z-50 bg-black/50 items-center justify-center backdrop-blur-sm">
    <div class="bg-surface w-full max-w-lg rounded-2xl p-xl shadow-xl flex flex-col gap-lg border border-outline-variant">
        <div class="flex justify-between items-center">
            <h2 class="font-headline-md text-headline-md font-bold">Upload Resume</h2>
            <button id="btn-close-resume-modal" class="text-on-surface-variant hover:bg-surface-container-high rounded-full w-8 h-8 flex items-center justify-center transition-colors">
                <span class="material-symbols-outlined">close</span>
            </button>
        </div>
        <form id="upload-resume-form" class="flex flex-col gap-4">
            <div>
                <label class="block font-label-md mb-1">Resume File (PDF/TXT)</label>
                <input type="file" id="resume-file" required accept=".txt,.pdf" class="w-full rounded-lg border-outline-variant shadow-sm focus:border-primary focus:ring-primary px-3 py-2 text-sm">
            </div>
            <div class="flex justify-end gap-3 mt-4">
                <button type="button" id="btn-cancel-resume" class="px-4 py-2 text-sm font-semibold rounded-lg hover:bg-surface-container-high transition-colors">Cancel</button>
                <button type="submit" class="px-4 py-2 text-sm font-semibold bg-primary text-on-primary rounded-lg shadow-sm hover:opacity-90 flex items-center gap-2">
                    <span>Upload</span>
                    <span class="material-symbols-outlined text-[14px] hidden" id="resume-loading">sync</span>
                </button>
            </div>
        </form>
    </div>
</div>"""
content = re.sub(r'<!-- Add Job Modal -->.*?</div>\s*</div>', modal_html, content, flags=re.DOTALL)

# Fix Table Headers
table_headers = """<tr>
<th class="p-4 font-semibold border-b border-surface-variant">Candidate</th>
<th class="p-4 font-semibold border-b border-surface-variant">Applied Role</th>
<th class="p-4 font-semibold border-b border-surface-variant">Match Score</th>
<th class="p-4 font-semibold border-b border-surface-variant">Status</th>
<th class="p-4 font-semibold border-b border-surface-variant text-right">Actions</th>
</tr>"""
content = re.sub(r'<thead.*?>.*?</thead>', f'<thead class="bg-surface-container-low font-label-md text-label-md text-on-surface-variant uppercase tracking-wider">\n{table_headers}\n</thead>', content, flags=re.DOTALL)

# Fix tbody ID
content = content.replace('id="jobs-list"', 'id="candidates-list"')

# Fix JS
js_logic = """
    <script src="js/auth.js"></script>
    <script>
    Auth.requireAuth();

    let globalCandidates = [];
    
    function renderCandidates(candidates) {
        const list = document.getElementById('candidates-list');
        list.innerHTML = '';
        candidates.forEach(cand => {
            list.innerHTML += `
<tr class="border-b border-surface-variant hover:bg-surface-container-lowest transition-colors duration-150 cursor-pointer" onclick="alert('Viewing profile for ${cand.name}')">
<td class="p-4 flex items-center gap-md">
    <div class="w-10 h-10 rounded bg-primary-container text-on-primary-container flex items-center justify-center font-bold">${cand.initials || 'C'}</div>
    <div>
        <p class="font-semibold text-on-surface">${cand.name}</p>
        <p class="text-on-surface-variant text-xs">${cand.email}</p>
    </div>
</td>
<td class="p-4 text-on-surface-variant">${cand.role}</td>
<td class="p-4">
    <span class="font-bold text-primary">${cand.match_score}</span> / 100
</td>
<td class="p-4">
    <span class="inline-flex items-center px-2.5 py-0.5 rounded-full font-label-md text-[10px] bg-secondary-container text-on-secondary-container">
        ${cand.status}
    </span>
</td>
<td class="p-4 text-right">
    <button class="text-primary hover:text-primary-fixed-dim transition-colors font-label-md" onclick="event.stopPropagation(); window.location.href='interview.html'">Interview</button>
</td>
</tr>`;
        });
    }

    async function loadCandidates() {
        try {
            const res = await Auth.fetchAuth('http://localhost:8080/api/v1/dashboard/summary');
            if(res.ok) {
                const data = await res.json();
                globalCandidates = data.recent_candidates;
                renderCandidates(globalCandidates);
            }
        } catch (e) {
            console.error('Error loading candidates:', e);
        }
    }
    
    function setupInteractivity() {
        document.getElementById('search-input').addEventListener('input', (e) => {
            const query = e.target.value.toLowerCase();
            const filtered = globalCandidates.filter(c => 
                c.name.toLowerCase().includes(query) || 
                c.role.toLowerCase().includes(query) ||
                c.email.toLowerCase().includes(query)
            );
            renderCandidates(filtered);
        });

        document.getElementById('btn-notifications').addEventListener('click', () => alert('You have no new notifications.'));
        document.getElementById('btn-help').addEventListener('click', () => alert('Opening Help Center...'));
        document.getElementById('btn-profile').addEventListener('click', () => Auth.logout());

        document.querySelectorAll('#sidebar-nav a, #sidebar-footer a').forEach(el => {
            el.addEventListener('click', (e) => {
                const nav = e.currentTarget.getAttribute('data-nav');
                if(nav === 'Reports') {
                    e.preventDefault();
                    window.location.href = 'reports.html';
                } else if(nav === 'Settings') {
                    e.preventDefault();
                    Auth.logout();
                }
            });
        });

        const modal = document.getElementById('upload-resume-modal');
        const closeModal = () => modal.classList.remove('active');
        
        document.getElementById('btn-upload-resume').addEventListener('click', () => modal.classList.add('active'));
        document.getElementById('btn-close-resume-modal').addEventListener('click', closeModal);
        document.getElementById('btn-cancel-resume').addEventListener('click', closeModal);

        document.getElementById('upload-resume-form').addEventListener('submit', async (e) => {
            e.preventDefault();
            const loading = document.getElementById('resume-loading');
            loading.classList.remove('hidden');
            loading.classList.add('animate-spin');

            const fileInput = document.getElementById('resume-file');
            if (fileInput.files.length === 0) return;
            
            const formData = new FormData();
            formData.append("file", fileInput.files[0]);

            try {
                const res = await Auth.fetchAuth('http://localhost:8080/api/v1/resumes', {
                    method: 'POST',
                    body: formData // Note: Content-Type is omitted so browser sets it with boundary
                });
                if(res.ok) {
                    alert("Resume uploaded! It will be parsed and matched in the background.");
                    closeModal();
                    loadCandidates();
                    e.target.reset();
                } else {
                    const err = await res.json();
                    alert(err.detail || 'Failed to upload resume');
                }
            } catch (err) {
                alert('Error uploading resume');
            } finally {
                loading.classList.add('hidden');
                loading.classList.remove('animate-spin');
            }
        });
    }

    document.addEventListener("DOMContentLoaded", () => {
        loadCandidates();
        setupInteractivity();
    });
    </script>
"""
content = re.sub(r'<script src="js/auth.js"></script>.*?</script>', js_logic, content, flags=re.DOTALL)

with open('frontend/candidates.html', 'w') as f:
    f.write(content)
print("candidates.html written")

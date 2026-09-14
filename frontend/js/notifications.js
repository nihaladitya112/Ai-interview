// Notifications logic
document.addEventListener('DOMContentLoaded', () => {
    const btnNotifications = document.getElementById('btn-notifications');
    if (!btnNotifications) return;

    // Create dropdown container
    const dropdown = document.createElement('div');
    dropdown.id = 'notifications-dropdown';
    dropdown.className = 'absolute top-16 right-4 w-80 max-h-96 bg-surface-container-lowest border border-outline-variant shadow-lg rounded-xl overflow-y-auto hidden z-50 p-2 flex flex-col gap-2';
    document.body.appendChild(dropdown);

    // Create badge
    const badge = document.createElement('span');
    badge.className = 'absolute top-0 right-0 w-2.5 h-2.5 bg-error rounded-full hidden border-2 border-surface';
    btnNotifications.style.position = 'relative';
    btnNotifications.appendChild(badge);

    let unreadCount = 0;

    async function loadNotifications() {
        try {
            const res = await Auth.fetchAuth('/api/v1/notifications');
            if (res.ok) {
                const data = await res.json();
                renderNotifications(data.notifications);
            }
        } catch (e) {
            console.error('Failed to load notifications', e);
        }
    }

    function renderNotifications(notifications) {
        dropdown.innerHTML = '';
        unreadCount = notifications.length;

        if (unreadCount > 0) {
            badge.classList.remove('hidden');
            const header = document.createElement('div');
            header.className = 'flex justify-between items-center px-2 py-1 border-b border-outline-variant mb-1';
            header.innerHTML = `
                <span class="font-label-md text-on-surface">Notifications</span>
                <button id="btn-read-all" class="text-xs text-primary hover:underline font-label-sm">Mark all as read</button>
            `;
            dropdown.appendChild(header);

            document.getElementById('btn-read-all').addEventListener('click', markAllAsRead);

            notifications.forEach(n => {
                const item = document.createElement('div');
                item.className = 'p-3 rounded-lg bg-surface-container hover:bg-surface-container-high transition-colors text-sm text-on-surface flex justify-between items-start gap-2';
                
                const icon = n.type === 'SUCCESS' ? 'check_circle' : 'info';
                const iconColor = n.type === 'SUCCESS' ? 'text-primary' : 'text-secondary';
                
                item.innerHTML = `
                    <div class="flex items-start gap-2">
                        <span class="material-symbols-outlined ${iconColor} text-[18px]">${icon}</span>
                        <div>
                            <p>${n.message}</p>
                            <p class="text-xs text-on-surface-variant mt-1">${new Date(n.created_at).toLocaleString()}</p>
                        </div>
                    </div>
                    <button class="btn-dismiss text-on-surface-variant hover:text-error" data-id="${n.id}">
                        <span class="material-symbols-outlined text-[16px]">close</span>
                    </button>
                `;
                dropdown.appendChild(item);
            });

            document.querySelectorAll('.btn-dismiss').forEach(btn => {
                btn.addEventListener('click', (e) => {
                    e.stopPropagation();
                    markAsRead(e.currentTarget.dataset.id);
                });
            });
        } else {
            badge.classList.add('hidden');
            dropdown.innerHTML = '<div class="p-4 text-center text-on-surface-variant text-sm">No new notifications</div>';
        }
    }

    async function markAsRead(id) {
        try {
            const res = await Auth.fetchAuth(`/api/v1/notifications/${id}/read`, { method: 'POST' });
            if (res.ok) {
                loadNotifications();
            }
        } catch (e) {
            console.error('Failed to dismiss notification', e);
        }
    }

    async function markAllAsRead() {
        try {
            const res = await Auth.fetchAuth(`/api/v1/notifications/read-all`, { method: 'POST' });
            if (res.ok) {
                loadNotifications();
            }
        } catch (e) {
            console.error('Failed to dismiss all', e);
        }
    }

    // Toggle dropdown
    btnNotifications.addEventListener('click', (e) => {
        e.stopPropagation();
        dropdown.classList.toggle('hidden');
    });

    // Close when clicking outside
    document.addEventListener('click', (e) => {
        if (!dropdown.contains(e.target) && !btnNotifications.contains(e.target)) {
            dropdown.classList.add('hidden');
        }
    });

    // Replace the default dummy alert logic
    const oldBtn = btnNotifications.cloneNode(true);
    btnNotifications.parentNode.replaceChild(oldBtn, btnNotifications);
    
    // Re-attach our logic to the new button
    const newBtn = document.getElementById('btn-notifications');
    newBtn.style.position = 'relative';
    newBtn.appendChild(badge);
    
    newBtn.addEventListener('click', (e) => {
        e.stopPropagation();
        dropdown.classList.toggle('hidden');
    });

    // Initial load
    loadNotifications();

    // Poll every 30 seconds
    setInterval(loadNotifications, 30000);
});

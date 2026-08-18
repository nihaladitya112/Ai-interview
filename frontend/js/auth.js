const API_BASE = "http://localhost:8080/api/v1";

const Auth = {
    getToken() {
        return localStorage.getItem('access_token');
    },
    
    setToken(token) {
        localStorage.setItem('access_token', token);
    },
    
    logout() {
        localStorage.removeItem('access_token');
        window.location.href = 'login.html';
    },

    isAuthenticated() {
        return !!this.getToken();
    },

    requireAuth() {
        if (!this.isAuthenticated()) {
            window.location.href = 'login.html';
        }
    },

    async fetchAuth(url, options = {}) {
        this.requireAuth();
        const headers = {
            ...options.headers,
            'Authorization': `Bearer ${this.getToken()}`
        };
        
        const response = await fetch(url, { ...options, headers });
        if (response.status === 401) {
            this.logout();
        }
        return response;
    },

    async initProfile() {
        if (!this.isAuthenticated()) return;
        
        try {
            const res = await this.fetchAuth(`${API_BASE}/users/me`);
            if (res.ok) {
                const user = await res.json();
                const nameDisplay = document.getElementById('sidebar-user-name');
                const roleDisplay = document.getElementById('sidebar-user-role');
                const avatarDisplay = document.getElementById('sidebar-user-avatar');

                let displayName = "Admin User";
                if (user.first_name || user.last_name) {
                    displayName = `${user.first_name || ''} ${user.last_name || ''}`.trim();
                } else if (user.email) {
                    displayName = user.email.split('@')[0];
                }

                if (nameDisplay) nameDisplay.innerText = displayName;
                if (roleDisplay) roleDisplay.innerText = user.email; // Use email as secondary text
                if (avatarDisplay) avatarDisplay.innerText = displayName.charAt(0).toUpperCase();

                const btnProfile = document.getElementById('btn-profile');
                if (btnProfile) {
                    btnProfile.innerHTML = `<div class="w-full h-full bg-primary flex items-center justify-center text-on-primary font-bold text-sm">${displayName.charAt(0).toUpperCase()}</div>`;
                }
            }
        } catch (e) {
            console.error("Failed to load profile", e);
        }
    }
};

document.addEventListener("DOMContentLoaded", () => {
    if (window.location.pathname.indexOf('login.html') === -1) {
        Auth.initProfile();
    }
});

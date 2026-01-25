const API_BASE = "/api";

const auth = {
    login: async (username, password) => {
        // Check for Serverless Mode (ENV is defined in index.html, assumes this runs in browser context)
        const isGas = (typeof ENV !== 'undefined' && ENV.API_MODE === 'gas');
        
        if (isGas) {
            // GAS Login
            // We use GET for login as per google_script.gs handleLogin
            // For better security in real app, use POST, but here we follow the implemented script.
            const url = `${ENV.GAS_API_URL}?action=login&username=${encodeURIComponent(username)}&password=${encodeURIComponent(password)}`;
            
            const response = await fetch(url);
            const data = await response.json();
            
            if (data.status === "error") {
                throw new Error(data.message || 'Login failed');
            }
            
            localStorage.setItem('token', data.access_token);
            localStorage.setItem('user', JSON.stringify(data.user)); // Store minimal user info
            return data;
            
        } else {
            // Original Python Login
            const formData = new FormData();
            formData.append('username', username);
            formData.append('password', password);
    
            const response = await fetch(`${API_BASE}/token`, { // Fixed endpoint from /login to /token based on main.py
                method: 'POST',
                body: formData
            });
    
            if (!response.ok) {
                const errorData = await response.json();
                throw new Error(errorData.detail || 'Login failed');
            }
    
            const data = await response.json();
            localStorage.setItem('token', data.access_token);
            return data;
        }
    },

    logout: () => {
        localStorage.removeItem('token');
        localStorage.removeItem('user');
        window.location.href = '/login.html';
    },

    getToken: () => {
        return localStorage.getItem('token');
    },

    getUser: () => {
         const u = localStorage.getItem('user');
         return u ? JSON.parse(u) : null;
    },

    checkAuth: () => {
        const token = auth.getToken();
        if (!token) {
            return false;
        }
        return true;
    },

    fetchProtected: async (url, options = {}) => {
        // In GAS mode, usually no specialized fetch needed unless we secure GAS API with token?
        // Current GAS implementation is public (Anyone can access). Token is just client-side state.
        // So we just pass through.
        
        const token = auth.getToken();
        if (!token) {
            window.location.href = '/login.html';
            return;
        }

        const headers = options.headers || {};
        headers['Authorization'] = `Bearer ${token}`;

        const response = await fetch(url, {
            ...options,
            headers: headers
        });

        if (response.status === 401) {
            auth.logout();
            return;
        }

        return response;
    }
};

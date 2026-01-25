const API_BASE = "/api";

const auth = {
    login: async (username, password) => {
        const formData = new FormData();
        formData.append('username', username);
        formData.append('password', password);

        const response = await fetch(`${API_BASE}/login`, {
            method: 'POST',
            body: formData
        });

        if (!response.ok) {
            const errorData = await response.json();
            throw new Error(errorData.detail || 'Login failed');
        }

        const data = await response.json();
        localStorage.setItem('token', data.access_token);
        // Decode token to get role/user info if needed, or fetch /api/me
        // For simplicity, we fetch /api/me immediately after or on dashboard load
        return data;
    },

    logout: () => {
        localStorage.removeItem('token');
        window.location.href = '/login.html';
    },

    getToken: () => {
        return localStorage.getItem('token');
    },

    checkAuth: () => {
        const token = auth.getToken();
        if (!token) {
            return false;
        }
        // Basic expiry check could be done here if we decoded JWT
        return true;
    },

    fetchProtected: async (url, options = {}) => {
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

const API_URL = ''; // Relative path since we serve from same origin

const auth = {
    async login(username, password) {
        const formData = new URLSearchParams();
        formData.append('username', username);
        formData.append('password', password);

        try {
            const response = await fetch(`${API_URL}/token`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/x-www-form-urlencoded',
                },
                body: formData,
            });

            if (!response.ok) {
                const error = await response.json();
                throw new Error(error.detail || 'Login failed');
            }

            const data = await response.json();
            localStorage.setItem('token', data.access_token);
            
            // Decode token to get user info (basic decode without verification)
            const payload = JSON.parse(atob(data.access_token.split('.')[1]));
            localStorage.setItem('user', JSON.stringify({
                username: payload.sub,
                role: payload.role
            }));

            return data;
        } catch (error) {
            throw error;
        }
    },

    logout() {
        localStorage.removeItem('token');
        localStorage.removeItem('user');
        window.location.href = '/login.html';
    },

    getToken() {
        return localStorage.getItem('token');
    },

    getUser() {
        const userStr = localStorage.getItem('user');
        return userStr ? JSON.parse(userStr) : null;
    },

    checkAuth() {
        const token = this.getToken();
        if (!token) {
            window.location.href = '/login.html';
            return false;
        }
        return true;
    },

    async fetchProtected(url, options = {}) {
        const token = this.getToken();
        const headers = {
            ...options.headers,
            'Authorization': `Bearer ${token}`,
        };

        const response = await fetch(`${API_URL}${url}`, {
            ...options,
            headers,
        });

        if (response.status === 401) {
            this.logout();
            throw new Error('Unauthorized');
        }

        return response;
    }
};

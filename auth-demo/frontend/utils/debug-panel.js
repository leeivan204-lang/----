class DebugPanel {
    constructor() {
        this.render();
        this.loadConfig();
    }

    async loadConfig() {
        try {
            const response = await fetch('/api/debug/config');
            if (response.ok) {
                const config = await response.json();
                this.updateUI(config);
            }
        } catch (e) {
            console.error('Failed to load debug config', e);
        }
    }

    updateUI(config) {
        if (!config) return;

        // Update Login Error dropdown
        const loginSelect = document.getElementById('debugLoginError');
        if (loginSelect) {
            loginSelect.value = config.force_login_error || 'none';
        }

        // Update API Error checkboxes
        const tokenExpireCheck = document.getElementById('debugTokenExpire');
        if (tokenExpireCheck) {
            tokenExpireCheck.checked = config.force_token_expire;
        }

        const serverErrorCheck = document.getElementById('debugServerError');
        if (serverErrorCheck) {
            serverErrorCheck.checked = config.force_server_error;
        }
    }

    async updateConfig(key, value) {
        const payload = {};

        if (key === 'force_login_error') {
            payload.force_login_error = value === 'none' ? null : value;
        } else {
            payload[key] = value;
        }

        try {
            await fetch('/api/debug/config', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(payload)
            });
        } catch (e) {
            console.error('Failed to update debug config', e);
        }
    }

    render() {
        const container = document.createElement('div');
        container.className = 'debug-panel';
        container.innerHTML = `
            <div class="debug-header" onclick="this.parentElement.classList.toggle('collapsed')">
                <span>🛠 Dev Panel</span>
                <span class="toggle-icon">_</span>
            </div>
            <div class="debug-content">
                <div class="debug-section">
                    <label>Next Login Result:</label>
                    <select id="debugLoginError" onchange="window.debugPanel.updateConfig('force_login_error', this.value)">
                        <option value="none">Success (Normal)</option>
                        <option value="invalid_password">Invalid Password (401)</option>
                        <option value="user_not_found">User Not Found (404)</option>
                        <option value="server_error">Server Error (500)</option>
                    </select>
                </div>

                <div class="debug-section">
                    <label>Next API Call:</label>
                    <div class="checkbox-group">
                        <input type="checkbox" id="debugTokenExpire" onchange="window.debugPanel.updateConfig('force_token_expire', this.checked)">
                        <label for="debugTokenExpire">Force Token Expired</label>
                    </div>
                    <div class="checkbox-group">
                        <input type="checkbox" id="debugServerError" onchange="window.debugPanel.updateConfig('force_server_error', this.checked)">
                        <label for="debugServerError">Force Server Error</label>
                    </div>
                </div>

                <div class="debug-section">
                    <button class="danger-btn" onclick="auth.logout()">Clear Token & Logout</button>
                </div>
            </div>
        `;
        document.body.appendChild(container);
    }
}

// Initialize on load
window.addEventListener('DOMContentLoaded', () => {
    window.debugPanel = new DebugPanel();
});

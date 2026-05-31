/**
 * app.js - Renderer logic for the login screen
 */

document.addEventListener('DOMContentLoaded', async () => {
    const statusDiv = document.getElementById('backend-status');
    const connectBtn = document.getElementById('connect-btn');
    const sessionInput = document.getElementById('session-code');
    const errorMsg = document.getElementById('error-msg');

    // Initial backend check
    try {
        const result = await window.coadex.checkBackend();
        if (result.reachable) {
            statusDiv.innerHTML = '<span class="status-ok">● Backend Reachable</span>';
        } else {
            statusDiv.innerHTML = '<span class="status-err">● Backend Offline</span>';
        }
    } catch (e) {
        statusDiv.innerHTML = '<span class="status-err">● Backend Connection Error</span>';
    }

    // Connect button click
    connectBtn.addEventListener('click', async () => {
        const code = sessionInput.value.trim();
        if (!code) {
            alert('Please enter a session code');
            return;
        }

        connectBtn.disabled = true;
        connectBtn.innerText = 'Establishing Tunnel...';
        errorMsg.style.display = 'none';

        try {
            const result = await window.coadex.startSession(code);
            if (result.success) {
                // Redirect to status page with params
                const iface = encodeURIComponent((result.wg && result.wg.interface) ? result.wg.interface : "");
                window.location.href = `status.html?id=${result.session_id}&ip=${result.client_ip}&iface=${iface}`;
            } else {
                throw new Error(result.error || 'Unknown error starting session');
            }
        } catch (e) {
            errorMsg.innerText = e.message;
            errorMsg.style.display = 'block';
            connectBtn.disabled = false;
            connectBtn.innerText = 'Connect & Start Interview';
        }
    });
});

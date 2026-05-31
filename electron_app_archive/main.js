/**
 * main.js — Coadex Desktop Client - Electron Main Process
 * Manages the BrowserWindow, IPC handlers, and spawns the Python bridge.
 */

const { app, BrowserWindow, ipcMain, dialog } = require('electron');
const path = require('path');
const { spawn } = require('child_process');
const fs = require('fs');

// ─── State ────────────────────────────────────────────────────────────────────
let mainWindow = null;
let activeSessionId = null;
let confPath = null;
let wgInterfaceName = null;
const pythonBridgePath = path.join(__dirname, '..', 'python_bridge');

// ─── Window Setup ────────────────────────────────────────────────────────────
function createWindow() {
    mainWindow = new BrowserWindow({
        width: 520,
        height: 680,
        resizable: false,
        frame: true,
        title: 'Coadex 2.0 — Interview Client',
        icon: path.join(__dirname, 'assets', 'logo.png'),
        webPreferences: {
            preload: path.join(__dirname, 'preload.js'),
            contextIsolation: true,
            nodeIntegration: false
        }
    });

    mainWindow.loadFile(path.join(__dirname, 'renderer', 'index.html'));
    mainWindow.setMenuBarVisibility(false);
}

app.whenReady().then(() => {
    createWindow();
    app.on('activate', () => {
        if (BrowserWindow.getAllWindows().length === 0) createWindow();
    });
});

app.on('window-all-closed', () => {
    if (process.platform !== 'darwin') app.quit();
});

// Ensure tunnel is torn down on quit
app.on('before-quit', () => {
    if (activeSessionId) {
        runPython('session_client.py', ['--end', activeSessionId]);
    }
    if (confPath) {
        runPython('tunnel_manager.py', ['--down', confPath]);
    }
});

// ─── Python Bridge Utility ───────────────────────────────────────────────────
/**
 * Spawn a Python script from python_bridge/ and collect stdout as JSON.
 * Returns a Promise that resolves to the parsed JSON result.
 */
function runPython(script, args = []) {
    return new Promise((resolve, reject) => {
        const python = process.platform === 'win32' ? 'python' : 'python3';
        const scriptPath = path.join(pythonBridgePath, script);
        const proc = spawn(python, [scriptPath, ...args], { env: process.env });

        let stdout = '';
        let stderr = '';

        proc.stdout.on('data', d => stdout += d.toString());
        proc.stderr.on('data', d => stderr += d.toString());

        proc.on('close', code => {
            if (code !== 0) {
                reject(new Error(stderr || `Python exited with code ${code}`));
                return;
            }
            try {
                resolve(JSON.parse(stdout));
            } catch {
                // If output isn't JSON, return raw stdout
                resolve({ raw: stdout.trim() });
            }
        });
    });
}

// ─── IPC Handlers ────────────────────────────────────────────────────────────

/** Check if EC2 backend is reachable */
ipcMain.handle('check-backend', async () => {
    try {
        const result = await runPython('session_client.py', ['--health']);
        return { reachable: result.reachable === true };
    } catch (e) {
        return { reachable: false, error: e.message };
    }
});

/** Start session: call EC2, activate WireGuard tunnel */
ipcMain.handle('start-session', async (_event, candidateId) => {
    try {
        // Step 1: Call EC2 to create session and get WireGuard config
        const session = await runPython('session_client.py', ['--start', candidateId]);
        if (session.error) throw new Error(session.error);

        activeSessionId = session.session_id;

        // Step 2: Write config and activate tunnel
        const os = require('os');
        const confPathTemp = path.join(os.tmpdir(), `optimus-${session.session_id.substring(0, 8)}.conf`);
        fs.writeFileSync(confPathTemp, session.wg_config);

        const tunnelResult = await runPython('tunnel_manager.py', [
            '--up', confPathTemp
        ]);

        if (tunnelResult.error) throw new Error(tunnelResult.error);
        confPath = tunnelResult.conf_path || confPathTemp;
        wgInterfaceName = tunnelResult.interface || null;

        return {
            success: true,
            session_id: activeSessionId,
            client_ip: session.client_ip,
            conf_path: confPath,
            wg: {
                interface: wgInterfaceName,
                latest_handshake: tunnelResult.latest_handshake,
                rx_bytes: tunnelResult.rx_bytes,
                tx_bytes: tunnelResult.tx_bytes
            }
        };
    } catch (e) {
        return { success: false, error: e.message };
    }
});

/** End session: tear down tunnel, notify EC2 */
ipcMain.handle('end-session', async () => {
    const errors = [];

    if (confPath) {
        try {
            await runPython('tunnel_manager.py', ['--down', confPath]);
            confPath = null;
            wgInterfaceName = null;
        } catch (e) {
            errors.push(`Tunnel teardown: ${e.message}`);
        }
    }

    if (activeSessionId) {
        try {
            await runPython('session_client.py', ['--end', activeSessionId]);
            activeSessionId = null;
        } catch (e) {
            errors.push(`Session end: ${e.message}`);
        }
    }

    return { success: errors.length === 0, errors };
});

/** Check tunnel status */
ipcMain.handle('tunnel-status', async () => {
    try {
        if (!wgInterfaceName) return { active: false };
        const result = await runPython('tunnel_manager.py', ['--validate', wgInterfaceName]);
        return { active: result.connected === true, details: result };
    } catch {
        return { active: false };
    }
});

/**
 * preload.js — Secure IPC bridge between Electron main and renderer.
 * Exposes only the specific functions the UI needs via contextBridge.
 */

const { contextBridge, ipcRenderer } = require('electron');

contextBridge.exposeInMainWorld('coadex', {
    checkBackend: () => ipcRenderer.invoke('check-backend'),
    startSession: (candidateId) => ipcRenderer.invoke('start-session', candidateId),
    endSession: () => ipcRenderer.invoke('end-session'),
    tunnelStatus: () => ipcRenderer.invoke('tunnel-status'),
});

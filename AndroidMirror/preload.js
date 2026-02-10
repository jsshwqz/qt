/**
 * AndroidMirror - 预加载脚本
 * 安全地暴露 API 给渲染进程
 */

const { contextBridge, ipcRenderer } = require('electron');

// 暴露安全的 API 给渲染进程
contextBridge.exposeInMainWorld('androidMirror', {
    // 设备管理
    getDevices: () => ipcRenderer.invoke('get-devices'),
    getNetworkInfo: () => ipcRenderer.invoke('get-network-info'),
    scanWireless: () => ipcRenderer.invoke('scan-wireless'),
    connectWireless: (address) => ipcRenderer.invoke('connect-wireless', address),
    disconnectWireless: (address) => ipcRenderer.invoke('disconnect-wireless', address),

    // 投屏控制
    startMirror: (serial, options) => ipcRenderer.invoke('start-mirror', serial, options),
    stopMirror: () => ipcRenderer.invoke('stop-mirror'),

    // 输入控制
    sendKey: (serial, keycode) => ipcRenderer.invoke('send-key', serial, keycode),
    sendKeyChar: (serial, char, keyCode, modifiers) => ipcRenderer.invoke('send-key-char', serial, char, keyCode, modifiers),
    sendTouch: (serial, action, x, y) => ipcRenderer.invoke('send-touch', serial, action, x, y),
    sendSwipe: (serial, x1, y1, x2, y2, duration) => ipcRenderer.invoke('send-swipe', serial, x1, y1, x2, y2, duration),
    sendText: (serial, text) => ipcRenderer.invoke('send-text', serial, text),

    // 文件操作
    installApk: (serial, apkPath) => ipcRenderer.invoke('install-apk', serial, apkPath),
    pushFile: (serial, localPath) => ipcRenderer.invoke('push-file', serial, localPath),

    // 快捷操作
    expandNotifications: (serial) => ipcRenderer.invoke('expand-notifications', serial),
    expandSettings: (serial) => ipcRenderer.invoke('expand-settings', serial),

    // 剪贴板
    getClipboard: () => ipcRenderer.invoke('get-clipboard'),
    setClipboard: (text) => ipcRenderer.invoke('set-clipboard', text),
    syncClipboardToDevice: (serial) => ipcRenderer.invoke('sync-clipboard-to-device', serial),

    // 窗口控制
    toggleFullscreen: () => ipcRenderer.invoke('toggle-fullscreen'),

    // 事件监听
    onRefreshDevices: (callback) => ipcRenderer.on('refresh-devices', callback),
    onInstallProgress: (callback) => ipcRenderer.on('install-progress', (event, data) => callback(data)),
    onTransferProgress: (callback) => ipcRenderer.on('transfer-progress', (event, data) => callback(data)),

    // 常用按键码
    KeyCodes: {
        HOME: 3,
        BACK: 4,
        APP_SWITCH: 187,
        MENU: 82,
        POWER: 26,
        VOLUME_UP: 24,
        VOLUME_DOWN: 25,
        ENTER: 66,
        DEL: 67
    }
});

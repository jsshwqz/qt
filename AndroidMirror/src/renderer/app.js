/**
 * AndroidMirror - 前端应用逻辑
 */

// 检查 API 是否可用
if (!window.androidMirror) {
    console.error('androidMirror API 未找到，请确保在 Electron 环境中运行');
    document.body.innerHTML = '<div style="padding:40px;text-align:center;color:#e94560;font-family:sans-serif;"><h2>⚠️ 应用加载失败</h2><p>请通过 Electron 启动应用</p></div>';
    throw new Error('androidMirror API not available');
}

const mirrorApi = window.androidMirror;
const KeyCodes = mirrorApi.KeyCodes || {};

// 状态管理
const state = {
    devices: [],
    currentDevice: null,
    isConnected: false,
    isMirroring: false,
    videoSocket: null,
    controlSocket: null
};

// DOM 元素
const elements = {
    deviceList: document.getElementById('device-list'),
    wirelessList: document.getElementById('wireless-list'),
    networkInfo: document.getElementById('network-info'),
    btnRefresh: document.getElementById('btn-refresh'),
    btnScan: document.getElementById('btn-scan'),
    btnHelp: document.getElementById('btn-help'),
    btnConnect: document.getElementById('btn-connect'),
    inputIp: document.getElementById('input-ip'),
    
    welcomeView: document.getElementById('welcome-view'),
    mirrorView: document.getElementById('mirror-view'),
    videoContainer: document.getElementById('video-container'),
    videoPlayer: document.getElementById('video-player'),
    // videoCanvas: document.getElementById('video-canvas'), // 已弃用
    videoOverlay: document.getElementById('video-overlay'),
    deviceInfo: document.getElementById('device-info'),
    fpsInfo: document.getElementById('fps-info'),
    btnDisconnect: document.getElementById('btn-disconnect'),
    
    // 快捷操作
    btnHome: document.getElementById('btn-home'),
    btnBack: document.getElementById('btn-back'),
    btnSwitch: document.getElementById('btn-switch'),
    btnMenu: document.getElementById('btn-menu'),
    btnPower: document.getElementById('btn-power'),
    btnVolUp: document.getElementById('btn-vol-up'),
    btnVolDown: document.getElementById('btn-vol-down'),
    btnNotify: document.getElementById('btn-notify'),
    btnSettings: document.getElementById('btn-settings'),
    btnFullscreen: document.getElementById('btn-fullscreen'),
    
    // 剪贴板
    btnPasteToDevice: document.getElementById('btn-paste-to-device'),
    btnTypeText: document.getElementById('btn-type-text'),
    
    // 对话框
    textDialog: document.getElementById('text-dialog'),
    inputText: document.getElementById('input-text'),
    btnCancelText: document.getElementById('btn-cancel-text'),
    btnSendText: document.getElementById('btn-send-text'),
    
    // 帮助对话框
    helpDialog: document.getElementById('help-dialog'),
    btnCloseHelp: document.getElementById('btn-close-help'),
    
    toast: document.getElementById('toast')
};

/**
 * 初始化应用
 */
async function init() {
    setupEventListeners();
    setupDragAndDrop();
    await refreshDevices();
    await loadNetworkInfo();
    
    // 监听来自主进程的事件
    mirrorApi.onRefreshDevices(() => refreshDevices());
    mirrorApi.onInstallProgress(showInstallProgress);
    mirrorApi.onTransferProgress(showTransferProgress);
}

/**
 * 加载网络信息
 */
async function loadNetworkInfo() {
    try {
        const networks = await mirrorApi.getNetworkInfo();
        if (networks.length > 0) {
            const net = networks[0];
            state.networkInfo = net;
            
            // 显示网络信息
            elements.networkInfo.innerHTML = `
                <div class="net-badge">
                    <span class="net-icon">🌐</span>
                    <span class="net-text">${net.name}: ${net.ip}</span>
                </div>
            `;
            elements.inputIp.placeholder = `手动输入或点击扫描`;
            
            // 更新无线列表提示
            elements.wirelessList.innerHTML = `
                <div class="hint">
                    扫描范围: <strong>${net.subnet}.1-254</strong><br>
                    <small>点击 📡 按钮开始搜索</small>
                </div>
            `;
        } else {
            elements.networkInfo.innerHTML = `<div class="net-badge warning">⚠️ 未检测到局域网</div>`;
        }
    } catch (e) {
        console.error('获取网络信息失败:', e);
        elements.networkInfo.innerHTML = `<div class="net-badge warning">⚠️ 网络检测失败</div>`;
    }
}

/**
 * 设置事件监听
 */
function setupEventListeners() {
    // 设备刷新
    elements.btnRefresh.addEventListener('click', refreshDevices);
    
    // 无线扫描
    elements.btnScan.addEventListener('click', scanWirelessDevices);
    
    // 帮助按钮
    elements.btnHelp.addEventListener('click', showHelpDialog);
    elements.btnCloseHelp.addEventListener('click', hideHelpDialog);
    
    // 手动连接
    elements.btnConnect.addEventListener('click', () => {
        const address = elements.inputIp.value.trim();
        if (address) connectWireless(address);
    });
    
    elements.inputIp.addEventListener('keypress', (e) => {
        if (e.key === 'Enter') {
            const address = elements.inputIp.value.trim();
            if (address) connectWireless(address);
        }
    });
    
    // 断开连接
    elements.btnDisconnect.addEventListener('click', disconnect);
    
    // 快捷操作
    elements.btnHome.addEventListener('click', () => sendKey(KeyCodes.HOME));
    elements.btnBack.addEventListener('click', () => sendKey(KeyCodes.BACK));
    elements.btnSwitch.addEventListener('click', () => sendKey(KeyCodes.APP_SWITCH));
    elements.btnMenu.addEventListener('click', () => sendKey(KeyCodes.MENU));
    elements.btnPower.addEventListener('click', () => sendKey(KeyCodes.POWER));
    elements.btnVolUp.addEventListener('click', () => sendKey(KeyCodes.VOLUME_UP));
    elements.btnVolDown.addEventListener('click', () => sendKey(KeyCodes.VOLUME_DOWN));
    elements.btnNotify.addEventListener('click', () => expandNotifications());
    elements.btnSettings.addEventListener('click', () => expandSettings());
    elements.btnFullscreen.addEventListener('click', () => mirrorApi.toggleFullscreen());
    
    // 剪贴板
    elements.btnPasteToDevice.addEventListener('click', pasteToDevice);
    elements.btnTypeText.addEventListener('click', showTextDialog);
    elements.btnCancelText.addEventListener('click', hideTextDialog);
    elements.btnSendText.addEventListener('click', sendTextToDevice);
    
    // 键盘快捷键
    document.addEventListener('keydown', handleKeyboard);
    
    // 视频容器交互
    setupVideoInteraction();
}

/**
 * 设置视频交互（鼠标控制）
 */
function setupVideoInteraction() {
    const player = elements.videoPlayer;
    let isMouseDown = false;
    let lastX = 0, lastY = 0;
    
    // 禁用默认右键菜单
    player.addEventListener('contextmenu', e => e.preventDefault());
    
    player.addEventListener('mousedown', (e) => {
        if (!state.isMirroring) return;
        isMouseDown = true;
        const pos = getScaledPosition(e);
        if (!pos) return;
        lastX = pos.x;
        lastY = pos.y;
        
        // 鼠标右键作为 Back 键
        if (e.button === 2) {
            mirrorApi.sendKey(state.currentDevice, KeyCodes.BACK);
            return;
        }
        
        mirrorApi.sendTouch(state.currentDevice, 'tap', pos.x, pos.y);
    });
    
    player.addEventListener('mousemove', (e) => {
        if (!isMouseDown || !state.isMirroring) return;
        const pos = getScaledPosition(e);
        if (!pos) return;
        // 实时发送滑动
        if (Math.abs(pos.x - lastX) > 5 || Math.abs(pos.y - lastY) > 5) {
            mirrorApi.sendSwipe(state.currentDevice, lastX, lastY, pos.x, pos.y, 50);
            lastX = pos.x;
            lastY = pos.y;
        }
    });
    
    player.addEventListener('mouseup', () => {
        isMouseDown = false;
    });
    
    player.addEventListener('dblclick', () => {
        mirrorApi.toggleFullscreen();
    });
    
    // 滚轮滚动
    player.addEventListener('wheel', (e) => {
        if (!state.isMirroring) return;
        e.preventDefault();
        const pos = getScaledPosition(e);
        if (!pos) return;
        const direction = e.deltaY > 0 ? 100 : -100;
        mirrorApi.sendSwipe(state.currentDevice, pos.x, pos.y, pos.x, pos.y + direction, 100);
    });
}

/**
 * 获取缩放后的坐标
 */
function getScaledPosition(e) {
    const player = elements.videoPlayer;
    const rect = player.getBoundingClientRect();
    
    // 获取视频原始分辨率 - 必须等待视频加载完成
    const videoWidth = player.videoWidth;
    const videoHeight = player.videoHeight;
    
    // 如果视频尚未加载，无法计算正确坐标
    if (!videoWidth || !videoHeight) {
        console.warn('视频尺寸未就绪，跳过触控');
        return null;
    }
    
    // 计算视频和容器的宽高比
    const videoRatio = videoWidth / videoHeight;
    const elementRatio = rect.width / rect.height;
    
    let visualWidth, visualHeight;
    let offsetX = 0;
    let offsetY = 0;
    
    // 根据宽高比判断黑边位置
    if (elementRatio > videoRatio) {
        // 容器更宽，黑边在左右 (Pillarbox)
        visualHeight = rect.height;
        visualWidth = visualHeight * videoRatio;
        offsetX = (rect.width - visualWidth) / 2;
    } else {
        // 容器更高，黑边在上下 (Letterbox)
        visualWidth = rect.width;
        visualHeight = visualWidth / videoRatio;
        offsetY = (rect.height - visualHeight) / 2;
    }
    
    // 计算点击位置相对于视频实际显示区域的坐标
    const clientX = e.clientX - rect.left;
    const clientY = e.clientY - rect.top;
    
    // 映射到视频原始坐标系
    const x = (clientX - offsetX) * (videoWidth / visualWidth);
    const y = (clientY - offsetY) * (videoHeight / visualHeight);
    
    return { x, y };
}

/**
 * 设置拖放功能
 */
function setupDragAndDrop() {
    const container = elements.videoContainer;
    
    container.addEventListener('dragover', (e) => {
        e.preventDefault();
        container.classList.add('drag-over');
    });
    
    container.addEventListener('dragleave', () => {
        container.classList.remove('drag-over');
    });
    
    container.addEventListener('drop', async (e) => {
        e.preventDefault();
        container.classList.remove('drag-over');
        
        if (!state.currentDevice) {
            showToast('请先连接设备', 'error');
            return;
        }
        
        const files = Array.from(e.dataTransfer.files);
        for (const file of files) {
            const filePath = file.path;
            if (filePath.endsWith('.apk')) {
                showToast(`正在安装 ${file.name}...`);
                await mirrorApi.installApk(state.currentDevice, filePath);
            } else {
                showToast(`正在传输 ${file.name}...`);
                await mirrorApi.pushFile(state.currentDevice, filePath);
            }
        }
    });
}

/**
 * 刷新设备列表
 */
async function refreshDevices() {
    elements.deviceList.innerHTML = '<div class="loading">正在检测设备...</div>';
    
    try {
        const devices = await mirrorApi.getDevices();
        state.devices = devices;
        renderDeviceList(devices);
    } catch (error) {
        elements.deviceList.innerHTML = '<div class="hint">获取设备失败</div>';
        showToast('获取设备列表失败', 'error');
    }
}

/**
 * 渲染设备列表
 */
function renderDeviceList(devices) {
    if (devices.length === 0) {
        elements.deviceList.innerHTML = '<div class="hint">未检测到设备</div>';
        return;
    }
    
    elements.deviceList.innerHTML = devices.map(device => `
        <div class="device-item ${state.currentDevice === device.serial ? 'connected' : ''}" 
             data-serial="${device.serial}">
            <span class="device-icon">${device.isWireless ? '📶' : '📱'}</span>
            <div class="device-info">
                <div class="device-name">${device.model}</div>
                <div class="device-serial">${device.serial}</div>
            </div>
            <span class="device-status ${device.status}">${getStatusText(device.status)}</span>
        </div>
    `).join('');
    
    // 添加点击事件
    elements.deviceList.querySelectorAll('.device-item').forEach(item => {
        item.addEventListener('dblclick', () => {
            const serial = item.dataset.serial;
            const device = devices.find(d => d.serial === serial);
            if (device && device.status === 'device') {
                startMirror(serial, device.model);
            } else if (device.status === 'unauthorized') {
                showToast('请在手机上允许 USB 调试', 'warning');
            }
        });
    });
}

/**
 * 获取状态文本
 */
function getStatusText(status) {
    const texts = {
        device: '已连接',
        offline: '离线',
        unauthorized: '未授权'
    };
    return texts[status] || status;
}

/**
 * 扫描无线设备
 */
async function scanWirelessDevices() {
    // 显示正在扫描的网段信息
    const netInfo = state.networkInfo;
    const scanInfo = netInfo ? `正在扫描 ${netInfo.subnet}.1-254...` : '正在扫描局域网...';
    elements.wirelessList.innerHTML = `<div class="loading">${scanInfo}</div>`;
    elements.btnScan.disabled = true;
    
    try {
        const devices = await mirrorApi.scanWireless();
        
        if (devices.length === 0) {
            const hint = netInfo 
                ? `在 ${netInfo.subnet}.x 网段未发现设备<br><small>提示: 确保手机已开启无线调试</small>`
                : '未发现无线设备';
            elements.wirelessList.innerHTML = `<div class="hint">${hint}</div>`;
        } else {
            elements.wirelessList.innerHTML = devices.map(device => `
                <div class="device-item" data-address="${device.address}">
                    <span class="device-icon">📶</span>
                    <div class="device-info">
                        <div class="device-name">${device.ip}</div>
                        <div class="device-serial">端口 ${device.port}</div>
                    </div>
                    <span class="device-status">点击连接</span>
                </div>
            `).join('');
            
            // 添加点击事件
            elements.wirelessList.querySelectorAll('.device-item').forEach(item => {
                item.addEventListener('click', () => {
                    connectWireless(item.dataset.address);
                });
            });
            
            showToast(`发现 ${devices.length} 个无线设备`, 'success');
        }
    } catch (error) {
        elements.wirelessList.innerHTML = '<div class="hint">扫描失败</div>';
    }
    
    elements.btnScan.disabled = false;
}

/**
 * 连接无线设备
 */
async function connectWireless(address) {
    showToast(`正在连接 ${address}...`);
    
    const success = await mirrorApi.connectWireless(address);
    if (success) {
        showToast('连接成功', 'success');
        await refreshDevices();
    } else {
        showToast('连接失败', 'error');
    }
}

/**
 * 开始投屏
 */
async function startMirror(serial, deviceName) {
    state.currentDevice = serial;
    showMirrorView();
    elements.deviceInfo.textContent = deviceName || serial;
    elements.videoOverlay.classList.remove('hidden');
    
    try {
        showToast('正在启动投屏...');
        const { videoPort, controlPort } = await mirrorApi.startMirror(serial, {
            maxSize: 1920,
            maxFps: 60,
            bitRate: 8000000
        });
        
        state.isMirroring = true;
        elements.videoOverlay.classList.add('hidden');
        showToast('投屏已启动', 'success');
        
        // 连接视频流
        connectVideoStream(videoPort);
        
    } catch (error) {
        console.error('投屏启动失败:', error);
        showToast('投屏启动失败: ' + error.message, 'error');
        showWelcomeView();
    }
}

/**
 * 连接视频流（WebSocket -> JMuxer）
 */
function connectVideoStream(port) {
    if (window.jmuxer) {
        window.jmuxer.destroy();
        window.jmuxer = null;
    }

    // 初始化 JMuxer
    window.jmuxer = new JMuxer({
        node: 'video-player',
        mode: 'video',
        flushingTime: 0,
        fps: 60,
        debug: false,
        onError: function(data) {
            console.error('JMuxer Error:', data);
        }
    });

    // 连接 WebSocket
    const ws = new WebSocket('ws://127.0.0.1:3333');
    ws.binaryType = 'arraybuffer';
    
    ws.onopen = () => {
        console.log('视频流已连接 (WebSocket)');
    };
    
    ws.onmessage = (event) => {
        if (state.isMirroring && window.jmuxer) {
            window.jmuxer.feed({ video: new Uint8Array(event.data) });
        }
    };
    
    ws.onerror = (e) => {
        console.error('视频流 WebSocket 错误:', e);
        showToast('视频流连接错误', 'error');
    };
}

/**
 * 断开连接
 */
async function disconnect() {
    showToast('正在断开...');
    await mirrorApi.stopMirror();
    
    state.isMirroring = false;
    state.currentDevice = null;
    
    showWelcomeView();
    showToast('已断开连接', 'success');
    await refreshDevices();
}

/**
 * 发送按键
 */
async function sendKey(keycode) {
    if (!state.currentDevice) {
        showToast('请先连接设备', 'error');
        return;
    }
    await mirrorApi.sendKey(state.currentDevice, keycode);
}

/**
 * 下拉通知栏
 */
async function expandNotifications() {
    if (!state.currentDevice) {
        showToast('请先连接设备', 'error');
        return;
    }
    await mirrorApi.expandNotifications(state.currentDevice);
}

/**
 * 展开快捷设置
 */
async function expandSettings() {
    if (!state.currentDevice) {
        showToast('请先连接设备', 'error');
        return;
    }
    await mirrorApi.expandSettings(state.currentDevice);
}

/**
 * 粘贴到设备
 */
async function pasteToDevice() {
    if (!state.currentDevice) {
        showToast('请先连接设备', 'error');
        return;
    }
    
    const text = await mirrorApi.getClipboard();
    if (text) {
        await mirrorApi.sendText(state.currentDevice, text);
        showToast('已粘贴到手机', 'success');
    } else {
        showToast('剪贴板为空', 'warning');
    }
}

/**
 * 显示帮助对话框
 */
function showHelpDialog() {
    elements.helpDialog.classList.add('show');
}

/**
 * 隐藏帮助对话框
 */
function hideHelpDialog() {
    elements.helpDialog.classList.remove('show');
}

/**
 * 显示文本输入对话框
 */
function showTextDialog() {
    elements.textDialog.classList.add('show');
    elements.inputText.value = '';
    elements.inputText.focus();
}

/**
 * 隐藏文本输入对话框
 */
function hideTextDialog() {
    elements.textDialog.classList.remove('show');
}

/**
 * 发送文本到设备
 */
async function sendTextToDevice() {
    if (!state.currentDevice) {
        showToast('请先连接设备', 'error');
        return;
    }
    
    const text = elements.inputText.value;
    if (text) {
        await mirrorApi.sendText(state.currentDevice, text);
        showToast('已发送文本', 'success');
    }
    hideTextDialog();
}

/**
 * 键盘快捷键处理
 */
function handleKeyboard(e) {
    // 如果在输入框中，不处理
    if (e.target.tagName === 'INPUT' || e.target.tagName === 'TEXTAREA') return;
    
    // 系统快捷键
    switch (e.key) {
        case 'F5':
            e.preventDefault();
            refreshDevices();
            return;
        case 'F11':
            e.preventDefault();
            mirrorApi.toggleFullscreen();
            return;
        case 'Escape':
            if (elements.textDialog.classList.contains('show')) {
                hideTextDialog();
            }
            return;
    }
    
    // 如果没有连接设备，不处理
    if (!state.currentDevice || !state.isMirroring) return;
    
    // Ctrl 组合键 - 快捷操作
    if (e.ctrlKey) {
        e.preventDefault();
        switch (e.key.toLowerCase()) {
            case 'h': sendKey(KeyCodes.HOME); break;
            case 'b': sendKey(KeyCodes.BACK); break;
            case 's': sendKey(KeyCodes.APP_SWITCH); break;
            case 'm': sendKey(KeyCodes.MENU); break;
            case 'p': sendKey(KeyCodes.POWER); break;
            case 'n': e.shiftKey ? expandSettings() : expandNotifications(); break;
            case 'v': pasteToDevice(); break; // Ctrl+V 粘贴到手机
        }
        return;
    }
    
    // 实时键盘输入 - 直接发送到手机
    e.preventDefault();
    sendKeyCharToDevice(e.key, e.keyCode, {
        shift: e.shiftKey,
        ctrl: e.ctrlKey,
        alt: e.altKey
    });
}

/**
 * 发送单个按键字符到设备（实时输入）
 */
async function sendKeyCharToDevice(char, keyCode, modifiers) {
    if (!state.currentDevice) return;
    
    // 忽略修饰键本身
    const ignoreKeys = ['Shift', 'Control', 'Alt', 'Meta', 'CapsLock', 'NumLock'];
    if (ignoreKeys.includes(char)) return;
    
    try {
        await mirrorApi.sendKeyChar(state.currentDevice, char, keyCode, modifiers);
    } catch (e) {
        console.error('发送按键失败:', e);
    }
}

/**
 * 显示欢迎视图
 */
function showWelcomeView() {
    elements.welcomeView.classList.add('active');
    elements.mirrorView.classList.remove('active');
}

/**
 * 显示投屏视图
 */
function showMirrorView() {
    elements.welcomeView.classList.remove('active');
    elements.mirrorView.classList.add('active');
}

/**
 * 显示提示消息
 */
function showToast(message, type = '') {
    const toast = elements.toast;
    toast.textContent = message;
    toast.className = 'toast show ' + type;
    
    setTimeout(() => {
        toast.classList.remove('show');
    }, 3000);
}

/**
 * 显示安装进度
 */
function showInstallProgress({ status, progress }) {
    if (progress === 100) {
        showToast(status, 'success');
    } else if (progress < 0) {
        showToast(status, 'error');
    } else {
        showToast(status);
    }
}

/**
 * 显示传输进度
 */
function showTransferProgress({ status, fileName, progress }) {
    if (progress === 100) {
        showToast(`${fileName} ${status}`, 'success');
    } else if (progress < 0) {
        showToast(`${fileName} ${status}`, 'error');
    } else {
        showToast(`${fileName}: ${status}`);
    }
}

// 启动应用
init();

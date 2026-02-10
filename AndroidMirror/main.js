/**
 * AndroidMirror - Electron 涓昏繘绋?
 * 瀹夊崜鎶曞睆鎺у埗杞欢
 */

const { app, BrowserWindow, ipcMain, dialog, clipboard, Menu } = require('electron');
const path = require('path');
const { spawn, exec } = require('child_process');
const fs = require('fs');
const net = require('net');
const os = require('os');
const WebSocket = require('ws');

// 鍏ㄥ眬鍙橀噺
let mainWindow = null;
let adbProcess = null;
let scrcpyProcess = null;
let currentDevice = null;
let originalVolume = null;
let wss = null;
let videoStreamSocket = null;
let videoServer = null;  // TCP 鏈嶅姟鍣ㄧ敤浜庢帴鏀?scrcpy 瑙嗛娴?
let currentDeviceSize = null; // 璁惧鐪熷疄鐗╃悊鍒嗚鲸鐜?{width, height}
let currentVideoStreamSize = null; // 瑙嗛娴佸垎杈ㄧ巼 {width, height}

// 鍒涘缓 WebSocket 鏈嶅姟鍣?
function createWebSocketServer() {
    wss = new WebSocket.Server({ port: 3333 });
    console.log('WebSocket 瑙嗛娴佹湇鍔″櫒杩愯鍦ㄧ鍙?3333');
    
    wss.on('connection', (ws) => {
        console.log('鍓嶇宸茶繛鎺ュ埌瑙嗛娴?);
        // 鍙戦€佸垵濮嬪寲澶撮儴锛圝Muxer 闇€瑕侊級
        // ws.send(Buffer.from([0x00, 0x00, 0x00, 0x01])); 
    });
}

// 璧勬簮璺緞
const resourcesPath = app.isPackaged 
    ? path.join(process.resourcesPath) 
    : path.join(__dirname, 'resources');

const adbPath = path.join(resourcesPath, 'adb', 'adb.exe');
const scrcpyServerPath = path.join(resourcesPath, 'scrcpy-server');

/**
 * 鍒涘缓涓荤獥鍙?
 */
function createWindow() {
    mainWindow = new BrowserWindow({
        width: 1200,
        height: 800,
        minWidth: 800,
        minHeight: 600,
        backgroundColor: '#1e1e1e',
        webPreferences: {
            nodeIntegration: false,
            contextIsolation: true,
            preload: path.join(__dirname, 'preload.js')
        },
        frame: true,
        show: false
    });

    mainWindow.loadFile(path.join(__dirname, 'src', 'index.html'));

    mainWindow.once('ready-to-show', () => {
        mainWindow.show();
    });

    mainWindow.on('closed', () => {
        cleanup();
        mainWindow = null;
    });

    // 寮€鍙戞ā寮忎笅鎵撳紑 DevTools锛堟殏鏃剁鐢紝鍙寜 F12 鎵嬪姩鎵撳紑锛?
    // if (!app.isPackaged) {
    //     mainWindow.webContents.openDevTools({ mode: 'detach' });
    // }

    // 寮€鍙戞ā寮忎笅鎵撳紑 DevTools锛堟殏鏃剁鐢紝鍙寜 F12 鎵嬪姩鎵撳紑锛?
    // if (!app.isPackaged) {
    //     mainWindow.webContents.openDevTools({ mode: 'detach' });
    // }

    createMenu();
    createWebSocketServer(); // 鍚姩瑙嗛娴佹湇鍔?
}

/**
 * 鍒涘缓鑿滃崟
 */
function createMenu() {
    const template = [
        {
            label: '鏂囦欢',
            submenu: [
                { label: '鍒锋柊璁惧', accelerator: 'F5', click: () => mainWindow.webContents.send('refresh-devices') },
                { type: 'separator' },
                { label: '閫€鍑?, accelerator: 'Alt+F4', click: () => app.quit() }
            ]
        },
        {
            label: '瑙嗗浘',
            submenu: [
                { label: '鍏ㄥ睆', accelerator: 'F11', click: () => mainWindow.setFullScreen(!mainWindow.isFullScreen()) },
                { type: 'separator' },
                { label: '寮€鍙戣€呭伐鍏?, accelerator: 'F12', click: () => mainWindow.webContents.toggleDevTools() }
            ]
        },
        {
            label: '甯姪',
            submenu: [
                { label: '鍏充簬', click: () => showAbout() }
            ]
        }
    ];

    Menu.setApplicationMenu(Menu.buildFromTemplate(template));
}

/**
 * 鏄剧ず鍏充簬瀵硅瘽妗?
 */
function showAbout() {
    dialog.showMessageBox(mainWindow, {
        type: 'info',
        title: '鍏充簬 AndroidMirror',
        message: 'AndroidMirror v1.0.0',
        detail: '瀹夊崜鎶曞睆鎺у埗杞欢\n\n鍔熻兘鐗规€?\n鈥?瀹炴椂灞忓箷闀滃儚\n鈥?榧犳爣閿洏鎺у埗\n鈥?鏃犵嚎杩炴帴\n鈥?鏂囦欢浼犺緭\n鈥?鍓创鏉垮悓姝?
    });
}

/**
 * 鎵ц ADB 鍛戒护
 */
function runAdbCommand(args) {
    return new Promise((resolve, reject) => {
        const adb = spawn(adbPath, args, { windowsHide: true });
        let stdout = '';
        let stderr = '';

        adb.stdout.on('data', (data) => { stdout += data.toString(); });
        adb.stderr.on('data', (data) => { stderr += data.toString(); });

        adb.on('close', (code) => {
            if (code === 0) {
                resolve(stdout.trim());
            } else {
                reject(new Error(stderr || `ADB exited with code ${code}`));
            }
        });

        adb.on('error', (err) => reject(err));
    });
}

/**
 * 鑾峰彇璁惧鍒楄〃
 */
async function getDevices() {
    try {
        const output = await runAdbCommand(['devices', '-l']);
        const lines = output.split('\n').slice(1); // 璺宠繃绗竴琛?
        const devices = [];

        for (const line of lines) {
            const match = line.match(/^(\S+)\s+(device|unauthorized|offline)\s*(.*)/);
            if (match) {
                const [, serial, status, info] = match;
                const modelMatch = info.match(/model:(\S+)/);
                const model = modelMatch ? modelMatch[1].replace(/_/g, ' ') : serial;
                
                devices.push({
                    serial,
                    status,
                    model,
                    isWireless: serial.includes(':')
                });
            }
        }

        return devices;
    } catch (error) {
        console.error('鑾峰彇璁惧鍒楄〃澶辫触:', error);
        return [];
    }
}

/**
 * 鑾峰彇鏈満缃戠粶淇℃伅
 */
function getNetworkInfo() {
    const interfaces = os.networkInterfaces();
    const networks = [];
    
    // 闇€瑕佽繃婊ょ殑铏氭嫙缃戝崱鍏抽敭璇?
    const virtualKeywords = ['vmware', 'virtualbox', 'vbox', 'docker', 'vpn', 'tun', 'tap', 'radmin', 'hamachi', 'zerotier', 'singbox'];
    
    for (const name of Object.keys(interfaces)) {
        // 杩囨护铏氭嫙缃戝崱
        const lowerName = name.toLowerCase();
        if (virtualKeywords.some(kw => lowerName.includes(kw))) {
            continue;
        }
        
        for (const iface of interfaces[name]) {
            if (iface.family === 'IPv4' && !iface.internal) {
                const subnet = iface.address.substring(0, iface.address.lastIndexOf('.'));
                
                // 浼樺厛閫夋嫨甯歌鐨勫眬鍩熺綉缃戞 (192.168.x.x, 10.x.x.x, 172.16-31.x.x)
                const isPrivate = iface.address.startsWith('192.168.') || 
                                  iface.address.startsWith('10.') ||
                                  (iface.address.startsWith('172.') && parseInt(subnet.split('.')[1]) >= 16 && parseInt(subnet.split('.')[1]) <= 31);
                
                networks.push({
                    name,
                    ip: iface.address,
                    subnet: subnet,
                    scanRange: `${subnet}.1 - ${subnet}.254`,
                    isPrivate: isPrivate,
                    priority: isPrivate ? (iface.address.startsWith('192.168.') ? 1 : 2) : 3
                });
            }
        }
    }
    
    // 鎸変紭鍏堢骇鎺掑簭锛?92.168.x.x 浼樺厛
    networks.sort((a, b) => a.priority - b.priority);
    
    return networks;
}

/**
 * 鍙戦€佸崟涓瓧绗︼紙瀹炴椂閿洏杈撳叆锛?
 */
async function sendKeyChar(serial, char, keyCode, modifiers = {}) {
    // 澶勭悊鐗规畩鎸夐敭
    const specialKeys = {
        'Backspace': 67,
        'Enter': 66,
        'Tab': 61,
        'Escape': 111,
        'Delete': 112,
        'ArrowUp': 19,
        'ArrowDown': 20,
        'ArrowLeft': 21,
        'ArrowRight': 22,
        'Home': 3,
        'End': 123,
        'PageUp': 92,
        'PageDown': 93,
        ' ': 62  // Space
    };
    
    if (specialKeys[char]) {
        await runAdbCommand(['-s', serial, 'shell', 'input', 'keyevent', String(specialKeys[char])]);
        return;
    }
    
    // 鏅€氬瓧绗︾洿鎺ヨ緭鍏?
    if (char.length === 1) {
        // 瀵逛簬涓枃鍜岀壒娈婂瓧绗︼紝浣跨敤 input text
        // 瀵逛簬甯歌瀛楃锛屼篃浣跨敤 input text 鍥犱负鏇村彲闈?
        const escaped = char.replace(/[\\'"` &|<>()$!]/g, '\\$&');
        await runAdbCommand(['-s', serial, 'shell', 'input', 'text', escaped]);
    }
}

/**
 * 鎵弿灞€鍩熺綉璁惧
 */
async function scanWirelessDevices() {
    const localIp = getLocalIp();
    if (!localIp) return [];

    const subnet = localIp.substring(0, localIp.lastIndexOf('.'));
    const discoveredDevices = [];

    // 鎵弿甯歌 ADB 绔彛
    const ports = [5555, 5556, 5557];
    const scanPromises = [];

    for (let i = 1; i <= 254; i++) {
        const ip = `${subnet}.${i}`;
        for (const port of ports) {
            scanPromises.push(checkAdbDevice(ip, port));
        }
    }

    const results = await Promise.allSettled(scanPromises);
    
    for (const result of results) {
        if (result.status === 'fulfilled' && result.value) {
            discoveredDevices.push(result.value);
        }
    }

    return discoveredDevices;
}

/**
 * 妫€鏌?ADB 璁惧
 */
function checkAdbDevice(ip, port) {
    return new Promise((resolve) => {
        const socket = new net.Socket();
        socket.setTimeout(500);

        socket.on('connect', () => {
            socket.destroy();
            resolve({ ip, port, address: `${ip}:${port}` });
        });

        socket.on('timeout', () => {
            socket.destroy();
            resolve(null);
        });

        socket.on('error', () => {
            socket.destroy();
            resolve(null);
        });

        socket.connect(port, ip);
    });
}

/**
 * 鑾峰彇鏈満 IP
 */
function getLocalIp() {
    const interfaces = os.networkInterfaces();
    for (const name of Object.keys(interfaces)) {
        for (const iface of interfaces[name]) {
            if (iface.family === 'IPv4' && !iface.internal) {
                return iface.address;
            }
        }
    }
    return null;
}

/**
 * 杩炴帴鏃犵嚎璁惧
 */
async function connectWireless(address) {
    try {
        await runAdbCommand(['connect', address]);
        return true;
    } catch (error) {
        console.error('杩炴帴澶辫触:', error);
        return false;
    }
}

/**
 * 鏂紑鏃犵嚎璁惧
 */
async function disconnectWireless(address) {
    try {
        await runAdbCommand(['disconnect', address]);
        return true;
    } catch (error) {
        return false;
    }
}

/**
 * 鍚姩 scrcpy
 */
/**
 * 鍚姩 scrcpy
 */
async function startMirror(serial, options = {}) {
    // 鍏堝仠姝箣鍓嶇殑鎶曞睆锛堝鏋滄湁锛?
    await stopMirror();
    
    // 鏉€鎺夋墜鏈轰笂鍙兘娈嬬暀鐨?scrcpy 杩涚▼
    try {
        await runAdbCommand(['-s', serial, 'shell', 'pkill', '-f', 'scrcpy']);
    } catch (e) {
        // 蹇界暐閿欒锛堝彲鑳芥病鏈夋棫杩涚▼锛?
    }
    
    // 绛夊緟涓€涓嬭杩涚▼瀹屽叏閫€鍑?
    await new Promise(resolve => setTimeout(resolve, 500));
    
    currentDevice = serial;

    // 鑾峰彇璁惧鐪熷疄鍒嗚鲸鐜?
    try {
        const sizeOutput = await runAdbCommand(['-s', serial, 'shell', 'wm', 'size']);
        const match = sizeOutput.match(/Physical size: (\d+)x(\d+)/);
        if (match) {
            currentDeviceSize = {
                width: parseInt(match[1]),
                height: parseInt(match[2])
            };
            console.log(`璁惧鐪熷疄鍒嗚鲸鐜? ${currentDeviceSize.width}x${currentDeviceSize.height}`);
        }
    } catch (e) {
        console.error('鑾峰彇璁惧鍒嗚鲸鐜囧け璐?', e);
    }

    // 淇濆瓨骞堕潤闊虫墜鏈洪煶閲?
    try {
        const volumeOutput = await runAdbCommand(['-s', serial, 'shell', 'settings', 'get', 'system', 'volume_music']);
        originalVolume = parseInt(volumeOutput) || 7;
        await runAdbCommand(['-s', serial, 'shell', 'media', 'volume', '--set', '0']);
    } catch (e) {
        console.log('鏃犳硶鎺у埗闊抽噺');
    }

    // 鎺ㄩ€?scrcpy-server
    await runAdbCommand(['-s', serial, 'push', scrcpyServerPath, '/data/local/tmp/scrcpy-server.jar']);

    // scrcpy 3.x 浣跨敤 scid 鍙傛暟鏉ュ垱寤哄敮涓€鐨?socket 鍚嶇О
    const scid = Math.floor(Math.random() * 0x7FFFFFFF); // 31-bit random number
    const socketName = `scrcpy_${scid.toString(16).padStart(8, '0')}`;
    console.log(`[Scrcpy] 浣跨敤 SCID: ${scid} (0x${scid.toString(16)}), Socket: ${socketName}`);

    // 绔彛鏄犲皠锛圧everse锛夛細璁╂墜鏈鸿繛鎺ョ數鑴戠鍙?
    // 鍏堟竻鐞嗗彲鑳芥畫鐣欑殑鏄犲皠
    try { await runAdbCommand(['-s', serial, 'reverse', '--remove-all']); } catch (e) {}
    
    // 鍒涘缓鏂扮殑 Reverse 鏄犲皠 - scrcpy 3.x 鏍煎紡
    await runAdbCommand(['-s', serial, 'reverse', `localabstract:${socketName}`, 'tcp:27183']);

    // 鍏堝垱寤烘湰鍦?TCP 鏈嶅姟鍣ㄧ瓑寰?scrcpy 杩炴帴
    return new Promise(async (resolve, reject) => {
        let started = false;
        let outputLog = '';

        // 鍏抽棴鏃х殑瑙嗛鏈嶅姟鍣紙绛夊緟瀹屾垚锛?
        if (videoServer) {
            await new Promise((r) => {
                videoServer.close(() => {
                    console.log('鏃ц棰戞湇鍔″櫒宸插叧闂?);
                    r();
                });
            });
            videoServer = null;
        }

        // 鍒涘缓瑙嗛娴佹湇鍔″櫒 - scrcpy 3.x 鍗忚
        videoServer = net.createServer((socket) => {
            console.log('scrcpy 瑙嗛娴佸凡杩炴帴');
            
            let metadataReceived = false;
            let buffer = Buffer.alloc(0);
            let frameCount = 0;
            
            socket.on('data', (data) => {
                buffer = Buffer.concat([buffer, data]);
                
                // 绗竴姝? 瑙ｆ瀽鍒濆鍏冩暟鎹?
                // scrcpy 3.x 鏍煎紡: 64瀛楄妭璁惧鍚?+ 4瀛楄妭codec + 4瀛楄妭width + 4瀛楄妭height = 76瀛楄妭
                if (!metadataReceived) {
                    if (buffer.length >= 76) {
                        const deviceName = buffer.slice(0, 64).toString('utf8').replace(/\0/g, '').trim();
                        const codecId = buffer.readUInt32BE(64);
                        const width = buffer.readUInt32BE(68);
                        const height = buffer.readUInt32BE(72);
                        
                        // 淇濆瓨瑙嗛娴佸垎杈ㄧ巼
                        currentVideoStreamSize = { width, height };
                        
                        console.log(`[Scrcpy] Device: ${deviceName}, Codec: 0x${codecId.toString(16)}, Size: ${width}x${height}`);
                        buffer = buffer.slice(76);
                        metadataReceived = true;
                    } else {
                        return;
                    }
                }
                
                // 绗簩姝? 澶勭悊瑙嗛甯?
                // scrcpy 3.x 甯ф牸寮? 8瀛楄妭 PTS + 4瀛楄妭 packet size + 瑙嗛鏁版嵁
                while (buffer.length >= 12) {
                    // 璇诲彇甯уご
                    const packetSize = buffer.readUInt32BE(8);
                    
                    // 瀹夊叏妫€鏌?
                    if (packetSize > 10000000 || packetSize < 0) {
                        console.error(`[Error] Invalid packet size: ${packetSize}, buffer: ${buffer.slice(0, 20).toString('hex')}`);
                        buffer = Buffer.alloc(0);
                        break;
                    }
                    
                    // 妫€鏌ユ槸鍚︽湁瀹屾暣鐨勫抚
                    if (buffer.length < 12 + packetSize) {
                        break; // 绛夊緟鏇村鏁版嵁
                    }
                    
                    // 鎻愬彇瑙嗛鏁版嵁
                    const videoData = buffer.slice(12, 12 + packetSize);
                    buffer = buffer.slice(12 + packetSize);
                    
                    frameCount++;
                    if (frameCount <= 3) {
                        console.log(`[Frame ${frameCount}] Size: ${packetSize}, First bytes: ${videoData.slice(0, 16).toString('hex')}`);
                    }
                    
                    // 鍙戦€佸埌 WebSocket
                    if (wss && videoData.length > 0) {
                        wss.clients.forEach(client => {
                            if (client.readyState === WebSocket.OPEN) {
                                client.send(videoData);
                            }
                        });
                    }
                }
            });
            
            socket.on('error', (e) => console.error('瑙嗛娴侀敊璇?', e));
        });

        videoServer.on('error', (e) => {
            console.error('瑙嗛鏈嶅姟鍣ㄩ敊璇?', e);
            reject(new Error(`瑙嗛鏈嶅姟鍣ㄩ敊璇? ${e.message}`));
        });

        videoServer.listen(27183, '127.0.0.1', () => {
            console.log('瑙嗛娴佹湇鍔″櫒鐩戝惉鍦?27183');
        });

        // 鍚姩 scrcpy-server
        const serverProcess = spawn(adbPath, [
            '-s', serial, 'shell',
            'CLASSPATH=/data/local/tmp/scrcpy-server.jar',
            'app_process', '/', 'com.genymobile.scrcpy.Server',
            '3.3.4',
            `scid=${scid.toString(16).padStart(8, '0')}`, // scrcpy 3.x 蹇呴渶鐨?scid 鍙傛暟
            'tunnel_forward=false', // Reverse 妯″紡
            'video=true',
            'video_codec=h264',     // 鏄庣‘浣跨敤 H.264 缂栫爜
            'video_source=display',
            'audio=false',
            'control=false',        // 绂佺敤鎺у埗浠ョ畝鍖栬皟璇?
            'cleanup=true',
            `max_size=${options.maxSize || 1920}`,
            `max_fps=${options.maxFps || 60}`,
            `video_bit_rate=${options.bitRate || 8000000}`
        ], { windowsHide: true });

        scrcpyProcess = serverProcess;

        const timeout = setTimeout(() => {
            if (!started) {
                videoServer.close();
                scrcpyProcess.kill();
                reject(new Error(`鍚姩瓒呮椂銆傛棩蹇?\n${outputLog}`));
            }
        }, 10000);

        serverProcess.stdout.on('data', (data) => {
            const output = data.toString();
            outputLog += output;
            console.log('scrcpy stdout:', output);
            
            if (!started && output.includes('INFO:')) {
                started = true;
                clearTimeout(timeout);
                resolve({ videoPort: 27183, controlPort: 27184 });
            }
        });

        serverProcess.stderr.on('data', (data) => {
            const output = data.toString();
            outputLog += output;
            console.error('scrcpy stderr:', output);
        });

        serverProcess.on('close', (code) => {
            if (!started) {
                clearTimeout(timeout);
                videoServer.close();
                reject(new Error(`scrcpy 閫€鍑?(${code})銆傛棩蹇?\n${outputLog}`));
            }
        });
    });
}

/**
 * 鍋滄鎶曞睆
 */
async function stopMirror() {
    if (scrcpyProcess) {
        scrcpyProcess.kill();
        scrcpyProcess = null;
    }

    // 鍏抽棴瑙嗛娴佹湇鍔″櫒
    if (videoServer) {
        try {
            videoServer.close();
        } catch (e) { /* 蹇界暐 */ }
        videoServer = null;
    }

    // 鎭㈠闊抽噺
    if (currentDevice && originalVolume !== null) {
        try {
            await runAdbCommand(['-s', currentDevice, 'shell', 'media', 'volume', '--set', String(originalVolume)]);
        } catch (e) {
            console.log('鏃犳硶鎭㈠闊抽噺');
        }
        originalVolume = null;
    }

    // 绉婚櫎绔彛杞彂
    if (currentDevice) {
        try {
            await runAdbCommand(['-s', currentDevice, 'forward', '--remove-all']);
        } catch (e) {}
    }

    currentDevice = null;
    currentDeviceSize = null;
    currentVideoStreamSize = null;
}

/**
 * 鍙戦€佹寜閿簨浠?
 */
async function sendKeyEvent(serial, keycode) {
    await runAdbCommand(['-s', serial, 'shell', 'input', 'keyevent', String(keycode)]);
}

/**
 * 杞崲鍧愭爣 (鍓嶇瑙嗛鍧愭爣 -> 鐪熷疄鐗╃悊鍧愭爣)
 */
function mapCoordinate(x, y) {
    if (!currentDeviceSize || !currentVideoStreamSize) {
        return { x, y };
    }
    
    // 缂╂斁姣斾緥
    const scaleX = currentDeviceSize.width / currentVideoStreamSize.width;
    const scaleY = currentDeviceSize.height / currentVideoStreamSize.height;
    
    return {
        x: Math.round(x * scaleX),
        y: Math.round(y * scaleY)
    };
}

/**
 * 鍙戦€佽Е鎽镐簨浠?
 */
async function sendTouchEvent(serial, action, x, y) {
    const coords = mapCoordinate(x, y);
    await runAdbCommand(['-s', serial, 'shell', 'input', action, String(coords.x), String(coords.y)]);
}

/**
 * 鍙戦€佹粦鍔ㄤ簨浠?
 */
async function sendSwipeEvent(serial, x1, y1, x2, y2, duration = 300) {
    const p1 = mapCoordinate(x1, y1);
    const p2 = mapCoordinate(x2, y2);
    
    await runAdbCommand(['-s', serial, 'shell', 'input', 'swipe', 
        String(p1.x), String(p1.y),
        String(p2.x), String(p2.y),
        String(duration)
    ]);
}

/**
 * 鍙戦€佹枃鏈緭鍏?
 */
async function sendText(serial, text) {
    // 杞箟鐗规畩瀛楃
    const escaped = text.replace(/[\\'"` ]/g, '\\$&');
    await runAdbCommand(['-s', serial, 'shell', 'input', 'text', escaped]);
}

/**
 * 瀹夎 APK
 */
async function installApk(serial, apkPath) {
    mainWindow.webContents.send('install-progress', { status: '姝ｅ湪瀹夎...', progress: 0 });
    
    try {
        await runAdbCommand(['-s', serial, 'install', '-r', apkPath]);
        mainWindow.webContents.send('install-progress', { status: '瀹夎瀹屾垚', progress: 100 });
        return true;
    } catch (error) {
        mainWindow.webContents.send('install-progress', { status: '瀹夎澶辫触: ' + error.message, progress: -1 });
        return false;
    }
}

/**
 * 浼犺緭鏂囦欢
 */
async function pushFile(serial, localPath, remotePath = '/sdcard/Download/') {
    const fileName = path.basename(localPath);
    const destination = remotePath + fileName;

    mainWindow.webContents.send('transfer-progress', { status: '姝ｅ湪浼犺緭...', fileName, progress: 0 });

    try {
        await runAdbCommand(['-s', serial, 'push', localPath, destination]);
        mainWindow.webContents.send('transfer-progress', { status: '浼犺緭瀹屾垚', fileName, progress: 100 });
        return true;
    } catch (error) {
        mainWindow.webContents.send('transfer-progress', { status: '浼犺緭澶辫触: ' + error.message, fileName, progress: -1 });
        return false;
    }
}

/**
 * 鑾峰彇鍓创鏉垮唴瀹?
 */
async function getDeviceClipboard(serial) {
    try {
        const output = await runAdbCommand(['-s', serial, 'shell', 'service', 'call', 'clipboard', '2', 's16', 'com.android.shell']);
        // 瑙ｆ瀽鍓创鏉垮唴瀹?..
        return '';
    } catch (e) {
        return '';
    }
}

/**
 * 璁剧疆璁惧鍓创鏉?
 */
async function setDeviceClipboard(serial, text) {
    try {
        await runAdbCommand(['-s', serial, 'shell', 'am', 'broadcast', '-a', 'clipper.set', '-e', 'text', text]);
        return true;
    } catch (e) {
        // 澶囩敤鏂规硶锛氶€氳繃 input 鍙戦€?
        try {
            const escaped = text.replace(/[\\'"` ]/g, '\\$&');
            await runAdbCommand(['-s', serial, 'shell', 'input', 'text', escaped]);
            return true;
        } catch (e2) {
            return false;
        }
    }
}

/**
 * 涓嬫媺閫氱煡鏍?
 */
async function expandNotifications(serial) {
    await runAdbCommand(['-s', serial, 'shell', 'cmd', 'statusbar', 'expand-notifications']);
}

/**
 * 灞曞紑蹇嵎璁剧疆
 */
async function expandSettings(serial) {
    await runAdbCommand(['-s', serial, 'shell', 'cmd', 'statusbar', 'expand-settings']);
}

/**
 * 娓呯悊璧勬簮
 */
function cleanup() {
    stopMirror();
}

// IPC 浜嬩欢澶勭悊
ipcMain.handle('get-devices', getDevices);
ipcMain.handle('get-network-info', getNetworkInfo);
ipcMain.handle('scan-wireless', scanWirelessDevices);
ipcMain.handle('connect-wireless', (event, address) => connectWireless(address));
ipcMain.handle('disconnect-wireless', (event, address) => disconnectWireless(address));
ipcMain.handle('start-mirror', (event, serial, options) => startMirror(serial, options));
ipcMain.handle('stop-mirror', stopMirror);
ipcMain.handle('send-key', (event, serial, keycode) => sendKeyEvent(serial, keycode));
ipcMain.handle('send-key-char', (event, serial, char, keyCode, modifiers) => sendKeyChar(serial, char, keyCode, modifiers));
ipcMain.handle('send-touch', (event, serial, action, x, y) => sendTouchEvent(serial, action, x, y));
ipcMain.handle('send-swipe', (event, serial, x1, y1, x2, y2, duration) => sendSwipeEvent(serial, x1, y1, x2, y2, duration));
ipcMain.handle('send-text', (event, serial, text) => sendText(serial, text));
ipcMain.handle('install-apk', (event, serial, apkPath) => installApk(serial, apkPath));
ipcMain.handle('push-file', (event, serial, localPath) => pushFile(serial, localPath));
ipcMain.handle('expand-notifications', (event, serial) => expandNotifications(serial));
ipcMain.handle('expand-settings', (event, serial) => expandSettings(serial));
ipcMain.handle('get-clipboard', () => clipboard.readText());
ipcMain.handle('set-clipboard', (event, text) => { clipboard.writeText(text); return true; });
ipcMain.handle('sync-clipboard-to-device', (event, serial) => setDeviceClipboard(serial, clipboard.readText()));
ipcMain.handle('toggle-fullscreen', () => { mainWindow.setFullScreen(!mainWindow.isFullScreen()); });

// 搴旂敤绋嬪簭浜嬩欢
app.whenReady().then(createWindow);

app.on('window-all-closed', () => {
    cleanup();
    if (process.platform !== 'darwin') {
        app.quit();
    }
});

app.on('activate', () => {
    if (BrowserWindow.getAllWindows().length === 0) {
        createWindow();
    }
});

app.on('before-quit', cleanup);

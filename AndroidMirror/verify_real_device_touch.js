/**
 * 触控坐标映射逻辑验证脚本
 * 使用从日志中提取的真实设备数据进行回放测试
 * 
 * 设备: HUAWEI VOG-AL10
 * 物理分辨率: 1080 x 2340
 * 视频流分辨率: 888 x 1920 (受限于 max_size 或 scrcpy 编码对齐)
 */

// 模拟 main.js 中的全局状态
const currentDeviceSize = { width: 1080, height: 2340 };
const currentVideoStreamSize = { width: 888, height: 1920 };

// 模拟 main.js 中的转换函数
function mapCoordinate(x, y) {
    if (!currentDeviceSize || !currentVideoStreamSize) {
        return { x, y };
    }
    
    // 缩放比例
    const scaleX = currentDeviceSize.width / currentVideoStreamSize.width;
    const scaleY = currentDeviceSize.height / currentVideoStreamSize.height;
    
    return {
        x: Math.round(x * scaleX),
        y: Math.round(y * scaleY),
        // 调试信息
        _debug: {
            scaleX: scaleX.toFixed(4), 
            scaleY: scaleY.toFixed(4)
        }
    };
}

// === 测试用例 ===

console.log(`[配置] 物理分辨率: ${currentDeviceSize.width}x${currentDeviceSize.height}`);
console.log(`[配置] 视频流分辨率: ${currentVideoStreamSize.width}x${currentVideoStreamSize.height}`);

// Case 1: 点击视频左上角 (0, 0)
// 预期: 物理 (0, 0)
const p1 = mapCoordinate(0, 0);
console.log(`\n[测试 1] 左上角 (0,0) -> 物理 (${p1.x}, ${p1.y}) | 预期: (0,0)`);
if (p1.x === 0 && p1.y === 0) console.log("✅ 通过"); else console.error("❌ 失败");

// Case 2: 点击视频右下角 (888, 1920)
// 预期: 物理 (1080, 2340)
const p2 = mapCoordinate(888, 1920);
console.log(`\n[测试 2] 右下角 (888,1920) -> 物理 (${p2.x}, ${p2.y}) | 预期: (1080,2340)`);
if (p2.x === 1080 && p2.y === 2340) console.log("✅ 通过"); else console.error("❌ 失败");

// Case 3: 点击视频中心 (444, 960)
// 预期: 物理 (540, 1170)
const p3 = mapCoordinate(444, 960);
console.log(`\n[测试 3] 中心点 (444,960) -> 物理 (${p3.x}, ${p3.y}) | 预期: (540,1170)`);
if (p3.x === 540 && p3.y === 1170) console.log("✅ 通过"); else console.error("❌ 失败");

// Case 4: 任意点 (100, 200)
// ScaleX = 1080/888 ≈ 1.2162
// ScaleY = 2340/1920 = 1.21875
// 预期 X = 100 * 1.2162 = 122
// 预期 Y = 200 * 1.21875 = 244
const p4 = mapCoordinate(100, 200);
console.log(`\n[测试 4] 任意点 (100,200) -> 物理 (${p4.x}, ${p4.y}) | Scale: ${p4._debug.scaleX}, ${p4._debug.scaleY}`);
if (Math.abs(p4.x - 122) <= 1 && Math.abs(p4.y - 244) <= 1) console.log("✅ 通过"); else console.error("❌ 失败");

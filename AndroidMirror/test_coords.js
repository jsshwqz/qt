/**
 * 测试 getScaledPosition 的逻辑
 * 模拟 DOM 环境和 video 元素
 */

function testGetScaledPosition(
    clickX, clickY,          // 鼠标点击坐标 (相对于 client)
    rectWidth, rectHeight,   // 播放器容器尺寸
    videoWidth, videoHeight  // 视频原始尺寸
) {
    // 模拟 element.getBoundingClientRect()
    // 假设 element 在 (0,0)
    const rect = {
        left: 0,
        top: 0,
        width: rectWidth,
        height: rectHeight
    };

    // --- 复制 app.js 中的逻辑 ---
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
        console.log(`Type: Pillarbox (黑边在左右), OffsetX: ${offsetX}`);
    } else {
        // 容器更高，黑边在上下 (Letterbox)
        visualWidth = rect.width;
        visualHeight = visualWidth / videoRatio;
        offsetY = (rect.height - visualHeight) / 2;
        console.log(`Type: Letterbox (黑边在上下), OffsetY: ${offsetY}`);
    }
    
    // 计算点击位置相对于视频实际显示区域的坐标
    const clientX = clickX - rect.left;
    const clientY = clickY - rect.top;
    
    // 映射到视频原始坐标系
    const x = (clientX - offsetX) * (videoWidth / visualWidth);
    const y = (clientY - offsetY) * (videoHeight / visualHeight);
    
    return { x, y };
}

// === 测试用例 ===

console.log("=== Test 1: 完美匹配 (1:1 scaling) ===");
// 容器 1080x1920, 视频 1080x1920
// 点击中心 (540, 960) -> 应该返回 (540, 960)
let res1 = testGetScaledPosition(540, 960, 1080, 1920, 1080, 1920);
console.log(`Expected: 540, 960. Got: ${res1.x.toFixed(1)}, ${res1.y.toFixed(1)}\n`);

console.log("=== Test 2: Letterbox (容器过高) ===");
// 容器 1080x2500, 视频 1080x1920
// 视频应该高 1920 (如果宽填满1080)，黑边上下各 (2500-1920)/2 = 290
// 点击视频中心 (540, 1250) -> 应该返回 (540, 960)
let res2 = testGetScaledPosition(540, 1250, 1080, 2500, 1080, 1920);
console.log(`Visual Height: 1920, OffsetY: 290`);
console.log(`Click Y=1250 (Center of 2500). Relative to video top: 1250-290 = 960`);
console.log(`Expected: 540, 960. Got: ${res2.x.toFixed(1)}, ${res2.y.toFixed(1)}\n`);

console.log("=== Test 3: Pillarbox (容器过宽) ===");
// 容器 2000x1920, 视频 1080x1920
// 视频应该宽 1080 (如果高填满1920)，黑边左右各 (2000-1080)/2 = 460
// 点击视频左上角 (460, 0) -> 应该返回 (0, 0)
let res3 = testGetScaledPosition(460, 0, 2000, 1920, 1080, 1920);
console.log(`Visual Width: 1080, OffsetX: 460`);
console.log(`Click X=460. Relative to video left: 0`);
console.log(`Expected: 0, 0. Got: ${res3.x.toFixed(1)}, ${res3.y.toFixed(1)}\n`);

console.log("=== Test 4: 点击黑边区域 (Pillarbox) ===");
// 容器 2000x1920, 视频 1080x1920
// 点击最左侧黑边 (10, 100) -> 应该返回 负数 X
let res4 = testGetScaledPosition(10, 100, 2000, 1920, 1080, 1920);
console.log(`Expected: Negative X. Got: ${res4.x.toFixed(1)}, ${res4.y.toFixed(1)}\n`);

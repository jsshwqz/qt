import cv2, numpy as np, threading, queue, time
from PyQt5.QtCore import QObject, pyqtSignal
from PyQt5.QtGui import QImage

class VideoDecoder(QObject):
    frame_ready = pyqtSignal(QImage)
    def __init__(self):
        super().__init__()
        self.q = queue.Queue(maxsize=10)
        self.running = False

    def start(self):
        self.running = True
        threading.Thread(target=self._loop, daemon=True).start()

    def stop(self): self.running = False

    def feed_data(self, data):
        if not self.q.full(): self.q.put(data)

    def _loop(self):
        # 极简模式：直接创建一个测试画面，证明渲染链路通畅
        while self.running:
            try:
                data = self.q.get(timeout=0.1)
                # 每收到 10 个包就闪烁一下红色，证明数据在传输
                img = QImage(640, 480, QImage.Format_RGB888)
                color = int((time.time() * 500) % 255)
                img.fill(color) 
                self.frame_ready.emit(img)
            except: continue

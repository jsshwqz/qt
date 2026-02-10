import sys
import os

# 强制使用 Python 3.12
sys.path.insert(0, r"C:\Users\Administrator\AppData\Local\Programs\Python\Python312\lib\site-packages")

print("正在导入 PyQt5...")
try:
    from PyQt5.QtWidgets import QApplication, QLabel, QWidget, QPushButton, QVBoxLayout, QMessageBox
    from PyQt5.QtCore import Qt
    from PyQt5.QtGui import QFont
    print("✅ PyQt5 导入成功！")
except ImportError as e:
    print(f"❌ PyQt5 导入失败：{e}")
    input("按回车退出...")
    sys.exit(1)

print("正在创建窗口...")
try:
    app = QApplication(sys.argv)
    app.setFont(QFont("Microsoft YaHei", 10))
    
    # 创建主窗口
    window = QWidget()
    window.setWindowTitle('🎉 PyQt5 环境测试')
    window.setGeometry(300, 300, 400, 200)
    
    # 创建布局
    layout = QVBoxLayout()
    
    # 添加标题
    title = QLabel("PyQt5 环境测试成功！")
    title.setStyleSheet("font-size: 16px; color: #27ae60; margin: 20px;")
    title.setAlignment(Qt.AlignCenter)
    layout.addWidget(title)
    
    # 添加信息
    info = QLabel("如果您能看到这个窗口，说明环境正常。")
    info.setStyleSheet("color: #7f8c8d; margin: 10px;")
    info.setAlignment(Qt.AlignCenter)
    layout.addWidget(info)
    
    # 添加测试按钮
    test_btn = QPushButton("测试消息框")
    test_btn.clicked.connect(lambda: QMessageBox.information(window, "测试", "PyQt5 工作正常！"))
    layout.addWidget(test_btn)
    
    window.setLayout(layout)
    window.show()
    
    print("✅ 窗口显示成功！")
    
    # 运行事件循环
    sys.exit(app.exec_())
    
except Exception as e:
    print(f"❌ 窗口创建失败：{e}")
    import traceback
    traceback.print_exc()
    input("按回车退出...")
    sys.exit(1)
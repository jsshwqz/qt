/**
 * QtScrcpy - Android Screen Mirroring Application
 * Copyright (C) 2024 QtScrcpy Contributors
 *
 * Licensed under the Apache License, Version 2.0
 */

#include <QApplication>
#include <QStyleFactory>
#include <QMessageBox>

#include "ui/mainwindow.h"
#include "adb/adbprocess.h"

// 鎼存梻鏁ょ粙瀣碍閻楀牊婀?
const char* APP_VERSION = "1.0.0";
const char* APP_NAME = "QtScrcpy";

/**
 * @brief 閸掓繂顫愰崠鏍х安閻劎鈻兼惔蹇旂壉瀵?
 */
void initializeStyle(QApplication& app)
{
    // 娴ｈ法鏁?Fusion 妞嬪孩鐗告担婊€璐熼崺铏诡攨
    app.setStyle(QStyleFactory::create("Fusion"));
    
    // 鐠佸墽鐤嗗ǎ杈娑撳顣界拫鍐閺?
    QPalette darkPalette;
    darkPalette.setColor(QPalette::Window, QColor(45, 45, 48));
    darkPalette.setColor(QPalette::WindowText, Qt::white);
    darkPalette.setColor(QPalette::Base, QColor(30, 30, 30));
    darkPalette.setColor(QPalette::AlternateBase, QColor(45, 45, 48));
    darkPalette.setColor(QPalette::ToolTipBase, QColor(60, 60, 60));
    darkPalette.setColor(QPalette::ToolTipText, Qt::white);
    darkPalette.setColor(QPalette::Text, Qt::white);
    darkPalette.setColor(QPalette::Button, QColor(53, 53, 53));
    darkPalette.setColor(QPalette::ButtonText, Qt::white);
    darkPalette.setColor(QPalette::BrightText, Qt::red);
    darkPalette.setColor(QPalette::Link, QColor(42, 130, 218));
    darkPalette.setColor(QPalette::Highlight, QColor(42, 130, 218));
    darkPalette.setColor(QPalette::HighlightedText, Qt::black);
    
    app.setPalette(darkPalette);
    
    // 鐠佸墽鐤嗛崗銊ョ湰閺嶅嘲绱＄悰?
    app.setStyleSheet(R"(
        QToolTip {
            color: #ffffff;
            background-color: #2d2d30;
            border: 1px solid #3f3f46;
            border-radius: 4px;
            padding: 4px;
        }
        
        QPushButton {
            background-color: #0e639c;
            border: none;
            border-radius: 4px;
            padding: 6px 16px;
            color: white;
            font-weight: bold;
        }
        
        QPushButton:hover {
            background-color: #1177bb;
        }
        
        QPushButton:pressed {
            background-color: #0d5a8c;
        }
        
        QPushButton:disabled {
            background-color: #3d3d3d;
            color: #808080;
        }
        
        QLineEdit, QSpinBox, QComboBox {
            background-color: #3c3c3c;
            border: 1px solid #3f3f46;
            border-radius: 4px;
            padding: 4px 8px;
            color: white;
        }
        
        QLineEdit:focus, QSpinBox:focus, QComboBox:focus {
            border: 1px solid #0e639c;
        }
        
        QListWidget {
            background-color: #252526;
            border: 1px solid #3f3f46;
            border-radius: 4px;
        }
        
        QListWidget::item {
            padding: 8px;
            border-radius: 4px;
        }
        
        QListWidget::item:hover {
            background-color: #2a2d2e;
        }
        
        QListWidget::item:selected {
            background-color: #094771;
        }
        
        QScrollBar:vertical {
            background-color: #1e1e1e;
            width: 12px;
            margin: 0;
        }
        
        QScrollBar::handle:vertical {
            background-color: #5a5a5a;
            border-radius: 6px;
            min-height: 20px;
            margin: 2px;
        }
        
        QScrollBar::handle:vertical:hover {
            background-color: #787878;
        }
        
        QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
            height: 0;
        }
        
        QProgressBar {
            background-color: #3c3c3c;
            border: none;
            border-radius: 4px;
            text-align: center;
            color: white;
        }
        
        QProgressBar::chunk {
            background-color: #0e639c;
            border-radius: 4px;
        }
        
        QMenuBar {
            background-color: #2d2d30;
            border-bottom: 1px solid #3f3f46;
        }
        
        QMenuBar::item {
            padding: 6px 12px;
        }
        
        QMenuBar::item:selected {
            background-color: #3e3e42;
        }
        
        QMenu {
            background-color: #2d2d30;
            border: 1px solid #3f3f46;
        }
        
        QMenu::item {
            padding: 6px 24px;
        }
        
        QMenu::item:selected {
            background-color: #094771;
        }
        
        QStatusBar {
            background-color: #007acc;
            color: white;
        }
    )");
}

/**
 * @brief 濡偓閺岊檱DB閺勵垰鎯佺€涙ê婀?
 */
bool checkAdbExists(QString* resolvedAdbPath = nullptr)
{
    const QString adbPath = AdbProcess::resolveAdbPath();
    if (resolvedAdbPath) {
        *resolvedAdbPath = adbPath;
    }

    AdbProcess adb;
    adb.setAdbPath(adbPath);

    return adb.checkAdbVersion();
}

/**
 * @brief 娑撹鍤遍弫?
 */
int main(int argc, char *argv[])
{
    // 閸氼垳鏁ゆ妤I缂傗晜鏂?
    QApplication::setHighDpiScaleFactorRoundingPolicy(
        Qt::HighDpiScaleFactorRoundingPolicy::PassThrough);
    
    QApplication app(argc, argv);
    
    // 鐠佸墽鐤嗘惔鏃傛暏缁嬪绨穱鈩冧紖
    app.setApplicationName(APP_NAME);
    app.setApplicationVersion(APP_VERSION);
    app.setOrganizationName("QtScrcpy");
    app.setOrganizationDomain("github.com/qtscrcpy");
    
    // 閸掓繂顫愰崠鏍ㄧ壉瀵?
    initializeStyle(app);
    
    // 濡偓閺岊檱DB
    QString detectedAdbPath;
    if (!checkAdbExists(&detectedAdbPath)) {
        const QString warningText = QString(
            "未检测到 ADB。\n\n"
            "请确认以下任一条件成立：\n"
            "1. 程序同级目录存在 adb/adb.exe；\n"
            "2. 程序同级目录存在 adb.exe；\n"
            "3. 系统 PATH 中可找到 ADB。\n\n"
            "当前解析到的 ADB 路径：%1\n\n"
            "在 ADB 可用前，部分功能可能无法使用。")
            .arg(detectedAdbPath);

        QMessageBox::warning(
            nullptr,
            "警告",
            warningText);
    }
    
    // 閸掓稑缂撴稉鑽ょ崶閸?
    MainWindow mainWindow;
    mainWindow.show();
    
    return app.exec();
}

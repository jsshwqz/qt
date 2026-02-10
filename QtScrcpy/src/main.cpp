/**
 * QtScrcpy - Android Screen Mirroring Application
 * Copyright (C) 2024 QtScrcpy Contributors
 *
 * Licensed under the Apache License, Version 2.0
 */

#include <QApplication>
#include <QStyleFactory>
#include <QFile>
#include <QDir>
#include <QStandardPaths>
#include <QMessageBox>

#include "ui/mainwindow.h"
#include "adb/adbprocess.h"

// 应用程序版本
const char* APP_VERSION = "1.0.0";
const char* APP_NAME = "QtScrcpy";

/**
 * @brief 初始化应用程序样式
 */
void initializeStyle(QApplication& app)
{
    // 使用 Fusion 风格作为基础
    app.setStyle(QStyleFactory::create("Fusion"));
    
    // 设置深色主题调色板
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
    
    // 设置全局样式表
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
 * @brief 检查ADB是否存在
 */
bool checkAdbExists()
{
    QString adbPath = QCoreApplication::applicationDirPath() + "/adb/adb.exe";
    
    if (!QFile::exists(adbPath)) {
        // 尝试系统PATH中的adb
        #ifdef Q_OS_WIN
        adbPath = "adb.exe";
        #else
        adbPath = "adb";
        #endif
    }
    
    AdbProcess adb;
    adb.setAdbPath(adbPath);
    
    return adb.checkAdbVersion();
}

/**
 * @brief 主函数
 */
int main(int argc, char *argv[])
{
    // 启用高DPI缩放
    QApplication::setHighDpiScaleFactorRoundingPolicy(
        Qt::HighDpiScaleFactorRoundingPolicy::PassThrough);
    
    QApplication app(argc, argv);
    
    // 设置应用程序信息
    app.setApplicationName(APP_NAME);
    app.setApplicationVersion(APP_VERSION);
    app.setOrganizationName("QtScrcpy");
    app.setOrganizationDomain("github.com/qtscrcpy");
    
    // 初始化样式
    initializeStyle(app);
    
    // 检查ADB
    if (!checkAdbExists()) {
        QMessageBox::warning(nullptr, "警告", 
            "未检测到ADB工具。\n\n"
            "请确保以下任一条件满足：\n"
            "1. adb目录下有adb.exe\n"
            "2. ADB已添加到系统PATH环境变量\n\n"
            "部分功能可能无法正常使用。");
    }
    
    // 创建主窗口
    MainWindow mainWindow;
    mainWindow.show();
    
    return app.exec();
}

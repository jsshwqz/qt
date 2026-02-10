/**
 * QtScrcpy - Toolbar Widget
 * Copyright (C) 2024 QtScrcpy Contributors
 *
 * Licensed under the Apache License, Version 2.0
 */

#include "toolbarwidget.h"
#include <QStyle>

ToolbarWidget::ToolbarWidget(QWidget *parent)
    : QWidget(parent)
    , m_layout(new QHBoxLayout(this))
{
    setupUi();
}

ToolbarWidget::~ToolbarWidget()
{
}

void ToolbarWidget::setupUi()
{
    m_layout->setContentsMargins(4, 4, 4, 4);
    m_layout->setSpacing(4);
    
    // 创建按钮
    m_homeBtn = createButton("🏠", "Home (Ctrl+H)");
    m_backBtn = createButton("←", "返回 (Ctrl+B)");
    m_appSwitchBtn = createButton("⧉", "多任务 (Ctrl+S)");
    m_menuBtn = createButton("☰", "菜单 (Ctrl+M)");
    
    m_layout->addWidget(m_homeBtn);
    m_layout->addWidget(m_backBtn);
    m_layout->addWidget(m_appSwitchBtn);
    m_layout->addWidget(m_menuBtn);
    
    // 分隔符
    QFrame* sep1 = new QFrame(this);
    sep1->setFrameShape(QFrame::VLine);
    sep1->setStyleSheet("color: #3f3f46;");
    m_layout->addWidget(sep1);
    
    m_powerBtn = createButton("⏻", "电源 (Ctrl+P)");
    m_volumeUpBtn = createButton("🔊", "音量+ (Ctrl+↑)");
    m_volumeDownBtn = createButton("🔉", "音量- (Ctrl+↓)");
    
    m_layout->addWidget(m_powerBtn);
    m_layout->addWidget(m_volumeUpBtn);
    m_layout->addWidget(m_volumeDownBtn);
    
    // 分隔符
    QFrame* sep2 = new QFrame(this);
    sep2->setFrameShape(QFrame::VLine);
    sep2->setStyleSheet("color: #3f3f46;");
    m_layout->addWidget(sep2);
    
    m_notificationBtn = createButton("🔔", "通知栏 (Ctrl+N)");
    m_settingsBtn = createButton("⚙️", "快捷设置 (Ctrl+Shift+N)");
    
    m_layout->addWidget(m_notificationBtn);
    m_layout->addWidget(m_settingsBtn);
    
    // 分隔符
    QFrame* sep3 = new QFrame(this);
    sep3->setFrameShape(QFrame::VLine);
    sep3->setStyleSheet("color: #3f3f46;");
    m_layout->addWidget(sep3);
    
    m_fullscreenBtn = createButton("⛶", "全屏 (F11)");
    m_screenshotBtn = createButton("📷", "截图");
    m_rotateBtn = createButton("🔄", "旋转");
    
    m_layout->addWidget(m_fullscreenBtn);
    m_layout->addWidget(m_screenshotBtn);
    m_layout->addWidget(m_rotateBtn);
    
    m_layout->addStretch();
    
    // 连接信号
    connect(m_homeBtn, &QPushButton::clicked, this, &ToolbarWidget::homeClicked);
    connect(m_backBtn, &QPushButton::clicked, this, &ToolbarWidget::backClicked);
    connect(m_appSwitchBtn, &QPushButton::clicked, this, &ToolbarWidget::appSwitchClicked);
    connect(m_menuBtn, &QPushButton::clicked, this, &ToolbarWidget::menuClicked);
    connect(m_powerBtn, &QPushButton::clicked, this, &ToolbarWidget::powerClicked);
    connect(m_volumeUpBtn, &QPushButton::clicked, this, &ToolbarWidget::volumeUpClicked);
    connect(m_volumeDownBtn, &QPushButton::clicked, this, &ToolbarWidget::volumeDownClicked);
    connect(m_notificationBtn, &QPushButton::clicked, this, &ToolbarWidget::expandNotificationsClicked);
    connect(m_settingsBtn, &QPushButton::clicked, this, &ToolbarWidget::expandSettingsClicked);
    connect(m_fullscreenBtn, &QPushButton::clicked, this, &ToolbarWidget::fullscreenClicked);
    connect(m_screenshotBtn, &QPushButton::clicked, this, &ToolbarWidget::screenshotClicked);
    connect(m_rotateBtn, &QPushButton::clicked, this, &ToolbarWidget::rotateClicked);
    
    // 初始状态
    setConnected(false);
}

QPushButton* ToolbarWidget::createButton(const QString& icon, const QString& tooltip)
{
    QPushButton* btn = new QPushButton(icon, this);
    btn->setToolTip(tooltip);
    btn->setFixedSize(36, 36);
    btn->setStyleSheet(R"(
        QPushButton {
            background-color: #3c3c3c;
            border: 1px solid #3f3f46;
            border-radius: 4px;
            font-size: 16px;
        }
        QPushButton:hover {
            background-color: #4a4a4a;
            border-color: #0e639c;
        }
        QPushButton:pressed {
            background-color: #2d2d2d;
        }
        QPushButton:disabled {
            background-color: #2d2d2d;
            color: #666666;
        }
    )");
    
    return btn;
}

void ToolbarWidget::setConnected(bool connected)
{
    m_homeBtn->setEnabled(connected);
    m_backBtn->setEnabled(connected);
    m_appSwitchBtn->setEnabled(connected);
    m_menuBtn->setEnabled(connected);
    m_powerBtn->setEnabled(connected);
    m_volumeUpBtn->setEnabled(connected);
    m_volumeDownBtn->setEnabled(connected);
    m_notificationBtn->setEnabled(connected);
    m_settingsBtn->setEnabled(connected);
    m_fullscreenBtn->setEnabled(connected);
    m_screenshotBtn->setEnabled(connected);
    m_rotateBtn->setEnabled(connected);
}

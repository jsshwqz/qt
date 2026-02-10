/**
 * QtScrcpy - Toolbar Widget
 * Copyright (C) 2024 QtScrcpy Contributors
 *
 * Licensed under the Apache License, Version 2.0
 */

#include "toolbarwidget.h"

#include <QFrame>

ToolbarWidget::ToolbarWidget(QWidget *parent)
    : QWidget(parent)
    , m_layout(new QHBoxLayout(this))
    , m_homeBtn(nullptr)
    , m_backBtn(nullptr)
    , m_appSwitchBtn(nullptr)
    , m_menuBtn(nullptr)
    , m_powerBtn(nullptr)
    , m_volumeUpBtn(nullptr)
    , m_volumeDownBtn(nullptr)
    , m_notificationBtn(nullptr)
    , m_settingsBtn(nullptr)
    , m_fullscreenBtn(nullptr)
    , m_screenshotBtn(nullptr)
    , m_rotateBtn(nullptr)
{
    setupUi();
}

ToolbarWidget::~ToolbarWidget()
{
}

QPushButton* ToolbarWidget::createButton(const QString& icon, const QString& tooltip)
{
    QPushButton* btn = new QPushButton(icon, this);
    btn->setToolTip(tooltip);
    btn->setFixedHeight(34);
    btn->setMinimumWidth(40);
    btn->setStyleSheet(R"(
        QPushButton {
            background-color: #3c3c3c;
            border: 1px solid #4a4a4a;
            border-radius: 4px;
            padding: 4px 10px;
            color: white;
        }
        QPushButton:hover {
            background-color: #4a4a4a;
        }
        QPushButton:pressed {
            background-color: #2d2d2d;
        }
        QPushButton:disabled {
            background-color: #2d2d2d;
            color: #808080;
            border-color: #3a3a3a;
        }
    )");
    return btn;
}

void ToolbarWidget::setupUi()
{
    m_layout->setContentsMargins(8, 6, 8, 6);
    m_layout->setSpacing(6);

    m_homeBtn = createButton("Home", "Home (Ctrl+H)");
    m_backBtn = createButton("Back", "Back (Ctrl+B)");
    m_appSwitchBtn = createButton("Recent", "Recent Apps (Ctrl+S)");
    m_menuBtn = createButton("Menu", "Menu (Ctrl+M)");
    m_layout->addWidget(m_homeBtn);
    m_layout->addWidget(m_backBtn);
    m_layout->addWidget(m_appSwitchBtn);
    m_layout->addWidget(m_menuBtn);

    QFrame* sep1 = new QFrame(this);
    sep1->setFrameShape(QFrame::VLine);
    sep1->setStyleSheet("color: #555;");
    m_layout->addWidget(sep1);

    m_powerBtn = createButton("Power", "Power (Ctrl+P)");
    m_volumeUpBtn = createButton("Vol+", "Volume Up (Ctrl+Up)");
    m_volumeDownBtn = createButton("Vol-", "Volume Down (Ctrl+Down)");
    m_layout->addWidget(m_powerBtn);
    m_layout->addWidget(m_volumeUpBtn);
    m_layout->addWidget(m_volumeDownBtn);

    QFrame* sep2 = new QFrame(this);
    sep2->setFrameShape(QFrame::VLine);
    sep2->setStyleSheet("color: #555;");
    m_layout->addWidget(sep2);

    m_notificationBtn = createButton("Notif", "Notifications (Ctrl+N)");
    m_settingsBtn = createButton("Quick", "Quick Settings (Ctrl+Shift+N)");
    m_layout->addWidget(m_notificationBtn);
    m_layout->addWidget(m_settingsBtn);

    QFrame* sep3 = new QFrame(this);
    sep3->setFrameShape(QFrame::VLine);
    sep3->setStyleSheet("color: #555;");
    m_layout->addWidget(sep3);

    m_fullscreenBtn = createButton("Full", "Fullscreen (F11)");
    m_screenshotBtn = createButton("Shot", "Screenshot");
    m_rotateBtn = createButton("Rotate", "Rotate");
    m_layout->addWidget(m_fullscreenBtn);
    m_layout->addWidget(m_screenshotBtn);
    m_layout->addWidget(m_rotateBtn);

    m_layout->addStretch();

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

    setConnected(false);
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


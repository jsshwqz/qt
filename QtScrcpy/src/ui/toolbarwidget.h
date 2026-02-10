/**
 * QtScrcpy - Toolbar Widget
 * Copyright (C) 2024 QtScrcpy Contributors
 *
 * Licensed under the Apache License, Version 2.0
 */

#ifndef TOOLBARWIDGET_H
#define TOOLBARWIDGET_H

#include <QWidget>
#include <QPushButton>
#include <QHBoxLayout>

/**
 * @brief 工具栏部件
 * 
 * 提供快捷操作按钮
 */
class ToolbarWidget : public QWidget
{
    Q_OBJECT

public:
    explicit ToolbarWidget(QWidget *parent = nullptr);
    ~ToolbarWidget();

    /**
     * @brief 设置连接状态
     */
    void setConnected(bool connected);

signals:
    // 导航按钮
    void homeClicked();
    void backClicked();
    void appSwitchClicked();
    void menuClicked();
    
    // 电源和音量
    void powerClicked();
    void volumeUpClicked();
    void volumeDownClicked();
    
    // 通知栏
    void expandNotificationsClicked();
    void expandSettingsClicked();
    
    // 屏幕控制
    void fullscreenClicked();
    void screenshotClicked();
    void rotateClicked();

private:
    void setupUi();
    QPushButton* createButton(const QString& icon, const QString& tooltip);
    
    QHBoxLayout* m_layout;
    
    QPushButton* m_homeBtn;
    QPushButton* m_backBtn;
    QPushButton* m_appSwitchBtn;
    QPushButton* m_menuBtn;
    QPushButton* m_powerBtn;
    QPushButton* m_volumeUpBtn;
    QPushButton* m_volumeDownBtn;
    QPushButton* m_notificationBtn;
    QPushButton* m_settingsBtn;
    QPushButton* m_fullscreenBtn;
    QPushButton* m_screenshotBtn;
    QPushButton* m_rotateBtn;
};

#endif // TOOLBARWIDGET_H

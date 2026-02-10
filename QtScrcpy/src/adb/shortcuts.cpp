/**
 * QtScrcpy - Shortcut Commands
 * Copyright (C) 2024 QtScrcpy Contributors
 *
 * Licensed under the Apache License, Version 2.0
 */

#include "shortcuts.h"
#include "adbprocess.h"
#include <QDebug>

Shortcuts::Shortcuts(const QString& serial, QObject *parent)
    : QObject(parent)
    , m_serial(serial)
    , m_adb(new AdbProcess(this))
{
    connect(m_adb, &AdbProcess::commandFinished, this, [this](const AdbProcess::AdbResult& result) {
        emit commandFinished(result.success, result.output);
        if (!result.success) {
            emit commandError(result.error);
        }
    });
}

Shortcuts::~Shortcuts()
{
}

void Shortcuts::executeShellCommand(const QString& command)
{
    m_adb->shell(m_serial, command);
}

void Shortcuts::executeShellCommandAsync(const QString& command)
{
    m_adb->shellAsync(m_serial, command);
}

// 系统导航键
void Shortcuts::pressHome()
{
    pressKeyCode(AndroidKeyCode::KEYCODE_HOME);
}

void Shortcuts::pressBack()
{
    pressKeyCode(AndroidKeyCode::KEYCODE_BACK);
}

void Shortcuts::pressAppSwitch()
{
    pressKeyCode(AndroidKeyCode::KEYCODE_APP_SWITCH);
}

void Shortcuts::pressMenu()
{
    pressKeyCode(AndroidKeyCode::KEYCODE_MENU);
}

void Shortcuts::pressPower()
{
    pressKeyCode(AndroidKeyCode::KEYCODE_POWER);
}

// 音量控制
void Shortcuts::volumeUp()
{
    pressKeyCode(AndroidKeyCode::KEYCODE_VOLUME_UP);
}

void Shortcuts::volumeDown()
{
    pressKeyCode(AndroidKeyCode::KEYCODE_VOLUME_DOWN);
}

void Shortcuts::volumeMute()
{
    pressKeyCode(AndroidKeyCode::KEYCODE_VOLUME_MUTE);
}

// 通知栏控制
void Shortcuts::expandNotifications()
{
    executeShellCommandAsync("cmd statusbar expand-notifications");
}

void Shortcuts::expandQuickSettings()
{
    executeShellCommandAsync("cmd statusbar expand-settings");
}

void Shortcuts::collapseStatusBar()
{
    executeShellCommandAsync("cmd statusbar collapse");
}

// 屏幕控制
void Shortcuts::rotateScreen()
{
    // 获取当前旋转状态并切换
    auto result = m_adb->shell(m_serial, "settings get system user_rotation");
    int currentRotation = result.output.trimmed().toInt();
    int newRotation = (currentRotation + 1) % 4;
    executeShellCommandAsync(QString("settings put system user_rotation %1").arg(newRotation));
}

void Shortcuts::turnScreenOn()
{
    // 检查屏幕状态
    auto result = m_adb->shell(m_serial, "dumpsys power | grep 'Display Power: state='");
    if (result.output.contains("OFF")) {
        pressKeyCode(AndroidKeyCode::KEYCODE_POWER);
    }
}

void Shortcuts::turnScreenOff()
{
    auto result = m_adb->shell(m_serial, "dumpsys power | grep 'Display Power: state='");
    if (result.output.contains("ON")) {
        pressKeyCode(AndroidKeyCode::KEYCODE_POWER);
    }
}

// 其他快捷操作
void Shortcuts::takeScreenshot()
{
    executeShellCommandAsync("input keyevent KEYCODE_SYSRQ");
}

void Shortcuts::openCamera()
{
    pressKeyCode(AndroidKeyCode::KEYCODE_CAMERA);
}

void Shortcuts::lockScreen()
{
    executeShellCommandAsync("input keyevent KEYCODE_SLEEP");
}

// 通用按键
void Shortcuts::pressKeyCode(int keyCode)
{
    executeShellCommandAsync(QString("input keyevent %1").arg(keyCode));
}

// 模拟输入
void Shortcuts::inputText(const QString& text)
{
    // 转义特殊字符
    QString escapedText = text;
    escapedText.replace("\\", "\\\\");
    escapedText.replace("\"", "\\\"");
    escapedText.replace("'", "\\'");
    escapedText.replace(" ", "%s");
    escapedText.replace("&", "\\&");
    escapedText.replace("<", "\\<");
    escapedText.replace(">", "\\>");
    escapedText.replace("|", "\\|");
    escapedText.replace(";", "\\;");
    escapedText.replace("(", "\\(");
    escapedText.replace(")", "\\)");
    
    executeShellCommandAsync(QString("input text \"%1\"").arg(escapedText));
}

void Shortcuts::inputSwipe(int x1, int y1, int x2, int y2, int durationMs)
{
    executeShellCommandAsync(QString("input swipe %1 %2 %3 %4 %5")
        .arg(x1).arg(y1).arg(x2).arg(y2).arg(durationMs));
}

void Shortcuts::inputTap(int x, int y)
{
    executeShellCommandAsync(QString("input tap %1 %2").arg(x).arg(y));
}

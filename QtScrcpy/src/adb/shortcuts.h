/**
 * QtScrcpy - Shortcut Commands
 * Copyright (C) 2024 QtScrcpy Contributors
 *
 * Licensed under the Apache License, Version 2.0
 */

#ifndef SHORTCUTS_H
#define SHORTCUTS_H

#include <QObject>
#include <QString>

class AdbProcess;

/**
 * @brief 快捷操作类
 * 
 * 提供Android设备的快捷操作功能
 */
class Shortcuts : public QObject
{
    Q_OBJECT

public:
    explicit Shortcuts(const QString& serial, QObject *parent = nullptr);
    ~Shortcuts();

    /**
     * @brief 设置设备序列号
     */
    void setSerial(const QString& serial) { m_serial = serial; }

    // 系统导航键
    void pressHome();
    void pressBack();
    void pressAppSwitch();     // 多任务
    void pressMenu();
    void pressPower();
    
    // 音量控制
    void volumeUp();
    void volumeDown();
    void volumeMute();
    
    // 通知栏控制
    void expandNotifications();
    void expandQuickSettings();
    void collapseStatusBar();
    
    // 屏幕控制
    void rotateScreen();
    void turnScreenOn();
    void turnScreenOff();
    
    // 其他快捷操作
    void takeScreenshot();
    void openCamera();
    void lockScreen();
    
    // 通用按键
    void pressKeyCode(int keyCode);
    
    // 模拟输入
    void inputText(const QString& text);
    void inputSwipe(int x1, int y1, int x2, int y2, int durationMs = 300);
    void inputTap(int x, int y);

signals:
    /**
     * @brief 命令执行完成信号
     */
    void commandFinished(bool success, const QString& output);
    
    /**
     * @brief 命令执行错误信号
     */
    void commandError(const QString& error);

private:
    void executeShellCommand(const QString& command);
    void executeShellCommandAsync(const QString& command);
    
    QString m_serial;
    AdbProcess* m_adb;
};

// Android KeyCode 常量
namespace AndroidKeyCode {
    constexpr int KEYCODE_UNKNOWN = 0;
    constexpr int KEYCODE_SOFT_LEFT = 1;
    constexpr int KEYCODE_SOFT_RIGHT = 2;
    constexpr int KEYCODE_HOME = 3;
    constexpr int KEYCODE_BACK = 4;
    constexpr int KEYCODE_CALL = 5;
    constexpr int KEYCODE_ENDCALL = 6;
    constexpr int KEYCODE_0 = 7;
    constexpr int KEYCODE_1 = 8;
    constexpr int KEYCODE_2 = 9;
    constexpr int KEYCODE_3 = 10;
    constexpr int KEYCODE_4 = 11;
    constexpr int KEYCODE_5 = 12;
    constexpr int KEYCODE_6 = 13;
    constexpr int KEYCODE_7 = 14;
    constexpr int KEYCODE_8 = 15;
    constexpr int KEYCODE_9 = 16;
    constexpr int KEYCODE_STAR = 17;
    constexpr int KEYCODE_POUND = 18;
    constexpr int KEYCODE_DPAD_UP = 19;
    constexpr int KEYCODE_DPAD_DOWN = 20;
    constexpr int KEYCODE_DPAD_LEFT = 21;
    constexpr int KEYCODE_DPAD_RIGHT = 22;
    constexpr int KEYCODE_DPAD_CENTER = 23;
    constexpr int KEYCODE_VOLUME_UP = 24;
    constexpr int KEYCODE_VOLUME_DOWN = 25;
    constexpr int KEYCODE_POWER = 26;
    constexpr int KEYCODE_CAMERA = 27;
    constexpr int KEYCODE_CLEAR = 28;
    constexpr int KEYCODE_ENTER = 66;
    constexpr int KEYCODE_DEL = 67;
    constexpr int KEYCODE_MENU = 82;
    constexpr int KEYCODE_SEARCH = 84;
    constexpr int KEYCODE_MEDIA_PLAY_PAUSE = 85;
    constexpr int KEYCODE_MEDIA_STOP = 86;
    constexpr int KEYCODE_MEDIA_NEXT = 87;
    constexpr int KEYCODE_MEDIA_PREVIOUS = 88;
    constexpr int KEYCODE_VOLUME_MUTE = 164;
    constexpr int KEYCODE_APP_SWITCH = 187;
    constexpr int KEYCODE_SCREENSHOT = 120;
}

#endif // SHORTCUTS_H

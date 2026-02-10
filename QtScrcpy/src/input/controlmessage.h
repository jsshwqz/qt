/**
 * QtScrcpy - Control Message
 * Copyright (C) 2024 QtScrcpy Contributors
 *
 * Licensed under the Apache License, Version 2.0
 */

#ifndef CONTROLMESSAGE_H
#define CONTROLMESSAGE_H

#include <QByteArray>
#include <QString>
#include <QPointF>
#include <QSizeF>

/**
 * @brief 控制消息类型
 */
enum class ControlMessageType : quint8 {
    InjectKeycode = 0,
    InjectText = 1,
    InjectTouch = 2,
    InjectScroll = 3,
    BackOrScreenOn = 4,
    ExpandNotificationPanel = 5,
    ExpandSettingsPanel = 6,
    CollapsePanels = 7,
    GetClipboard = 8,
    SetClipboard = 9,
    SetScreenPowerMode = 10,
    RotateDevice = 11,
    UhidCreate = 12,
    UhidInput = 13,
    OpenHardKeyboardSettings = 14
};

/**
 * @brief Android按键动作
 */
enum class AndroidKeyAction : quint8 {
    Down = 0,
    Up = 1
};

/**
 * @brief Android触摸动作
 */
enum class AndroidMotionAction : quint8 {
    Down = 0,
    Up = 1,
    Move = 2,
    Cancel = 3,
    OutSide = 4,
    PointerDown = 5,
    PointerUp = 6,
    HoverMove = 7,
    Scroll = 8,
    HoverEnter = 9,
    HoverExit = 10,
    ButtonPress = 11,
    ButtonRelease = 12
};

/**
 * @brief 屏幕电源模式
 */
enum class ScreenPowerMode : quint8 {
    Off = 0,
    Normal = 2
};

/**
 * @brief 复制键
 */
enum class CopyKey : quint8 {
    None = 0,
    Copy = 1,
    Cut = 2
};

/**
 * @brief 控制消息结构
 */
struct ControlMessage {
    ControlMessageType type;
    
    // 按键码注入
    struct InjectKeycode {
        AndroidKeyAction action;
        int keycode;
        int repeat;
        int metaState;
    } injectKeycode;
    
    // 文本注入
    struct InjectText {
        QString text;
    } injectText;
    
    // 触摸注入
    struct InjectTouch {
        AndroidMotionAction action;
        qint64 pointerId;
        QPointF position;
        QSizeF screenSize;
        float pressure;
        int buttons;
    } injectTouch;
    
    // 滚动注入
    struct InjectScroll {
        QPointF position;
        QSizeF screenSize;
        float hScroll;
        float vScroll;
    } injectScroll;
    
    // 返回或点亮屏幕
    struct BackOrScreenOn {
        AndroidKeyAction action;
    } backOrScreenOn;
    
    // 获取剪贴板
    struct GetClipboard {
        CopyKey copyKey;
    } getClipboard;
    
    // 设置剪贴板
    struct SetClipboard {
        qint64 sequence;
        QString text;
        bool paste;
    } setClipboard;
    
    // 设置屏幕电源模式
    struct SetScreenPowerMode {
        ScreenPowerMode mode;
    } setScreenPowerMode;
    
    /**
     * @brief 序列化为字节数组
     */
    QByteArray serialize() const;
    
    /**
     * @brief 从字节数组反序列化
     */
    static ControlMessage deserialize(const QByteArray& data);
};

#endif // CONTROLMESSAGE_H

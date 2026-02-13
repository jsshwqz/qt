/**
 * QtScrcpy - Input Handler
 * Copyright (C) 2024 QtScrcpy Contributors
 *
 * Licensed under the Apache License, Version 2.0
 */

#ifndef INPUTHANDLER_H
#define INPUTHANDLER_H

#include <QObject>
#include <QMouseEvent>
#include <QKeyEvent>
#include <QWheelEvent>
#include <QPointF>
#include <QSizeF>
#include <QMap>

#include "controlmessage.h"

class ControlStream;

/**
 * @brief 输入事件处理器
 * 
 * 将Qt输入事件转换为Android控制消息
 */
class InputHandler : public QObject
{
    Q_OBJECT

public:
    explicit InputHandler(QObject *parent = nullptr);
    ~InputHandler();

    /**
     * @brief 设置控制流
     */
    void setControlStream(ControlStream* stream);

    /**
     * @brief 设置设备屏幕尺寸
     */
    void setDeviceScreenSize(const QSize& size);

    /**
     * @brief 设置视频显示尺寸
     */
    void setVideoDisplaySize(const QSize& size);

    /**
     * @brief 处理鼠标按下事件
     */
    void handleMousePress(QMouseEvent* event);

    /**
     * @brief 处理鼠标释放事件
     */
    void handleMouseRelease(QMouseEvent* event);

    /**
     * @brief 处理鼠标移动事件
     */
    void handleMouseMove(QMouseEvent* event);

    /**
     * @brief 处理滚轮事件
     */
    void handleWheel(QWheelEvent* event);

    /**
     * @brief 处理按键按下事件
     */
    void handleKeyPress(QKeyEvent* event);

    /**
     * @brief 处理按键释放事件
     */
    void handleKeyRelease(QKeyEvent* event);

    /**
     * @brief 处理文本输入
     */
    void handleTextInput(const QString& text);

    /**
     * @brief 启用/禁用输入
     */
    void setEnabled(bool enabled) { m_enabled = enabled; }

    /**
     * @brief 是否启用
     */
    bool isEnabled() const { return m_enabled; }

signals:
    /**
     * @brief 控制消息生成信号
     */
    void controlMessageGenerated(const ControlMessage& message);

    /**
     * @brief 快捷键触发信号
     */
    void shortcutTriggered(const QString& action);

    void unicodeTextInputRequested(const QString& text);

private:
    QPointF convertPosition(const QPoint& pos) const;
    int convertMouseButton(Qt::MouseButton button) const;
    int convertMouseButtons(Qt::MouseButtons buttons) const;
    int convertKeyCode(int qtKey) const;
    int convertMetaState(Qt::KeyboardModifiers modifiers) const;
    bool handleShortcut(QKeyEvent* event);
    
    ControlStream* m_controlStream;
    QSize m_deviceScreenSize;
    QSize m_videoDisplaySize;
    bool m_enabled;
    
    // 触摸追踪
    bool m_mousePressed;
    QPointF m_lastMousePos;
    qint64 m_pointerId;
    
    // 按键映射
    static QMap<int, int> s_keyMap;
    static bool s_keyMapInitialized;
    static void initKeyMap();
};

#endif // INPUTHANDLER_H

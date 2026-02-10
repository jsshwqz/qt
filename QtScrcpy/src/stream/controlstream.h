/**
 * QtScrcpy - Control Stream
 * Copyright (C) 2024 QtScrcpy Contributors
 *
 * Licensed under the Apache License, Version 2.0
 */

#ifndef CONTROLSTREAM_H
#define CONTROLSTREAM_H

#include <QObject>
#include <QTcpSocket>
#include <QByteArray>

#include "input/controlmessage.h"

/**
 * @brief 控制流类
 * 
 * 用于发送控制命令到scrcpy服务端
 */
class ControlStream : public QObject
{
    Q_OBJECT

public:
    explicit ControlStream(QObject *parent = nullptr);
    ~ControlStream();

    /**
     * @brief 连接到控制通道
     */
    bool connectToHost(const QString& host, quint16 port);

    /**
     * @brief 断开连接
     */
    void disconnect();

    /**
     * @brief 是否已连接
     */
    bool isConnected() const;

    /**
     * @brief 发送控制消息
     */
    bool sendMessage(const ControlMessage& message);

    /**
     * @brief 发送原始数据
     */
    bool sendRawData(const QByteArray& data);

    // 便捷方法
    bool sendKeycode(int action, int keycode, int repeat, int metaState);
    bool sendText(const QString& text);
    bool sendTouch(int action, qint64 pointerId, const QPointF& position, 
                   const QSizeF& screenSize, float pressure, int buttons);
    bool sendScroll(const QPointF& position, const QSizeF& screenSize, 
                    float hScroll, float vScroll);
    bool sendBackOrScreenOn(int action);
    bool expandNotificationPanel();
    bool expandSettingsPanel();
    bool collapsePanel();
    bool getClipboard(int copyKey);
    bool setClipboard(qint64 sequence, const QString& text, bool paste);
    bool setScreenPowerMode(int mode);
    bool rotateDevice();

signals:
    /**
     * @brief 连接成功
     */
    void connected();

    /**
     * @brief 断开连接
     */
    void disconnected();

    /**
     * @brief 接收到剪贴板数据
     */
    void clipboardReceived(const QString& text);

    /**
     * @brief ACK接收信号
     */
    void ackReceived(qint64 sequence);

    /**
     * @brief 错误信号
     */
    void error(const QString& message);

private slots:
    void onConnected();
    void onDisconnected();
    void onReadyRead();
    void onError(QAbstractSocket::SocketError error);

private:
    void processDeviceMessage();
    
    QTcpSocket* m_socket;
    QByteArray m_readBuffer;
};

#endif // CONTROLSTREAM_H

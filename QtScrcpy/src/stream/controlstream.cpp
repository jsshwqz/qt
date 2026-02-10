/**
 * QtScrcpy - Control Stream
 * Copyright (C) 2024 QtScrcpy Contributors
 *
 * Licensed under the Apache License, Version 2.0
 */

#include "controlstream.h"
#include <QDebug>
#include <QtEndian>

ControlStream::ControlStream(QObject *parent)
    : QObject(parent)
    , m_socket(new QTcpSocket(this))
{
    connect(m_socket, &QTcpSocket::connected, this, &ControlStream::onConnected);
    connect(m_socket, &QTcpSocket::disconnected, this, &ControlStream::onDisconnected);
    connect(m_socket, &QTcpSocket::readyRead, this, &ControlStream::onReadyRead);
    connect(m_socket, &QTcpSocket::errorOccurred, this, &ControlStream::onError);
}

ControlStream::~ControlStream()
{
    disconnect();
}

bool ControlStream::connectToHost(const QString& host, quint16 port)
{
    if (m_socket->state() != QAbstractSocket::UnconnectedState) {
        return false;
    }
    
    m_readBuffer.clear();
    m_socket->connectToHost(host, port);
    
    return m_socket->waitForConnected(5000);
}

void ControlStream::disconnect()
{
    if (m_socket->state() != QAbstractSocket::UnconnectedState) {
        m_socket->disconnectFromHost();
    }
}

bool ControlStream::isConnected() const
{
    return m_socket->state() == QAbstractSocket::ConnectedState;
}

bool ControlStream::sendMessage(const ControlMessage& message)
{
    if (!isConnected()) {
        return false;
    }
    
    QByteArray data = message.serialize();
    return m_socket->write(data) == data.size();
}

bool ControlStream::sendRawData(const QByteArray& data)
{
    if (!isConnected()) {
        return false;
    }
    
    return m_socket->write(data) == data.size();
}

bool ControlStream::sendKeycode(int action, int keycode, int repeat, int metaState)
{
    ControlMessage msg;
    msg.type = ControlMessageType::InjectKeycode;
    msg.injectKeycode.action = static_cast<AndroidKeyAction>(action);
    msg.injectKeycode.keycode = keycode;
    msg.injectKeycode.repeat = repeat;
    msg.injectKeycode.metaState = metaState;
    
    return sendMessage(msg);
}

bool ControlStream::sendText(const QString& text)
{
    ControlMessage msg;
    msg.type = ControlMessageType::InjectText;
    msg.injectText.text = text;
    
    return sendMessage(msg);
}

bool ControlStream::sendTouch(int action, qint64 pointerId, const QPointF& position,
                              const QSizeF& screenSize, float pressure, int buttons)
{
    ControlMessage msg;
    msg.type = ControlMessageType::InjectTouch;
    msg.injectTouch.action = static_cast<AndroidMotionAction>(action);
    msg.injectTouch.pointerId = pointerId;
    msg.injectTouch.position = position;
    msg.injectTouch.screenSize = screenSize;
    msg.injectTouch.pressure = pressure;
    msg.injectTouch.buttons = buttons;
    
    return sendMessage(msg);
}

bool ControlStream::sendScroll(const QPointF& position, const QSizeF& screenSize,
                               float hScroll, float vScroll)
{
    ControlMessage msg;
    msg.type = ControlMessageType::InjectScroll;
    msg.injectScroll.position = position;
    msg.injectScroll.screenSize = screenSize;
    msg.injectScroll.hScroll = hScroll;
    msg.injectScroll.vScroll = vScroll;
    
    return sendMessage(msg);
}

bool ControlStream::sendBackOrScreenOn(int action)
{
    ControlMessage msg;
    msg.type = ControlMessageType::BackOrScreenOn;
    msg.backOrScreenOn.action = static_cast<AndroidKeyAction>(action);
    
    return sendMessage(msg);
}

bool ControlStream::expandNotificationPanel()
{
    ControlMessage msg;
    msg.type = ControlMessageType::ExpandNotificationPanel;
    return sendMessage(msg);
}

bool ControlStream::expandSettingsPanel()
{
    ControlMessage msg;
    msg.type = ControlMessageType::ExpandSettingsPanel;
    return sendMessage(msg);
}

bool ControlStream::collapsePanel()
{
    ControlMessage msg;
    msg.type = ControlMessageType::CollapsePanels;
    return sendMessage(msg);
}

bool ControlStream::getClipboard(int copyKey)
{
    ControlMessage msg;
    msg.type = ControlMessageType::GetClipboard;
    msg.getClipboard.copyKey = static_cast<CopyKey>(copyKey);
    
    return sendMessage(msg);
}

bool ControlStream::setClipboard(qint64 sequence, const QString& text, bool paste)
{
    ControlMessage msg;
    msg.type = ControlMessageType::SetClipboard;
    msg.setClipboard.sequence = sequence;
    msg.setClipboard.text = text;
    msg.setClipboard.paste = paste;
    
    return sendMessage(msg);
}

bool ControlStream::setScreenPowerMode(int mode)
{
    ControlMessage msg;
    msg.type = ControlMessageType::SetScreenPowerMode;
    msg.setScreenPowerMode.mode = static_cast<ScreenPowerMode>(mode);
    
    return sendMessage(msg);
}

bool ControlStream::rotateDevice()
{
    ControlMessage msg;
    msg.type = ControlMessageType::RotateDevice;
    return sendMessage(msg);
}

void ControlStream::onConnected()
{
    qDebug() << "Control stream connected";
    emit connected();
}

void ControlStream::onDisconnected()
{
    qDebug() << "Control stream disconnected";
    emit disconnected();
}

void ControlStream::onReadyRead()
{
    m_readBuffer.append(m_socket->readAll());
    processDeviceMessage();
}

void ControlStream::processDeviceMessage()
{
    // 设备消息格式:
    // - 类型 (1 byte)
    // - 具体数据
    
    while (m_readBuffer.size() >= 1) {
        quint8 type = static_cast<quint8>(m_readBuffer[0]);
        
        switch (type) {
            case 0: { // 剪贴板
                // 格式: type(1) + length(4) + data
                if (m_readBuffer.size() < 5) {
                    return;
                }
                
                quint32 length = qFromBigEndian<quint32>(
                    reinterpret_cast<const uchar*>(m_readBuffer.constData() + 1));
                
                if (m_readBuffer.size() < static_cast<int>(5 + length)) {
                    return;
                }
                
                QString text = QString::fromUtf8(m_readBuffer.mid(5, length));
                m_readBuffer.remove(0, 5 + length);
                
                emit clipboardReceived(text);
                break;
            }
            
            case 1: { // ACK
                // 格式: type(1) + sequence(8)
                if (m_readBuffer.size() < 9) {
                    return;
                }
                
                qint64 sequence = qFromBigEndian<qint64>(
                    reinterpret_cast<const uchar*>(m_readBuffer.constData() + 1));
                m_readBuffer.remove(0, 9);
                
                emit ackReceived(sequence);
                break;
            }
            
            default:
                qWarning() << "Unknown device message type:" << type;
                m_readBuffer.clear();
                return;
        }
    }
}

void ControlStream::onError(QAbstractSocket::SocketError error)
{
    Q_UNUSED(error)
    qDebug() << "Control stream error:" << m_socket->errorString();
    emit this->error(m_socket->errorString());
}

/**
 * QtScrcpy - Control Message
 * Copyright (C) 2024 QtScrcpy Contributors
 *
 * Licensed under the Apache License, Version 2.0
 */

#include "controlmessage.h"
#include <QtEndian>
#include <QDataStream>
#include <QDebug>
#include <algorithm>

// 辅助函数：写入大端字节
static void writeBE16(QByteArray& buffer, quint16 value) {
    char bytes[2];
    qToBigEndian(value, bytes);
    buffer.append(bytes, 2);
}

static void writeBE32(QByteArray& buffer, quint32 value) {
    char bytes[4];
    qToBigEndian(value, bytes);
    buffer.append(bytes, 4);
}

static void writeBE64(QByteArray& buffer, quint64 value) {
    char bytes[8];
    qToBigEndian(value, bytes);
    buffer.append(bytes, 8);
}

// 将浮点坐标转换为定点表示
static quint16 toFixedPoint16(float value) {
    return static_cast<quint16>(value * 65535.0f);
}

static qint16 toSignedFixedPoint16(float value) {
    const float clamped = std::max(-1.0f, std::min(1.0f, value));
    return static_cast<qint16>(clamped * 32767.0f);
}

QByteArray ControlMessage::serialize() const
{
    QByteArray buffer;
    
    // 写入类型
    buffer.append(static_cast<char>(type));
    
    switch (type) {
        case ControlMessageType::InjectKeycode: {
            buffer.append(static_cast<char>(injectKeycode.action));
            writeBE32(buffer, static_cast<quint32>(injectKeycode.keycode));
            writeBE32(buffer, static_cast<quint32>(injectKeycode.repeat));
            writeBE32(buffer, static_cast<quint32>(injectKeycode.metaState));
            break;
        }
        
        case ControlMessageType::InjectText: {
            QByteArray textBytes = injectText.text.toUtf8();
            writeBE32(buffer, static_cast<quint32>(textBytes.size()));
            buffer.append(textBytes);
            break;
        }
        
        case ControlMessageType::InjectTouch: {
            buffer.append(static_cast<char>(injectTouch.action));
            writeBE64(buffer, static_cast<quint64>(injectTouch.pointerId));
            
            // 位置
            quint32 x = static_cast<quint32>(injectTouch.position.x());
            quint32 y = static_cast<quint32>(injectTouch.position.y());
            writeBE32(buffer, x);
            writeBE32(buffer, y);
            
            // 屏幕尺寸
            writeBE16(buffer, static_cast<quint16>(injectTouch.screenSize.width()));
            writeBE16(buffer, static_cast<quint16>(injectTouch.screenSize.height()));
            
            // 压力 (0-65535)
            writeBE16(buffer, toFixedPoint16(injectTouch.pressure));

            // action button
            writeBE32(buffer, static_cast<quint32>(injectTouch.actionButton));
            
            // 按钮
            writeBE32(buffer, static_cast<quint32>(injectTouch.buttons));
            break;
        }
        
        case ControlMessageType::InjectScroll: {
            // 位置
            quint32 x = static_cast<quint32>(injectScroll.position.x());
            quint32 y = static_cast<quint32>(injectScroll.position.y());
            writeBE32(buffer, x);
            writeBE32(buffer, y);
            
            // 屏幕尺寸
            writeBE16(buffer, static_cast<quint16>(injectScroll.screenSize.width()));
            writeBE16(buffer, static_cast<quint16>(injectScroll.screenSize.height()));
            
            // 滚动距离 (使用定点表示)
            qint16 hScroll = toSignedFixedPoint16(injectScroll.hScroll / 16.0f);
            qint16 vScroll = toSignedFixedPoint16(injectScroll.vScroll / 16.0f);
            
            char hBytes[2], vBytes[2];
            qToBigEndian(hScroll, hBytes);
            qToBigEndian(vScroll, vBytes);
            buffer.append(hBytes, 2);
            buffer.append(vBytes, 2);
            
            // buttons (用于兼容性)
            writeBE32(buffer, static_cast<quint32>(injectScroll.buttons));
            break;
        }
        
        case ControlMessageType::BackOrScreenOn: {
            buffer.append(static_cast<char>(backOrScreenOn.action));
            break;
        }
        
        case ControlMessageType::ExpandNotificationPanel:
        case ControlMessageType::ExpandSettingsPanel:
        case ControlMessageType::CollapsePanels:
        case ControlMessageType::RotateDevice:
            // 这些消息没有额外数据
            break;
        
        case ControlMessageType::GetClipboard: {
            buffer.append(static_cast<char>(getClipboard.copyKey));
            break;
        }
        
        case ControlMessageType::SetClipboard: {
            writeBE64(buffer, static_cast<quint64>(setClipboard.sequence));
            buffer.append(static_cast<char>(setClipboard.paste ? 1 : 0));
            
            QByteArray textBytes = setClipboard.text.toUtf8();
            writeBE32(buffer, static_cast<quint32>(textBytes.size()));
            buffer.append(textBytes);
            break;
        }
        
        case ControlMessageType::SetScreenPowerMode: {
            buffer.append(static_cast<char>(setScreenPowerMode.mode));
            break;
        }
        
        default:
            qWarning() << "Unknown control message type:" << static_cast<int>(type);
            break;
    }
    
    return buffer;
}

ControlMessage ControlMessage::deserialize(const QByteArray& data)
{
    ControlMessage msg;
    
    if (data.isEmpty()) {
        return msg;
    }
    
    msg.type = static_cast<ControlMessageType>(static_cast<quint8>(data[0]));
    
    // 根据需要实现反序列化
    // 通常客户端不需要反序列化控制消息
    
    return msg;
}

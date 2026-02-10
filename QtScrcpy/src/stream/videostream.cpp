/**
 * QtScrcpy - Video Stream
 * Copyright (C) 2024 QtScrcpy Contributors
 *
 * Licensed under the Apache License, Version 2.0
 */

#include "videostream.h"
#include "decoder/decoder.h"
#include <QDebug>
#include <QtEndian>

// scrcpy协议常量
constexpr int DEVICE_NAME_LENGTH = 64;
constexpr int DEVICE_INFO_SIZE = DEVICE_NAME_LENGTH + 4; // name + resolution

VideoStream::VideoStream(QObject *parent)
    : QObject(parent)
    , m_socket(new QTcpSocket(this))
    , m_decoder(new Decoder())
    , m_decoderThread(new QThread(this))
    , m_bytesReceived(0)
    , m_deviceWidth(0)
    , m_deviceHeight(0)
    , m_deviceInfoReceived(false)
    , m_waitingForHeader(true)
{
    // 将解码器移到独立线程
    m_decoder->moveToThread(m_decoderThread);
    m_decoderThread->start();
    
    // 连接socket信号
    connect(m_socket, &QTcpSocket::connected, this, &VideoStream::onConnected);
    connect(m_socket, &QTcpSocket::disconnected, this, &VideoStream::onDisconnected);
    connect(m_socket, &QTcpSocket::readyRead, this, &VideoStream::onReadyRead);
    connect(m_socket, &QTcpSocket::errorOccurred, this, &VideoStream::onError);
    
    // 连接解码器信号
    connect(m_decoder, &Decoder::frameReady, this, &VideoStream::frameReady);
}

VideoStream::~VideoStream()
{
    disconnect();
    
    m_decoderThread->quit();
    m_decoderThread->wait();
    
    delete m_decoder;
}

bool VideoStream::connectToHost(const QString& host, quint16 port)
{
    if (m_socket->state() != QAbstractSocket::UnconnectedState) {
        return false;
    }
    
    m_buffer.clear();
    m_bytesReceived = 0;
    m_deviceInfoReceived = false;
    m_waitingForHeader = true;
    
    m_socket->connectToHost(host, port);
    
    return m_socket->waitForConnected(5000);
}

void VideoStream::disconnect()
{
    if (m_socket->state() != QAbstractSocket::UnconnectedState) {
        m_socket->disconnectFromHost();
    }
    
    m_decoder->close();
}

bool VideoStream::isConnected() const
{
    return m_socket->state() == QAbstractSocket::ConnectedState;
}

void VideoStream::onConnected()
{
    qDebug() << "Video stream connected";
    
    // 初始化解码器
    QMetaObject::invokeMethod(m_decoder, "init", Qt::QueuedConnection);
    
    emit connected();
}

void VideoStream::onDisconnected()
{
    qDebug() << "Video stream disconnected";
    emit disconnected();
}

void VideoStream::onReadyRead()
{
    QByteArray data = m_socket->readAll();
    m_buffer.append(data);
    m_bytesReceived += data.size();
    
    // 首先解析设备信息
    if (!m_deviceInfoReceived) {
        if (!parseDeviceInfo()) {
            return; // 等待更多数据
        }
    }
    
    // 处理视频数据
    processVideoData();
}

bool VideoStream::parseDeviceInfo()
{
    if (m_buffer.size() < DEVICE_INFO_SIZE) {
        return false;
    }
    
    // 设备名称 (64 bytes, null-terminated)
    m_deviceName = QString::fromUtf8(m_buffer.left(DEVICE_NAME_LENGTH)).trimmed();
    
    // 分辨率 (4 bytes: 2 for width, 2 for height)
    m_deviceWidth = qFromBigEndian<quint16>(
        reinterpret_cast<const uchar*>(m_buffer.constData() + DEVICE_NAME_LENGTH));
    m_deviceHeight = qFromBigEndian<quint16>(
        reinterpret_cast<const uchar*>(m_buffer.constData() + DEVICE_NAME_LENGTH + 2));
    
    // 移除已处理的数据
    m_buffer.remove(0, DEVICE_INFO_SIZE);
    m_deviceInfoReceived = true;
    
    qDebug() << "Device info received:" << m_deviceName 
             << m_deviceWidth << "x" << m_deviceHeight;
    
    emit deviceInfoReceived(m_deviceName, m_deviceWidth, m_deviceHeight);
    
    return true;
}

void VideoStream::processVideoData()
{
    // scrcpy视频流格式：
    // - 每个帧以 NAL 单元开始
    // - 直接将数据传递给解码器
    
    while (!m_buffer.isEmpty()) {
        // 查找NAL单元起始码
        int nalStart = -1;
        
        for (int i = 0; i < m_buffer.size() - 3; i++) {
            // 检查 0x00 0x00 0x01 或 0x00 0x00 0x00 0x01
            if (m_buffer[i] == 0x00 && m_buffer[i+1] == 0x00) {
                if (m_buffer[i+2] == 0x01) {
                    nalStart = i;
                    break;
                }
                if (i < m_buffer.size() - 4 && m_buffer[i+2] == 0x00 && m_buffer[i+3] == 0x01) {
                    nalStart = i;
                    break;
                }
            }
        }
        
        if (nalStart == -1) {
            // 没有找到完整的NAL单元，等待更多数据
            break;
        }
        
        // 查找下一个NAL单元
        int nextNalStart = -1;
        int startPos = nalStart + 3;
        if (nalStart < m_buffer.size() - 4 && 
            m_buffer[nalStart] == 0x00 && 
            m_buffer[nalStart+1] == 0x00 && 
            m_buffer[nalStart+2] == 0x00 &&
            m_buffer[nalStart+3] == 0x01) {
            startPos = nalStart + 4;
        }
        
        for (int i = startPos; i < m_buffer.size() - 3; i++) {
            if (m_buffer[i] == 0x00 && m_buffer[i+1] == 0x00) {
                if (m_buffer[i+2] == 0x01) {
                    nextNalStart = i;
                    break;
                }
                if (i < m_buffer.size() - 4 && m_buffer[i+2] == 0x00 && m_buffer[i+3] == 0x01) {
                    nextNalStart = i;
                    break;
                }
            }
        }
        
        if (nextNalStart == -1) {
            // 这是最后一个NAL单元，检查缓冲区大小
            // 如果缓冲区过大，可能是不完整的帧，发送到解码器
            if (m_buffer.size() > 1024 * 1024) {
                QByteArray nalUnit = m_buffer;
                m_buffer.clear();
                
                QMetaObject::invokeMethod(m_decoder, [this, nalUnit]() {
                    m_decoder->decode(nalUnit);
                }, Qt::QueuedConnection);
            }
            break;
        }
        
        // 提取NAL单元
        QByteArray nalUnit = m_buffer.mid(nalStart, nextNalStart - nalStart);
        m_buffer.remove(0, nextNalStart);
        
        // 发送到解码器
        QMetaObject::invokeMethod(m_decoder, [this, nalUnit]() {
            m_decoder->decode(nalUnit);
        }, Qt::QueuedConnection);
    }
}

void VideoStream::onError(QAbstractSocket::SocketError error)
{
    QString errorMsg;
    switch (error) {
        case QAbstractSocket::ConnectionRefusedError:
            errorMsg = "连接被拒绝";
            break;
        case QAbstractSocket::HostNotFoundError:
            errorMsg = "找不到主机";
            break;
        case QAbstractSocket::SocketTimeoutError:
            errorMsg = "连接超时";
            break;
        case QAbstractSocket::RemoteHostClosedError:
            errorMsg = "远程主机关闭连接";
            break;
        default:
            errorMsg = m_socket->errorString();
            break;
    }
    
    qDebug() << "Video stream error:" << errorMsg;
    emit this->error(errorMsg);
}

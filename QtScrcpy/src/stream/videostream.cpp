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

// scrcpy鍗忚甯搁噺
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
    // 灏嗚В鐮佸櫒绉诲埌鐙珛绾跨▼
    m_decoder->moveToThread(m_decoderThread);
    m_decoderThread->start();
    
    // 杩炴帴socket淇″彿
    connect(m_socket, &QTcpSocket::connected, this, &VideoStream::onConnected);
    connect(m_socket, &QTcpSocket::disconnected, this, &VideoStream::onDisconnected);
    connect(m_socket, &QTcpSocket::readyRead, this, &VideoStream::onReadyRead);
    connect(m_socket, &QTcpSocket::errorOccurred, this, &VideoStream::onError);
    
    // 杩炴帴瑙ｇ爜鍣ㄤ俊鍙?
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
    
    // 鍒濆鍖栬В鐮佸櫒
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
    
    // 棣栧厛瑙ｆ瀽璁惧淇℃伅
    if (!m_deviceInfoReceived) {
        if (!parseDeviceInfo()) {
            return; // 绛夊緟鏇村鏁版嵁
        }
    }
    
    // 澶勭悊瑙嗛鏁版嵁
    processVideoData();
}

bool VideoStream::parseDeviceInfo()
{
    if (m_buffer.size() < DEVICE_INFO_SIZE) {
        return false;
    }
    
    // 璁惧鍚嶇О (64 bytes, null-terminated)
    m_deviceName = QString::fromUtf8(m_buffer.left(DEVICE_NAME_LENGTH)).trimmed();
    
    // 鍒嗚鲸鐜?(4 bytes: 2 for width, 2 for height)
    m_deviceWidth = qFromBigEndian<quint16>(
        reinterpret_cast<const uchar*>(m_buffer.constData() + DEVICE_NAME_LENGTH));
    m_deviceHeight = qFromBigEndian<quint16>(
        reinterpret_cast<const uchar*>(m_buffer.constData() + DEVICE_NAME_LENGTH + 2));
    
    // 绉婚櫎宸插鐞嗙殑鏁版嵁
    m_buffer.remove(0, DEVICE_INFO_SIZE);
    m_deviceInfoReceived = true;
    
    qDebug() << "Device info received:" << m_deviceName 
             << m_deviceWidth << "x" << m_deviceHeight;
    
    emit deviceInfoReceived(m_deviceName, m_deviceWidth, m_deviceHeight);
    
    return true;
}

void VideoStream::processVideoData()
{
    // scrcpy瑙嗛娴佹牸寮忥細
    // - 姣忎釜甯т互 NAL 鍗曞厓寮€濮?
    // - 鐩存帴灏嗘暟鎹紶閫掔粰瑙ｇ爜鍣?
    
    while (!m_buffer.isEmpty()) {
        // 鏌ユ壘NAL鍗曞厓璧峰鐮?
        int nalStart = -1;
        
        for (int i = 0; i < m_buffer.size() - 3; i++) {
            // 妫€鏌?0x00 0x00 0x01 鎴?0x00 0x00 0x00 0x01
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
            // 娌℃湁鎵惧埌瀹屾暣鐨凬AL鍗曞厓锛岀瓑寰呮洿澶氭暟鎹?
            break;
        }
        
        // 鏌ユ壘涓嬩竴涓狽AL鍗曞厓
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
            // 杩欐槸鏈€鍚庝竴涓狽AL鍗曞厓锛屾鏌ョ紦鍐插尯澶у皬
            // 濡傛灉缂撳啿鍖鸿繃澶э紝鍙兘鏄笉瀹屾暣鐨勫抚锛屽彂閫佸埌瑙ｇ爜鍣?
            if (m_buffer.size() > 1024 * 1024) {
                QByteArray nalUnit = m_buffer;
                m_buffer.clear();
                
                QMetaObject::invokeMethod(m_decoder, [this, nalUnit]() {
                    m_decoder->decode(nalUnit);
                }, Qt::QueuedConnection);
            }
            break;
        }
        
        // 鎻愬彇NAL鍗曞厓
        QByteArray nalUnit = m_buffer.mid(nalStart, nextNalStart - nalStart);
        m_buffer.remove(0, nextNalStart);
        
        // 鍙戦€佸埌瑙ｇ爜鍣?
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
            errorMsg = "Connection refused";
            break;
        case QAbstractSocket::HostNotFoundError:
            errorMsg = "Host not found";
            break;
        case QAbstractSocket::SocketTimeoutError:
            errorMsg = "杩炴帴瓒呮椂";
            break;
        case QAbstractSocket::RemoteHostClosedError:
            errorMsg = "杩滅▼涓绘満鍏抽棴杩炴帴";
            break;
        default:
            errorMsg = m_socket->errorString();
            break;
    }
    
    qDebug() << "Video stream error:" << errorMsg;
    emit this->error(errorMsg);
}

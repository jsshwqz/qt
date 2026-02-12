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
constexpr int DEVICE_NAME_META_SIZE = DEVICE_NAME_LENGTH;
constexpr int LEGACY_DEVICE_INFO_SIZE = DEVICE_NAME_LENGTH + 4; // name + resolution
constexpr uchar SCRCPY_DUMMY_BYTE = 0x00;

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
    connect(m_decoder, &Decoder::initialized, this, [this](int width, int height) {
        if (width <= 0 || height <= 0) {
            return;
        }
        m_deviceWidth = width;
        m_deviceHeight = height;
        if (m_deviceName.isEmpty()) {
            m_deviceName = QStringLiteral("Android Device");
        }
        emit deviceInfoReceived(m_deviceName, m_deviceWidth, m_deviceHeight);
    });
    connect(m_decoder, &Decoder::decodeError, this, [this](const QString& message) {
        qWarning() << "Decoder error:" << message;
        emit error(QString("Decoder error: %1").arg(message));
    });
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
    const bool queued = QMetaObject::invokeMethod(m_decoder, [this]() {
        if (!m_decoder->init()) {
            emit error("Failed to initialize video decoder");
        }
    }, Qt::QueuedConnection);
    if (!queued) {
        qWarning() << "Failed to queue decoder initialization";
        emit error("Failed to queue decoder initialization");
    }
    
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
    int offset = 0;

    if (!m_buffer.isEmpty() && static_cast<uchar>(m_buffer.at(0)) == SCRCPY_DUMMY_BYTE) {
        if (m_buffer.size() < DEVICE_NAME_META_SIZE + 1) {
            return false;
        }
        offset = 1;
    }

    if (m_buffer.size() < offset + DEVICE_NAME_META_SIZE) {
        return false;
    }

    m_deviceName = QString::fromUtf8(m_buffer.mid(offset, DEVICE_NAME_META_SIZE)).trimmed();
    if (m_deviceName.isEmpty()) {
        m_deviceName = QStringLiteral("Android Device");
    }

    m_deviceWidth = 0;
    m_deviceHeight = 0;
    int bytesToRemove = offset + DEVICE_NAME_META_SIZE;

    if (m_buffer.size() >= offset + LEGACY_DEVICE_INFO_SIZE) {
        const int w = qFromBigEndian<quint16>(
            reinterpret_cast<const uchar*>(m_buffer.constData() + offset + DEVICE_NAME_LENGTH));
        const int h = qFromBigEndian<quint16>(
            reinterpret_cast<const uchar*>(m_buffer.constData() + offset + DEVICE_NAME_LENGTH + 2));

        if (w > 0 && w <= 8192 && h > 0 && h <= 8192) {
            m_deviceWidth = w;
            m_deviceHeight = h;
            bytesToRemove = offset + LEGACY_DEVICE_INFO_SIZE;
        }
    }

    m_buffer.remove(0, bytesToRemove);
    m_deviceInfoReceived = true;

    qDebug() << "Device info received:" << m_deviceName
             << m_deviceWidth << "x" << m_deviceHeight
             << "metaBytes=" << bytesToRemove;

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

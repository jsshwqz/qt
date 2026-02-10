/**
 * QtScrcpy - Video Stream
 * Copyright (C) 2024 QtScrcpy Contributors
 *
 * Licensed under the Apache License, Version 2.0
 */

#ifndef VIDEOSTREAM_H
#define VIDEOSTREAM_H

#include <QObject>
#include <QTcpSocket>
#include <QByteArray>
#include <QThread>

class Decoder;

/**
 * @brief 视频流接收器
 * 
 * 接收来自scrcpy服务端的视频流数据
 */
class VideoStream : public QObject
{
    Q_OBJECT

public:
    explicit VideoStream(QObject *parent = nullptr);
    ~VideoStream();

    /**
     * @brief 连接到视频流
     * @param host 主机地址
     * @param port 端口
     * @return 是否成功
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
     * @brief 获取解码器
     */
    Decoder* decoder() const { return m_decoder; }

    /**
     * @brief 获取接收的字节数
     */
    qint64 bytesReceived() const { return m_bytesReceived; }

signals:
    /**
     * @brief 连接成功信号
     */
    void connected();

    /**
     * @brief 断开连接信号
     */
    void disconnected();

    /**
     * @brief 帧准备就绪信号
     */
    void frameReady(const QImage& frame);

    /**
     * @brief 设备信息接收信号
     */
    void deviceInfoReceived(const QString& deviceName, int width, int height);

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
    bool parseDeviceInfo();
    void processVideoData();
    
    QTcpSocket* m_socket;
    Decoder* m_decoder;
    QThread* m_decoderThread;
    
    QByteArray m_buffer;
    qint64 m_bytesReceived;
    
    // 设备信息
    QString m_deviceName;
    int m_deviceWidth;
    int m_deviceHeight;
    bool m_deviceInfoReceived;
    
    // 帧头信息
    struct FrameHeader {
        quint64 pts;
        quint32 size;
    };
    bool m_waitingForHeader;
    FrameHeader m_currentHeader;
};

#endif // VIDEOSTREAM_H

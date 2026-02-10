/**
 * QtScrcpy - Device Discovery
 * Copyright (C) 2024 QtScrcpy Contributors
 *
 * Licensed under the Apache License, Version 2.0
 */

#ifndef DEVICEDISCOVERY_H
#define DEVICEDISCOVERY_H

#include <QObject>
#include <QTcpSocket>
#include <QHostAddress>
#include <QNetworkInterface>
#include <QList>
#include <QTimer>
#include <QThread>
#include <QMutex>

/**
 * @brief 发现的设备信息
 */
struct DiscoveredDevice {
    QString ip;
    int port;
    QString model;  // 如果能获取的话
};

/**
 * @brief 端口扫描工作线程
 */
class PortScanWorker : public QObject
{
    Q_OBJECT

public:
    explicit PortScanWorker(QObject *parent = nullptr);
    
    void setTarget(const QString& ip, int port, int timeout);

public slots:
    void process();

signals:
    void portOpen(const QString& ip, int port);
    void finished();

private:
    QString m_ip;
    int m_port;
    int m_timeout;
};

/**
 * @brief 设备发现器
 * 
 * 扫描局域网内的ADB设备
 */
class DeviceDiscovery : public QObject
{
    Q_OBJECT

public:
    explicit DeviceDiscovery(QObject *parent = nullptr);
    ~DeviceDiscovery();

    /**
     * @brief 获取本地网络段
     * @return 网络段列表（如 "192.168.1"）
     */
    QStringList getLocalNetworkSegments() const;

    /**
     * @brief 开始扫描
     * @param portToScan 要扫描的端口（默认5555）
     * @param timeout 每个IP的扫描超时（毫秒）
     */
    void startScan(int portToScan = 5555, int timeout = 200);

    /**
     * @brief 停止扫描
     */
    void stopScan();

    /**
     * @brief 是否正在扫描
     */
    bool isScanning() const { return m_isScanning; }

    /**
     * @brief 连接发现的设备
     */
    bool connectDevice(const QString& ip, int port = 5555);

    /**
     * @brief 设置并发扫描数
     */
    void setConcurrency(int count) { m_concurrency = count; }

signals:
    /**
     * @brief 发现设备信号
     */
    void deviceFound(const QString& ip, int port);

    /**
     * @brief 扫描进度信号
     */
    void scanProgress(int current, int total);

    /**
     * @brief 扫描完成信号
     */
    void scanFinished(const QList<DiscoveredDevice>& devices);

    /**
     * @brief 扫描开始信号
     */
    void scanStarted();

private slots:
    void onScanTimeout();
    void onSocketConnected();
    void onSocketError(QAbstractSocket::SocketError error);
    void processNextBatch();

private:
    void scanIp(const QString& ip, int port);
    
    bool m_isScanning;
    int m_portToScan;
    int m_timeout;
    int m_concurrency;
    
    QStringList m_ipsToScan;
    int m_currentIndex;
    int m_totalIps;
    int m_activeScans;
    
    QList<DiscoveredDevice> m_foundDevices;
    QList<QTcpSocket*> m_sockets;
    QTimer* m_progressTimer;
    QMutex m_mutex;
};

#endif // DEVICEDISCOVERY_H

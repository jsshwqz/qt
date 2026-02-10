/**
 * QtScrcpy - Device Discovery
 * Copyright (C) 2024 QtScrcpy Contributors
 *
 * Licensed under the Apache License, Version 2.0
 */

#include "devicediscovery.h"
#include "adbprocess.h"
#include <QDebug>

// PortScanWorker Implementation
PortScanWorker::PortScanWorker(QObject *parent)
    : QObject(parent)
    , m_port(5555)
    , m_timeout(200)
{
}

void PortScanWorker::setTarget(const QString& ip, int port, int timeout)
{
    m_ip = ip;
    m_port = port;
    m_timeout = timeout;
}

void PortScanWorker::process()
{
    QTcpSocket socket;
    socket.connectToHost(m_ip, m_port);
    
    if (socket.waitForConnected(m_timeout)) {
        socket.disconnectFromHost();
        emit portOpen(m_ip, m_port);
    }
    
    emit finished();
}

// DeviceDiscovery Implementation
DeviceDiscovery::DeviceDiscovery(QObject *parent)
    : QObject(parent)
    , m_isScanning(false)
    , m_portToScan(5555)
    , m_timeout(200)
    , m_concurrency(50)
    , m_currentIndex(0)
    , m_totalIps(0)
    , m_activeScans(0)
    , m_progressTimer(new QTimer(this))
{
    connect(m_progressTimer, &QTimer::timeout, this, &DeviceDiscovery::processNextBatch);
}

DeviceDiscovery::~DeviceDiscovery()
{
    stopScan();
}

QStringList DeviceDiscovery::getLocalNetworkSegments() const
{
    QStringList segments;
    
    QList<QNetworkInterface> interfaces = QNetworkInterface::allInterfaces();
    
    for (const QNetworkInterface& iface : interfaces) {
        // 跳过回环和未激活的接口
        if (iface.flags() & QNetworkInterface::IsLoopBack) {
            continue;
        }
        if (!(iface.flags() & QNetworkInterface::IsUp)) {
            continue;
        }
        if (!(iface.flags() & QNetworkInterface::IsRunning)) {
            continue;
        }
        
        QList<QNetworkAddressEntry> entries = iface.addressEntries();
        
        for (const QNetworkAddressEntry& entry : entries) {
            QHostAddress ip = entry.ip();
            
            // 只处理IPv4地址
            if (ip.protocol() != QAbstractSocket::IPv4Protocol) {
                continue;
            }
            
            // 跳过本地回环地址
            if (ip.isLoopback()) {
                continue;
            }
            
            // 提取网络段
            QString ipStr = ip.toString();
            QStringList parts = ipStr.split('.');
            if (parts.size() == 4) {
                QString segment = QString("%1.%2.%3")
                    .arg(parts[0])
                    .arg(parts[1])
                    .arg(parts[2]);
                
                if (!segments.contains(segment)) {
                    segments.append(segment);
                }
            }
        }
    }
    
    return segments;
}

void DeviceDiscovery::startScan(int portToScan, int timeout)
{
    if (m_isScanning) {
        return;
    }
    
    m_portToScan = portToScan;
    m_timeout = timeout;
    m_foundDevices.clear();
    m_ipsToScan.clear();
    m_currentIndex = 0;
    m_activeScans = 0;
    
    // 清理旧的socket
    for (QTcpSocket* socket : m_sockets) {
        socket->abort();
        socket->deleteLater();
    }
    m_sockets.clear();
    
    // 获取本地网络段
    QStringList segments = getLocalNetworkSegments();
    
    if (segments.isEmpty()) {
        emit scanFinished(m_foundDevices);
        return;
    }
    
    // 生成所有要扫描的IP
    for (const QString& segment : segments) {
        for (int i = 1; i <= 254; i++) {
            m_ipsToScan.append(QString("%1.%2").arg(segment).arg(i));
        }
    }
    
    m_totalIps = m_ipsToScan.size();
    m_isScanning = true;
    
    emit scanStarted();
    
    // 开始扫描
    processNextBatch();
    m_progressTimer->start(50);
}

void DeviceDiscovery::stopScan()
{
    m_isScanning = false;
    m_progressTimer->stop();
    
    for (QTcpSocket* socket : m_sockets) {
        socket->abort();
        socket->deleteLater();
    }
    m_sockets.clear();
}

bool DeviceDiscovery::connectDevice(const QString& ip, int port)
{
    AdbProcess adb;
    return adb.connectDevice(ip, port);
}

void DeviceDiscovery::processNextBatch()
{
    if (!m_isScanning) {
        return;
    }
    
    // 发射进度信号
    emit scanProgress(m_currentIndex, m_totalIps);
    
    // 检查是否完成
    if (m_currentIndex >= m_ipsToScan.size() && m_activeScans == 0) {
        m_isScanning = false;
        m_progressTimer->stop();
        emit scanFinished(m_foundDevices);
        return;
    }
    
    // 启动新的扫描（保持并发数）
    while (m_activeScans < m_concurrency && m_currentIndex < m_ipsToScan.size()) {
        QString ip = m_ipsToScan[m_currentIndex++];
        scanIp(ip, m_portToScan);
    }
}

void DeviceDiscovery::scanIp(const QString& ip, int port)
{
    QTcpSocket* socket = new QTcpSocket(this);
    socket->setProperty("ip", ip);
    socket->setProperty("port", port);
    
    m_sockets.append(socket);
    m_activeScans++;
    
    connect(socket, &QTcpSocket::connected, this, &DeviceDiscovery::onSocketConnected);
    connect(socket, &QTcpSocket::errorOccurred, this, &DeviceDiscovery::onSocketError);
    
    // 设置超时定时器
    QTimer* timeoutTimer = new QTimer(socket);
    timeoutTimer->setSingleShot(true);
    connect(timeoutTimer, &QTimer::timeout, this, [this, socket]() {
        socket->abort();
        m_sockets.removeOne(socket);
        m_activeScans--;
        socket->deleteLater();
    });
    timeoutTimer->start(m_timeout);
    
    socket->connectToHost(ip, port);
}

void DeviceDiscovery::onSocketConnected()
{
    QTcpSocket* socket = qobject_cast<QTcpSocket*>(sender());
    if (!socket) return;
    
    QString ip = socket->property("ip").toString();
    int port = socket->property("port").toInt();
    
    // 发现设备
    DiscoveredDevice device;
    device.ip = ip;
    device.port = port;
    
    m_mutex.lock();
    m_foundDevices.append(device);
    m_mutex.unlock();
    
    emit deviceFound(ip, port);
    
    socket->disconnectFromHost();
    m_sockets.removeOne(socket);
    m_activeScans--;
    socket->deleteLater();
}

void DeviceDiscovery::onSocketError(QAbstractSocket::SocketError error)
{
    Q_UNUSED(error)
    
    QTcpSocket* socket = qobject_cast<QTcpSocket*>(sender());
    if (!socket) return;
    
    m_sockets.removeOne(socket);
    m_activeScans--;
    socket->deleteLater();
}

void DeviceDiscovery::onScanTimeout()
{
    // 由每个socket自己的定时器处理
}

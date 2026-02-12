/**
 * QtScrcpy - Device Discovery
 * Copyright (C) 2024 QtScrcpy Contributors
 *
 * Licensed under the Apache License, Version 2.0
 */

#include "devicediscovery.h"
#include "adbprocess.h"

// PortScanWorker
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

// DeviceDiscovery
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

bool DeviceDiscovery::isPreferredWirelessInterface(const QNetworkInterface& iface) const
{
    if (iface.type() == QNetworkInterface::Wifi) {
        return true;
    }

    const QString name = (iface.humanReadableName() + " " + iface.name()).toLower();
    return name.contains("wi-fi")
        || name.contains("wifi")
        || name.contains("wlan")
        || name.contains("wireless");
}

bool DeviceDiscovery::isIgnoredInterface(const QNetworkInterface& iface) const
{
    const QString name = (iface.humanReadableName() + " " + iface.name()).toLower();
    const QStringList ignoredKeywords = {
        "virtual",
        "vmware",
        "vbox",
        "hyper-v",
        "docker",
        "wsl",
        "loopback",
        "bluetooth",
        "tailscale",
        "zerotier",
        "hamachi",
        "npcap",
        "tap"
    };

    for (const QString& keyword : ignoredKeywords) {
        if (name.contains(keyword)) {
            return true;
        }
    }
    return false;
}

QStringList DeviceDiscovery::getLocalNetworkSegments() const
{
    auto collectSegments = [this](bool wifiOnly) {
        QStringList segments;
        const QList<QNetworkInterface> interfaces = QNetworkInterface::allInterfaces();

        for (const QNetworkInterface& iface : interfaces) {
            if (isIgnoredInterface(iface)) {
                continue;
            }
            if (iface.flags() & QNetworkInterface::IsLoopBack) {
                continue;
            }
            if (!(iface.flags() & QNetworkInterface::IsUp)) {
                continue;
            }
            if (!(iface.flags() & QNetworkInterface::IsRunning)) {
                continue;
            }
            if (wifiOnly && !isPreferredWirelessInterface(iface)) {
                continue;
            }

            const QList<QNetworkAddressEntry> entries = iface.addressEntries();
            bool addedFromCurrentInterface = false;
            for (const QNetworkAddressEntry& entry : entries) {
                const QHostAddress ip = entry.ip();
                if (ip.protocol() != QAbstractSocket::IPv4Protocol) {
                    continue;
                }
                if (ip.isLoopback()) {
                    continue;
                }
                if (ip.toString().startsWith("169.254.")) {
                    continue;
                }

                const QStringList parts = ip.toString().split('.');
                if (parts.size() != 4) {
                    continue;
                }

                const QString segment = QString("%1.%2.%3")
                    .arg(parts[0]).arg(parts[1]).arg(parts[2]);
                if (!segments.contains(segment)) {
                    segments.append(segment);
                    addedFromCurrentInterface = true;
                }
            }

            // Prefer scanning the first active eligible interface to avoid
            // expensive scans across unrelated adapters.
            if (addedFromCurrentInterface && !segments.isEmpty()) {
                return QStringList{segments.first()};
            }
        }
        return segments;
    };

    const QStringList wifiSegments = collectSegments(true);
    if (!wifiSegments.isEmpty()) {
        return wifiSegments;
    }
    return collectSegments(false);
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

    for (QTcpSocket* socket : m_sockets) {
        socket->abort();
        socket->deleteLater();
    }
    m_sockets.clear();

    const QStringList segments = getLocalNetworkSegments();
    if (segments.isEmpty()) {
        emit scanFinished(m_foundDevices);
        return;
    }

    for (const QString& segment : segments) {
        for (int i = 1; i <= 254; ++i) {
            m_ipsToScan.append(QString("%1.%2").arg(segment).arg(i));
        }
    }

    m_totalIps = m_ipsToScan.size();
    m_isScanning = true;

    emit scanStarted();
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
    m_activeScans = 0;
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

    emit scanProgress(m_currentIndex, m_totalIps);

    if (m_currentIndex >= m_ipsToScan.size() && m_activeScans == 0) {
        m_isScanning = false;
        m_progressTimer->stop();
        emit scanFinished(m_foundDevices);
        return;
    }

    while (m_activeScans < m_concurrency && m_currentIndex < m_ipsToScan.size()) {
        const QString ip = m_ipsToScan[m_currentIndex++];
        scanIp(ip, m_portToScan);
    }
}

void DeviceDiscovery::scanIp(const QString& ip, int port)
{
    QTcpSocket* socket = new QTcpSocket(this);
    socket->setProperty("ip", ip);
    socket->setProperty("port", port);
    m_sockets.append(socket);
    ++m_activeScans;

    connect(socket, &QTcpSocket::connected, this, &DeviceDiscovery::onSocketConnected);
    connect(socket, &QTcpSocket::errorOccurred, this, &DeviceDiscovery::onSocketError);

    QTimer* timeoutTimer = new QTimer(socket);
    timeoutTimer->setSingleShot(true);
    connect(timeoutTimer, &QTimer::timeout, this, [this, socket]() {
        socket->abort();
        m_sockets.removeOne(socket);
        --m_activeScans;
        socket->deleteLater();
    });
    timeoutTimer->start(m_timeout);

    socket->connectToHost(ip, port);
}

void DeviceDiscovery::onSocketConnected()
{
    QTcpSocket* socket = qobject_cast<QTcpSocket*>(sender());
    if (!socket) {
        return;
    }

    DiscoveredDevice device;
    device.ip = socket->property("ip").toString();
    device.port = socket->property("port").toInt();

    m_mutex.lock();
    m_foundDevices.append(device);
    m_mutex.unlock();

    emit deviceFound(device.ip, device.port);

    socket->disconnectFromHost();
    m_sockets.removeOne(socket);
    --m_activeScans;
    socket->deleteLater();
}

void DeviceDiscovery::onSocketError(QAbstractSocket::SocketError error)
{
    Q_UNUSED(error)
    QTcpSocket* socket = qobject_cast<QTcpSocket*>(sender());
    if (!socket) {
        return;
    }

    m_sockets.removeOne(socket);
    --m_activeScans;
    socket->deleteLater();
}

void DeviceDiscovery::onScanTimeout()
{
    // Per-socket timeout is handled in scanIp().
}

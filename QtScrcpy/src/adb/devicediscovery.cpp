/**
 * QtScrcpy - Device Discovery
 * Copyright (C) 2024 QtScrcpy Contributors
 *
 * Licensed under the Apache License, Version 2.0
 */

#include "devicediscovery.h"
#include "adbprocess.h"
#include <QSettings>
#include <QRegularExpression>

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

bool DeviceDiscovery::isValidSegment(const QString& segment)
{
    static const QRegularExpression re(
        "^((25[0-5]|2[0-4]\\d|1\\d\\d|[1-9]?\\d)\\.){2}(25[0-5]|2[0-4]\\d|1\\d\\d|[1-9]?\\d)$");
    return re.match(segment).hasMatch();
}

QStringList DeviceDiscovery::loadSavedSegments() const
{
    QSettings settings("QtScrcpy", "QtScrcpy");
    QStringList segments = settings.value("network/lastScanSegments").toStringList();
    if (segments.isEmpty()) {
        const QString legacy = settings.value("network/lastScanSegment").toString().trimmed();
        if (!legacy.isEmpty()) {
            segments.append(legacy);
        }
    }

    QStringList filtered;
    for (const QString& segment : segments) {
        const QString trimmed = segment.trimmed();
        if (!isValidSegment(trimmed)) {
            continue;
        }
        if (!filtered.contains(trimmed)) {
            filtered.append(trimmed);
        }
        if (filtered.size() >= 4) {
            break;
        }
    }
    return filtered;
}

void DeviceDiscovery::saveSegments(const QStringList& segments) const
{
    QStringList filtered;
    for (const QString& segment : segments) {
        const QString trimmed = segment.trimmed();
        if (!isValidSegment(trimmed)) {
            continue;
        }
        if (!filtered.contains(trimmed)) {
            filtered.append(trimmed);
        }
        if (filtered.size() >= 4) {
            break;
        }
    }

    if (filtered.isEmpty()) {
        return;
    }

    QSettings settings("QtScrcpy", "QtScrcpy");
    settings.setValue("network/lastScanSegments", filtered);
    settings.setValue("network/lastScanSegment", filtered.first());
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
    auto collectSegments = [this](bool wifiOnly, bool requireRunning, int maxCount) {
        QStringList segments;
        const QList<QNetworkInterface> interfaces = QNetworkInterface::allInterfaces();

        for (const QNetworkInterface& iface : interfaces) {
            if (isIgnoredInterface(iface)) {
                continue;
            }
            if (iface.flags() & QNetworkInterface::IsLoopBack) {
                continue;
            }
            if (requireRunning) {
                if (!(iface.flags() & QNetworkInterface::IsUp)) {
                    continue;
                }
                if (!(iface.flags() & QNetworkInterface::IsRunning)) {
                    continue;
                }
            }
            if (wifiOnly && !isPreferredWirelessInterface(iface)) {
                continue;
            }

            const QList<QNetworkAddressEntry> entries = iface.addressEntries();
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
                if (isValidSegment(segment) && !segments.contains(segment)) {
                    segments.append(segment);
                    if (segments.size() >= maxCount) {
                        return segments;
                    }
                }
            }
        }
        return segments;
    };

    constexpr int kSingleTargetSegment = 1;

    // 1) Prefer the currently connected Wi-Fi subnet.
    const QStringList connectedWifi = collectSegments(true, true, kSingleTargetSegment);
    if (!connectedWifi.isEmpty()) {
        return connectedWifi;
    }

    // 2) If no connected Wi-Fi, reuse the most recent successful subnet.
    const QStringList savedSegments = loadSavedSegments();
    if (!savedSegments.isEmpty()) {
        return { savedSegments.first() };
    }

    // 3) Fallback to configured Wi-Fi subnet.
    const QStringList configuredWifi = collectSegments(true, false, kSingleTargetSegment);
    if (!configuredWifi.isEmpty()) {
        return configuredWifi;
    }

    // 4) Fallback to any active subnet.
    const QStringList activeSegments = collectSegments(false, true, kSingleTargetSegment);
    if (!activeSegments.isEmpty()) {
        return activeSegments;
    }

    // 5) Last-resort configured subnet.
    return collectSegments(false, false, kSingleTargetSegment);
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
    m_scanSegments.clear();
    m_currentIndex = 0;
    m_activeScans = 0;

    for (QTcpSocket* socket : m_sockets) {
        socket->disconnect(this);
        socket->abort();
        socket->deleteLater();
    }
    m_sockets.clear();

    const QStringList segments = getLocalNetworkSegments();
    if (segments.isEmpty()) {
        emit scanFinished(m_foundDevices);
        return;
    }
    m_scanSegments = segments;
    saveSegments(m_scanSegments);

    for (const QString& segment : m_scanSegments) {
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
        socket->disconnect(this);
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

    if (m_currentIndex >= m_ipsToScan.size() && m_activeScans <= 0) {
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
        if (!m_sockets.contains(socket)) {
            return;
        }
        socket->disconnect(this);
        socket->abort();
        m_sockets.removeOne(socket);
        m_activeScans = qMax(0, m_activeScans - 1);
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
    if (!m_sockets.removeOne(socket)) {
        return;
    }
    m_activeScans = qMax(0, m_activeScans - 1);
    socket->deleteLater();
}

void DeviceDiscovery::onSocketError(QAbstractSocket::SocketError error)
{
    Q_UNUSED(error)
    QTcpSocket* socket = qobject_cast<QTcpSocket*>(sender());
    if (!socket) {
        return;
    }

    if (!m_sockets.removeOne(socket)) {
        return;
    }
    m_activeScans = qMax(0, m_activeScans - 1);
    socket->deleteLater();
}

void DeviceDiscovery::onScanTimeout()
{
    // Per-socket timeout is handled in scanIp().
}

/**
 * QtScrcpy - Device Manager
 * Copyright (C) 2024 QtScrcpy Contributors
 *
 * Licensed under the Apache License, Version 2.0
 */

#include "devicemanager.h"
#include "adbprocess.h"
#include <QDebug>
#include <QRegularExpression>

DeviceManager* DeviceManager::s_instance = nullptr;

DeviceManager* DeviceManager::instance()
{
    if (!s_instance) {
        s_instance = new DeviceManager();
    }
    return s_instance;
}

DeviceManager::DeviceManager(QObject *parent)
    : QObject(parent)
    , m_adb(new AdbProcess(this))
    , m_refreshTimer(new QTimer(this))
    , m_refreshInterval(2000)
{
    connect(m_refreshTimer, &QTimer::timeout, this, &DeviceManager::onRefreshTimer);
}

DeviceManager::~DeviceManager()
{
    stopMonitoring();
}

void DeviceManager::startMonitoring()
{
    refreshDevices();
    m_refreshTimer->start(m_refreshInterval);
}

void DeviceManager::stopMonitoring()
{
    m_refreshTimer->stop();
}

void DeviceManager::refreshDevices()
{
    QStringList serials = m_adb->getDevices();
    
    // 检查移除的设备
    QList<QString> toRemove;
    for (auto it = m_devices.begin(); it != m_devices.end(); ++it) {
        if (!serials.contains(it.key())) {
            toRemove.append(it.key());
        }
    }
    
    for (const QString& serial : toRemove) {
        m_devices.remove(serial);
        emit deviceRemoved(serial);
    }
    
    // 检查新增的设备
    for (const QString& serial : serials) {
        if (!m_devices.contains(serial)) {
            DeviceInfo info;
            info.serial = serial;
            info.isWireless = isWirelessDevice(serial);
            
            if (info.isWireless) {
                info.ipAddress = extractIpFromSerial(serial);
                info.port = 5555;
                // 尝试从序列号提取端口
                QRegularExpression re(":(\\d+)$");
                QRegularExpressionMatch match = re.match(serial);
                if (match.hasMatch()) {
                    info.port = match.captured(1).toInt();
                }
            }
            
            // 获取设备详细信息
            info.model = m_adb->getDeviceModel(serial);
            info.resolution = m_adb->getDeviceResolution(serial);
            
            m_devices[serial] = info;
            emit deviceAdded(info);
        }
    }
    
    emit devicesUpdated(m_devices.values());
}

DeviceInfo DeviceManager::getDevice(const QString& serial) const
{
    return m_devices.value(serial);
}

bool DeviceManager::connectWirelessDevice(const QString& ip, int port)
{
    if (m_adb->connectDevice(ip, port)) {
        refreshDevices();
        return true;
    }
    return false;
}

bool DeviceManager::disconnectDevice(const QString& serial)
{
    if (isWirelessDevice(serial)) {
        QString ip = extractIpFromSerial(serial);
        int port = 5555;
        
        QRegularExpression re(":(\\d+)$");
        QRegularExpressionMatch match = re.match(serial);
        if (match.hasMatch()) {
            port = match.captured(1).toInt();
        }
        
        if (m_adb->disconnectDevice(ip, port)) {
            m_devices.remove(serial);
            emit deviceRemoved(serial);
            return true;
        }
    }
    return false;
}

void DeviceManager::setDeviceConnected(const QString& serial, bool connected)
{
    if (m_devices.contains(serial)) {
        m_devices[serial].isConnected = connected;
        emit deviceStateChanged(m_devices[serial]);
    }
}

void DeviceManager::updateDeviceInfo(const QString& serial)
{
    if (m_devices.contains(serial)) {
        DeviceInfo& info = m_devices[serial];
        info.model = m_adb->getDeviceModel(serial);
        info.resolution = m_adb->getDeviceResolution(serial);
        emit deviceStateChanged(info);
    }
}

bool DeviceManager::isWirelessDevice(const QString& serial) const
{
    // 无线设备的序列号格式通常是 IP:PORT
    QRegularExpression re("^\\d{1,3}\\.\\d{1,3}\\.\\d{1,3}\\.\\d{1,3}:\\d+$");
    return re.match(serial).hasMatch();
}

QString DeviceManager::extractIpFromSerial(const QString& serial) const
{
    QRegularExpression re("^(\\d{1,3}\\.\\d{1,3}\\.\\d{1,3}\\.\\d{1,3})");
    QRegularExpressionMatch match = re.match(serial);
    if (match.hasMatch()) {
        return match.captured(1);
    }
    return QString();
}

void DeviceManager::onRefreshTimer()
{
    refreshDevices();
}

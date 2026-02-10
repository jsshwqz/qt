/**
 * QtScrcpy - Device Manager
 * Copyright (C) 2024 QtScrcpy Contributors
 *
 * Licensed under the Apache License, Version 2.0
 */

#ifndef DEVICEMANAGER_H
#define DEVICEMANAGER_H

#include <QObject>
#include <QString>
#include <QList>
#include <QTimer>
#include <QMap>

class AdbProcess;

/**
 * @brief 设备信息结构
 */
struct DeviceInfo {
    QString serial;          // 设备序列号
    QString model;           // 设备型号
    QString ipAddress;       // IP地址（如果是无线连接）
    int port;                // 端口
    QSize resolution;        // 分辨率
    bool isWireless;         // 是否无线连接
    bool isConnected;        // 是否已连接投屏
    
    DeviceInfo() : port(5555), isWireless(false), isConnected(false) {}
};

/**
 * @brief 设备管理器
 * 
 * 负责管理设备的发现、连接和状态跟踪
 */
class DeviceManager : public QObject
{
    Q_OBJECT

public:
    static DeviceManager* instance();
    
    explicit DeviceManager(QObject *parent = nullptr);
    ~DeviceManager();

    /**
     * @brief 开始监控设备
     */
    void startMonitoring();

    /**
     * @brief 停止监控设备
     */
    void stopMonitoring();

    /**
     * @brief 刷新设备列表
     */
    void refreshDevices();

    /**
     * @brief 获取设备列表
     */
    QList<DeviceInfo> getDevices() const { return m_devices.values(); }

    /**
     * @brief 根据序列号获取设备信息
     */
    DeviceInfo getDevice(const QString& serial) const;

    /**
     * @brief 连接无线设备
     */
    bool connectWirelessDevice(const QString& ip, int port = 5555);

    /**
     * @brief 断开无线设备
     */
    bool disconnectDevice(const QString& serial);

    /**
     * @brief 设置设备投屏状态
     */
    void setDeviceConnected(const QString& serial, bool connected);

    /**
     * @brief 获取ADB进程实例
     */
    AdbProcess* adb() const { return m_adb; }

signals:
    /**
     * @brief 设备列表更新信号
     */
    void devicesUpdated(const QList<DeviceInfo>& devices);

    /**
     * @brief 设备添加信号
     */
    void deviceAdded(const DeviceInfo& device);

    /**
     * @brief 设备移除信号
     */
    void deviceRemoved(const QString& serial);

    /**
     * @brief 设备状态改变信号
     */
    void deviceStateChanged(const DeviceInfo& device);

private slots:
    void onRefreshTimer();

private:
    void updateDeviceInfo(const QString& serial);
    bool isWirelessDevice(const QString& serial) const;
    QString extractIpFromSerial(const QString& serial) const;
    
    static DeviceManager* s_instance;
    
    AdbProcess* m_adb;
    QTimer* m_refreshTimer;
    QMap<QString, DeviceInfo> m_devices;
    int m_refreshInterval;
};

#endif // DEVICEMANAGER_H

/**
 * QtScrcpy - Device List Dialog
 * Copyright (C) 2024 QtScrcpy Contributors
 *
 * Licensed under the Apache License, Version 2.0
 */

#include "devicelistdialog.h"
#include "adb/devicemanager.h"

#include <QVBoxLayout>
#include <QHBoxLayout>

DeviceListDialog::DeviceListDialog(QWidget *parent)
    : QDialog(parent)
{
    setWindowTitle("选择设备");
    setMinimumSize(400, 300);
    
    QVBoxLayout* layout = new QVBoxLayout(this);
    
    // 状态标签
    m_statusLabel = new QLabel("已连接的设备：", this);
    layout->addWidget(m_statusLabel);
    
    // 设备列表
    m_listWidget = new QListWidget(this);
    layout->addWidget(m_listWidget);
    
    // 按钮
    QHBoxLayout* btnLayout = new QHBoxLayout();
    
    m_refreshBtn = new QPushButton("刷新", this);
    btnLayout->addWidget(m_refreshBtn);
    
    btnLayout->addStretch();
    
    m_connectBtn = new QPushButton("连接", this);
    m_connectBtn->setDefault(true);
    btnLayout->addWidget(m_connectBtn);
    
    m_cancelBtn = new QPushButton("取消", this);
    btnLayout->addWidget(m_cancelBtn);
    
    layout->addLayout(btnLayout);
    
    // 连接信号
    connect(m_listWidget, &QListWidget::itemDoubleClicked,
            this, &DeviceListDialog::onItemDoubleClicked);
    connect(m_refreshBtn, &QPushButton::clicked,
            this, &DeviceListDialog::onRefreshClicked);
    connect(m_connectBtn, &QPushButton::clicked,
            this, &DeviceListDialog::onConnectClicked);
    connect(m_cancelBtn, &QPushButton::clicked,
            this, &QDialog::reject);
    
    connect(DeviceManager::instance(), &DeviceManager::devicesUpdated,
            this, &DeviceListDialog::onDevicesUpdated);
    
    // 初始化列表
    updateDeviceList();
}

DeviceListDialog::~DeviceListDialog()
{
}

void DeviceListDialog::updateDeviceList()
{
    m_listWidget->clear();
    
    QList<DeviceInfo> devices = DeviceManager::instance()->getDevices();
    
    for (const DeviceInfo& info : devices) {
        QString text = info.model.isEmpty() ? info.serial : info.model;
        
        if (info.isWireless) {
            text += QString(" (无线 %1)").arg(info.ipAddress);
        } else {
            text += " (USB)";
        }
        
        QListWidgetItem* item = new QListWidgetItem(text, m_listWidget);
        item->setData(Qt::UserRole, info.serial);
    }
    
    m_statusLabel->setText(QString("已连接 %1 个设备").arg(devices.size()));
}

void DeviceListDialog::onDevicesUpdated()
{
    updateDeviceList();
}

void DeviceListDialog::onItemDoubleClicked(QListWidgetItem* item)
{
    m_selectedSerial = item->data(Qt::UserRole).toString();
    accept();
}

void DeviceListDialog::onRefreshClicked()
{
    DeviceManager::instance()->refreshDevices();
}

void DeviceListDialog::onConnectClicked()
{
    QListWidgetItem* item = m_listWidget->currentItem();
    if (item) {
        m_selectedSerial = item->data(Qt::UserRole).toString();
        accept();
    }
}

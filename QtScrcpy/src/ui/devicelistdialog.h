/**
 * QtScrcpy - Device List Dialog
 * Copyright (C) 2024 QtScrcpy Contributors
 *
 * Licensed under the Apache License, Version 2.0
 */

#ifndef DEVICELISTDIALOG_H
#define DEVICELISTDIALOG_H

#include <QDialog>
#include <QListWidget>
#include <QPushButton>
#include <QLabel>

class DeviceManager;

/**
 * @brief 设备列表对话框
 */
class DeviceListDialog : public QDialog
{
    Q_OBJECT

public:
    explicit DeviceListDialog(QWidget *parent = nullptr);
    ~DeviceListDialog();

    /**
     * @brief 获取选中的设备序列号
     */
    QString selectedSerial() const { return m_selectedSerial; }

private slots:
    void onDevicesUpdated();
    void onItemDoubleClicked(QListWidgetItem* item);
    void onRefreshClicked();
    void onConnectClicked();

private:
    void updateDeviceList();
    
    QListWidget* m_listWidget;
    QPushButton* m_refreshBtn;
    QPushButton* m_connectBtn;
    QPushButton* m_cancelBtn;
    QLabel* m_statusLabel;
    
    QString m_selectedSerial;
};

#endif // DEVICELISTDIALOG_H

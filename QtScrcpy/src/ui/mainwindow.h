/**
 * QtScrcpy - Main Window
 * Copyright (C) 2024 QtScrcpy Contributors
 *
 * Licensed under the Apache License, Version 2.0
 */

#ifndef MAINWINDOW_H
#define MAINWINDOW_H

#include <QMainWindow>
#include <QListWidget>
#include <QLabel>
#include <QProgressBar>
#include <QStackedWidget>
#include <QTimer>

#include "adb/devicemanager.h"
#include "adb/devicediscovery.h"
#include "server/servermanager.h"

class VideoWidget;
class ToolbarWidget;
class VideoStream;
class AudioPlaybackStream;
class ControlStream;
class InputHandler;
class ClipboardManager;
class FileTransfer;
class Shortcuts;
class VolumeController;
class QPushButton;
class QLineEdit;

/**
 * @brief 主窗口
 */
class MainWindow : public QMainWindow
{
    Q_OBJECT

public:
    explicit MainWindow(QWidget *parent = nullptr);
    ~MainWindow();

protected:
    void closeEvent(QCloseEvent* event) override;

private slots:
    // 设备管理
    void onDevicesUpdated(const QList<DeviceInfo>& devices);
    void onDeviceDoubleClicked(QListWidgetItem* item);
    void onScanDevices();
    void onScanProgress(int current, int total);
    void onScanFinished(const QList<DiscoveredDevice>& devices);
    void onConnectDevice();
    void onDisconnectDevice();
    
    // 服务端管理
    void onServerStateChanged(ServerManager::ServerState state);
    void onServerReady(int videoPort, int audioPort, int controlPort);
    void onServerError(const QString& message);
    
    // 视频流
    void onVideoConnected();
    void onVideoDisconnected();
    void onFrameReady(const QImage& frame);
    void onDeviceInfoReceived(const QString& deviceName, int width, int height);
    
    // 工具栏操作
    void onHomeClicked();
    void onBackClicked();
    void onAppSwitchClicked();
    void onMenuClicked();
    void onPowerClicked();
    void onVolumeUpClicked();
    void onVolumeDownClicked();
    void onExpandNotificationsClicked();
    void onExpandSettingsClicked();
    void onFullscreenClicked();
    void onScreenshotClicked();
    void onRotateClicked();
    
    // 文件传输
    void onFilesDropped(const QStringList& paths);
    void onTransferStarted(const QString& fileName, bool isApk);
    void onTransferProgress(const QString& fileName, int percent);
    void onTransferCompleted(const QString& fileName, bool success, const QString& message);
    
    // 其他
    void onFpsUpdated(double fps);
    void onVideoDoubleClicked();
    void onShortcutTriggered(const QString& action);

private:
    void setupUi();
    void setupMenuBar();
    void setupStatusBar();
    void setupConnections();
    
    void connectToDevice(const QString& serial);
    void disconnectFromDevice();
    void showDeviceList();
    void showVideoView();
    void triggerAutoWirelessScan(bool force = false);
    void updateStatusBar();
    
    // UI组件
    QStackedWidget* m_stackedWidget;
    
    // 设备列表页
    QWidget* m_deviceListPage;
    QListWidget* m_deviceList;
    QPushButton* m_scanBtn;
    QPushButton* m_connectBtn;
    QProgressBar* m_scanProgress;
    QLineEdit* m_ipInput;
    
    // 视频页
    QWidget* m_videoPage;
    VideoWidget* m_videoWidget;
    ToolbarWidget* m_toolbar;
    
    // 状态栏
    QLabel* m_statusLabel;
    QLabel* m_fpsLabel;
    QLabel* m_resolutionLabel;
    
    // 核心组件
    DeviceManager* m_deviceManager;
    DeviceDiscovery* m_deviceDiscovery;
    ServerManager* m_serverManager;
    VideoStream* m_videoStream;
    AudioPlaybackStream* m_audioStream;
    ControlStream* m_controlStream;
    InputHandler* m_inputHandler;
    ClipboardManager* m_clipboardManager;
    FileTransfer* m_fileTransfer;
    Shortcuts* m_shortcuts;
    VolumeController* m_volumeController;
    
    // 状态
    QString m_currentSerial;
    bool m_isConnected;
    QTimer* m_autoScanTimer;
    bool m_autoScanEnabled;
    bool m_autoScanPausedByUser;
    bool m_manualScanInProgress;
};

#endif // MAINWINDOW_H

/**
 * QtScrcpy - Main Window
 * Copyright (C) 2024 QtScrcpy Contributors
 *
 * Licensed under the Apache License, Version 2.0
 */

#include "mainwindow.h"
#include "videowidget.h"
#include "toolbarwidget.h"
#include "adb/devicediscovery.h"
#include "adb/shortcuts.h"
#include "adb/volumecontroller.h"
#include "stream/videostream.h"
#include "stream/controlstream.h"
#include "input/inputhandler.h"
#include "clipboard/clipboardmanager.h"
#include "filetransfer/filetransfer.h"

#include <QVBoxLayout>
#include <QHBoxLayout>
#include <QMenuBar>
#include <QMenu>
#include <QStatusBar>
#include <QMessageBox>
#include <QCloseEvent>
#include <QLineEdit>
#include <QGroupBox>
#include <QKeySequence>
#include <QDebug>
#include <QSettings>

MainWindow::MainWindow(QWidget *parent)
    : QMainWindow(parent)
    , m_stackedWidget(new QStackedWidget(this))
    , m_deviceManager(DeviceManager::instance())
    , m_deviceDiscovery(new DeviceDiscovery(this))
    , m_serverManager(new ServerManager(this))
    , m_videoStream(new VideoStream(this))
    , m_controlStream(new ControlStream(this))
    , m_inputHandler(new InputHandler(this))
    , m_clipboardManager(new ClipboardManager(this))
    , m_fileTransfer(nullptr)
    , m_shortcuts(nullptr)
    , m_volumeController(nullptr)
    , m_isConnected(false)
    , m_autoScanTimer(new QTimer(this))
    , m_autoScanEnabled(true)
    , m_autoScanPausedByUser(false)
{
    setupUi();
    setupMenuBar();
    setupStatusBar();
    setupConnections();

    m_autoScanTimer->setInterval(30000);
    connect(m_autoScanTimer, &QTimer::timeout, this, [this]() {
        triggerAutoWirelessScan(false);
    });
    m_autoScanTimer->start();

    m_deviceManager->startMonitoring();
    showDeviceList();

    QTimer::singleShot(1200, this, [this]() {
        triggerAutoWirelessScan(true);
    });
}

MainWindow::~MainWindow()
{
    disconnectFromDevice();
    m_deviceManager->stopMonitoring();
}

void MainWindow::setupUi()
{
    setWindowTitle("QtScrcpy - 安卓投屏");
    setMinimumSize(400, 600);
    resize(400, 700);

    setCentralWidget(m_stackedWidget);

    m_deviceListPage = new QWidget(this);
    QVBoxLayout* deviceLayout = new QVBoxLayout(m_deviceListPage);
    deviceLayout->setContentsMargins(16, 16, 16, 16);
    deviceLayout->setSpacing(12);

    QLabel* titleLabel = new QLabel("选择设备", m_deviceListPage);
    titleLabel->setStyleSheet("font-size: 24px; font-weight: bold; margin-bottom: 8px;");
    deviceLayout->addWidget(titleLabel);

    m_deviceList = new QListWidget(m_deviceListPage);
    m_deviceList->setStyleSheet(R"(
        QListWidget {
            background-color: #252526;
            border: 1px solid #3f3f46;
            border-radius: 8px;
            padding: 4px;
        }
        QListWidget::item {
            padding: 12px;
            border-radius: 4px;
            margin: 2px;
        }
        QListWidget::item:hover {
            background-color: #2a2d2e;
        }
        QListWidget::item:selected {
            background-color: #094771;
        }
    )");
    deviceLayout->addWidget(m_deviceList, 1);

    m_scanProgress = new QProgressBar(m_deviceListPage);
    m_scanProgress->setVisible(false);
    m_scanProgress->setTextVisible(true);
    m_scanProgress->setFormat("扫描中... %p%");
    deviceLayout->addWidget(m_scanProgress);

    QGroupBox* manualGroup = new QGroupBox("手动无线连接", m_deviceListPage);
    QHBoxLayout* manualLayout = new QHBoxLayout(manualGroup);

    m_ipInput = new QLineEdit(manualGroup);
    m_ipInput->setPlaceholderText("手机 IP，例如 192.168.1.100");
    manualLayout->addWidget(m_ipInput);

    m_connectBtn = new QPushButton("连接", manualGroup);
    m_connectBtn->setFixedWidth(80);
    manualLayout->addWidget(m_connectBtn);
    deviceLayout->addWidget(manualGroup);

    QHBoxLayout* btnLayout = new QHBoxLayout();

    m_scanBtn = new QPushButton("扫描无线设备", m_deviceListPage);
    m_scanBtn->setStyleSheet(R"(
        QPushButton {
            background-color: #0e639c;
            border: none;
            border-radius: 4px;
            padding: 10px 20px;
            font-size: 14px;
        }
        QPushButton:hover {
            background-color: #1177bb;
        }
    )");
    btnLayout->addWidget(m_scanBtn);

    QPushButton* refreshBtn = new QPushButton("刷新", m_deviceListPage);
    connect(refreshBtn, &QPushButton::clicked, m_deviceManager, &DeviceManager::refreshDevices);
    btnLayout->addWidget(refreshBtn);
    deviceLayout->addLayout(btnLayout);

    QLabel* tipLabel = new QLabel(
        "提示：\n"
        "- USB：开启 USB 调试并用数据线连接。\n"
        "- 无线：手机和电脑需在同一 Wi-Fi 网段。\n"
        "- 双击设备即可开始投屏。",
        m_deviceListPage
    );
    tipLabel->setStyleSheet("color: #888888; font-size: 12px; margin-top: 8px;");
    tipLabel->setWordWrap(true);
    deviceLayout->addWidget(tipLabel);

    m_stackedWidget->addWidget(m_deviceListPage);

    m_videoPage = new QWidget(this);
    QVBoxLayout* videoLayout = new QVBoxLayout(m_videoPage);
    videoLayout->setContentsMargins(0, 0, 0, 0);
    videoLayout->setSpacing(0);

    m_toolbar = new ToolbarWidget(m_videoPage);
    videoLayout->addWidget(m_toolbar);

    m_videoWidget = new VideoWidget(m_videoPage);
    videoLayout->addWidget(m_videoWidget, 1);

    m_stackedWidget->addWidget(m_videoPage);
}

void MainWindow::setupMenuBar()
{
    QMenuBar* menuBar = this->menuBar();

    QMenu* fileMenu = menuBar->addMenu("文件(&F)");
    fileMenu->addAction("返回设备列表", this, [this]() {
        disconnectFromDevice();
        showDeviceList();
    });
    fileMenu->addSeparator();
    fileMenu->addAction("退出(&X)", this, &QMainWindow::close, QKeySequence::Quit);

    QMenu* deviceMenu = menuBar->addMenu("设备(&D)");
    deviceMenu->addAction("刷新设备", m_deviceManager, &DeviceManager::refreshDevices, QKeySequence::Refresh);
    deviceMenu->addAction("扫描无线设备", this, &MainWindow::onScanDevices);
    deviceMenu->addSeparator();
    deviceMenu->addAction("断开连接", this, &MainWindow::onDisconnectDevice);

    QMenu* controlMenu = menuBar->addMenu("控制(&C)");
    controlMenu->addAction("主页", this, &MainWindow::onHomeClicked, QKeySequence("Ctrl+H"));
    controlMenu->addAction("返回", this, &MainWindow::onBackClicked, QKeySequence("Ctrl+B"));
    controlMenu->addAction("最近任务", this, &MainWindow::onAppSwitchClicked, QKeySequence("Ctrl+S"));
    controlMenu->addSeparator();
    controlMenu->addAction("音量 +", this, &MainWindow::onVolumeUpClicked, QKeySequence("Ctrl+Up"));
    controlMenu->addAction("音量 -", this, &MainWindow::onVolumeDownClicked, QKeySequence("Ctrl+Down"));
    controlMenu->addSeparator();
    controlMenu->addAction("通知栏", this, &MainWindow::onExpandNotificationsClicked, QKeySequence("Ctrl+N"));
    controlMenu->addAction("快捷设置", this, &MainWindow::onExpandSettingsClicked, QKeySequence("Ctrl+Shift+N"));

    QMenu* viewMenu = menuBar->addMenu("视图(&V)");
    viewMenu->addAction("全屏", this, &MainWindow::onFullscreenClicked, QKeySequence::FullScreen);
    viewMenu->addAction("适应窗口", m_videoWidget, &VideoWidget::resizeToFit, QKeySequence("Ctrl+G"));
    viewMenu->addAction("原始大小", m_videoWidget, &VideoWidget::resizeToOriginal, QKeySequence("Ctrl+X"));

    QMenu* helpMenu = menuBar->addMenu("帮助(&H)");
    helpMenu->addAction("关于", this, [this]() {
        QMessageBox::about(this, "关于 QtScrcpy",
            "<h2>QtScrcpy</h2>"
            "<p>版本 1.0.0</p>"
            "<p>开源安卓投屏与控制工具</p>"
            "<p>许可证：Apache License 2.0</p>");
    });
}

void MainWindow::setupStatusBar()
{
    QStatusBar* status = statusBar();
    m_statusLabel = new QLabel("就绪");
    status->addWidget(m_statusLabel, 1);

    m_resolutionLabel = new QLabel("");
    status->addPermanentWidget(m_resolutionLabel);

    m_fpsLabel = new QLabel("");
    status->addPermanentWidget(m_fpsLabel);
}

void MainWindow::setupConnections()
{
    connect(m_deviceManager, &DeviceManager::devicesUpdated,
            this, &MainWindow::onDevicesUpdated);

    connect(m_deviceList, &QListWidget::itemDoubleClicked,
            this, &MainWindow::onDeviceDoubleClicked);
    connect(m_scanBtn, &QPushButton::clicked,
            this, &MainWindow::onScanDevices);
    connect(m_connectBtn, &QPushButton::clicked,
            this, &MainWindow::onConnectDevice);

    connect(m_deviceDiscovery, &DeviceDiscovery::scanProgress,
            this, &MainWindow::onScanProgress);
    connect(m_deviceDiscovery, &DeviceDiscovery::scanFinished,
            this, &MainWindow::onScanFinished);

    connect(m_serverManager, &ServerManager::stateChanged,
            this, &MainWindow::onServerStateChanged);
    connect(m_serverManager, &ServerManager::serverReady,
            this, &MainWindow::onServerReady);
    connect(m_serverManager, &ServerManager::error,
            this, &MainWindow::onServerError);

    connect(m_videoStream, &VideoStream::connected,
            this, &MainWindow::onVideoConnected);
    connect(m_videoStream, &VideoStream::disconnected,
            this, &MainWindow::onVideoDisconnected);
    connect(m_videoStream, &VideoStream::frameReady,
            this, &MainWindow::onFrameReady);
    connect(m_videoStream, &VideoStream::deviceInfoReceived,
            this, &MainWindow::onDeviceInfoReceived);

    connect(m_videoWidget, &VideoWidget::filesDropped,
            this, &MainWindow::onFilesDropped);
    connect(m_videoWidget, &VideoWidget::fpsUpdated,
            this, &MainWindow::onFpsUpdated);
    connect(m_videoWidget, &VideoWidget::doubleClicked,
            this, &MainWindow::onVideoDoubleClicked);

    connect(m_inputHandler, &InputHandler::shortcutTriggered,
            this, &MainWindow::onShortcutTriggered);

    connect(m_toolbar, &ToolbarWidget::homeClicked, this, &MainWindow::onHomeClicked);
    connect(m_toolbar, &ToolbarWidget::backClicked, this, &MainWindow::onBackClicked);
    connect(m_toolbar, &ToolbarWidget::appSwitchClicked, this, &MainWindow::onAppSwitchClicked);
    connect(m_toolbar, &ToolbarWidget::menuClicked, this, &MainWindow::onMenuClicked);
    connect(m_toolbar, &ToolbarWidget::powerClicked, this, &MainWindow::onPowerClicked);
    connect(m_toolbar, &ToolbarWidget::volumeUpClicked, this, &MainWindow::onVolumeUpClicked);
    connect(m_toolbar, &ToolbarWidget::volumeDownClicked, this, &MainWindow::onVolumeDownClicked);
    connect(m_toolbar, &ToolbarWidget::expandNotificationsClicked, this, &MainWindow::onExpandNotificationsClicked);
    connect(m_toolbar, &ToolbarWidget::expandSettingsClicked, this, &MainWindow::onExpandSettingsClicked);
    connect(m_toolbar, &ToolbarWidget::fullscreenClicked, this, &MainWindow::onFullscreenClicked);
    connect(m_toolbar, &ToolbarWidget::screenshotClicked, this, &MainWindow::onScreenshotClicked);
    connect(m_toolbar, &ToolbarWidget::rotateClicked, this, &MainWindow::onRotateClicked);
}

void MainWindow::closeEvent(QCloseEvent* event)
{
    disconnectFromDevice();
    event->accept();
}

void MainWindow::onDevicesUpdated(const QList<DeviceInfo>& devices)
{
    m_deviceList->clear();

    for (const DeviceInfo& info : devices) {
        QString name = info.model.isEmpty() ? info.serial : info.model;
        QString label = name;
        if (info.isWireless) {
            label += QString(" (Wi-Fi %1:%2)").arg(info.ipAddress).arg(info.port);
            label = "[Wi-Fi] " + label;
        } else {
            label += " (USB)";
            label = "[USB] " + label;
        }

        QListWidgetItem* item = new QListWidgetItem(label, m_deviceList);
        item->setData(Qt::UserRole, info.serial);
    }

    if (devices.isEmpty()) {
        QListWidgetItem* item = new QListWidgetItem("未检测到设备", m_deviceList);
        item->setFlags(item->flags() & ~Qt::ItemIsSelectable);
        item->setForeground(Qt::gray);
    }

    triggerAutoWirelessScan(false);
}

void MainWindow::onDeviceDoubleClicked(QListWidgetItem* item)
{
    const QString serial = item->data(Qt::UserRole).toString();
    if (!serial.isEmpty()) {
        connectToDevice(serial);
    }
}

void MainWindow::onScanDevices()
{
    if (m_deviceDiscovery->isScanning()) {
        m_deviceDiscovery->stopScan();
        m_autoScanPausedByUser = true;
        m_scanBtn->setText("扫描无线设备");
        m_scanProgress->setVisible(false);
        m_statusLabel->setText("扫描已停止（自动扫描已暂停）");
        return;
    }

    m_autoScanPausedByUser = false;
    m_scanBtn->setText("停止扫描");
    m_scanProgress->setVisible(true);
    m_scanProgress->setValue(0);
    m_statusLabel->setText("正在扫描当前网段中的无线 ADB 设备...");
    m_deviceDiscovery->startScan();
}

void MainWindow::onScanProgress(int current, int total)
{
    m_scanProgress->setMaximum(total);
    m_scanProgress->setValue(current);
}

void MainWindow::onScanFinished(const QList<DiscoveredDevice>& devices)
{
    m_scanBtn->setText("扫描无线设备");
    m_scanProgress->setVisible(false);

    if (devices.isEmpty()) {
        m_statusLabel->setText("当前网段未找到无线设备");
        return;
    }

    m_statusLabel->setText(QString("发现 %1 台无线设备").arg(devices.size()));

    for (const DiscoveredDevice& device : devices) {
        m_deviceManager->connectWirelessDevice(device.ip, device.port);
    }
}

void MainWindow::onConnectDevice()
{
    const QString ip = m_ipInput->text().trimmed();
    if (ip.isEmpty()) {
        QMessageBox::warning(this, "输入错误", "请输入手机 IP 地址。");
        return;
    }

    m_statusLabel->setText("正在连接 " + ip + " ...");
    if (m_deviceManager->connectWirelessDevice(ip)) {
        m_statusLabel->setText("连接成功");
        m_ipInput->clear();
    } else {
        m_statusLabel->setText("连接失败");
        QMessageBox::warning(
            this,
            "连接失败",
            "无法连接到 " + ip + "\n\n请确认已开启无线调试。");
    }
}

void MainWindow::onDisconnectDevice()
{
    disconnectFromDevice();
    showDeviceList();
}

void MainWindow::connectToDevice(const QString& serial)
{
    if (m_isConnected) {
        disconnectFromDevice();
    }

    m_currentSerial = serial;
    m_statusLabel->setText("正在连接设备 " + serial + " ...");

    m_fileTransfer = new FileTransfer(serial, this);
    m_shortcuts = new Shortcuts(serial, this);
    m_volumeController = new VolumeController(serial, this);

    connect(m_fileTransfer, &FileTransfer::transferStarted,
            this, &MainWindow::onTransferStarted);
    connect(m_fileTransfer, &FileTransfer::transferProgress,
            this, &MainWindow::onTransferProgress);
    connect(m_fileTransfer, &FileTransfer::transferCompleted,
            this, &MainWindow::onTransferCompleted);

    m_serverManager->setSerial(serial);
    m_serverManager->start();
}

void MainWindow::disconnectFromDevice()
{
    if (!m_isConnected && m_currentSerial.isEmpty()) {
        return;
    }

    m_clipboardManager->stopSync();

    if (m_volumeController) {
        m_volumeController->restore();
    }

    m_videoStream->disconnect();
    m_controlStream->disconnect();
    m_serverManager->stop();

    delete m_fileTransfer;
    m_fileTransfer = nullptr;

    delete m_shortcuts;
    m_shortcuts = nullptr;

    delete m_volumeController;
    m_volumeController = nullptr;

    m_currentSerial.clear();
    m_isConnected = false;
    m_toolbar->setConnected(false);
    m_statusLabel->setText("已断开连接");
}

void MainWindow::showDeviceList()
{
    m_stackedWidget->setCurrentWidget(m_deviceListPage);
    setWindowTitle("QtScrcpy - 安卓投屏");
    resize(400, 700);

    QTimer::singleShot(600, this, [this]() {
        triggerAutoWirelessScan(false);
    });
}

void MainWindow::showVideoView()
{
    m_stackedWidget->setCurrentWidget(m_videoPage);
}

void MainWindow::triggerAutoWirelessScan(bool force)
{
    Q_UNUSED(force)

    if (!m_autoScanEnabled || m_isConnected) {
        return;
    }
    if (m_autoScanPausedByUser) {
        return;
    }
    if (m_stackedWidget->currentWidget() != m_deviceListPage) {
        return;
    }
    if (m_deviceDiscovery->isScanning()) {
        return;
    }

    const QList<DeviceInfo> devices = m_deviceManager->getDevices();
    bool hasWireless = false;
    for (const DeviceInfo& d : devices) {
        if (d.isWireless) {
            hasWireless = true;
            break;
        }
    }
    if (hasWireless) {
        return;
    }

    m_scanBtn->setText("停止扫描");
    m_scanProgress->setVisible(true);
    m_scanProgress->setValue(0);
    m_statusLabel->setText("自动扫描 Wi-Fi 网段中...");
    m_deviceDiscovery->startScan();
}

void MainWindow::onServerStateChanged(ServerManager::ServerState state)
{
    switch (state) {
    case ServerManager::ServerState::Pushing:
        m_statusLabel->setText("正在推送服务端到设备...");
        break;
    case ServerManager::ServerState::Starting:
        m_statusLabel->setText("正在启动服务端...");
        break;
    case ServerManager::ServerState::Running:
        m_statusLabel->setText("服务端运行中");
        break;
    case ServerManager::ServerState::Error:
        m_statusLabel->setText("服务端错误");
        break;
    default:
        break;
    }
}

void MainWindow::onServerReady(int videoPort, int controlPort)
{
    qDebug() << "Server ready, connecting to ports:" << videoPort << controlPort;

    if (!m_videoStream->connectToHost("127.0.0.1", videoPort)) {
        QMessageBox::critical(this, "连接失败", "无法连接视频流。");
        disconnectFromDevice();
        return;
    }

    if (!m_controlStream->connectToHost("127.0.0.1", controlPort)) {
        QMessageBox::critical(this, "连接失败", "无法连接控制通道。");
        disconnectFromDevice();
        return;
    }

    m_inputHandler->setControlStream(m_controlStream);
    m_videoWidget->setInputHandler(m_inputHandler);

    m_clipboardManager->setControlStream(m_controlStream);
    m_clipboardManager->startSync();

    if (m_volumeController) {
        QSettings settings("QtScrcpy", "QtScrcpy");
        const bool muteOnConnect = settings.value("control/muteOnConnect", false).toBool();
        if (muteOnConnect) {
            m_volumeController->saveAndMute();
        }
    }

    m_isConnected = true;
    m_toolbar->setConnected(true);
    showVideoView();
}

void MainWindow::onServerError(const QString& message)
{
    QMessageBox::critical(this, "服务端错误", message);
    disconnectFromDevice();
    showDeviceList();
}

void MainWindow::onVideoConnected()
{
    m_statusLabel->setText("视频流已连接");
}

void MainWindow::onVideoDisconnected()
{
    m_statusLabel->setText("视频流已断开");

    if (m_isConnected) {
        disconnectFromDevice();
        showDeviceList();
        QMessageBox::warning(this, "连接断开", "与设备的连接已丢失。");
    }
}

void MainWindow::onFrameReady(const QImage& frame)
{
    if (frame.width() > 0 && frame.height() > 0 && m_resolutionLabel->text().isEmpty()) {
        m_resolutionLabel->setText(QString("%1 x %2").arg(frame.width()).arg(frame.height()));
        const QSize frameSize(frame.width(), frame.height());
        m_inputHandler->setDeviceScreenSize(frameSize);
        m_videoWidget->setDeviceScreenSize(frameSize);
        m_videoWidget->resizeToFit();
    }
    m_videoWidget->updateFrame(frame);
}

void MainWindow::onDeviceInfoReceived(const QString& deviceName, int width, int height)
{
    const QString shownName = deviceName.isEmpty() ? m_currentSerial : deviceName;
    setWindowTitle(QString("QtScrcpy - %1").arg(shownName));

    if (width > 0 && height > 0) {
        m_resolutionLabel->setText(QString("%1 x %2").arg(width).arg(height));
        const QSize deviceSize(width, height);
        m_inputHandler->setDeviceScreenSize(deviceSize);
        m_videoWidget->setDeviceScreenSize(deviceSize);
        m_videoWidget->resizeToFit();
    }
}

void MainWindow::onFpsUpdated(double fps)
{
    m_fpsLabel->setText(QString("%1 FPS").arg(fps, 0, 'f', 1));
}

void MainWindow::onVideoDoubleClicked()
{
    onFullscreenClicked();
}

void MainWindow::onHomeClicked()
{
    if (m_shortcuts) m_shortcuts->pressHome();
}

void MainWindow::onBackClicked()
{
    if (m_shortcuts) m_shortcuts->pressBack();
}

void MainWindow::onAppSwitchClicked()
{
    if (m_shortcuts) m_shortcuts->pressAppSwitch();
}

void MainWindow::onMenuClicked()
{
    if (m_shortcuts) m_shortcuts->pressMenu();
}

void MainWindow::onPowerClicked()
{
    if (m_shortcuts) m_shortcuts->pressPower();
}

void MainWindow::onVolumeUpClicked()
{
    if (m_shortcuts) m_shortcuts->volumeUp();
}

void MainWindow::onVolumeDownClicked()
{
    if (m_shortcuts) m_shortcuts->volumeDown();
}

void MainWindow::onExpandNotificationsClicked()
{
    if (m_shortcuts) m_shortcuts->expandNotifications();
}

void MainWindow::onExpandSettingsClicked()
{
    if (m_shortcuts) m_shortcuts->expandQuickSettings();
}

void MainWindow::onFullscreenClicked()
{
    m_videoWidget->setFullScreen(!m_videoWidget->isFullScreen());
}

void MainWindow::onScreenshotClicked()
{
    if (m_shortcuts) m_shortcuts->takeScreenshot();
}

void MainWindow::onRotateClicked()
{
    if (m_shortcuts) m_shortcuts->rotateScreen();
}

void MainWindow::onShortcutTriggered(const QString& action)
{
    if (action == "home") onHomeClicked();
    else if (action == "back") onBackClicked();
    else if (action == "app_switch") onAppSwitchClicked();
    else if (action == "menu") onMenuClicked();
    else if (action == "power") onPowerClicked();
    else if (action == "volume_up") onVolumeUpClicked();
    else if (action == "volume_down") onVolumeDownClicked();
    else if (action == "expand_notifications") onExpandNotificationsClicked();
    else if (action == "expand_settings") onExpandSettingsClicked();
    else if (action == "resize_to_fit") m_videoWidget->resizeToFit();
    else if (action == "resize_to_screen") m_videoWidget->resizeToOriginal();
}

void MainWindow::onFilesDropped(const QStringList& paths)
{
    if (!m_fileTransfer) {
        return;
    }

    const int count = m_fileTransfer->handleDroppedFiles(paths);
    m_statusLabel->setText(QString("正在处理 %1 个文件...").arg(count));
}

void MainWindow::onTransferStarted(const QString& fileName, bool isApk)
{
    if (isApk) {
        m_statusLabel->setText(QString("正在安装：%1").arg(fileName));
    } else {
        m_statusLabel->setText(QString("正在传输：%1").arg(fileName));
    }
}

void MainWindow::onTransferProgress(const QString& fileName, int percent)
{
    Q_UNUSED(fileName)
    m_statusLabel->setText(QString("传输进度：%1%").arg(percent));
}

void MainWindow::onTransferCompleted(const QString& fileName, bool success, const QString& message)
{
    if (success) {
        m_statusLabel->setText(QString("%1: %2").arg(fileName).arg(message));
    } else {
        QMessageBox::warning(this, "传输失败", QString("%1: %2").arg(fileName).arg(message));
    }
}

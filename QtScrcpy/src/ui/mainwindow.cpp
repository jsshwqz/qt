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
    setWindowTitle("QtScrcpy - Android Mirroring");
    setMinimumSize(400, 600);
    resize(400, 700);

    setCentralWidget(m_stackedWidget);

    m_deviceListPage = new QWidget(this);
    QVBoxLayout* deviceLayout = new QVBoxLayout(m_deviceListPage);
    deviceLayout->setContentsMargins(16, 16, 16, 16);
    deviceLayout->setSpacing(12);

    QLabel* titleLabel = new QLabel("Select Device", m_deviceListPage);
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
    m_scanProgress->setFormat("Scanning... %p%");
    deviceLayout->addWidget(m_scanProgress);

    QGroupBox* manualGroup = new QGroupBox("Manual Wireless Connection", m_deviceListPage);
    QHBoxLayout* manualLayout = new QHBoxLayout(manualGroup);

    m_ipInput = new QLineEdit(manualGroup);
    m_ipInput->setPlaceholderText("Phone IP, e.g. 192.168.1.100");
    manualLayout->addWidget(m_ipInput);

    m_connectBtn = new QPushButton("Connect", manualGroup);
    m_connectBtn->setFixedWidth(80);
    manualLayout->addWidget(m_connectBtn);
    deviceLayout->addWidget(manualGroup);

    QHBoxLayout* btnLayout = new QHBoxLayout();

    m_scanBtn = new QPushButton("Scan Wireless Devices", m_deviceListPage);
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

    QPushButton* refreshBtn = new QPushButton("Refresh", m_deviceListPage);
    connect(refreshBtn, &QPushButton::clicked, m_deviceManager, &DeviceManager::refreshDevices);
    btnLayout->addWidget(refreshBtn);
    deviceLayout->addLayout(btnLayout);

    QLabel* tipLabel = new QLabel(
        "Tips:\n"
        "- USB: enable USB debugging and connect via cable.\n"
        "- Wireless: keep phone and PC on the same Wi-Fi subnet.\n"
        "- Double-click a device to start mirroring.",
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

    QMenu* fileMenu = menuBar->addMenu("File(&F)");
    fileMenu->addAction("Back to Device List", this, [this]() {
        disconnectFromDevice();
        showDeviceList();
    });
    fileMenu->addSeparator();
    fileMenu->addAction("Exit(&X)", this, &QMainWindow::close, QKeySequence::Quit);

    QMenu* deviceMenu = menuBar->addMenu("Device(&D)");
    deviceMenu->addAction("Refresh Devices", m_deviceManager, &DeviceManager::refreshDevices, QKeySequence::Refresh);
    deviceMenu->addAction("Scan Wireless Devices", this, &MainWindow::onScanDevices);
    deviceMenu->addSeparator();
    deviceMenu->addAction("Disconnect", this, &MainWindow::onDisconnectDevice);

    QMenu* controlMenu = menuBar->addMenu("Control(&C)");
    controlMenu->addAction("Home", this, &MainWindow::onHomeClicked, QKeySequence("Ctrl+H"));
    controlMenu->addAction("Back", this, &MainWindow::onBackClicked, QKeySequence("Ctrl+B"));
    controlMenu->addAction("Recent Apps", this, &MainWindow::onAppSwitchClicked, QKeySequence("Ctrl+S"));
    controlMenu->addSeparator();
    controlMenu->addAction("Volume +", this, &MainWindow::onVolumeUpClicked, QKeySequence("Ctrl+Up"));
    controlMenu->addAction("Volume -", this, &MainWindow::onVolumeDownClicked, QKeySequence("Ctrl+Down"));
    controlMenu->addSeparator();
    controlMenu->addAction("Notifications", this, &MainWindow::onExpandNotificationsClicked, QKeySequence("Ctrl+N"));
    controlMenu->addAction("Quick Settings", this, &MainWindow::onExpandSettingsClicked, QKeySequence("Ctrl+Shift+N"));

    QMenu* viewMenu = menuBar->addMenu("View(&V)");
    viewMenu->addAction("Fullscreen", this, &MainWindow::onFullscreenClicked, QKeySequence::FullScreen);
    viewMenu->addAction("Resize to Fit", m_videoWidget, &VideoWidget::resizeToFit, QKeySequence("Ctrl+G"));
    viewMenu->addAction("Original Size", m_videoWidget, &VideoWidget::resizeToOriginal, QKeySequence("Ctrl+X"));

    QMenu* helpMenu = menuBar->addMenu("Help(&H)");
    helpMenu->addAction("About", this, [this]() {
        QMessageBox::about(this, "About QtScrcpy",
            "<h2>QtScrcpy</h2>"
            "<p>Version 1.0.0</p>"
            "<p>Open source Android mirroring and control application</p>"
            "<p>License: Apache License 2.0</p>");
    });
}

void MainWindow::setupStatusBar()
{
    QStatusBar* status = statusBar();
    m_statusLabel = new QLabel("Ready");
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
        QListWidgetItem* item = new QListWidgetItem("No device detected", m_deviceList);
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
        m_scanBtn->setText("Scan Wireless Devices");
        m_scanProgress->setVisible(false);
        m_statusLabel->setText("Scan stopped");
        return;
    }

    m_scanBtn->setText("Stop Scan");
    m_scanProgress->setVisible(true);
    m_scanProgress->setValue(0);
    m_statusLabel->setText("Scanning current subnet for wireless ADB devices...");
    m_deviceDiscovery->startScan();
}

void MainWindow::onScanProgress(int current, int total)
{
    m_scanProgress->setMaximum(total);
    m_scanProgress->setValue(current);
}

void MainWindow::onScanFinished(const QList<DiscoveredDevice>& devices)
{
    m_scanBtn->setText("Scan Wireless Devices");
    m_scanProgress->setVisible(false);

    if (devices.isEmpty()) {
        m_statusLabel->setText("No wireless device found on the current subnet");
        return;
    }

    m_statusLabel->setText(QString("Found %1 wireless device(s)").arg(devices.size()));

    for (const DiscoveredDevice& device : devices) {
        m_deviceManager->connectWirelessDevice(device.ip, device.port);
    }
}

void MainWindow::onConnectDevice()
{
    const QString ip = m_ipInput->text().trimmed();
    if (ip.isEmpty()) {
        QMessageBox::warning(this, "Input Error", "Please enter a phone IP address.");
        return;
    }

    m_statusLabel->setText("Connecting to " + ip + " ...");
    if (m_deviceManager->connectWirelessDevice(ip)) {
        m_statusLabel->setText("Connected");
        m_ipInput->clear();
    } else {
        m_statusLabel->setText("Connection failed");
        QMessageBox::warning(
            this,
            "Connection Failed",
            "Unable to connect to " + ip + "\n\nPlease ensure wireless debugging is enabled.");
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
    m_statusLabel->setText("Connecting to " + serial + " ...");

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
    m_statusLabel->setText("Disconnected");
}

void MainWindow::showDeviceList()
{
    m_stackedWidget->setCurrentWidget(m_deviceListPage);
    setWindowTitle("QtScrcpy - Android Mirroring");
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
    if (!m_autoScanEnabled || m_isConnected) {
        return;
    }
    if (m_stackedWidget->currentWidget() != m_deviceListPage) {
        return;
    }
    if (m_deviceDiscovery->isScanning()) {
        return;
    }

    if (!force) {
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
    }

    m_scanBtn->setText("Stop Scan");
    m_scanProgress->setVisible(true);
    m_scanProgress->setValue(0);
    m_statusLabel->setText("Auto scanning Wi-Fi subnet...");
    m_deviceDiscovery->startScan();
}

void MainWindow::onServerStateChanged(ServerManager::ServerState state)
{
    switch (state) {
    case ServerManager::ServerState::Pushing:
        m_statusLabel->setText("Pushing server to device...");
        break;
    case ServerManager::ServerState::Starting:
        m_statusLabel->setText("Starting server...");
        break;
    case ServerManager::ServerState::Running:
        m_statusLabel->setText("Server running");
        break;
    case ServerManager::ServerState::Error:
        m_statusLabel->setText("Server error");
        break;
    default:
        break;
    }
}

void MainWindow::onServerReady(int videoPort, int controlPort)
{
    qDebug() << "Server ready, connecting to ports:" << videoPort << controlPort;

    if (!m_videoStream->connectToHost("127.0.0.1", videoPort)) {
        QMessageBox::critical(this, "Connection Failed", "Unable to connect to video stream.");
        disconnectFromDevice();
        return;
    }

    if (!m_controlStream->connectToHost("127.0.0.1", controlPort)) {
        QMessageBox::critical(this, "Connection Failed", "Unable to connect to control stream.");
        disconnectFromDevice();
        return;
    }

    m_inputHandler->setControlStream(m_controlStream);
    m_videoWidget->setInputHandler(m_inputHandler);

    m_clipboardManager->setControlStream(m_controlStream);
    m_clipboardManager->startSync();

    if (m_volumeController) {
        m_volumeController->saveAndMute();
    }

    m_isConnected = true;
    m_toolbar->setConnected(true);
    showVideoView();
}

void MainWindow::onServerError(const QString& message)
{
    QMessageBox::critical(this, "Server Error", message);
    disconnectFromDevice();
    showDeviceList();
}

void MainWindow::onVideoConnected()
{
    m_statusLabel->setText("Video stream connected");
}

void MainWindow::onVideoDisconnected()
{
    m_statusLabel->setText("Video stream disconnected");

    if (m_isConnected) {
        disconnectFromDevice();
        showDeviceList();
        QMessageBox::warning(this, "Disconnected", "The connection to the device has been lost.");
    }
}

void MainWindow::onFrameReady(const QImage& frame)
{
    m_videoWidget->updateFrame(frame);
}

void MainWindow::onDeviceInfoReceived(const QString& deviceName, int width, int height)
{
    setWindowTitle(QString("QtScrcpy - %1").arg(deviceName));
    m_resolutionLabel->setText(QString("%1 x %2").arg(width).arg(height));

    m_inputHandler->setDeviceScreenSize(QSize(width, height));
    m_videoWidget->setDeviceScreenSize(QSize(width, height));
    m_videoWidget->resizeToFit();
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
    m_statusLabel->setText(QString("Processing %1 file(s)...").arg(count));
}

void MainWindow::onTransferStarted(const QString& fileName, bool isApk)
{
    if (isApk) {
        m_statusLabel->setText(QString("Installing: %1").arg(fileName));
    } else {
        m_statusLabel->setText(QString("Transferring: %1").arg(fileName));
    }
}

void MainWindow::onTransferProgress(const QString& fileName, int percent)
{
    Q_UNUSED(fileName)
    m_statusLabel->setText(QString("Transfer progress: %1%").arg(percent));
}

void MainWindow::onTransferCompleted(const QString& fileName, bool success, const QString& message)
{
    if (success) {
        m_statusLabel->setText(QString("%1: %2").arg(fileName).arg(message));
    } else {
        QMessageBox::warning(this, "Transfer Failed", QString("%1: %2").arg(fileName).arg(message));
    }
}

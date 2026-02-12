/**
 * QtScrcpy - Server Manager
 * Copyright (C) 2024 QtScrcpy Contributors
 *
 * Licensed under the Apache License, Version 2.0
 */

#include "servermanager.h"
#include "adb/adbprocess.h"
#include <QCoreApplication>
#include <QFileInfo>
#include <QTcpServer>
#include <QDebug>
#include <QRegularExpression>

const QString ServerManager::SERVER_FILE_NAME = "scrcpy-server";
const QString ServerManager::SERVER_PATH_ON_DEVICE = "/data/local/tmp/scrcpy-server.jar";

ServerManager::ServerManager(QObject *parent)
    : QObject(parent)
    , m_state(ServerState::Idle)
    , m_adb(new AdbProcess(this))
    , m_serverProcess(nullptr)
    , m_startTimer(new QTimer(this))
    , m_videoPort(0)
    , m_audioPort(0)
    , m_controlPort(0)
    , m_clientVersion("2.4")
    , m_startAttemptId(0)
    , m_versionRetryCount(0)
    , m_audioEnabled(false)
    , m_deviceSdk(0)
{
    m_startTimer->setSingleShot(true);
    m_startTimer->setInterval(10000); // 10绉掕秴鏃?
    connect(m_startTimer, &QTimer::timeout, this, &ServerManager::onStartTimeout);
}

ServerManager::~ServerManager()
{
    stop();
}

QString ServerManager::serverPath()
{
    // 棣栧厛妫€鏌ュ簲鐢ㄧ▼搴忕洰褰?
    QString appDir = QCoreApplication::applicationDirPath();
    QString path = appDir + "/" + SERVER_FILE_NAME;
    
    if (QFileInfo::exists(path)) {
        return path;
    }
    
    // 妫€鏌ヨ祫婧愮洰褰?
    path = appDir + "/resources/" + SERVER_FILE_NAME;
    if (QFileInfo::exists(path)) {
        return path;
    }
    
    return QString();
}

bool ServerManager::start()
{
    if (m_state != ServerState::Idle) {
        qWarning() << "Server is not in idle state";
        return false;
    }
    
    if (m_serial.isEmpty()) {
        emit error("璁惧搴忓垪鍙锋湭璁剧疆");
        return false;
    }
    
    // 妫€鏌ユ湇鍔＄鏂囦欢
    QString serverFile = serverPath();
    if (serverFile.isEmpty() || !QFileInfo::exists(serverFile)) {
        emit error("scrcpy server file not found");
        return false;
    }
    m_clientVersion = "2.4";
    m_startAttemptId = 0;
    m_versionRetryCount = 0;
    m_deviceSdk = 0;
    m_audioEnabled = false;

    const QString sdkValue = m_adb->getDeviceProperty(m_serial, "ro.build.version.sdk");
    bool sdkOk = false;
    const int sdkInt = sdkValue.trimmed().toInt(&sdkOk);
    if (sdkOk) {
        m_deviceSdk = sdkInt;
        m_audioEnabled = (sdkInt >= 30); // Android 11+
    } else {
        // Keep audio disabled if SDK cannot be detected to avoid protocol mismatch.
        qWarning() << "Failed to parse device SDK from:" << sdkValue;
    }

    qDebug() << "Device SDK:" << m_deviceSdk << "audioEnabled:" << m_audioEnabled;
    
    // 寮€濮嬫帹閫佹湇鍔＄
    return pushServer();
}

void ServerManager::stop()
{
    m_startTimer->stop();
    setState(ServerState::Stopping);
    
    if (m_serverProcess) {
        m_serverProcess->blockSignals(true);
        if (m_serverProcess->state() != QProcess::NotRunning) {
            m_serverProcess->terminate();
            if (!m_serverProcess->waitForFinished(1500)) {
                m_serverProcess->kill();
                m_serverProcess->waitForFinished(3000);
            }
        }
        delete m_serverProcess;
        m_serverProcess = nullptr;
    }
    
    // 绉婚櫎绔彛杞彂
    if (m_videoPort > 0) {
        m_adb->removeForward(m_serial, m_videoPort);
    }
    if (m_audioPort > 0) {
        m_adb->removeForward(m_serial, m_audioPort);
    }
    if (m_controlPort > 0) {
        m_adb->removeForward(m_serial, m_controlPort);
    }
    
    m_videoPort = 0;
    m_audioPort = 0;
    m_controlPort = 0;
    
    setState(ServerState::Idle);
    emit serverStopped();
}

bool ServerManager::pushServer()
{
    setState(ServerState::Pushing);
    
    QString serverFile = serverPath();
    qDebug() << "Pushing server:" << serverFile << "to" << SERVER_PATH_ON_DEVICE;
    
    // 鍚屾鎺ㄩ€?
    auto result = m_adb->executeForDevice(m_serial, 
        {"push", serverFile, SERVER_PATH_ON_DEVICE}, 30000);
    
    if (!result.success) {
        emit error("鎺ㄩ€佹湇鍔＄澶辫触: " + result.error);
        setState(ServerState::Error);
        return false;
    }
    
    // 璁剧疆绔彛杞彂
    return setupPortForward();
}

bool ServerManager::setupPortForward()
{
    m_videoPort = findFreePort(27183);
    if (m_audioEnabled) {
        m_audioPort = findFreePort(m_videoPort + 1);
        m_controlPort = findFreePort(m_audioPort + 1);
    } else {
        m_audioPort = 0;
        m_controlPort = findFreePort(m_videoPort + 1);
    }

    qDebug() << "Setting up port forward:" << m_videoPort << m_audioPort << m_controlPort;

    if (!m_adb->forwardToLocalAbstract(m_serial, m_videoPort, "scrcpy")) {
        emit error("Failed to setup video port forwarding");
        setState(ServerState::Error);
        return false;
    }

    if (m_audioEnabled) {
        if (!m_adb->forwardToLocalAbstract(m_serial, m_audioPort, "scrcpy")) {
            emit error("Failed to setup audio port forwarding");
            m_adb->removeForward(m_serial, m_videoPort);
            setState(ServerState::Error);
            return false;
        }
    }

    if (!m_adb->forwardToLocalAbstract(m_serial, m_controlPort, "scrcpy")) {
        emit error("Failed to setup control port forwarding");
        m_adb->removeForward(m_serial, m_videoPort);
        if (m_audioEnabled && m_audioPort > 0) {
            m_adb->removeForward(m_serial, m_audioPort);
        }
        setState(ServerState::Error);
        return false;
    }

    return startServer();
}
bool ServerManager::startServer()
{
    if (m_serverProcess) {
        m_serverProcess->blockSignals(true);
        m_serverProcess->kill();
        m_serverProcess->waitForFinished(2000);
        delete m_serverProcess;
        m_serverProcess = nullptr;
    }
    setState(ServerState::Starting);
    const int attemptId = ++m_startAttemptId;
    
    // 鏋勫缓鍚姩鍛戒护
    QStringList args = buildServerArgs();
    
    qDebug() << "Starting server with args:" << args;
    
    // 浣跨敤寮傛shell鍛戒护鍚姩鏈嶅姟绔?
    QString shellCmd = QString("CLASSPATH=%1 app_process / com.genymobile.scrcpy.Server %2")
        .arg(SERVER_PATH_ON_DEVICE)
        .arg(args.join(" "));
    
    m_serverProcess = new QProcess(this);
    
    connect(m_serverProcess, &QProcess::readyReadStandardOutput,
            this, &ServerManager::onServerOutput);
    connect(m_serverProcess, &QProcess::readyReadStandardError,
            this, &ServerManager::onServerOutput);
    connect(m_serverProcess, &QProcess::errorOccurred,
            this, [this](QProcess::ProcessError error) {
                Q_UNUSED(error)
                onServerError();
            });
    
    // 鏋勫缓瀹屾暣鐨刟db鍛戒护
    QStringList adbArgs;
    adbArgs << "-s" << m_serial << "shell" << shellCmd;
    
    m_serverProcess->start(m_adb->adbPath(), adbArgs);
    
    if (!m_serverProcess->waitForStarted(5000)) {
        emit error("Failed to start server process");
        setState(ServerState::Error);
        return false;
    }
    
    // 鍚姩瓒呮椂瀹氭椂鍣?
    m_startTimer->start();
    
    // 绛夊緟涓€灏忔鏃堕棿璁╂湇鍔＄鍒濆鍖?
    QTimer::singleShot(1000, this, [this, attemptId]() {
        if (m_state == ServerState::Starting &&
            attemptId == m_startAttemptId &&
            m_serverProcess &&
            m_serverProcess->state() != QProcess::NotRunning) {
            onServerStarted();
        }
    });
    
    return true;
}

void ServerManager::onServerStarted()
{
    m_startTimer->stop();
    setState(ServerState::Running);
    
    qDebug() << "Server is ready on ports:" << m_videoPort << m_audioPort << m_controlPort;
    emit serverReady(m_videoPort, m_audioPort, m_controlPort);
}

void ServerManager::onServerOutput()
{
    if (!m_serverProcess) return;
    
    QString output = QString::fromUtf8(m_serverProcess->readAllStandardOutput());
    QString error = QString::fromUtf8(m_serverProcess->readAllStandardError());
    const QString combined = output + "\n" + error;

    if (m_state == ServerState::Starting && tryHandleVersionMismatch(combined)) {
        return;
    }
    
    if (!output.isEmpty()) {
        qDebug() << "Server output:" << output;
    }
    if (!error.isEmpty()) {
        qDebug() << "Server error:" << error;
    }
}

bool ServerManager::tryHandleVersionMismatch(const QString& text)
{
    static const QRegularExpression mismatchPattern(
        "server version \\(([^)]+)\\) does not match the client \\(([^)]+)\\)",
        QRegularExpression::CaseInsensitiveOption
    );

    const QRegularExpressionMatch match = mismatchPattern.match(text);
    if (!match.hasMatch()) {
        return false;
    }

    const QString serverVersion = match.captured(1).trimmed();
    const QString clientVersion = match.captured(2).trimmed();
    qWarning() << "Detected scrcpy version mismatch. server=" << serverVersion
               << "client=" << clientVersion;

    if (serverVersion.isEmpty()) {
        return false;
    }

    if (m_versionRetryCount >= 1 || m_clientVersion == serverVersion) {
        emit error(QString("scrcpy server/client version mismatch: server=%1 client=%2")
                   .arg(serverVersion, clientVersion));
        stop();
        return true;
    }

    m_versionRetryCount++;
    m_clientVersion = serverVersion;
    qWarning() << "Retrying server startup with client version" << m_clientVersion;

    if (m_serverProcess) {
        m_serverProcess->blockSignals(true);
        m_serverProcess->kill();
        m_serverProcess->waitForFinished(2000);
        delete m_serverProcess;
        m_serverProcess = nullptr;
    }

    m_startTimer->stop();
    QTimer::singleShot(100, this, [this]() {
        if (m_state == ServerState::Starting) {
            startServer();
        }
    });
    return true;
}

void ServerManager::onServerError()
{
    if (m_state == ServerState::Stopping || m_state == ServerState::Idle) {
        return;
    }

    QString errorMsg = m_serverProcess ? m_serverProcess->errorString() : "Unknown error";
    qDebug() << "Server process error:" << errorMsg;
    emit error(QString("Server process error: %1").arg(errorMsg));
    stop();
}

void ServerManager::onStartTimeout()
{
    if (m_state == ServerState::Starting) {
        emit error("Server startup timed out");
        stop();
    }
}

void ServerManager::setState(ServerState state)
{
    if (m_state != state) {
        m_state = state;
        emit stateChanged(state);
    }
}

QStringList ServerManager::buildServerArgs() const
{
    QStringList args;
    
    // 鐗堟湰
    args << m_clientVersion;  // scrcpy server client-version marker
    
    // 鏃ュ織绾у埆
    args << "log_level=info";
    args << "video=true";
    args << QString("audio=%1").arg(m_audioEnabled ? "true" : "false");
    if (m_audioEnabled) {
        args << "audio_codec=raw";
    }
    args << "control=true";
    args << "send_device_meta=true";
    args << "send_frame_meta=false";
    args << "send_codec_meta=false";
    args << "send_dummy_byte=false";
    
    // 鏈€澶у昂瀵?
    if (m_config.maxSize > 0) {
        args << QString("max_size=%1").arg(m_config.maxSize);
    }
    
    // 姣旂壒鐜?
    args << QString("video_bit_rate=%1").arg(m_config.bitRate);
    
    // 鏈€澶у抚鐜?
    args << QString("max_fps=%1").arg(m_config.maxFps);
    
    // 瑙嗛缂栫爜
    args << QString("video_codec=%1").arg(m_config.videoCodec);
    
    // 鏂瑰悜閿佸畾
    if (m_config.lockVideoOrientation >= 0) {
        args << QString("lock_video_orientation=%1").arg(m_config.lockVideoOrientation);
    }
    
    // 闅ч亾杞彂
    args << "tunnel_forward=true";
    
    // 鎺у埗
    // 鏄剧ず瑙︽懜
    if (m_config.showTouches) {
        args << "show_touches=true";
    }
    
    // 淇濇寔鍞ら啋
    if (m_config.stayAwake) {
        args << "stay_awake=true";
    }
    
    // 鍓创鏉垮悓姝?
    if (m_config.clipboardAutosync) {
        args << "clipboard_autosync=true";
    }
    
    // 鐢垫簮鎺у埗
    if (m_config.powerOn) {
        args << "power_on=true";
    }
    
    if (m_config.powerOffOnClose) {
        args << "power_off_on_close=true";
    }
    
    return args;
}

int ServerManager::findFreePort(int startPort)
{
    QTcpServer server;
    
    for (int port = startPort; port < startPort + 100; port++) {
        if (server.listen(QHostAddress::LocalHost, port)) {
            server.close();
            return port;
        }
    }
    
    // 璁╃郴缁熷垎閰?
    if (server.listen(QHostAddress::LocalHost, 0)) {
        int port = server.serverPort();
        server.close();
        return port;
    }
    
    return startPort;
}

void ServerManager::onPushFinished()
{
    // 鐢卞悓姝ヨ皟鐢ㄥ鐞?
}

void ServerManager::onForwardFinished()
{
    // 鐢卞悓姝ヨ皟鐢ㄥ鐞?
}

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

const QString ServerManager::SERVER_FILE_NAME = "scrcpy-server";
const QString ServerManager::SERVER_PATH_ON_DEVICE = "/data/local/tmp/scrcpy-server.jar";

ServerManager::ServerManager(QObject *parent)
    : QObject(parent)
    , m_state(ServerState::Idle)
    , m_adb(new AdbProcess(this))
    , m_serverProcess(nullptr)
    , m_startTimer(new QTimer(this))
    , m_videoPort(0)
    , m_controlPort(0)
{
    m_startTimer->setSingleShot(true);
    m_startTimer->setInterval(10000); // 10秒超时
    connect(m_startTimer, &QTimer::timeout, this, &ServerManager::onStartTimeout);
}

ServerManager::~ServerManager()
{
    stop();
}

QString ServerManager::serverPath()
{
    // 首先检查应用程序目录
    QString appDir = QCoreApplication::applicationDirPath();
    QString path = appDir + "/" + SERVER_FILE_NAME;
    
    if (QFileInfo::exists(path)) {
        return path;
    }
    
    // 检查资源目录
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
        emit error("设备序列号未设置");
        return false;
    }
    
    // 检查服务端文件
    QString serverFile = serverPath();
    if (serverFile.isEmpty() || !QFileInfo::exists(serverFile)) {
        emit error("找不到scrcpy服务端文件");
        return false;
    }
    
    // 开始推送服务端
    return pushServer();
}

void ServerManager::stop()
{
    m_startTimer->stop();
    
    if (m_serverProcess) {
        m_serverProcess->kill();
        m_serverProcess->waitForFinished(3000);
        delete m_serverProcess;
        m_serverProcess = nullptr;
    }
    
    // 移除端口转发
    if (m_videoPort > 0) {
        m_adb->removeForward(m_serial, m_videoPort);
    }
    if (m_controlPort > 0) {
        m_adb->removeForward(m_serial, m_controlPort);
    }
    
    m_videoPort = 0;
    m_controlPort = 0;
    
    setState(ServerState::Idle);
    emit serverStopped();
}

bool ServerManager::pushServer()
{
    setState(ServerState::Pushing);
    
    QString serverFile = serverPath();
    qDebug() << "Pushing server:" << serverFile << "to" << SERVER_PATH_ON_DEVICE;
    
    // 同步推送
    auto result = m_adb->executeForDevice(m_serial, 
        {"push", serverFile, SERVER_PATH_ON_DEVICE}, 30000);
    
    if (!result.success) {
        emit error("推送服务端失败: " + result.error);
        setState(ServerState::Error);
        return false;
    }
    
    // 设置端口转发
    return setupPortForward();
}

bool ServerManager::setupPortForward()
{
    // 查找可用端口
    m_videoPort = findFreePort(27183);
    m_controlPort = findFreePort(m_videoPort + 1);
    
    qDebug() << "Setting up port forward:" << m_videoPort << m_controlPort;
    
    // 设置视频端口转发
    if (!m_adb->forwardToLocalAbstract(m_serial, m_videoPort, "scrcpy")) {
        emit error("设置视频端口转发失败");
        setState(ServerState::Error);
        return false;
    }
    
    // 设置控制端口转发
    if (!m_adb->forwardToLocalAbstract(m_serial, m_controlPort, "scrcpy")) {
        emit error("设置控制端口转发失败");
        m_adb->removeForward(m_serial, m_videoPort);
        setState(ServerState::Error);
        return false;
    }
    
    // 启动服务端
    return startServer();
}

bool ServerManager::startServer()
{
    setState(ServerState::Starting);
    
    // 构建启动命令
    QStringList args = buildServerArgs();
    
    qDebug() << "Starting server with args:" << args;
    
    // 使用异步shell命令启动服务端
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
    
    // 构建完整的adb命令
    QStringList adbArgs;
    adbArgs << "-s" << m_serial << "shell" << shellCmd;
    
    m_serverProcess->start(m_adb->adbPath(), adbArgs);
    
    if (!m_serverProcess->waitForStarted(5000)) {
        emit error("启动服务端进程失败");
        setState(ServerState::Error);
        return false;
    }
    
    // 启动超时定时器
    m_startTimer->start();
    
    // 等待一小段时间让服务端初始化
    QTimer::singleShot(1000, this, [this]() {
        if (m_state == ServerState::Starting) {
            onServerStarted();
        }
    });
    
    return true;
}

void ServerManager::onServerStarted()
{
    m_startTimer->stop();
    setState(ServerState::Running);
    
    qDebug() << "Server is ready on ports:" << m_videoPort << m_controlPort;
    emit serverReady(m_videoPort, m_controlPort);
}

void ServerManager::onServerOutput()
{
    if (!m_serverProcess) return;
    
    QString output = QString::fromUtf8(m_serverProcess->readAllStandardOutput());
    QString error = QString::fromUtf8(m_serverProcess->readAllStandardError());
    
    if (!output.isEmpty()) {
        qDebug() << "Server output:" << output;
    }
    if (!error.isEmpty()) {
        qDebug() << "Server error:" << error;
    }
}

void ServerManager::onServerError()
{
    QString errorMsg = m_serverProcess ? m_serverProcess->errorString() : "Unknown error";
    qDebug() << "Server process error:" << errorMsg;
    
    emit error("服务端进程错误: " + errorMsg);
    stop();
}

void ServerManager::onStartTimeout()
{
    if (m_state == ServerState::Starting) {
        emit error("服务端启动超时");
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
    
    // 版本
    args << QString("2.4");  // scrcpy-server版本
    
    // 日志级别
    args << "log_level=info";
    
    // 最大尺寸
    if (m_config.maxSize > 0) {
        args << QString("max_size=%1").arg(m_config.maxSize);
    }
    
    // 比特率
    args << QString("video_bit_rate=%1").arg(m_config.bitRate);
    
    // 最大帧率
    args << QString("max_fps=%1").arg(m_config.maxFps);
    
    // 视频编码
    args << QString("video_codec=%1").arg(m_config.videoCodec);
    
    // 方向锁定
    if (m_config.lockVideoOrientation >= 0) {
        args << QString("lock_video_orientation=%1").arg(m_config.lockVideoOrientation);
    }
    
    // 隧道转发
    args << "tunnel_forward=true";
    
    // 控制
    args << "control=true";
    
    // 显示触摸
    if (m_config.showTouches) {
        args << "show_touches=true";
    }
    
    // 保持唤醒
    if (m_config.stayAwake) {
        args << "stay_awake=true";
    }
    
    // 剪贴板同步
    if (m_config.clipboardAutosync) {
        args << "clipboard_autosync=true";
    }
    
    // 电源控制
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
    
    // 让系统分配
    if (server.listen(QHostAddress::LocalHost, 0)) {
        int port = server.serverPort();
        server.close();
        return port;
    }
    
    return startPort;
}

void ServerManager::onPushFinished()
{
    // 由同步调用处理
}

void ServerManager::onForwardFinished()
{
    // 由同步调用处理
}

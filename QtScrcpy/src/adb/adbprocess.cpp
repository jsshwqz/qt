/**
 * QtScrcpy - ADB Process Manager
 * Copyright (C) 2024 QtScrcpy Contributors
 *
 * Licensed under the Apache License, Version 2.0
 */

#include "adbprocess.h"
#include <QCoreApplication>
#include <QRegularExpression>
#include <QFileInfo>
#include <QDebug>

AdbProcess::AdbProcess(QObject *parent)
    : QObject(parent)
    , m_process(new QProcess(this))
{
    // 设置默认ADB路径
    m_adbPath = QCoreApplication::applicationDirPath() + "/adb/adb.exe";
    
    // 连接信号
    connect(m_process, &QProcess::finished, 
            this, &AdbProcess::onProcessFinished);
    connect(m_process, &QProcess::readyReadStandardOutput, 
            this, &AdbProcess::onReadyReadStandardOutput);
    connect(m_process, &QProcess::readyReadStandardError, 
            this, &AdbProcess::onReadyReadStandardError);
    connect(m_process, &QProcess::errorOccurred, 
            this, &AdbProcess::onErrorOccurred);
}

AdbProcess::~AdbProcess()
{
    cancel();
}

void AdbProcess::setAdbPath(const QString& path)
{
    m_adbPath = path;
}

bool AdbProcess::checkAdbVersion()
{
    AdbResult result = execute({"version"}, 5000);
    return result.success && result.output.contains("Android Debug Bridge");
}

QStringList AdbProcess::getDevices()
{
    QStringList devices;
    AdbResult result = execute({"devices"}, 5000);
    
    if (!result.success) {
        return devices;
    }
    
    // 解析输出
    QStringList lines = result.output.split('\n', Qt::SkipEmptyParts);
    for (const QString& line : lines) {
        if (line.startsWith("List of devices")) {
            continue;
        }
        
        if (line.contains("\tdevice") || line.contains("\tunauthorized")) {
            QString serial = line.split('\t').first().trimmed();
            if (!serial.isEmpty()) {
                devices.append(serial);
            }
        }
    }
    
    return devices;
}

AdbProcess::AdbResult AdbProcess::execute(const QStringList& args, int timeoutMs)
{
    AdbResult result;
    result.success = false;
    result.exitCode = -1;
    
    m_stdOutput.clear();
    m_stdError.clear();
    
    m_process->start(m_adbPath, args);
    
    if (!m_process->waitForStarted(5000)) {
        result.error = "Failed to start ADB process";
        return result;
    }
    
    if (!m_process->waitForFinished(timeoutMs)) {
        m_process->kill();
        result.error = "ADB command timed out";
        return result;
    }
    
    result.exitCode = m_process->exitCode();
    result.output = QString::fromUtf8(m_process->readAllStandardOutput());
    result.error = QString::fromUtf8(m_process->readAllStandardError());
    result.success = (result.exitCode == 0);
    
    return result;
}

void AdbProcess::executeAsync(const QStringList& args)
{
    m_stdOutput.clear();
    m_stdError.clear();
    m_process->start(m_adbPath, args);
}

AdbProcess::AdbResult AdbProcess::executeForDevice(const QString& serial, 
                                                    const QStringList& args, 
                                                    int timeoutMs)
{
    QStringList fullArgs;
    fullArgs << "-s" << serial << args;
    return execute(fullArgs, timeoutMs);
}

void AdbProcess::executeForDeviceAsync(const QString& serial, const QStringList& args)
{
    QStringList fullArgs;
    fullArgs << "-s" << serial << args;
    executeAsync(fullArgs);
}

bool AdbProcess::connectDevice(const QString& ip, int port)
{
    QString target = QString("%1:%2").arg(ip).arg(port);
    AdbResult result = execute({"connect", target}, 10000);
    
    return result.success && 
           (result.output.contains("connected") || result.output.contains("already connected"));
}

bool AdbProcess::disconnectDevice(const QString& ip, int port)
{
    QString target = QString("%1:%2").arg(ip).arg(port);
    AdbResult result = execute({"disconnect", target}, 5000);
    return result.success;
}

bool AdbProcess::pushFile(const QString& serial, 
                          const QString& localPath, 
                          const QString& remotePath)
{
    AdbResult result = executeForDevice(serial, {"push", localPath, remotePath}, 120000);
    return result.success;
}

bool AdbProcess::installApk(const QString& serial, 
                            const QString& apkPath, 
                            bool reinstall)
{
    QStringList args;
    args << "install";
    if (reinstall) {
        args << "-r";
    }
    args << apkPath;
    
    AdbResult result = executeForDevice(serial, args, 180000);
    return result.success && result.output.contains("Success");
}

AdbProcess::AdbResult AdbProcess::shell(const QString& serial, const QString& shellCmd)
{
    return executeForDevice(serial, {"shell", shellCmd});
}

void AdbProcess::shellAsync(const QString& serial, const QString& shellCmd)
{
    executeForDeviceAsync(serial, {"shell", shellCmd});
}

bool AdbProcess::forward(const QString& serial, int localPort, int remotePort)
{
    QString local = QString("tcp:%1").arg(localPort);
    QString remote = QString("tcp:%1").arg(remotePort);
    AdbResult result = executeForDevice(serial, {"forward", local, remote});
    return result.success;
}

bool AdbProcess::forwardToLocalAbstract(const QString& serial, 
                                         int localPort, 
                                         const QString& socketName)
{
    QString local = QString("tcp:%1").arg(localPort);
    QString remote = QString("localabstract:%1").arg(socketName);
    AdbResult result = executeForDevice(serial, {"forward", local, remote});
    return result.success;
}

bool AdbProcess::removeForward(const QString& serial, int localPort)
{
    QString local = QString("tcp:%1").arg(localPort);
    AdbResult result = executeForDevice(serial, {"forward", "--remove", local});
    return result.success;
}

QString AdbProcess::getDeviceProperty(const QString& serial, const QString& property)
{
    AdbResult result = shell(serial, QString("getprop %1").arg(property));
    if (result.success) {
        return result.output.trimmed();
    }
    return QString();
}

QString AdbProcess::getDeviceModel(const QString& serial)
{
    QString model = getDeviceProperty(serial, "ro.product.model");
    if (model.isEmpty()) {
        model = getDeviceProperty(serial, "ro.product.name");
    }
    return model;
}

QSize AdbProcess::getDeviceResolution(const QString& serial)
{
    AdbResult result = shell(serial, "wm size");
    
    if (result.success) {
        // 解析 "Physical size: 1080x1920"
        QRegularExpression re("(\\d+)x(\\d+)");
        QRegularExpressionMatch match = re.match(result.output);
        
        if (match.hasMatch()) {
            int width = match.captured(1).toInt();
            int height = match.captured(2).toInt();
            return QSize(width, height);
        }
    }
    
    return QSize(1080, 1920); // 默认值
}

void AdbProcess::cancel()
{
    if (m_process->state() != QProcess::NotRunning) {
        m_process->kill();
        m_process->waitForFinished(3000);
    }
}

bool AdbProcess::isRunning() const
{
    return m_process->state() != QProcess::NotRunning;
}

void AdbProcess::onProcessFinished(int exitCode, QProcess::ExitStatus exitStatus)
{
    Q_UNUSED(exitStatus)
    
    AdbResult result;
    result.exitCode = exitCode;
    result.output = m_stdOutput;
    result.error = m_stdError;
    result.success = (exitCode == 0);
    
    emit commandFinished(result);
}

void AdbProcess::onReadyReadStandardOutput()
{
    QString output = QString::fromUtf8(m_process->readAllStandardOutput());
    m_stdOutput += output;
    emit standardOutput(output);
    
    // 解析进度信息（用于push操作）
    if (output.contains('%')) {
        QRegularExpression re("(\\d+)%");
        QRegularExpressionMatch match = re.match(output);
        if (match.hasMatch()) {
            emit progress(match.captured(1).toInt());
        }
    }
}

void AdbProcess::onReadyReadStandardError()
{
    QString error = QString::fromUtf8(m_process->readAllStandardError());
    m_stdError += error;
    emit standardError(error);
}

void AdbProcess::onErrorOccurred(QProcess::ProcessError error)
{
    QString errorMsg;
    switch (error) {
        case QProcess::FailedToStart:
            errorMsg = "ADB进程启动失败";
            break;
        case QProcess::Crashed:
            errorMsg = "ADB进程崩溃";
            break;
        case QProcess::Timedout:
            errorMsg = "ADB命令超时";
            break;
        case QProcess::WriteError:
            errorMsg = "写入错误";
            break;
        case QProcess::ReadError:
            errorMsg = "读取错误";
            break;
        default:
            errorMsg = "未知错误";
            break;
    }
    
    m_stdError += errorMsg;
    emit standardError(errorMsg);
}

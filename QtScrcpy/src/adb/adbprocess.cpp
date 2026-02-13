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
#include <QDir>
#include <QStandardPaths>
#include <QDebug>

namespace {
QString adbExecutableName()
{
#ifdef Q_OS_WIN
    return "adb.exe";
#else
    return "adb";
#endif
}

bool isAdbDiagEnabled()
{
    static const bool enabled = (qEnvironmentVariableIntValue("QT_SCRCPY_ADB_DIAG") > 0);
    return enabled;
}

bool isRunnableAdb(const QString& adbPath)
{
    if (adbPath.trimmed().isEmpty()) {
        return false;
    }

    const QFileInfo info(adbPath);
    if (!info.exists() || !info.isFile()) {
        return false;
    }

    QProcess probe;
    probe.start(info.absoluteFilePath(), {"version"});

    if (!probe.waitForStarted(3000)) {
        return false;
    }

    if (!probe.waitForFinished(5000)) {
        probe.kill();
        probe.waitForFinished(1000);
        return false;
    }

    return probe.exitStatus() == QProcess::NormalExit && probe.exitCode() == 0;
}
}

QString AdbProcess::resolveAdbPath()
{
    const QString adbName = adbExecutableName();
    const QDir appDir(QCoreApplication::applicationDirPath());
    const QStringList candidatePaths = {
        appDir.filePath("adb/" + adbName),
        appDir.filePath(adbName),
        appDir.filePath("platform-tools/" + adbName)
    };

    const QString fromPath = QStandardPaths::findExecutable(adbName);
    QStringList orderedCandidates = candidatePaths;
    if (!fromPath.isEmpty()) {
        orderedCandidates << fromPath;
    }

    QString firstExistingPath;
    QStringList checkedPaths;
    for (const QString& candidate : orderedCandidates) {
        const QFileInfo info(candidate);
        const QString absolutePath = info.absoluteFilePath();
        if (absolutePath.isEmpty()) {
            continue;
        }
        if (checkedPaths.contains(absolutePath, Qt::CaseInsensitive)) {
            continue;
        }
        checkedPaths << absolutePath;

        if (!info.exists() || !info.isFile()) {
            continue;
        }

        if (firstExistingPath.isEmpty()) {
            firstExistingPath = absolutePath;
        }

        if (isRunnableAdb(absolutePath)) {
            return absolutePath;
        }
    }

    if (!firstExistingPath.isEmpty()) {
        return firstExistingPath;
    }

    if (!fromPath.isEmpty()) {
        return QFileInfo(fromPath).absoluteFilePath();
    }

    return QFileInfo(candidatePaths.first()).absoluteFilePath();
}

AdbProcess::AdbProcess(QObject *parent)
    : QObject(parent)
    , m_process(new QProcess(this))
{
    // 设置默认ADB路径
    m_adbPath = resolveAdbPath();
    
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
    const QString trimmedPath = path.trimmed();
    m_adbPath = trimmedPath.isEmpty() ? resolveAdbPath() : trimmedPath;
}

bool AdbProcess::checkAdbVersion()
{
    AdbResult result = execute({"version"}, 5000);
    if (result.success) {
        return true;
    }

    const QString fallbackPath = QStandardPaths::findExecutable(adbExecutableName());
    if (fallbackPath.isEmpty()) {
        return false;
    }

    const QString currentPath = QFileInfo(m_adbPath).absoluteFilePath();
    const QString fallbackAbsolutePath = QFileInfo(fallbackPath).absoluteFilePath();
    if (currentPath.compare(fallbackAbsolutePath, Qt::CaseInsensitive) == 0) {
        return false;
    }

    if (!isRunnableAdb(fallbackAbsolutePath)) {
        return false;
    }

    setAdbPath(fallbackAbsolutePath);
    result = execute({"version"}, 5000);
    return result.success;
}

QStringList AdbProcess::getDevices()
{
    QStringList devices;
    AdbResult result = execute({"devices"}, 5000);
    
    if (!result.success) {
        return devices;
    }
    
    // 解析输出
    const QString combinedOutput = result.output + "\n" + result.error;
    const QStringList lines = combinedOutput.split('\n', Qt::SkipEmptyParts);
    const QRegularExpression linePattern(
        "^\\s*(\\S+)\\s+(device|unauthorized|offline)\\b",
        QRegularExpression::CaseInsensitiveOption
    );
    for (const QString& rawLine : lines) {
        const QString line = rawLine.trimmed();
        if (line.isEmpty()) {
            continue;
        }
        if (line.startsWith("List of devices", Qt::CaseInsensitive)) {
            continue;
        }
        const QRegularExpressionMatch match = linePattern.match(line);
        if (!match.hasMatch()) {
            continue;
        }
        const QString serial = match.captured(1).trimmed();
        if (!serial.isEmpty()) {
            devices.append(serial);
        }
    }

    if (isAdbDiagEnabled()) {
        qInfo().noquote() << QString("[ADB-DIAG] devices parsed_count=%1 serials=%2")
                                 .arg(devices.size())
                                 .arg(devices.join(", "));
    }
    
    return devices;
}

AdbProcess::AdbResult AdbProcess::execute(const QStringList& args, int timeoutMs)
{
    AdbResult result;
    result.success = false;
    result.exitCode = -1;

    // Guard against overlapping commands on the shared QProcess instance.
    if (m_process->state() != QProcess::NotRunning) {
        if (!m_process->waitForFinished(1000)) {
            m_process->kill();
            m_process->waitForFinished(1000);
        }
    }
    
    m_stdOutput.clear();
    m_stdError.clear();
    
    m_process->start(m_adbPath, args);
    
    if (!m_process->waitForStarted(5000)) {
        result.error = QString("Failed to start ADB process: %1").arg(m_adbPath);
        return result;
    }
    
    if (!m_process->waitForFinished(timeoutMs)) {
        m_process->kill();
        result.error = "ADB command timed out";
        return result;
    }
    
    result.exitCode = m_process->exitCode();

    const QString remainingOutput = QString::fromUtf8(m_process->readAllStandardOutput());
    const QString remainingError = QString::fromUtf8(m_process->readAllStandardError());
    result.output = m_stdOutput + remainingOutput;
    result.error = m_stdError + remainingError;
    result.success = (m_process->exitStatus() == QProcess::NormalExit && result.exitCode == 0);

    if (isAdbDiagEnabled()) {
        const QString cmd = args.join(' ');
        if (cmd.startsWith("devices") || cmd.startsWith("version") || cmd.startsWith("start-server")) {
            qInfo().noquote() << QString("[ADB-DIAG] cmd=\"%1\" path=\"%2\" exit=%3 success=%4")
                                     .arg(cmd, m_adbPath)
                                     .arg(result.exitCode)
                                     .arg(result.success ? "1" : "0");
            if (cmd.startsWith("devices")) {
                if (!result.output.trimmed().isEmpty()) {
                    qInfo().noquote() << QString("[ADB-DIAG] devices stdout:\n%1").arg(result.output);
                }
                if (!result.error.trimmed().isEmpty()) {
                    qInfo().noquote() << QString("[ADB-DIAG] devices stderr:\n%1").arg(result.error);
                }
            }
        }
    }
    
    return result;
}

void AdbProcess::executeAsync(const QStringList& args)
{
    if (m_process->state() != QProcess::NotRunning) {
        // Avoid re-entrant start() calls on the shared async process instance.
        qWarning() << "ADB async command skipped because process is busy:" << args;
        return;
    }

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

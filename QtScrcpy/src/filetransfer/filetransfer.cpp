/**
 * QtScrcpy - File Transfer
 * Copyright (C) 2024 QtScrcpy Contributors
 *
 * Licensed under the Apache License, Version 2.0
 */

#include "filetransfer.h"
#include "adb/adbprocess.h"
#include <QFileInfo>
#include <QDebug>

FileTransfer::FileTransfer(const QString& serial, QObject *parent)
    : QObject(parent)
    , m_serial(serial)
    , m_defaultRemotePath("/sdcard/Download/")
    , m_adb(new AdbProcess(this))
    , m_isTransferring(false)
    , m_succeededCount(0)
    , m_failedCount(0)
{
    connect(m_adb, &AdbProcess::progress, this, &FileTransfer::onTransferProgress);
    connect(m_adb, &AdbProcess::commandFinished, this, &FileTransfer::onTransferFinished);
}

FileTransfer::~FileTransfer()
{
    cancel();
}

void FileTransfer::pushFile(const QString& localPath, const QString& remotePath)
{
    QFileInfo fileInfo(localPath);
    if (!fileInfo.exists()) {
        emit transferCompleted(fileInfo.fileName(), false, "文件不存在");
        return;
    }
    
    TransferTask task;
    task.localPath = localPath;
    task.remotePath = remotePath.isEmpty() 
        ? m_defaultRemotePath + fileInfo.fileName() 
        : remotePath;
    task.isApk = false;
    task.fileSize = fileInfo.size();
    
    m_taskQueue.append(task);
    
    if (!m_isTransferring) {
        processNextTask();
    }
}

void FileTransfer::installApk(const QString& apkPath, bool reinstall)
{
    Q_UNUSED(reinstall)
    
    QFileInfo fileInfo(apkPath);
    if (!fileInfo.exists()) {
        emit apkInstalled(fileInfo.fileName(), false, "APK文件不存在");
        return;
    }
    
    if (!isApkFile(apkPath)) {
        emit apkInstalled(fileInfo.fileName(), false, "不是有效的APK文件");
        return;
    }
    
    TransferTask task;
    task.localPath = apkPath;
    task.remotePath = QString(); // APK安装不需要远程路径
    task.isApk = true;
    task.fileSize = fileInfo.size();
    
    m_taskQueue.append(task);
    
    if (!m_isTransferring) {
        processNextTask();
    }
}

int FileTransfer::handleDroppedFiles(const QStringList& paths)
{
    int count = 0;
    
    for (const QString& path : paths) {
        QFileInfo fileInfo(path);
        
        if (!fileInfo.exists() || !fileInfo.isFile()) {
            continue;
        }
        
        if (isApkFile(path)) {
            installApk(path);
        } else {
            pushFile(path);
        }
        
        count++;
    }
    
    return count;
}

void FileTransfer::cancel()
{
    m_adb->cancel();
    m_taskQueue.clear();
    m_isTransferring = false;
}

void FileTransfer::processNextTask()
{
    if (m_taskQueue.isEmpty()) {
        m_isTransferring = false;
        emit allTransfersCompleted(m_succeededCount, m_failedCount);
        m_succeededCount = 0;
        m_failedCount = 0;
        return;
    }
    
    m_currentTask = m_taskQueue.takeFirst();
    m_isTransferring = true;
    
    QString fileName = getFileName(m_currentTask.localPath);
    emit transferStarted(fileName, m_currentTask.isApk);
    
    if (m_currentTask.isApk) {
        qDebug() << "Installing APK:" << m_currentTask.localPath;
        m_adb->executeForDeviceAsync(m_serial, {"install", "-r", m_currentTask.localPath});
    } else {
        qDebug() << "Pushing file:" << m_currentTask.localPath << "to" << m_currentTask.remotePath;
        m_adb->executeForDeviceAsync(m_serial, {"push", m_currentTask.localPath, m_currentTask.remotePath});
    }
}

void FileTransfer::onTransferProgress(int percent)
{
    QString fileName = getFileName(m_currentTask.localPath);
    emit transferProgress(fileName, percent);
}

void FileTransfer::onTransferFinished(const AdbProcess::AdbResult& result)
{
    QString fileName = getFileName(m_currentTask.localPath);
    
    if (m_currentTask.isApk) {
        bool success = result.success && result.output.contains("Success");
        
        if (success) {
            m_succeededCount++;
            emit apkInstalled(fileName, true, "安装成功");
        } else {
            m_failedCount++;
            QString errorMsg = "安装失败";
            
            // 解析错误信息
            if (result.output.contains("INSTALL_FAILED_ALREADY_EXISTS")) {
                errorMsg = "应用已存在";
            } else if (result.output.contains("INSTALL_FAILED_INSUFFICIENT_STORAGE")) {
                errorMsg = "存储空间不足";
            } else if (result.output.contains("INSTALL_FAILED_INVALID_APK")) {
                errorMsg = "无效的APK文件";
            } else if (result.output.contains("INSTALL_FAILED_VERSION_DOWNGRADE")) {
                errorMsg = "版本降级被拒绝";
            } else if (!result.error.isEmpty()) {
                errorMsg = result.error;
            }
            
            emit apkInstalled(fileName, false, errorMsg);
        }
    } else {
        if (result.success) {
            m_succeededCount++;
            emit transferCompleted(fileName, true, "传输成功");
        } else {
            m_failedCount++;
            emit transferCompleted(fileName, false, result.error.isEmpty() ? "传输失败" : result.error);
        }
    }
    
    // 处理下一个任务
    processNextTask();
}

bool FileTransfer::isApkFile(const QString& path) const
{
    return path.toLower().endsWith(".apk");
}

QString FileTransfer::getFileName(const QString& path) const
{
    return QFileInfo(path).fileName();
}

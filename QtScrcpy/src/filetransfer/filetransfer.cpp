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
        emit transferCompleted(fileInfo.fileName(), false, "File does not exist");
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
        emit apkInstalled(fileInfo.fileName(), false, "APK file does not exist");
        return;
    }
    
    if (!isApkFile(apkPath)) {
        emit apkInstalled(fileInfo.fileName(), false, "Not a valid APK file");
        return;
    }
    
    TransferTask task;
    task.localPath = apkPath;
    task.remotePath = QString(); // APK闁诲海鎳撻ˇ鎶剿夋繝鍐枖鐎广儱顦版禒姗€鎮烽弴姘グ缂佺粯鐟х划娆戔偓锝庡幘閻斿懐鈧?
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
            emit apkInstalled(fileName, true, "Install succeeded");
        } else {
            m_failedCount++;
            QString errorMsg = "闁诲海鎳撻ˇ鎶剿夋繝鍐ㄧ窞閺夊牜鍋夎";
            
            // 闁荤喐鐟辩徊楣冩倵娴犲鐓ユ繛鍡樺俯閸ゆ牕菐閸ワ絽澧插ù?
            if (result.output.contains("INSTALL_FAILED_ALREADY_EXISTS")) {
                errorMsg = "App already installed";
            } else if (result.output.contains("INSTALL_FAILED_INSUFFICIENT_STORAGE")) {
                errorMsg = "Insufficient storage on device";
            } else if (result.output.contains("INSTALL_FAILED_INVALID_APK")) {
                errorMsg = "Invalid APK file";
            } else if (result.output.contains("INSTALL_FAILED_VERSION_DOWNGRADE")) {
                errorMsg = "Version downgrade is not allowed";
            } else if (!result.error.isEmpty()) {
                errorMsg = result.error;
            }
            
            emit apkInstalled(fileName, false, errorMsg);
        }
    } else {
        if (result.success) {
            m_succeededCount++;
            emit transferCompleted(fileName, true, "Transfer succeeded");
        } else {
            m_failedCount++;
            emit transferCompleted(fileName, false, result.error.isEmpty() ? "Transfer failed" : result.error);
        }
    }
    
    // 婵犮垼娉涚€氼噣骞冩繝鍐枖閻庯絺鏅濋鍗炩槈閹垮啩绨烽柟骞垮灲瀹?
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

/**
 * QtScrcpy - File Transfer
 * Copyright (C) 2024 QtScrcpy Contributors
 *
 * Licensed under the Apache License, Version 2.0
 */

#ifndef FILETRANSFER_H
#define FILETRANSFER_H

#include <QObject>
#include <QString>
#include <QStringList>
#include <QThread>

#include "adb/adbprocess.h"

/**
 * @brief 传输任务信息
 */
struct TransferTask {
    QString localPath;
    QString remotePath;
    bool isApk;
    qint64 fileSize;
};

/**
 * @brief 文件传输器
 * 
 * 负责APK安装和文件推送
 */
class FileTransfer : public QObject
{
    Q_OBJECT

public:
    explicit FileTransfer(const QString& serial, QObject *parent = nullptr);
    ~FileTransfer();

    /**
     * @brief 设置设备序列号
     */
    void setSerial(const QString& serial) { m_serial = serial; }

    /**
     * @brief 推送文件到设备
     * @param localPath 本地文件路径
     * @param remotePath 设备目标路径（默认/sdcard/Download/）
     */
    void pushFile(const QString& localPath, const QString& remotePath = QString());

    /**
     * @brief 安装APK
     * @param apkPath APK文件路径
     * @param reinstall 是否重新安装（覆盖）
     */
    void installApk(const QString& apkPath, bool reinstall = true);

    /**
     * @brief 处理拖放的文件
     * @param paths 文件路径列表
     * @return 成功处理的文件数
     */
    int handleDroppedFiles(const QStringList& paths);

    /**
     * @brief 是否正在传输
     */
    bool isTransferring() const { return m_isTransferring; }

    /**
     * @brief 取消当前传输
     */
    void cancel();

    /**
     * @brief 设置默认远程路径
     */
    void setDefaultRemotePath(const QString& path) { m_defaultRemotePath = path; }

signals:
    /**
     * @brief 传输开始信号
     */
    void transferStarted(const QString& fileName, bool isApk);

    /**
     * @brief 传输进度信号
     */
    void transferProgress(const QString& fileName, int percent);

    /**
     * @brief 传输完成信号
     */
    void transferCompleted(const QString& fileName, bool success, const QString& message);

    /**
     * @brief APK安装完成信号
     */
    void apkInstalled(const QString& apkName, bool success, const QString& message);

    /**
     * @brief 所有传输完成信号
     */
    void allTransfersCompleted(int succeeded, int failed);

private slots:
    void onTransferProgress(int percent);
    void onTransferFinished(const AdbProcess::AdbResult& result);

private:
    void processNextTask();
    bool isApkFile(const QString& path) const;
    QString getFileName(const QString& path) const;
    
    QString m_serial;
    QString m_defaultRemotePath;
    AdbProcess* m_adb;
    
    QList<TransferTask> m_taskQueue;
    TransferTask m_currentTask;
    bool m_isTransferring;
    int m_succeededCount;
    int m_failedCount;
};

#endif // FILETRANSFER_H

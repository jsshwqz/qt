/**
 * QtScrcpy - ADB Process Manager
 * Copyright (C) 2024 QtScrcpy Contributors
 *
 * Licensed under the Apache License, Version 2.0
 */

#ifndef ADBPROCESS_H
#define ADBPROCESS_H

#include <QObject>
#include <QProcess>
#include <QString>
#include <QStringList>
#include <QSize>

/**
 * @brief ADB进程管理类
 * 
 * 封装ADB命令的执行，提供异步和同步两种执行方式
 */
class AdbProcess : public QObject
{
    Q_OBJECT

public:
    static QString resolveAdbPath();
    /**
     * @brief ADB命令执行结果
     */
    struct AdbResult {
        bool success;
        QString output;
        QString error;
        int exitCode;
    };

    explicit AdbProcess(QObject *parent = nullptr);
    ~AdbProcess();

    /**
     * @brief 设置ADB可执行文件路径
     * @param path ADB路径
     */
    void setAdbPath(const QString& path);

    /**
     * @brief 获取ADB路径
     */
    QString adbPath() const { return m_adbPath; }

    /**
     * @brief 检查ADB版本
     * @return 是否成功执行
     */
    bool checkAdbVersion();

    /**
     * @brief 获取已连接的设备列表
     * @return 设备序列号列表
     */
    QStringList getDevices();

    /**
     * @brief 同步执行ADB命令
     * @param args 命令参数
     * @param timeoutMs 超时时间（毫秒）
     * @return 执行结果
     */
    AdbResult execute(const QStringList& args, int timeoutMs = 30000);

    /**
     * @brief 异步执行ADB命令
     * @param args 命令参数
     */
    void executeAsync(const QStringList& args);

    /**
     * @brief 针对特定设备执行命令
     * @param serial 设备序列号
     * @param args 命令参数
     * @param timeoutMs 超时时间
     * @return 执行结果
     */
    AdbResult executeForDevice(const QString& serial, const QStringList& args, int timeoutMs = 30000);

    /**
     * @brief 异步针对特定设备执行命令
     */
    void executeForDeviceAsync(const QString& serial, const QStringList& args);

    /**
     * @brief 通过TCP/IP连接设备
     * @param ip IP地址
     * @param port 端口号（默认5555）
     * @return 是否成功
     */
    bool connectDevice(const QString& ip, int port = 5555);

    /**
     * @brief 断开TCP/IP连接的设备
     */
    bool disconnectDevice(const QString& ip, int port = 5555);

    /**
     * @brief 推送文件到设备
     * @param serial 设备序列号
     * @param localPath 本地文件路径
     * @param remotePath 设备文件路径
     * @return 是否成功
     */
    bool pushFile(const QString& serial, const QString& localPath, const QString& remotePath);

    /**
     * @brief 安装APK
     * @param serial 设备序列号
     * @param apkPath APK文件路径
     * @param reinstall 是否重新安装
     * @return 是否成功
     */
    bool installApk(const QString& serial, const QString& apkPath, bool reinstall = true);

    /**
     * @brief 执行shell命令
     * @param serial 设备序列号
     * @param shellCmd Shell命令
     * @return 执行结果
     */
    AdbResult shell(const QString& serial, const QString& shellCmd);

    /**
     * @brief 异步执行shell命令
     */
    void shellAsync(const QString& serial, const QString& shellCmd);

    /**
     * @brief 转发端口
     * @param serial 设备序列号
     * @param localPort 本地端口
     * @param remotePort 远程端口
     * @return 是否成功
     */
    bool forward(const QString& serial, int localPort, int remotePort);

    /**
     * @brief 转发到本地抽象套接字
     * @param serial 设备序列号
     * @param localPort 本地端口
     * @param socketName 套接字名称
     * @return 是否成功
     */
    bool forwardToLocalAbstract(const QString& serial, int localPort, const QString& socketName);

    /**
     * @brief 移除端口转发
     */
    bool removeForward(const QString& serial, int localPort);

    /**
     * @brief 获取设备属性
     * @param serial 设备序列号
     * @param property 属性名
     * @return 属性值
     */
    QString getDeviceProperty(const QString& serial, const QString& property);

    /**
     * @brief 获取设备型号
     */
    QString getDeviceModel(const QString& serial);

    /**
     * @brief 获取设备分辨率
     * @return QSize(width, height)
     */
    QSize getDeviceResolution(const QString& serial);

    /**
     * @brief 取消当前正在执行的命令
     */
    void cancel();

    /**
     * @brief 检查是否正在执行
     */
    bool isRunning() const;

signals:
    /**
     * @brief 异步命令完成信号
     */
    void commandFinished(const AdbResult& result);

    /**
     * @brief 标准输出信号
     */
    void standardOutput(const QString& output);

    /**
     * @brief 标准错误信号
     */
    void standardError(const QString& error);

    /**
     * @brief 进度信号（用于文件传输）
     */
    void progress(int percent);

private slots:
    void onProcessFinished(int exitCode, QProcess::ExitStatus exitStatus);
    void onReadyReadStandardOutput();
    void onReadyReadStandardError();
    void onErrorOccurred(QProcess::ProcessError error);

private:
    QString m_adbPath;
    QProcess* m_process;
    QString m_stdOutput;
    QString m_stdError;
};

#endif // ADBPROCESS_H

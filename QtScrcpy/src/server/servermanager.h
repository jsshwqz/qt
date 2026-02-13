/**
 * QtScrcpy - Server Manager
 * Copyright (C) 2024 QtScrcpy Contributors
 *
 * Licensed under the Apache License, Version 2.0
 */

#ifndef SERVERMANAGER_H
#define SERVERMANAGER_H

#include <QObject>
#include <QString>
#include <QProcess>
#include <QTimer>

class AdbProcess;

/**
 * @brief scrcpy服务端配置
 */
struct ServerConfig {
    int maxSize = 0;           // 最大尺寸（0表示不限制）
    int bitRate = 8000000;     // 比特率（默认8Mbps）
    int maxFps = 60;           // 最大帧率
    bool stayAwake = true;     // 保持唤醒
    bool showTouches = false;  // 显示触摸点
    bool powerOffOnClose = false; // 关闭时息屏
    QString videoCodec = "h264"; // 视频编码
    int lockVideoOrientation = -1; // 锁定方向（-1不锁定）
    bool clipboardAutosync = true; // 自动同步剪贴板
    bool powerOn = true;       // 投屏时点亮屏幕
};

/**
 * @brief scrcpy服务端管理器
 * 
 * 负责推送和启动scrcpy服务端
 */
class ServerManager : public QObject
{
    Q_OBJECT

public:
    /**
     * @brief 服务端状态
     */
    enum class ServerState {
        Idle,
        Pushing,
        Starting,
        Running,
        Stopping,
        Error
    };
    Q_ENUM(ServerState)

    explicit ServerManager(QObject *parent = nullptr);
    ~ServerManager();

    /**
     * @brief 设置设备序列号
     */
    void setSerial(const QString& serial) { m_serial = serial; }

    /**
     * @brief 获取设备序列号
     */
    QString serial() const { return m_serial; }

    /**
     * @brief 设置服务端配置
     */
    void setConfig(const ServerConfig& config) { m_config = config; }

    /**
     * @brief 获取配置
     */
    ServerConfig config() const { return m_config; }

    /**
     * @brief 启动服务端
     * @return 是否成功启动
     */
    bool start();

    /**
     * @brief 停止服务端
     */
    void stop();

    /**
     * @brief 获取当前状态
     */
    ServerState state() const { return m_state; }

    /**
     * @brief 获取视频端口
     */
    int videoPort() const { return m_videoPort; }

    /**
     * @brief 获取控制端口
     */
    int controlPort() const { return m_controlPort; }
    int audioPort() const { return m_audioPort; }

    /**
     * @brief 服务端JAR路径
     */
    static QString serverPath();

signals:
    /**
     * @brief 状态改变信号
     */
    void stateChanged(ServerState state);

    /**
     * @brief 服务端就绪信号
     */
    void serverReady(int videoPort, int audioPort, int controlPort);

    /**
     * @brief 服务端停止信号
     */
    void serverStopped();

    /**
     * @brief 错误信号
     */
    void error(const QString& message);

private slots:
    void onPushFinished();
    void onForwardFinished();
    void onServerStarted();
    void onServerOutput();
    void onServerError();
    void onStartTimeout();

private:
    bool pushServer();
    bool setupPortForward();
    bool startServer();
    bool prepareAudioFallbackIfNeeded();
    bool prepareSndcpyFallback();
    bool ensureSndcpyInstalled(const QString& apkPath);
    bool launchSndcpyApp();
    static QString sndcpyApkPath();
    bool tryHandleVersionMismatch(const QString& text);
    void setState(ServerState state);
    QStringList buildServerArgs() const;
    int findFreePort(int startPort = 27183);
    
    QString m_serial;
    ServerConfig m_config;
    ServerState m_state;
    
    AdbProcess* m_adb;
    QProcess* m_serverProcess;
    QTimer* m_startTimer;
    
    int m_videoPort;
    int m_audioPort;
    int m_controlPort;
    QString m_clientVersion;
    int m_startAttemptId;
    int m_versionRetryCount;
    bool m_audioEnabled;
    bool m_useSndcpyFallback;
    int m_deviceSdk;
    
    static const QString SERVER_FILE_NAME;
    static const QString SERVER_PATH_ON_DEVICE;
    static const QString SNDCPY_PACKAGE_NAME;
    static const QString SNDCPY_ACTIVITY_NAME;
    static const int SERVER_VERSION = 2;  // 协议版本
};

#endif // SERVERMANAGER_H

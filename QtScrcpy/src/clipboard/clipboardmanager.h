/**
 * QtScrcpy - Clipboard Manager
 * Copyright (C) 2024 QtScrcpy Contributors
 *
 * Licensed under the Apache License, Version 2.0
 */

#ifndef CLIPBOARDMANAGER_H
#define CLIPBOARDMANAGER_H

#include <QObject>
#include <QClipboard>
#include <QString>

class ControlStream;

/**
 * @brief 剪贴板管理器
 * 
 * 实现电脑和手机之间的双向剪贴板同步
 */
class ClipboardManager : public QObject
{
    Q_OBJECT

public:
    explicit ClipboardManager(QObject *parent = nullptr);
    ~ClipboardManager();

    /**
     * @brief 设置控制流
     */
    void setControlStream(ControlStream* stream);

    /**
     * @brief 开始同步
     */
    void startSync();

    /**
     * @brief 停止同步
     */
    void stopSync();

    /**
     * @brief 是否正在同步
     */
    bool isSyncing() const { return m_syncing; }

    /**
     * @brief 发送文本到设备
     */
    void sendToDevice(const QString& text);

    /**
     * @brief 从设备获取剪贴板
     */
    void getFromDevice();

    /**
     * @brief 设置是否自动粘贴
     */
    void setAutoPaste(bool enabled) { m_autoPaste = enabled; }

signals:
    /**
     * @brief 设备剪贴板变化信号
     */
    void deviceClipboardChanged(const QString& text);

    /**
     * @brief 本地剪贴板变化信号
     */
    void localClipboardChanged(const QString& text);

    /**
     * @brief 同步完成信号
     */
    void syncCompleted(bool success);

private slots:
    void onLocalClipboardChanged();
    void onDeviceClipboardReceived(const QString& text);

private:
    QClipboard* m_clipboard;
    ControlStream* m_controlStream;
    bool m_syncing;
    bool m_autoPaste;
    QString m_lastLocalText;
    QString m_lastDeviceText;
    qint64 m_clipboardSequence;
    bool m_ignoreLocalChange;
};

#endif // CLIPBOARDMANAGER_H

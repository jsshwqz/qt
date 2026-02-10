/**
 * QtScrcpy - Volume Controller
 * Copyright (C) 2024 QtScrcpy Contributors
 *
 * Licensed under the Apache License, Version 2.0
 */

#ifndef VOLUMECONTROLLER_H
#define VOLUMECONTROLLER_H

#include <QObject>
#include <QString>
#include <QMap>

class AdbProcess;

/**
 * @brief 音量流类型
 */
enum class AudioStream {
    Voice = 0,      // 语音
    System = 1,     // 系统
    Ring = 2,       // 铃声
    Music = 3,      // 媒体
    Alarm = 4,      // 闹钟
    Notification = 5// 通知
};

/**
 * @brief 音量控制器
 * 
 * 管理设备音量，支持投屏时静音和断开后恢复
 */
class VolumeController : public QObject
{
    Q_OBJECT

public:
    explicit VolumeController(const QString& serial, QObject *parent = nullptr);
    ~VolumeController();

    /**
     * @brief 设置设备序列号
     */
    void setSerial(const QString& serial) { m_serial = serial; }

    /**
     * @brief 保存当前音量并静音
     */
    void saveAndMute();

    /**
     * @brief 恢复保存的音量
     */
    void restore();

    /**
     * @brief 获取指定流的音量
     * @param stream 音量流类型
     * @return 音量值 (0-15)
     */
    int getVolume(AudioStream stream);

    /**
     * @brief 设置指定流的音量
     * @param stream 音量流类型
     * @param volume 音量值 (0-15)
     */
    void setVolume(AudioStream stream, int volume);

    /**
     * @brief 获取媒体音量
     */
    int getMediaVolume() { return getVolume(AudioStream::Music); }

    /**
     * @brief 设置媒体音量
     */
    void setMediaVolume(int volume) { setVolume(AudioStream::Music, volume); }

    /**
     * @brief 检查是否已静音
     */
    bool isMuted() const { return m_isMuted; }

    /**
     * @brief 获取最大音量
     */
    int getMaxVolume(AudioStream stream);

signals:
    /**
     * @brief 音量恢复完成信号
     */
    void volumeRestored();

    /**
     * @brief 静音完成信号
     */
    void muted();

private:
    QString getStreamName(AudioStream stream) const;
    int getStreamIndex(AudioStream stream) const;
    
    QString m_serial;
    AdbProcess* m_adb;
    QMap<AudioStream, int> m_savedVolumes;
    bool m_isMuted;
};

#endif // VOLUMECONTROLLER_H

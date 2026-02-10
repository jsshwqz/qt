/**
 * QtScrcpy - Volume Controller
 * Copyright (C) 2024 QtScrcpy Contributors
 *
 * Licensed under the Apache License, Version 2.0
 */

#include "volumecontroller.h"
#include "adbprocess.h"
#include <QRegularExpression>
#include <QDebug>

VolumeController::VolumeController(const QString& serial, QObject *parent)
    : QObject(parent)
    , m_serial(serial)
    , m_adb(new AdbProcess(this))
    , m_isMuted(false)
{
}

VolumeController::~VolumeController()
{
    // 确保断开时恢复音量
    if (m_isMuted) {
        restore();
    }
}

void VolumeController::saveAndMute()
{
    if (m_isMuted) {
        return;
    }
    
    // 保存所有音量流
    m_savedVolumes[AudioStream::Music] = getVolume(AudioStream::Music);
    m_savedVolumes[AudioStream::Ring] = getVolume(AudioStream::Ring);
    m_savedVolumes[AudioStream::Notification] = getVolume(AudioStream::Notification);
    m_savedVolumes[AudioStream::Alarm] = getVolume(AudioStream::Alarm);
    m_savedVolumes[AudioStream::System] = getVolume(AudioStream::System);
    
    qDebug() << "Saved volume streams:" << m_savedVolumes.size();
    
    // 静音媒体音量（主要）
    setVolume(AudioStream::Music, 0);
    
    m_isMuted = true;
    emit muted();
}

void VolumeController::restore()
{
    if (!m_isMuted) {
        return;
    }
    
    // 恢复所有保存的音量
    for (auto it = m_savedVolumes.begin(); it != m_savedVolumes.end(); ++it) {
        setVolume(it.key(), it.value());
    }
    
    qDebug() << "Restored volume streams:" << m_savedVolumes.size();
    
    m_savedVolumes.clear();
    m_isMuted = false;
    emit volumeRestored();
}

int VolumeController::getVolume(AudioStream stream)
{
    int streamIndex = getStreamIndex(stream);
    
    // 使用 media 命令获取音量
    QString cmd = QString("media volume --stream %1 --get").arg(streamIndex);
    auto result = m_adb->shell(m_serial, cmd);
    
    if (result.success) {
        // 解析输出: "volume is 10 in range [0..15]"
        QRegularExpression re("volume is (\\d+)");
        QRegularExpressionMatch match = re.match(result.output);
        if (match.hasMatch()) {
            return match.captured(1).toInt();
        }
    }
    
    // 备用方法：使用 settings
    cmd = QString("settings get system volume_%1").arg(getStreamName(stream));
    result = m_adb->shell(m_serial, cmd);
    
    if (result.success) {
        return result.output.trimmed().toInt();
    }
    
    return 0;
}

void VolumeController::setVolume(AudioStream stream, int volume)
{
    int streamIndex = getStreamIndex(stream);
    
    // 限制音量范围
    volume = qBound(0, volume, 15);
    
    // 使用 media 命令设置音量
    QString cmd = QString("media volume --stream %1 --set %2").arg(streamIndex).arg(volume);
    m_adb->shell(m_serial, cmd);
}

int VolumeController::getMaxVolume(AudioStream stream)
{
    int streamIndex = getStreamIndex(stream);
    
    QString cmd = QString("media volume --stream %1 --get").arg(streamIndex);
    auto result = m_adb->shell(m_serial, cmd);
    
    if (result.success) {
        // 解析输出: "volume is 10 in range [0..15]"
        QRegularExpression re("\\[0\\.\\.(\\d+)\\]");
        QRegularExpressionMatch match = re.match(result.output);
        if (match.hasMatch()) {
            return match.captured(1).toInt();
        }
    }
    
    return 15; // 默认最大值
}

QString VolumeController::getStreamName(AudioStream stream) const
{
    switch (stream) {
        case AudioStream::Voice:
            return "voice";
        case AudioStream::System:
            return "system";
        case AudioStream::Ring:
            return "ring";
        case AudioStream::Music:
            return "music";
        case AudioStream::Alarm:
            return "alarm";
        case AudioStream::Notification:
            return "notification";
        default:
            return "music";
    }
}

int VolumeController::getStreamIndex(AudioStream stream) const
{
    return static_cast<int>(stream);
}

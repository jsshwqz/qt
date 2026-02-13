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

namespace {
bool commandLooksSuccessful(const AdbProcess::AdbResult& result)
{
    if (!result.success) {
        return false;
    }

    const QString combined = (result.output + "\n" + result.error).toLower();
    if (combined.contains("not found") ||
        combined.contains("unknown command") ||
        combined.contains("exception") ||
        combined.contains("error:")) {
        return false;
    }
    return true;
}
}

VolumeController::VolumeController(const QString& serial, QObject *parent)
    : QObject(parent)
    , m_serial(serial)
    , m_adb(new AdbProcess(this))
    , m_isMuted(false)
{
}

VolumeController::~VolumeController()
{
    // 绾喕绻氶弬顓炵磻閺冭埖浠径宥夌叾闁?
    if (m_isMuted) {
        restore();
    }
}

void VolumeController::saveAndMute()
{
    if (m_isMuted) {
        return;
    }
    
    // 娣囨繂鐡ㄩ幍鈧張澶愮叾闁插繑绁?
    m_savedVolumes[AudioStream::Music] = getVolume(AudioStream::Music);
    m_savedVolumes[AudioStream::Ring] = getVolume(AudioStream::Ring);
    m_savedVolumes[AudioStream::Notification] = getVolume(AudioStream::Notification);
    m_savedVolumes[AudioStream::Alarm] = getVolume(AudioStream::Alarm);
    m_savedVolumes[AudioStream::System] = getVolume(AudioStream::System);
    m_savedVolumes[AudioStream::Voice] = getVolume(AudioStream::Voice);
    
    qDebug() << "Saved volume streams:" << m_savedVolumes.size();
    
    // 闂堟瑩鐓舵刊鎺嶇秼闂婃娊鍣洪敍鍫滃瘜鐟曚緤绱?
    setVolume(AudioStream::Music, 0);
    setVolume(AudioStream::Ring, 0);
    setVolume(AudioStream::Notification, 0);
    setVolume(AudioStream::Alarm, 0);
    setVolume(AudioStream::System, 0);
    setVolume(AudioStream::Voice, 0);
    
    m_isMuted = true;
    emit muted();
}

void VolumeController::restore()
{
    if (!m_isMuted) {
        return;
    }
    
    // 閹垹顦查幍鈧張澶夌箽鐎涙娈戦棅鎶藉櫤
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
    const int streamIndex = getStreamIndex(stream);

    const QStringList probes = {
        QString("media volume --stream %1 --get").arg(streamIndex),
        QString("cmd media_session volume --stream %1 --get").arg(streamIndex)
    };

    for (const QString& cmd : probes) {
        const auto result = m_adb->shell(m_serial, cmd);
        if (!commandLooksSuccessful(result)) {
            continue;
        }

        const QString combined = result.output + "\n" + result.error;
        const QRegularExpression re("volume is (\\d+)");
        const QRegularExpressionMatch match = re.match(combined);
        if (match.hasMatch()) {
            return match.captured(1).toInt();
        }
    }

    const QString settingsCmd = QString("settings get system volume_%1").arg(getStreamName(stream));
    const auto settingsResult = m_adb->shell(m_serial, settingsCmd);
    if (commandLooksSuccessful(settingsResult)) {
        bool ok = false;
        const int parsed = settingsResult.output.trimmed().toInt(&ok);
        if (ok) {
            return parsed;
        }
    }

    return 0;
}

void VolumeController::setVolume(AudioStream stream, int volume)
{
    const int streamIndex = getStreamIndex(stream);
    volume = qBound(0, volume, 15);

    const QStringList commands = {
        QString("media volume --stream %1 --set %2").arg(streamIndex).arg(volume),
        QString("cmd media_session volume --stream %1 --set %2").arg(streamIndex).arg(volume),
        QString("cmd audio set-stream-volume %1 %2").arg(streamIndex).arg(volume)
    };

    bool applied = false;
    for (const QString& cmd : commands) {
        const auto result = m_adb->shell(m_serial, cmd);
        if (commandLooksSuccessful(result)) {
            applied = true;
            break;
        }
    }

    if (!applied) {
        qWarning() << "Failed to apply volume command for stream" << streamIndex
                   << "target" << volume;
        return;
    }

    if (volume == 0) {
        const int verified = getVolume(stream);
        if (verified != 0) {
            qWarning() << "Volume verify mismatch stream" << streamIndex
                       << "expected" << volume << "actual" << verified;
        }
    }
}

int VolumeController::getMaxVolume(AudioStream stream)
{
    int streamIndex = getStreamIndex(stream);
    
    QString cmd = QString("media volume --stream %1 --get").arg(streamIndex);
    auto result = m_adb->shell(m_serial, cmd);
    
    if (result.success) {
        // 鐟欙絾鐎芥潏鎾冲毉: "volume is 10 in range [0..15]"
        QRegularExpression re("\\[0\\.\\.(\\d+)\\]");
        QRegularExpressionMatch match = re.match(result.output);
        if (match.hasMatch()) {
            return match.captured(1).toInt();
        }
    }
    
    return 15; // 姒涙顓婚張鈧径褍鈧?
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

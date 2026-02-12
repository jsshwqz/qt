/**
 * QtScrcpy - Audio Stream
 * Copyright (C) 2024 QtScrcpy Contributors
 *
 * Licensed under the Apache License, Version 2.0
 */

#include "audiostream.h"

#include <QAudioDevice>
#include <QAudioFormat>
#include <QAudioSink>
#include <QMediaDevices>
#include <QIODevice>
#include <QDebug>

namespace {
constexpr int kSampleRate = 48000;
constexpr int kChannels = 2;
constexpr int kBytesPerSample = 2;
constexpr int kMaxPendingPcmBytes = kSampleRate * kChannels * kBytesPerSample; // 1 second
}

AudioPlaybackStream::AudioPlaybackStream(QObject *parent)
    : QObject(parent)
    , m_socket(new QTcpSocket(this))
    , m_audioSink(nullptr)
    , m_audioOutput(nullptr)
    , m_bytesReceived(0)
{
    connect(m_socket, &QTcpSocket::connected, this, &AudioPlaybackStream::onConnected);
    connect(m_socket, &QTcpSocket::disconnected, this, &AudioPlaybackStream::onDisconnected);
    connect(m_socket, &QTcpSocket::readyRead, this, &AudioPlaybackStream::onReadyRead);
    connect(m_socket, &QTcpSocket::errorOccurred, this, &AudioPlaybackStream::onError);
}

AudioPlaybackStream::~AudioPlaybackStream()
{
    disconnect();
    stopPlayback();
}

bool AudioPlaybackStream::connectToHost(const QString& host, quint16 port)
{
    if (m_socket->state() != QAbstractSocket::UnconnectedState) {
        return false;
    }

    m_pendingPcm.clear();
    m_bytesReceived = 0;

    m_socket->connectToHost(host, port);
    return m_socket->waitForConnected(5000);
}

void AudioPlaybackStream::disconnect()
{
    if (m_socket->state() != QAbstractSocket::UnconnectedState) {
        m_socket->disconnectFromHost();
    }
}

bool AudioPlaybackStream::isConnected() const
{
    return m_socket->state() == QAbstractSocket::ConnectedState;
}

void AudioPlaybackStream::onConnected()
{
    qDebug() << "Audio stream connected";
    if (!startPlayback()) {
        emit error("Failed to initialize audio playback");
    }
    emit connected();
}

void AudioPlaybackStream::onDisconnected()
{
    qDebug() << "Audio stream disconnected";
    stopPlayback();
    emit disconnected();
}

void AudioPlaybackStream::onReadyRead()
{
    const QByteArray data = m_socket->readAll();
    if (data.isEmpty()) {
        return;
    }

    m_bytesReceived += data.size();
    m_pendingPcm.append(data);

    // Keep latency bounded if producer outruns the output device.
    if (m_pendingPcm.size() > kMaxPendingPcmBytes) {
        m_pendingPcm.remove(0, m_pendingPcm.size() - kMaxPendingPcmBytes);
    }

    drainPendingPcm();
}

void AudioPlaybackStream::onError(QAbstractSocket::SocketError error)
{
    Q_UNUSED(error)
    const QString message = m_socket->errorString();
    qDebug() << "Audio stream error:" << message;
    emit this->error(message);
}

bool AudioPlaybackStream::startPlayback()
{
    stopPlayback();

    const QAudioDevice outputDevice = QMediaDevices::defaultAudioOutput();
    if (outputDevice.isNull()) {
        qWarning() << "No audio output device available";
        return false;
    }

    QAudioFormat fmt;
    fmt.setSampleRate(kSampleRate);
    fmt.setChannelCount(kChannels);
    fmt.setSampleFormat(QAudioFormat::Int16);

    if (!outputDevice.isFormatSupported(fmt)) {
        qWarning() << "Audio format not supported by default output device."
                   << "requested:" << fmt
                   << "preferred:" << outputDevice.preferredFormat();
        return false;
    }

    m_audioSink = new QAudioSink(outputDevice, fmt, this);
    m_audioSink->setBufferSize(kSampleRate * kChannels * kBytesPerSample / 5); // ~200ms
    m_audioOutput = m_audioSink->start();

    if (!m_audioOutput) {
        qWarning() << "Failed to start audio sink";
        delete m_audioSink;
        m_audioSink = nullptr;
        return false;
    }

    return true;
}

void AudioPlaybackStream::stopPlayback()
{
    m_pendingPcm.clear();
    m_audioOutput = nullptr;

    if (m_audioSink) {
        m_audioSink->stop();
        delete m_audioSink;
        m_audioSink = nullptr;
    }
}

void AudioPlaybackStream::drainPendingPcm()
{
    if (!m_audioOutput || m_pendingPcm.isEmpty()) {
        return;
    }

    while (!m_pendingPcm.isEmpty()) {
        const qint64 written = m_audioOutput->write(m_pendingPcm);
        if (written <= 0) {
            break;
        }
        m_pendingPcm.remove(0, static_cast<int>(written));
    }
}

/**
 * QtScrcpy - Audio Stream
 * Copyright (C) 2024 QtScrcpy Contributors
 *
 * Licensed under the Apache License, Version 2.0
 */

#ifndef AUDIOSTREAM_H
#define AUDIOSTREAM_H

#include <QObject>
#include <QTcpSocket>
#include <QByteArray>

class QAudioSink;
class QIODevice;

/**
 * @brief Audio stream receiver and PCM player
 *
 * Current implementation expects 48kHz stereo s16le PCM stream.
 */
class AudioStream : public QObject
{
    Q_OBJECT

public:
    explicit AudioStream(QObject *parent = nullptr);
    ~AudioStream();

    bool connectToHost(const QString& host, quint16 port);
    void disconnect();
    bool isConnected() const;
    qint64 bytesReceived() const { return m_bytesReceived; }

signals:
    void connected();
    void disconnected();
    void error(const QString& message);

private slots:
    void onConnected();
    void onDisconnected();
    void onReadyRead();
    void onError(QAbstractSocket::SocketError error);

private:
    bool startPlayback();
    void stopPlayback();
    void drainPendingPcm();

private:
    QTcpSocket* m_socket;
    QAudioSink* m_audioSink;
    QIODevice* m_audioOutput;
    QByteArray m_pendingPcm;
    qint64 m_bytesReceived;
};

#endif // AUDIOSTREAM_H

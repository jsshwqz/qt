/**
 * QtScrcpy - Video Decoder
 * Copyright (C) 2024 QtScrcpy Contributors
 *
 * Licensed under the Apache License, Version 2.0
 */

#ifndef DECODER_H
#define DECODER_H

#include <QObject>
#include <QImage>
#include <QMutex>
#include <QQueue>

// FFmpeg headers
extern "C" {
#include <libavcodec/avcodec.h>
#include <libavformat/avformat.h>
#include <libswscale/swscale.h>
#include <libavutil/imgutils.h>
}

/**
 * @brief H.264视频解码器
 * 
 * 使用FFmpeg解码H.264视频流，输出QImage
 */
class Decoder : public QObject
{
    Q_OBJECT

public:
    explicit Decoder(QObject *parent = nullptr);
    ~Decoder();

    /**
     * @brief 初始化解码器
     * @return 是否成功
     */
    bool init();

    /**
     * @brief 关闭解码器
     */
    void close();

    /**
     * @brief 解码H.264数据包
     * @param data 数据包
     * @return 是否成功解码出帧
     */
    bool decode(const QByteArray& data);

    /**
     * @brief 获取视频宽度
     */
    int width() const { return m_width; }

    /**
     * @brief 获取视频高度
     */
    int height() const { return m_height; }

    /**
     * @brief 是否已初始化
     */
    bool isInitialized() const { return m_initialized; }

    /**
     * @brief 推送原始数据包
     * @param data 数据
     */
    void pushPacket(const QByteArray& data);

    /**
     * @brief 获取解码统计
     */
    struct DecoderStats {
        qint64 framesDecoded;
        qint64 framesFailed;
        double averageDecodeTime;
    };
    DecoderStats getStats() const;

signals:
    /**
     * @brief 帧解码完成信号
     */
    void frameReady(const QImage& frame);

    /**
     * @brief 解码器初始化完成
     */
    void initialized(int width, int height);

    /**
     * @brief 解码错误信号
     */
    void decodeError(const QString& error);

private:
    bool initCodec();
    bool initSwsContext(int width, int height);
    QImage convertToQImage(AVFrame* frame);
    void processPacketQueue();
    
    // FFmpeg 组件
    const AVCodec* m_codec;
    AVCodecContext* m_codecCtx;
    AVCodecParserContext* m_parser;
    AVFrame* m_frame;
    AVFrame* m_rgbFrame;
    SwsContext* m_swsCtx;
    AVPacket* m_packet;
    
    // 状态
    bool m_initialized;
    int m_width;
    int m_height;
    
    // 数据包队列
    QQueue<QByteArray> m_packetQueue;
    QMutex m_queueMutex;
    
    // 统计
    qint64 m_framesDecoded;
    qint64 m_framesFailed;
    qint64 m_totalDecodeTime;
};

#endif // DECODER_H

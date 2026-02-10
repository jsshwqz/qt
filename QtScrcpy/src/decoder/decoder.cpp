/**
 * QtScrcpy - Video Decoder
 * Copyright (C) 2024 QtScrcpy Contributors
 *
 * Licensed under the Apache License, Version 2.0
 */

#include "decoder.h"
#include <QDebug>
#include <QElapsedTimer>

Decoder::Decoder(QObject *parent)
    : QObject(parent)
    , m_codec(nullptr)
    , m_codecCtx(nullptr)
    , m_parser(nullptr)
    , m_frame(nullptr)
    , m_rgbFrame(nullptr)
    , m_swsCtx(nullptr)
    , m_packet(nullptr)
    , m_initialized(false)
    , m_width(0)
    , m_height(0)
    , m_framesDecoded(0)
    , m_framesFailed(0)
    , m_totalDecodeTime(0)
{
}

Decoder::~Decoder()
{
    close();
}

bool Decoder::init()
{
    if (m_initialized) {
        return true;
    }
    
    return initCodec();
}

bool Decoder::initCodec()
{
    // 查找H.264解码器
    m_codec = avcodec_find_decoder(AV_CODEC_ID_H264);
    if (!m_codec) {
        emit decodeError("找不到H.264解码器");
        return false;
    }
    
    // 创建解码器上下文
    m_codecCtx = avcodec_alloc_context3(m_codec);
    if (!m_codecCtx) {
        emit decodeError("无法分配解码器上下文");
        return false;
    }
    
    // 配置解码器
    m_codecCtx->flags |= AV_CODEC_FLAG_LOW_DELAY;
    m_codecCtx->flags2 |= AV_CODEC_FLAG2_FAST;
    
    // 打开解码器
    if (avcodec_open2(m_codecCtx, m_codec, nullptr) < 0) {
        emit decodeError("无法打开解码器");
        avcodec_free_context(&m_codecCtx);
        return false;
    }
    
    // 创建解析器
    m_parser = av_parser_init(AV_CODEC_ID_H264);
    if (!m_parser) {
        emit decodeError("无法初始化H.264解析器");
        avcodec_free_context(&m_codecCtx);
        return false;
    }
    
    // 分配帧
    m_frame = av_frame_alloc();
    m_rgbFrame = av_frame_alloc();
    m_packet = av_packet_alloc();
    
    if (!m_frame || !m_rgbFrame || !m_packet) {
        emit decodeError("无法分配帧/数据包");
        close();
        return false;
    }
    
    m_initialized = true;
    qDebug() << "Decoder initialized successfully";
    
    return true;
}

bool Decoder::initSwsContext(int width, int height)
{
    if (m_swsCtx && m_width == width && m_height == height) {
        return true;
    }
    
    if (m_swsCtx) {
        sws_freeContext(m_swsCtx);
    }
    
    m_width = width;
    m_height = height;
    
    // 创建颜色空间转换上下文
    m_swsCtx = sws_getContext(
        width, height, AV_PIX_FMT_YUV420P,
        width, height, AV_PIX_FMT_RGB32,
        SWS_BILINEAR, nullptr, nullptr, nullptr
    );
    
    if (!m_swsCtx) {
        emit decodeError("无法创建颜色空间转换上下文");
        return false;
    }
    
    // 分配RGB帧缓冲区
    int numBytes = av_image_get_buffer_size(AV_PIX_FMT_RGB32, width, height, 1);
    uint8_t* buffer = (uint8_t*)av_malloc(numBytes);
    
    av_image_fill_arrays(
        m_rgbFrame->data, m_rgbFrame->linesize,
        buffer, AV_PIX_FMT_RGB32, width, height, 1
    );
    
    emit initialized(width, height);
    qDebug() << "SwsContext initialized:" << width << "x" << height;
    
    return true;
}

void Decoder::close()
{
    m_initialized = false;
    
    if (m_swsCtx) {
        sws_freeContext(m_swsCtx);
        m_swsCtx = nullptr;
    }
    
    if (m_frame) {
        av_frame_free(&m_frame);
    }
    
    if (m_rgbFrame) {
        if (m_rgbFrame->data[0]) {
            av_free(m_rgbFrame->data[0]);
        }
        av_frame_free(&m_rgbFrame);
    }
    
    if (m_packet) {
        av_packet_free(&m_packet);
    }
    
    if (m_parser) {
        av_parser_close(m_parser);
        m_parser = nullptr;
    }
    
    if (m_codecCtx) {
        avcodec_free_context(&m_codecCtx);
    }
    
    m_width = 0;
    m_height = 0;
}

bool Decoder::decode(const QByteArray& data)
{
    if (!m_initialized) {
        return false;
    }
    
    QElapsedTimer timer;
    timer.start();
    
    const uint8_t* inputData = reinterpret_cast<const uint8_t*>(data.constData());
    int inputSize = data.size();
    
    while (inputSize > 0) {
        // 解析数据包
        int ret = av_parser_parse2(
            m_parser, m_codecCtx,
            &m_packet->data, &m_packet->size,
            inputData, inputSize,
            AV_NOPTS_VALUE, AV_NOPTS_VALUE, 0
        );
        
        if (ret < 0) {
            emit decodeError("解析错误");
            m_framesFailed++;
            return false;
        }
        
        inputData += ret;
        inputSize -= ret;
        
        if (m_packet->size > 0) {
            // 发送数据包到解码器
            ret = avcodec_send_packet(m_codecCtx, m_packet);
            if (ret < 0) {
                emit decodeError("发送数据包失败");
                m_framesFailed++;
                continue;
            }
            
            // 接收解码后的帧
            while (ret >= 0) {
                ret = avcodec_receive_frame(m_codecCtx, m_frame);
                
                if (ret == AVERROR(EAGAIN) || ret == AVERROR_EOF) {
                    break;
                }
                
                if (ret < 0) {
                    emit decodeError("接收帧失败");
                    m_framesFailed++;
                    break;
                }
                
                // 初始化颜色空间转换（如果需要）
                if (!m_swsCtx || m_width != m_frame->width || m_height != m_frame->height) {
                    initSwsContext(m_frame->width, m_frame->height);
                }
                
                // 转换为QImage
                QImage image = convertToQImage(m_frame);
                if (!image.isNull()) {
                    m_framesDecoded++;
                    m_totalDecodeTime += timer.elapsed();
                    emit frameReady(image);
                }
            }
        }
    }
    
    return true;
}

QImage Decoder::convertToQImage(AVFrame* frame)
{
    if (!m_swsCtx) {
        return QImage();
    }
    
    // 执行颜色空间转换
    sws_scale(
        m_swsCtx,
        frame->data, frame->linesize,
        0, frame->height,
        m_rgbFrame->data, m_rgbFrame->linesize
    );
    
    // 创建QImage（复制数据）
    QImage image(
        m_rgbFrame->data[0],
        m_width, m_height,
        m_rgbFrame->linesize[0],
        QImage::Format_RGB32
    );
    
    // 返回深拷贝
    return image.copy();
}

void Decoder::pushPacket(const QByteArray& data)
{
    QMutexLocker locker(&m_queueMutex);
    m_packetQueue.enqueue(data);
}

void Decoder::processPacketQueue()
{
    while (true) {
        QByteArray data;
        {
            QMutexLocker locker(&m_queueMutex);
            if (m_packetQueue.isEmpty()) {
                break;
            }
            data = m_packetQueue.dequeue();
        }
        decode(data);
    }
}

Decoder::DecoderStats Decoder::getStats() const
{
    DecoderStats stats;
    stats.framesDecoded = m_framesDecoded;
    stats.framesFailed = m_framesFailed;
    stats.averageDecodeTime = m_framesDecoded > 0 
        ? static_cast<double>(m_totalDecodeTime) / m_framesDecoded 
        : 0;
    return stats;
}

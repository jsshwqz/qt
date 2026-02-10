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
    // 闁哄被鍎叉竟妤?264閻熸瑱绲块悥婊堝闯?
    m_codec = avcodec_find_decoder(AV_CODEC_ID_H264);
    if (!m_codec) {
        emit decodeError("H.264 decoder not found");
        return false;
    }
    
    // 闁告帗绋戠紓鎾舵喆閿濆洨鍨抽柛锝冨妺缁楀倹绋夌€ｎ偅鐎?
    m_codecCtx = avcodec_alloc_context3(m_codec);
    if (!m_codecCtx) {
        emit decodeError("Failed to allocate decoder context");
        return false;
    }
    
    // 闂佹澘绉堕悿鍡欐喆閿濆洨鍨抽柛?
    m_codecCtx->flags |= AV_CODEC_FLAG_LOW_DELAY;
    m_codecCtx->flags2 |= AV_CODEC_FLAG2_FAST;
    
    // 闁瑰灚鎸哥槐鎴犳喆閿濆洨鍨抽柛?
    if (avcodec_open2(m_codecCtx, m_codec, nullptr) < 0) {
        emit decodeError("Failed to open decoder");
        avcodec_free_context(&m_codecCtx);
        return false;
    }
    
    // 闁告帗绋戠紓鎾舵喆閿濆棛鈧粙宕?
    m_parser = av_parser_init(AV_CODEC_ID_H264);
    if (!m_parser) {
        emit decodeError("Failed to initialize H.264 parser");
        avcodec_free_context(&m_codecCtx);
        return false;
    }
    
    // 闁告帒妫濋崢銈囨暜?
    m_frame = av_frame_alloc();
    m_rgbFrame = av_frame_alloc();
    m_packet = av_packet_alloc();
    
    if (!m_frame || !m_rgbFrame || !m_packet) {
        emit decodeError("Failed to allocate frame buffers");
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
    
    // 闁告帗绋戠紓鎾达紣濠婂棗顥忕紒灞炬そ濡寧娼浣稿簥濞戞挸锕ｇ粭鍛村棘?
    m_swsCtx = sws_getContext(
        width, height, AV_PIX_FMT_YUV420P,
        width, height, AV_PIX_FMT_RGB32,
        SWS_BILINEAR, nullptr, nullptr, nullptr
    );
    
    if (!m_swsCtx) {
        emit decodeError("Failed to create color conversion context");
        return false;
    }
    
    // 闁告帒妫濋崢顥窯B閻㈩垎鍛闁告劖褰冪亸?
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
        // 閻熸瑱绲鹃悗浠嬪极閻楀牆绁﹂柛?
        int ret = av_parser_parse2(
            m_parser, m_codecCtx,
            &m_packet->data, &m_packet->size,
            inputData, inputSize,
            AV_NOPTS_VALUE, AV_NOPTS_VALUE, 0
        );
        
        if (ret < 0) {
            emit decodeError("Failed to parse input packet");
            m_framesFailed++;
            return false;
        }
        
        inputData += ret;
        inputSize -= ret;
        
        if (m_packet->size > 0) {
            // 闁告瑦鍨块埀顑跨劍閺嗙喖骞戦鐓庣樁闁告帗濯借闁活喕绀佸▍?
            ret = avcodec_send_packet(m_codecCtx, m_packet);
            if (ret < 0) {
                emit decodeError("Failed to send packet to decoder");
                m_framesFailed++;
                continue;
            }
            
            // 闁规亽鍎查弫鍦喆閿濆洨鍨抽柛姘捣濞堟垹鏁?
            while (ret >= 0) {
                ret = avcodec_receive_frame(m_codecCtx, m_frame);
                
                if (ret == AVERROR(EAGAIN) || ret == AVERROR_EOF) {
                    break;
                }
                
                if (ret < 0) {
                    emit decodeError("Failed to receive frame");
                    m_framesFailed++;
                    break;
                }
                
                // 闁告帗绻傞～鎰板礌閺嶎収鏉归柤纭呭皺閳规牠姊荤壕瀣ギ闁硅婢佺槐娆愪繆閸屾稓浜梻鍥ｅ亾閻熸洑绶ょ槐?
                if (!m_swsCtx || m_width != m_frame->width || m_height != m_frame->height) {
                    initSwsContext(m_frame->width, m_frame->height);
                }
                
                // 閺夌儐鍓氬畷鍙夌▔缁℃勘mage
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
    
    // 闁圭瑳鍡╂斀濡増绮忔竟濠勭矚濞差亝锛熼弶鐑嗗墯瀹?
    sws_scale(
        m_swsCtx,
        frame->data, frame->linesize,
        0, frame->height,
        m_rgbFrame->data, m_rgbFrame->linesize
    );
    
    // 闁告帗绋戠紓鎻汭mage闁挎稑鐗嗛ˇ鏌ュ礆閼稿灚娈堕柟璇″櫙缁?
    QImage image(
        m_rgbFrame->data[0],
        m_width, m_height,
        m_rgbFrame->linesize[0],
        QImage::Format_RGB32
    );
    
    // 閺夆晜鏌ㄥú鏍庢潏銊ヮ伓閻?
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

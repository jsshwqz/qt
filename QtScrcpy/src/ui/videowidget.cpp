/**
 * QtScrcpy - Video Widget
 * Copyright (C) 2024 QtScrcpy Contributors
 *
 * Licensed under the Apache License, Version 2.0
 */

#include "videowidget.h"
#include "input/inputhandler.h"
#include <QPainter>
#include <QResizeEvent>
#include <QMouseEvent>
#include <QKeyEvent>
#include <QWheelEvent>
#include <QInputMethodEvent>
#include <QDragEnterEvent>
#include <QDropEvent>
#include <QMimeData>
#include <QUrl>
#include <QScreen>
#include <QGuiApplication>
#include <QInputMethod>
#include <QDebug>

VideoWidget::VideoWidget(QWidget *parent)
    : QWidget(parent)
    , m_inputHandler(nullptr)
    , m_isFullScreen(false)
    , m_keepAspectRatio(true)
    , m_dropEnabled(true)
    , m_fpsTimer(new QTimer(this))
    , m_frameCount(0)
    , m_fps(0.0)
    , m_needsUpdate(false)
    , m_imeComposing(false)
{
    // 设置焦点策略
    setFocusPolicy(Qt::StrongFocus);
    setAttribute(Qt::WA_InputMethodEnabled, true);
    
    // 允许拖放
    setAcceptDrops(true);
    
    // 背景
    setAutoFillBackground(true);
    QPalette pal = palette();
    pal.setColor(QPalette::Window, Qt::black);
    setPalette(pal);
    
    // 鼠标跟踪
    setMouseTracking(true);
    
    // 帧率计算定时器
    connect(m_fpsTimer, &QTimer::timeout, this, &VideoWidget::calculateFps);
    m_fpsTimer->start(1000);
    
    // 设置最小尺寸
    setMinimumSize(320, 240);
}

VideoWidget::~VideoWidget()
{
}

void VideoWidget::updateFrame(const QImage& frame)
{
    {
        QMutexLocker locker(&m_frameMutex);
        m_currentFrame = frame;
        
        if (m_videoSize != frame.size()) {
            m_videoSize = frame.size();
            updateRenderRect();
        }
    }
    
    m_frameCount++;
    update();
}

void VideoWidget::setFullScreen(bool fullscreen)
{
    if (m_isFullScreen == fullscreen) {
        return;
    }
    
    m_isFullScreen = fullscreen;
    
    if (fullscreen) {
        // 获取父窗口并全屏
        QWidget* parentWindow = window();
        if (parentWindow) {
            parentWindow->showFullScreen();
        }
        setCursor(Qt::BlankCursor);
    } else {
        QWidget* parentWindow = window();
        if (parentWindow) {
            parentWindow->showNormal();
        }
        setCursor(Qt::ArrowCursor);
    }

    updateRenderRect();
    update();
    setFocus(Qt::OtherFocusReason);
}

void VideoWidget::setInputHandler(InputHandler* handler)
{
    m_inputHandler = handler;
    
    if (m_inputHandler) {
        m_inputHandler->setVideoDisplaySize(m_renderRect.size());
    }
}

void VideoWidget::setDropEnabled(bool enabled)
{
    m_dropEnabled = enabled;
    setAcceptDrops(enabled);
}

void VideoWidget::resizeToFit()
{
    if (m_videoSize.isEmpty()) {
        return;
    }
    
    // 获取屏幕可用区域
    QScreen* screen = this->screen();
    if (!screen) return;
    
    QRect available = screen->availableGeometry();
    
    // 计算适合的尺寸
    QSize targetSize = m_videoSize;
    
    // 限制在屏幕80%范围内
    int maxWidth = available.width() * 0.8;
    int maxHeight = available.height() * 0.8;
    
    if (targetSize.width() > maxWidth || targetSize.height() > maxHeight) {
        targetSize.scale(maxWidth, maxHeight, Qt::KeepAspectRatio);
    }
    
    // 调整窗口大小
    QWidget* parentWindow = window();
    if (parentWindow) {
        const int extraWidth = parentWindow->width() - width();
        const int extraHeight = parentWindow->height() - height();
        parentWindow->resize(targetSize.width() + extraWidth, targetSize.height() + extraHeight);
    }
}

void VideoWidget::resizeToOriginal()
{
    if (m_videoSize.isEmpty()) {
        return;
    }
    
    QWidget* parentWindow = window();
    if (parentWindow) {
        const int extraWidth = parentWindow->width() - width();
        const int extraHeight = parentWindow->height() - height();
        parentWindow->resize(m_videoSize.width() + extraWidth, m_videoSize.height() + extraHeight);
    }
}

void VideoWidget::paintEvent(QPaintEvent* event)
{
    Q_UNUSED(event)
    
    QPainter painter(this);
    painter.setRenderHint(QPainter::SmoothPixmapTransform, !m_isFullScreen);
    
    QMutexLocker locker(&m_frameMutex);
    
    if (m_currentFrame.isNull()) {
        // 绘制占位符
        painter.fillRect(rect(), Qt::black);
        
        painter.setPen(Qt::gray);
        painter.setFont(QFont("Arial", 14));
        painter.drawText(rect(), Qt::AlignCenter, "等待连接...");
    } else {
        // 绘制黑色背景
        painter.fillRect(rect(), Qt::black);
        
        // 绘制视频帧
        painter.drawImage(m_renderRect, m_currentFrame);
    }
}

void VideoWidget::resizeEvent(QResizeEvent* event)
{
    QWidget::resizeEvent(event);
    updateRenderRect();
    
    if (m_inputHandler) {
        m_inputHandler->setVideoDisplaySize(m_renderRect.size());
    }
}

void VideoWidget::updateRenderRect()
{
    if (m_videoSize.isEmpty()) {
        m_renderRect = rect();
        return;
    }
    
    if (m_keepAspectRatio) {
        // 保持宽高比
        QSize scaled = m_videoSize.scaled(size(), Qt::KeepAspectRatio);
        
        int x = (width() - scaled.width()) / 2;
        int y = (height() - scaled.height()) / 2;
        
        m_renderRect = QRect(QPoint(x, y), scaled);
    } else {
        m_renderRect = rect();
    }
}

QPoint VideoWidget::mapToVideo(const QPoint& pos) const
{
    if (m_renderRect.isEmpty() || m_videoSize.isEmpty()) {
        return pos;
    }
    
    // 检查是否在渲染区域内
    if (!m_renderRect.contains(pos)) {
        return QPoint(-1, -1);
    }
    
    // 映射到视频坐标
    int x = (pos.x() - m_renderRect.x()) * m_videoSize.width() / m_renderRect.width();
    int y = (pos.y() - m_renderRect.y()) * m_videoSize.height() / m_renderRect.height();
    
    return QPoint(x, y);
}

void VideoWidget::calculateFps()
{
    m_fps = m_frameCount;
    m_frameCount = 0;
    emit fpsUpdated(m_fps);
}

// 输入事件处理
void VideoWidget::mousePressEvent(QMouseEvent* event)
{
    setFocus(Qt::MouseFocusReason);

    if (m_inputHandler && m_renderRect.contains(event->pos())) {
        const QPoint mappedPos = mapToVideo(event->pos());
        QMouseEvent mappedEvent(
            event->type(),
            QPointF(mappedPos),
            event->globalPosition(),
            event->button(),
            event->buttons(),
            event->modifiers()
        );
        m_inputHandler->handleMousePress(&mappedEvent);
    }
}

void VideoWidget::mouseReleaseEvent(QMouseEvent* event)
{
    if (m_inputHandler) {
        const QPoint mappedPos = mapToVideo(event->pos());
        QMouseEvent mappedEvent(
            event->type(),
            QPointF(mappedPos),
            event->globalPosition(),
            event->button(),
            event->buttons(),
            event->modifiers()
        );
        m_inputHandler->handleMouseRelease(&mappedEvent);
    }
}

void VideoWidget::mouseMoveEvent(QMouseEvent* event)
{
    if (m_inputHandler) {
        const QPoint mappedPos = mapToVideo(event->pos());
        if (mappedPos.x() < 0 || mappedPos.y() < 0) {
            return;
        }
        QMouseEvent mappedEvent(
            event->type(),
            QPointF(mappedPos),
            event->globalPosition(),
            event->button(),
            event->buttons(),
            event->modifiers()
        );
        m_inputHandler->handleMouseMove(&mappedEvent);
    }
}

void VideoWidget::mouseDoubleClickEvent(QMouseEvent* event)
{
    Q_UNUSED(event)
    emit doubleClicked();
}

void VideoWidget::wheelEvent(QWheelEvent* event)
{
    if (m_inputHandler) {
        const QPoint mappedPos = mapToVideo(event->position().toPoint());
        if (mappedPos.x() < 0 || mappedPos.y() < 0) {
            return;
        }

        QWheelEvent mappedEvent(
            QPointF(mappedPos),
            event->globalPosition(),
            event->pixelDelta(),
            event->angleDelta(),
            event->buttons(),
            event->modifiers(),
            event->phase(),
            event->inverted(),
            event->source(),
            event->pointingDevice()
        );
        m_inputHandler->handleWheel(&mappedEvent);
    }
}

void VideoWidget::keyPressEvent(QKeyEvent* event)
{
    // F11切换全屏
    if (event->key() == Qt::Key_F11) {
        setFullScreen(!m_isFullScreen);
        return;
    }
    
    // ESC退出全屏
    if (event->key() == Qt::Key_Escape && m_isFullScreen) {
        setFullScreen(false);
        return;
    }

    if (m_inputHandler) {
        m_inputHandler->handleKeyPress(event);
    }
}

void VideoWidget::keyReleaseEvent(QKeyEvent* event)
{
    if (m_inputHandler) {
        m_inputHandler->handleKeyRelease(event);
    }
}

void VideoWidget::inputMethodEvent(QInputMethodEvent* event)
{
    if (event) {
        m_imeComposing = !event->preeditString().isEmpty();
    }

    if (m_inputHandler && event) {
        const QString committedText = event->commitString();
        if (!committedText.isEmpty()) {
            m_inputHandler->handleTextInput(committedText);
            m_imeComposing = false;
        }
    }
    if (event) {
        event->accept();
    }
}

QVariant VideoWidget::inputMethodQuery(Qt::InputMethodQuery query) const
{
    if (query == Qt::ImEnabled) {
        return true;
    }
    if (query == Qt::ImCursorRectangle) {
        return rect();
    }
    return QWidget::inputMethodQuery(query);
}

// 拖放处理
void VideoWidget::dragEnterEvent(QDragEnterEvent* event)
{
    if (!m_dropEnabled) {
        event->ignore();
        return;
    }
    
    if (event->mimeData()->hasUrls()) {
        event->acceptProposedAction();
        
        // 高亮显示
        QPalette pal = palette();
        pal.setColor(QPalette::Window, QColor(0, 100, 0));
        setPalette(pal);
    }
}

void VideoWidget::dragMoveEvent(QDragMoveEvent* event)
{
    if (m_dropEnabled && event->mimeData()->hasUrls()) {
        event->acceptProposedAction();
    }
}

void VideoWidget::dropEvent(QDropEvent* event)
{
    // 恢复背景
    QPalette pal = palette();
    pal.setColor(QPalette::Window, Qt::black);
    setPalette(pal);
    
    if (!m_dropEnabled) {
        return;
    }
    
    const QMimeData* mimeData = event->mimeData();
    
    if (mimeData->hasUrls()) {
        QStringList paths;
        
        for (const QUrl& url : mimeData->urls()) {
            if (url.isLocalFile()) {
                paths.append(url.toLocalFile());
            }
        }
        
        if (!paths.isEmpty()) {
            emit filesDropped(paths);
        }
        
        event->acceptProposedAction();
    }
}

void VideoWidget::focusInEvent(QFocusEvent* event)
{
    QWidget::focusInEvent(event);
    if (QGuiApplication::inputMethod()) {
        QGuiApplication::inputMethod()->update(Qt::ImEnabled | Qt::ImCursorRectangle);
    }
    // 可以在这里处理获得焦点时的逻辑
}

void VideoWidget::focusOutEvent(QFocusEvent* event)
{
    QWidget::focusOutEvent(event);
    m_imeComposing = false;
    // 可以在这里处理失去焦点时的逻辑
}

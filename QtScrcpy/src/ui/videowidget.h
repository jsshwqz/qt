/**
 * QtScrcpy - Video Widget
 * Copyright (C) 2024 QtScrcpy Contributors
 *
 * Licensed under the Apache License, Version 2.0
 */

#ifndef VIDEOWIDGET_H
#define VIDEOWIDGET_H

#include <QWidget>
#include <QImage>
#include <QSize>
#include <QTimer>
#include <QMutex>
#include <QVariant>
#include <QElapsedTimer>

class QInputMethodEvent;

class InputHandler;

/**
 * @brief 视频渲染窗口
 * 
 * 负责显示投屏画面和处理输入事件
 */
class VideoWidget : public QWidget
{
    Q_OBJECT

public:
    explicit VideoWidget(QWidget *parent = nullptr);
    ~VideoWidget();

    /**
     * @brief 更新视频帧
     */
    void updateFrame(const QImage& frame);

    /**
     * @brief 设置全屏模式
     */
    void setFullScreen(bool fullscreen);

    /**
     * @brief 是否全屏
     */
    bool isFullScreen() const { return m_isFullScreen; }

    /**
     * @brief 设置保持宽高比
     */
    void setKeepAspectRatio(bool keep) { m_keepAspectRatio = keep; update(); }

    /**
     * @brief 设置输入处理器
     */
    void setInputHandler(InputHandler* handler);

    /**
     * @brief 获取视频尺寸
     */
    QSize videoSize() const { return m_videoSize; }

    /**
     * @brief 设置设备屏幕尺寸
     */
    void setDeviceScreenSize(const QSize& size) { m_deviceScreenSize = size; }

    /**
     * @brief 获取帧率
     */
    double fps() const { return m_fps; }

    /**
     * @brief 启用/禁用拖放
     */
    void setDropEnabled(bool enabled);

    /**
     * @brief 调整窗口大小以适应视频
     */
    void resizeToFit();

    /**
     * @brief 调整窗口大小为1:1
     */
    void resizeToOriginal();

signals:
    /**
     * @brief 双击信号
     */
    void doubleClicked();

    /**
     * @brief 拖放文件信号
     */
    void filesDropped(const QStringList& paths);

    /**
     * @brief 帧率更新信号
     */
    void fpsUpdated(double fps);

protected:
    void paintEvent(QPaintEvent* event) override;
    void resizeEvent(QResizeEvent* event) override;
    void mousePressEvent(QMouseEvent* event) override;
    void mouseReleaseEvent(QMouseEvent* event) override;
    void mouseMoveEvent(QMouseEvent* event) override;
    void mouseDoubleClickEvent(QMouseEvent* event) override;
    void wheelEvent(QWheelEvent* event) override;
    void keyPressEvent(QKeyEvent* event) override;
    void keyReleaseEvent(QKeyEvent* event) override;
    void inputMethodEvent(QInputMethodEvent* event) override;
    QVariant inputMethodQuery(Qt::InputMethodQuery query) const override;
    void dragEnterEvent(QDragEnterEvent* event) override;
    void dragMoveEvent(QDragMoveEvent* event) override;
    void dropEvent(QDropEvent* event) override;
    void focusInEvent(QFocusEvent* event) override;
    void focusOutEvent(QFocusEvent* event) override;

private:
    void updateRenderRect();
    void calculateFps();
    QPoint mapToVideo(const QPoint& pos) const;
    
    QImage m_currentFrame;
    QMutex m_frameMutex;
    QSize m_videoSize;
    QSize m_deviceScreenSize;
    QRect m_renderRect;
    
    InputHandler* m_inputHandler;
    bool m_isFullScreen;
    bool m_keepAspectRatio;
    bool m_dropEnabled;
    
    // 帧率计算
    QTimer* m_fpsTimer;
    int m_frameCount;
    double m_fps;
    
    // 渲染优化
    bool m_needsUpdate;
    bool m_imeComposing;
    int m_targetFrameIntervalMs;
    QElapsedTimer m_presentTimer;
};

#endif // VIDEOWIDGET_H

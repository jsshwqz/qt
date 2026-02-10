/**
 * QtScrcpy - Clipboard Manager
 * Copyright (C) 2024 QtScrcpy Contributors
 *
 * Licensed under the Apache License, Version 2.0
 */

#include "clipboardmanager.h"
#include "stream/controlstream.h"
#include <QApplication>
#include <QDebug>

ClipboardManager::ClipboardManager(QObject *parent)
    : QObject(parent)
    , m_clipboard(QApplication::clipboard())
    , m_controlStream(nullptr)
    , m_syncing(false)
    , m_autoPaste(false)
    , m_clipboardSequence(0)
    , m_ignoreLocalChange(false)
{
    connect(m_clipboard, &QClipboard::dataChanged,
            this, &ClipboardManager::onLocalClipboardChanged);
}

ClipboardManager::~ClipboardManager()
{
    stopSync();
}

void ClipboardManager::setControlStream(ControlStream* stream)
{
    if (m_controlStream) {
        disconnect(m_controlStream, &ControlStream::clipboardReceived,
                   this, &ClipboardManager::onDeviceClipboardReceived);
    }
    
    m_controlStream = stream;
    
    if (m_controlStream) {
        connect(m_controlStream, &ControlStream::clipboardReceived,
                this, &ClipboardManager::onDeviceClipboardReceived);
    }
}

void ClipboardManager::startSync()
{
    if (m_syncing) {
        return;
    }
    
    m_syncing = true;
    m_lastLocalText = m_clipboard->text();
    
    qDebug() << "Clipboard sync started";
    
    // 获取设备当前剪贴板
    getFromDevice();
}

void ClipboardManager::stopSync()
{
    m_syncing = false;
    qDebug() << "Clipboard sync stopped";
}

void ClipboardManager::sendToDevice(const QString& text)
{
    if (!m_controlStream || text.isEmpty()) {
        return;
    }
    
    // 避免循环同步
    if (text == m_lastDeviceText) {
        return;
    }
    
    m_clipboardSequence++;
    m_lastDeviceText = text;
    
    qDebug() << "Sending clipboard to device:" << text.left(50) << "...";
    
    m_controlStream->setClipboard(m_clipboardSequence, text, m_autoPaste);
}

void ClipboardManager::getFromDevice()
{
    if (!m_controlStream) {
        return;
    }
    
    m_controlStream->getClipboard(0); // CopyKey::None
}

void ClipboardManager::onLocalClipboardChanged()
{
    if (!m_syncing || m_ignoreLocalChange) {
        return;
    }
    
    QString text = m_clipboard->text();
    
    // 检查是否真的改变了
    if (text == m_lastLocalText) {
        return;
    }
    
    m_lastLocalText = text;
    
    qDebug() << "Local clipboard changed:" << text.left(50) << "...";
    emit localClipboardChanged(text);
    
    // 发送到设备
    sendToDevice(text);
}

void ClipboardManager::onDeviceClipboardReceived(const QString& text)
{
    if (text.isEmpty()) {
        return;
    }
    
    // 避免循环同步
    if (text == m_lastLocalText) {
        return;
    }
    
    m_lastDeviceText = text;
    
    qDebug() << "Device clipboard received:" << text.left(50) << "...";
    emit deviceClipboardChanged(text);
    
    // 设置本地剪贴板
    m_ignoreLocalChange = true;
    m_clipboard->setText(text);
    m_lastLocalText = text;
    m_ignoreLocalChange = false;
    
    emit syncCompleted(true);
}

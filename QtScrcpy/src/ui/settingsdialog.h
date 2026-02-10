/**
 * QtScrcpy - Settings Dialog
 * Copyright (C) 2024 QtScrcpy Contributors
 *
 * Licensed under the Apache License, Version 2.0
 */

#ifndef SETTINGSDIALOG_H
#define SETTINGSDIALOG_H

#include <QDialog>
#include <QSpinBox>
#include <QCheckBox>
#include <QComboBox>

#include "server/servermanager.h"

/**
 * @brief 设置对话框
 */
class SettingsDialog : public QDialog
{
    Q_OBJECT

public:
    explicit SettingsDialog(QWidget *parent = nullptr);
    ~SettingsDialog();

    /**
     * @brief 获取服务端配置
     */
    ServerConfig getConfig() const;

    /**
     * @brief 设置服务端配置
     */
    void setConfig(const ServerConfig& config);

private slots:
    void onApply();
    void onRestoreDefaults();

private:
    void setupUi();
    void loadSettings();
    void saveSettings();
    
    // 视频设置
    QSpinBox* m_maxSizeSpinBox;
    QSpinBox* m_bitRateSpinBox;
    QSpinBox* m_maxFpsSpinBox;
    QComboBox* m_codecCombo;
    QComboBox* m_orientationCombo;
    
    // 控制设置
    QCheckBox* m_stayAwakeCheck;
    QCheckBox* m_showTouchesCheck;
    QCheckBox* m_clipboardSyncCheck;
    QCheckBox* m_powerOnCheck;
    QCheckBox* m_powerOffOnCloseCheck;
    QCheckBox* m_muteOnConnectCheck;
};

#endif // SETTINGSDIALOG_H

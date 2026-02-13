/**
 * QtScrcpy - Settings Dialog
 * Copyright (C) 2024 QtScrcpy Contributors
 *
 * Licensed under the Apache License, Version 2.0
 */

#include "settingsdialog.h"

#include <QVBoxLayout>
#include <QHBoxLayout>
#include <QFormLayout>
#include <QGroupBox>
#include <QPushButton>
#include <QSettings>

SettingsDialog::SettingsDialog(QWidget *parent)
    : QDialog(parent)
{
    setWindowTitle("Settings");
    setMinimumWidth(420);

    setupUi();
    loadSettings();
}

SettingsDialog::~SettingsDialog()
{
}

void SettingsDialog::setupUi()
{
    QVBoxLayout* mainLayout = new QVBoxLayout(this);

    QGroupBox* videoGroup = new QGroupBox("Video", this);
    QFormLayout* videoLayout = new QFormLayout(videoGroup);

    m_maxSizeSpinBox = new QSpinBox(this);
    m_maxSizeSpinBox->setRange(0, 3840);
    m_maxSizeSpinBox->setSingleStep(120);
    m_maxSizeSpinBox->setSpecialValueText("No limit");
    m_maxSizeSpinBox->setSuffix(" px");
    videoLayout->addRow("Max size:", m_maxSizeSpinBox);

    m_bitRateSpinBox = new QSpinBox(this);
    m_bitRateSpinBox->setRange(1, 100);
    m_bitRateSpinBox->setSuffix(" Mbps");
    videoLayout->addRow("Bit rate:", m_bitRateSpinBox);

    m_maxFpsSpinBox = new QSpinBox(this);
    m_maxFpsSpinBox->setRange(1, 120);
    m_maxFpsSpinBox->setSuffix(" fps");
    videoLayout->addRow("Max FPS:", m_maxFpsSpinBox);

    m_codecCombo = new QComboBox(this);
    m_codecCombo->addItem("H.264", "h264");
    m_codecCombo->addItem("H.265 (HEVC)", "h265");
    m_codecCombo->addItem("AV1", "av1");
    videoLayout->addRow("Codec:", m_codecCombo);

    m_orientationCombo = new QComboBox(this);
    m_orientationCombo->addItem("Unlocked", -1);
    m_orientationCombo->addItem("Portrait", 0);
    m_orientationCombo->addItem("Landscape (90)", 1);
    m_orientationCombo->addItem("Portrait upside-down", 2);
    m_orientationCombo->addItem("Landscape (270)", 3);
    videoLayout->addRow("Orientation lock:", m_orientationCombo);

    mainLayout->addWidget(videoGroup);

    QGroupBox* controlGroup = new QGroupBox("Control", this);
    QVBoxLayout* controlLayout = new QVBoxLayout(controlGroup);

    m_stayAwakeCheck = new QCheckBox("Keep phone awake while connected", this);
    controlLayout->addWidget(m_stayAwakeCheck);

    m_showTouchesCheck = new QCheckBox("Show touch points", this);
    controlLayout->addWidget(m_showTouchesCheck);

    m_clipboardSyncCheck = new QCheckBox("Auto sync clipboard", this);
    controlLayout->addWidget(m_clipboardSyncCheck);

    m_powerOnCheck = new QCheckBox("Turn screen on when connected", this);
    controlLayout->addWidget(m_powerOnCheck);

    m_powerOffOnCloseCheck = new QCheckBox("Turn screen off when disconnected", this);
    controlLayout->addWidget(m_powerOffOnCloseCheck);

    m_muteOnConnectCheck = new QCheckBox("Mute phone audio while mirroring (restore on disconnect)", this);
    controlLayout->addWidget(m_muteOnConnectCheck);

    mainLayout->addWidget(controlGroup);

    QHBoxLayout* btnLayout = new QHBoxLayout();

    QPushButton* defaultsBtn = new QPushButton("Restore Defaults", this);
    connect(defaultsBtn, &QPushButton::clicked, this, &SettingsDialog::onRestoreDefaults);
    btnLayout->addWidget(defaultsBtn);
    btnLayout->addStretch();

    QPushButton* applyBtn = new QPushButton("Apply", this);
    connect(applyBtn, &QPushButton::clicked, this, &SettingsDialog::onApply);
    btnLayout->addWidget(applyBtn);

    QPushButton* okBtn = new QPushButton("OK", this);
    okBtn->setDefault(true);
    connect(okBtn, &QPushButton::clicked, this, [this]() {
        onApply();
        accept();
    });
    btnLayout->addWidget(okBtn);

    QPushButton* cancelBtn = new QPushButton("Cancel", this);
    connect(cancelBtn, &QPushButton::clicked, this, &QDialog::reject);
    btnLayout->addWidget(cancelBtn);

    mainLayout->addLayout(btnLayout);
}

ServerConfig SettingsDialog::getConfig() const
{
    ServerConfig config;
    config.maxSize = m_maxSizeSpinBox->value();
    config.bitRate = m_bitRateSpinBox->value() * 1000000;
    config.maxFps = m_maxFpsSpinBox->value();
    config.videoCodec = m_codecCombo->currentData().toString();
    config.lockVideoOrientation = m_orientationCombo->currentData().toInt();
    config.stayAwake = m_stayAwakeCheck->isChecked();
    config.showTouches = m_showTouchesCheck->isChecked();
    config.clipboardAutosync = m_clipboardSyncCheck->isChecked();
    config.powerOn = m_powerOnCheck->isChecked();
    config.powerOffOnClose = m_powerOffOnCloseCheck->isChecked();
    return config;
}

void SettingsDialog::setConfig(const ServerConfig& config)
{
    m_maxSizeSpinBox->setValue(config.maxSize);
    m_bitRateSpinBox->setValue(config.bitRate / 1000000);
    m_maxFpsSpinBox->setValue(config.maxFps);

    const int codecIndex = m_codecCombo->findData(config.videoCodec);
    if (codecIndex >= 0) {
        m_codecCombo->setCurrentIndex(codecIndex);
    }

    const int orientIndex = m_orientationCombo->findData(config.lockVideoOrientation);
    if (orientIndex >= 0) {
        m_orientationCombo->setCurrentIndex(orientIndex);
    }

    m_stayAwakeCheck->setChecked(config.stayAwake);
    m_showTouchesCheck->setChecked(config.showTouches);
    m_clipboardSyncCheck->setChecked(config.clipboardAutosync);
    m_powerOnCheck->setChecked(config.powerOn);
    m_powerOffOnCloseCheck->setChecked(config.powerOffOnClose);
}

void SettingsDialog::loadSettings()
{
    QSettings settings("QtScrcpy", "QtScrcpy");

    ServerConfig config;
    config.maxSize = settings.value("video/maxSize", 0).toInt();
    config.bitRate = settings.value("video/bitRate", 8000000).toInt();
    config.maxFps = settings.value("video/maxFps", 60).toInt();
    config.videoCodec = settings.value("video/codec", "h264").toString();
    config.lockVideoOrientation = settings.value("video/orientation", -1).toInt();
    config.stayAwake = settings.value("control/stayAwake", true).toBool();
    config.showTouches = settings.value("control/showTouches", false).toBool();
    config.clipboardAutosync = settings.value("control/clipboardSync", true).toBool();
    config.powerOn = settings.value("control/powerOn", true).toBool();
    config.powerOffOnClose = settings.value("control/powerOffOnClose", false).toBool();

    setConfig(config);
    m_muteOnConnectCheck->setChecked(settings.value("control/muteOnConnect", true).toBool());
}

void SettingsDialog::saveSettings()
{
    QSettings settings("QtScrcpy", "QtScrcpy");
    const ServerConfig config = getConfig();

    settings.setValue("video/maxSize", config.maxSize);
    settings.setValue("video/bitRate", config.bitRate);
    settings.setValue("video/maxFps", config.maxFps);
    settings.setValue("video/codec", config.videoCodec);
    settings.setValue("video/orientation", config.lockVideoOrientation);
    settings.setValue("control/stayAwake", config.stayAwake);
    settings.setValue("control/showTouches", config.showTouches);
    settings.setValue("control/clipboardSync", config.clipboardAutosync);
    settings.setValue("control/powerOn", config.powerOn);
    settings.setValue("control/powerOffOnClose", config.powerOffOnClose);
    settings.setValue("control/muteOnConnect", m_muteOnConnectCheck->isChecked());
}

void SettingsDialog::onApply()
{
    saveSettings();
}

void SettingsDialog::onRestoreDefaults()
{
    ServerConfig defaults;
    setConfig(defaults);
    m_muteOnConnectCheck->setChecked(true);
}

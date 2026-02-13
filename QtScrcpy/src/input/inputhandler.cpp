/**
 * QtScrcpy - Input Handler
 * Copyright (C) 2024 QtScrcpy Contributors
 *
 * Licensed under the Apache License, Version 2.0
 */

#include "inputhandler.h"
#include "stream/controlstream.h"
#include <QDebug>

namespace {
bool containsNonAscii(const QString& text)
{
    for (QChar ch : text) {
        if (ch.unicode() > 0x7F) {
            return true;
        }
    }
    return false;
}
}

// 静态成员初始化
QMap<int, int> InputHandler::s_keyMap;
bool InputHandler::s_keyMapInitialized = false;

// Android按键码常量
namespace AKEYCODE {
    constexpr int UNKNOWN = 0;
    constexpr int SOFT_LEFT = 1;
    constexpr int SOFT_RIGHT = 2;
    constexpr int HOME = 3;
    constexpr int BACK = 4;
    constexpr int CALL = 5;
    constexpr int ENDCALL = 6;
    constexpr int KEY_0 = 7;
    constexpr int KEY_1 = 8;
    constexpr int KEY_2 = 9;
    constexpr int KEY_3 = 10;
    constexpr int KEY_4 = 11;
    constexpr int KEY_5 = 12;
    constexpr int KEY_6 = 13;
    constexpr int KEY_7 = 14;
    constexpr int KEY_8 = 15;
    constexpr int KEY_9 = 16;
    constexpr int STAR = 17;
    constexpr int POUND = 18;
    constexpr int DPAD_UP = 19;
    constexpr int DPAD_DOWN = 20;
    constexpr int DPAD_LEFT = 21;
    constexpr int DPAD_RIGHT = 22;
    constexpr int DPAD_CENTER = 23;
    constexpr int VOLUME_UP = 24;
    constexpr int VOLUME_DOWN = 25;
    constexpr int POWER = 26;
    constexpr int CAMERA = 27;
    constexpr int CLEAR = 28;
    constexpr int A = 29;
    constexpr int B = 30;
    constexpr int C = 31;
    constexpr int D = 32;
    constexpr int E = 33;
    constexpr int F = 34;
    constexpr int G = 35;
    constexpr int H = 36;
    constexpr int I = 37;
    constexpr int J = 38;
    constexpr int K = 39;
    constexpr int L = 40;
    constexpr int M = 41;
    constexpr int N = 42;
    constexpr int O = 43;
    constexpr int P = 44;
    constexpr int Q = 45;
    constexpr int R = 46;
    constexpr int S = 47;
    constexpr int T = 48;
    constexpr int U = 49;
    constexpr int V = 50;
    constexpr int W = 51;
    constexpr int X = 52;
    constexpr int Y = 53;
    constexpr int Z = 54;
    constexpr int COMMA = 55;
    constexpr int PERIOD = 56;
    constexpr int TAB = 61;
    constexpr int SPACE = 62;
    constexpr int ENTER = 66;
    constexpr int DEL = 67;  // Backspace
    constexpr int GRAVE = 68;
    constexpr int MINUS = 69;
    constexpr int EQUALS = 70;
    constexpr int LEFT_BRACKET = 71;
    constexpr int RIGHT_BRACKET = 72;
    constexpr int BACKSLASH = 73;
    constexpr int SEMICOLON = 74;
    constexpr int APOSTROPHE = 75;
    constexpr int SLASH = 76;
    constexpr int ESCAPE = 111;
    constexpr int FORWARD_DEL = 112;
    constexpr int CTRL_LEFT = 113;
    constexpr int CTRL_RIGHT = 114;
    constexpr int CAPS_LOCK = 115;
    constexpr int SCROLL_LOCK = 116;
    constexpr int SHIFT_LEFT = 59;
    constexpr int SHIFT_RIGHT = 60;
    constexpr int ALT_LEFT = 57;
    constexpr int ALT_RIGHT = 58;
    constexpr int F1 = 131;
    constexpr int F2 = 132;
    constexpr int F3 = 133;
    constexpr int F4 = 134;
    constexpr int F5 = 135;
    constexpr int F6 = 136;
    constexpr int F7 = 137;
    constexpr int F8 = 138;
    constexpr int F9 = 139;
    constexpr int F10 = 140;
    constexpr int F11 = 141;
    constexpr int F12 = 142;
    constexpr int INSERT = 124;
    constexpr int FORWARD = 125;
    constexpr int PAGE_UP = 92;
    constexpr int PAGE_DOWN = 93;
    constexpr int MOVE_HOME = 122;
    constexpr int MOVE_END = 123;
    constexpr int APP_SWITCH = 187;
    constexpr int MENU = 82;
}

// Android Meta状态
namespace AMETA {
    constexpr int NONE = 0;
    constexpr int ALT_ON = 0x02;
    constexpr int ALT_LEFT_ON = 0x10;
    constexpr int ALT_RIGHT_ON = 0x20;
    constexpr int SHIFT_ON = 0x01;
    constexpr int SHIFT_LEFT_ON = 0x40;
    constexpr int SHIFT_RIGHT_ON = 0x80;
    constexpr int CTRL_ON = 0x1000;
    constexpr int CTRL_LEFT_ON = 0x2000;
    constexpr int CTRL_RIGHT_ON = 0x4000;
    constexpr int META_ON = 0x10000;
}

// Android按钮
namespace AMOTION_EVENT_BUTTON {
    constexpr int PRIMARY = 1 << 0;
    constexpr int SECONDARY = 1 << 1;
    constexpr int TERTIARY = 1 << 2;
    constexpr int BACK = 1 << 3;
    constexpr int FORWARD = 1 << 4;
}

InputHandler::InputHandler(QObject *parent)
    : QObject(parent)
    , m_controlStream(nullptr)
    , m_enabled(true)
    , m_mousePressed(false)
    , m_pointerId(-1)
{
    if (!s_keyMapInitialized) {
        initKeyMap();
    }
}

InputHandler::~InputHandler()
{
}

void InputHandler::initKeyMap()
{
    s_keyMap[Qt::Key_A] = AKEYCODE::A;
    s_keyMap[Qt::Key_B] = AKEYCODE::B;
    s_keyMap[Qt::Key_C] = AKEYCODE::C;
    s_keyMap[Qt::Key_D] = AKEYCODE::D;
    s_keyMap[Qt::Key_E] = AKEYCODE::E;
    s_keyMap[Qt::Key_F] = AKEYCODE::F;
    s_keyMap[Qt::Key_G] = AKEYCODE::G;
    s_keyMap[Qt::Key_H] = AKEYCODE::H;
    s_keyMap[Qt::Key_I] = AKEYCODE::I;
    s_keyMap[Qt::Key_J] = AKEYCODE::J;
    s_keyMap[Qt::Key_K] = AKEYCODE::K;
    s_keyMap[Qt::Key_L] = AKEYCODE::L;
    s_keyMap[Qt::Key_M] = AKEYCODE::M;
    s_keyMap[Qt::Key_N] = AKEYCODE::N;
    s_keyMap[Qt::Key_O] = AKEYCODE::O;
    s_keyMap[Qt::Key_P] = AKEYCODE::P;
    s_keyMap[Qt::Key_Q] = AKEYCODE::Q;
    s_keyMap[Qt::Key_R] = AKEYCODE::R;
    s_keyMap[Qt::Key_S] = AKEYCODE::S;
    s_keyMap[Qt::Key_T] = AKEYCODE::T;
    s_keyMap[Qt::Key_U] = AKEYCODE::U;
    s_keyMap[Qt::Key_V] = AKEYCODE::V;
    s_keyMap[Qt::Key_W] = AKEYCODE::W;
    s_keyMap[Qt::Key_X] = AKEYCODE::X;
    s_keyMap[Qt::Key_Y] = AKEYCODE::Y;
    s_keyMap[Qt::Key_Z] = AKEYCODE::Z;
    
    s_keyMap[Qt::Key_0] = AKEYCODE::KEY_0;
    s_keyMap[Qt::Key_1] = AKEYCODE::KEY_1;
    s_keyMap[Qt::Key_2] = AKEYCODE::KEY_2;
    s_keyMap[Qt::Key_3] = AKEYCODE::KEY_3;
    s_keyMap[Qt::Key_4] = AKEYCODE::KEY_4;
    s_keyMap[Qt::Key_5] = AKEYCODE::KEY_5;
    s_keyMap[Qt::Key_6] = AKEYCODE::KEY_6;
    s_keyMap[Qt::Key_7] = AKEYCODE::KEY_7;
    s_keyMap[Qt::Key_8] = AKEYCODE::KEY_8;
    s_keyMap[Qt::Key_9] = AKEYCODE::KEY_9;
    
    s_keyMap[Qt::Key_Space] = AKEYCODE::SPACE;
    s_keyMap[Qt::Key_Return] = AKEYCODE::ENTER;
    s_keyMap[Qt::Key_Enter] = AKEYCODE::ENTER;
    s_keyMap[Qt::Key_Backspace] = AKEYCODE::DEL;
    s_keyMap[Qt::Key_Delete] = AKEYCODE::FORWARD_DEL;
    s_keyMap[Qt::Key_Tab] = AKEYCODE::TAB;
    s_keyMap[Qt::Key_Escape] = AKEYCODE::ESCAPE;
    
    s_keyMap[Qt::Key_Up] = AKEYCODE::DPAD_UP;
    s_keyMap[Qt::Key_Down] = AKEYCODE::DPAD_DOWN;
    s_keyMap[Qt::Key_Left] = AKEYCODE::DPAD_LEFT;
    s_keyMap[Qt::Key_Right] = AKEYCODE::DPAD_RIGHT;
    
    s_keyMap[Qt::Key_Home] = AKEYCODE::MOVE_HOME;
    s_keyMap[Qt::Key_End] = AKEYCODE::MOVE_END;
    s_keyMap[Qt::Key_PageUp] = AKEYCODE::PAGE_UP;
    s_keyMap[Qt::Key_PageDown] = AKEYCODE::PAGE_DOWN;
    s_keyMap[Qt::Key_Insert] = AKEYCODE::INSERT;
    
    s_keyMap[Qt::Key_Comma] = AKEYCODE::COMMA;
    s_keyMap[Qt::Key_Period] = AKEYCODE::PERIOD;
    s_keyMap[Qt::Key_Minus] = AKEYCODE::MINUS;
    s_keyMap[Qt::Key_Equal] = AKEYCODE::EQUALS;
    s_keyMap[Qt::Key_BracketLeft] = AKEYCODE::LEFT_BRACKET;
    s_keyMap[Qt::Key_BracketRight] = AKEYCODE::RIGHT_BRACKET;
    s_keyMap[Qt::Key_Backslash] = AKEYCODE::BACKSLASH;
    s_keyMap[Qt::Key_Semicolon] = AKEYCODE::SEMICOLON;
    s_keyMap[Qt::Key_Apostrophe] = AKEYCODE::APOSTROPHE;
    s_keyMap[Qt::Key_Slash] = AKEYCODE::SLASH;
    s_keyMap[Qt::Key_QuoteLeft] = AKEYCODE::GRAVE;
    
    s_keyMap[Qt::Key_F1] = AKEYCODE::F1;
    s_keyMap[Qt::Key_F2] = AKEYCODE::F2;
    s_keyMap[Qt::Key_F3] = AKEYCODE::F3;
    s_keyMap[Qt::Key_F4] = AKEYCODE::F4;
    s_keyMap[Qt::Key_F5] = AKEYCODE::F5;
    s_keyMap[Qt::Key_F6] = AKEYCODE::F6;
    s_keyMap[Qt::Key_F7] = AKEYCODE::F7;
    s_keyMap[Qt::Key_F8] = AKEYCODE::F8;
    s_keyMap[Qt::Key_F9] = AKEYCODE::F9;
    s_keyMap[Qt::Key_F10] = AKEYCODE::F10;
    s_keyMap[Qt::Key_F11] = AKEYCODE::F11;
    s_keyMap[Qt::Key_F12] = AKEYCODE::F12;
    
    s_keyMapInitialized = true;
}

void InputHandler::setControlStream(ControlStream* stream)
{
    m_controlStream = stream;
}

void InputHandler::setDeviceScreenSize(const QSize& size)
{
    m_deviceScreenSize = size;
}

void InputHandler::setVideoDisplaySize(const QSize& size)
{
    m_videoDisplaySize = size;
}

QPointF InputHandler::convertPosition(const QPoint& pos) const
{
    if (pos.x() < 0 || pos.y() < 0) {
        return QPointF(-1, -1);
    }

    if (m_deviceScreenSize.isEmpty()) {
        return QPointF(pos);
    }

    int x = pos.x();
    int y = pos.y();
    if (x >= m_deviceScreenSize.width()) {
        x = m_deviceScreenSize.width() - 1;
    }
    if (y >= m_deviceScreenSize.height()) {
        y = m_deviceScreenSize.height() - 1;
    }

    return QPointF(x, y);
}

int InputHandler::convertMouseButton(Qt::MouseButton button) const
{
    switch (button) {
        case Qt::LeftButton:
            return AMOTION_EVENT_BUTTON::PRIMARY;
        case Qt::RightButton:
            return AMOTION_EVENT_BUTTON::SECONDARY;
        case Qt::MiddleButton:
            return AMOTION_EVENT_BUTTON::TERTIARY;
        case Qt::BackButton:
            return AMOTION_EVENT_BUTTON::BACK;
        case Qt::ForwardButton:
            return AMOTION_EVENT_BUTTON::FORWARD;
        default:
            return 0;
    }
}

int InputHandler::convertMouseButtons(Qt::MouseButtons buttons) const
{
    int result = 0;
    
    if (buttons & Qt::LeftButton) {
        result |= convertMouseButton(Qt::LeftButton);
    }
    if (buttons & Qt::RightButton) {
        result |= convertMouseButton(Qt::RightButton);
    }
    if (buttons & Qt::MiddleButton) {
        result |= convertMouseButton(Qt::MiddleButton);
    }
    if (buttons & Qt::BackButton) {
        result |= convertMouseButton(Qt::BackButton);
    }
    if (buttons & Qt::ForwardButton) {
        result |= convertMouseButton(Qt::ForwardButton);
    }
    
    return result;
}

int InputHandler::convertKeyCode(int qtKey) const
{
    return s_keyMap.value(qtKey, AKEYCODE::UNKNOWN);
}

int InputHandler::convertMetaState(Qt::KeyboardModifiers modifiers) const
{
    int metaState = AMETA::NONE;
    
    if (modifiers & Qt::ShiftModifier) {
        metaState |= AMETA::SHIFT_ON | AMETA::SHIFT_LEFT_ON;
    }
    if (modifiers & Qt::ControlModifier) {
        metaState |= AMETA::CTRL_ON | AMETA::CTRL_LEFT_ON;
    }
    if (modifiers & Qt::AltModifier) {
        metaState |= AMETA::ALT_ON | AMETA::ALT_LEFT_ON;
    }
    if (modifiers & Qt::MetaModifier) {
        metaState |= AMETA::META_ON;
    }
    
    return metaState;
}

bool InputHandler::handleShortcut(QKeyEvent* event)
{
    if (!(event->modifiers() & Qt::ControlModifier)) {
        return false;
    }
    
    QString action;
    
    switch (event->key()) {
        case Qt::Key_H:
            action = "home";
            break;
        case Qt::Key_B:
            action = "back";
            break;
        case Qt::Key_S:
            action = "app_switch";
            break;
        case Qt::Key_M:
            action = "menu";
            break;
        case Qt::Key_P:
            action = "power";
            break;
        case Qt::Key_N:
            if (event->modifiers() & Qt::ShiftModifier) {
                action = "expand_settings";
            } else {
                action = "expand_notifications";
            }
            break;
        case Qt::Key_Up:
            action = "volume_up";
            break;
        case Qt::Key_Down:
            action = "volume_down";
            break;
        case Qt::Key_G:
            action = "resize_to_fit";
            break;
        case Qt::Key_X:
            action = "resize_to_screen";
            break;
        default:
            return false;
    }
    
    emit shortcutTriggered(action);
    return true;
}

void InputHandler::handleMousePress(QMouseEvent* event)
{
    if (!m_enabled || !m_controlStream) {
        return;
    }

    QPointF devicePos = convertPosition(event->pos());
    if (devicePos.x() < 0 || devicePos.y() < 0) {
        return;
    }

    m_mousePressed = true;
    m_lastMousePos = devicePos;
    m_pointerId = -1; // SC_POINTER_ID_MOUSE

    m_controlStream->sendTouch(
        static_cast<int>(AndroidMotionAction::Down),
        m_pointerId,
        devicePos,
        QSizeF(m_deviceScreenSize),
        1.0f,
        convertMouseButton(event->button()),
        convertMouseButtons(event->buttons())
    );
}

void InputHandler::handleMouseRelease(QMouseEvent* event)
{
    if (!m_enabled || !m_controlStream || !m_mousePressed) {
        return;
    }

    QPointF devicePos = convertPosition(event->pos());
    if (devicePos.x() < 0 || devicePos.y() < 0) {
        devicePos = m_lastMousePos;
    }

    m_controlStream->sendTouch(
        static_cast<int>(AndroidMotionAction::Up),
        m_pointerId,
        devicePos,
        QSizeF(m_deviceScreenSize),
        0.0f,
        convertMouseButton(event->button()),
        convertMouseButtons(event->buttons())
    );

    m_mousePressed = false;
}

void InputHandler::handleMouseMove(QMouseEvent* event)
{
    if (!m_enabled || !m_controlStream || !m_mousePressed) {
        return;
    }

    QPointF devicePos = convertPosition(event->pos());
    if (devicePos.x() < 0 || devicePos.y() < 0) {
        return;
    }

    // Only send when position changes
    if (devicePos != m_lastMousePos) {
        m_controlStream->sendTouch(
            static_cast<int>(AndroidMotionAction::Move),
            m_pointerId,
            devicePos,
            QSizeF(m_deviceScreenSize),
            1.0f,
            0,
            convertMouseButtons(event->buttons())
        );

        m_lastMousePos = devicePos;
    }
}

void InputHandler::handleWheel(QWheelEvent* event)
{
    if (!m_enabled || !m_controlStream) {
        return;
    }

    QPointF devicePos = convertPosition(event->position().toPoint());
    if (devicePos.x() < 0 || devicePos.y() < 0) {
        return;
    }

    // Normalize wheel delta to -1..1 steps
    float hScroll = event->angleDelta().x() / 120.0f;
    float vScroll = event->angleDelta().y() / 120.0f;

    m_controlStream->sendScroll(
        devicePos,
        QSizeF(m_deviceScreenSize),
        hScroll,
        vScroll,
        convertMouseButtons(event->buttons())
    );
}

void InputHandler::handleKeyPress(QKeyEvent* event)
{
    if (!m_enabled || !m_controlStream) {
        return;
    }
    
    // 首先检查快捷键
    if (handleShortcut(event)) {
        return;
    }
    
    // 处理文本输入
    if (event->key() == Qt::Key_unknown &&
        !event->text().isEmpty() &&
        !(event->modifiers() & (Qt::ControlModifier | Qt::AltModifier | Qt::MetaModifier))) {
        handleTextInput(event->text());
        return;
    }
    
    // 处理功能键
    int keycode = convertKeyCode(event->key());
    if (keycode != AKEYCODE::UNKNOWN) {
        m_controlStream->sendKeycode(
            static_cast<int>(AndroidKeyAction::Down),
            keycode,
            event->isAutoRepeat() ? 1 : 0,
            convertMetaState(event->modifiers())
        );
    }
}

void InputHandler::handleKeyRelease(QKeyEvent* event)
{
    if (!m_enabled || !m_controlStream) {
        return;
    }
    
    // 跳过快捷键
    if (event->modifiers() & Qt::ControlModifier) {
        return;
    }
    
    int keycode = convertKeyCode(event->key());
    if (keycode != AKEYCODE::UNKNOWN) {
        m_controlStream->sendKeycode(
            static_cast<int>(AndroidKeyAction::Up),
            keycode,
            0,
            convertMetaState(event->modifiers())
        );
    }
}

void InputHandler::handleTextInput(const QString& text)
{
    if (!m_enabled || !m_controlStream || text.isEmpty()) {
        return;
    }

    if (containsNonAscii(text)) {
        emit unicodeTextInputRequested(text);
        return;
    }

    m_controlStream->sendText(text);
}

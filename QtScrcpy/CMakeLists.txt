cmake_minimum_required(VERSION 3.16)
project(QtScrcpy VERSION 1.0.0 LANGUAGES CXX)

set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
set(CMAKE_AUTOMOC ON)
set(CMAKE_AUTORCC ON)
set(CMAKE_AUTOUIC ON)

# Qt6 配置
find_package(Qt6 REQUIRED COMPONENTS 
    Core 
    Gui 
    Widgets 
    Network
    Multimedia
)

# FFmpeg 配置
set(FFMPEG_DIR "${CMAKE_SOURCE_DIR}/third_party/ffmpeg")
if(WIN32)
    set(FFMPEG_INCLUDE_DIR "${FFMPEG_DIR}/include")
    set(FFMPEG_LIB_DIR "${FFMPEG_DIR}/lib")
    set(FFMPEG_BIN_DIR "${FFMPEG_DIR}/bin")
endif()

# 包含目录
include_directories(
    ${CMAKE_SOURCE_DIR}/src
    ${FFMPEG_INCLUDE_DIR}
)

# 链接库目录
link_directories(${FFMPEG_LIB_DIR})

# 源文件
set(SOURCES
    src/main.cpp
    src/ui/mainwindow.cpp
    src/ui/videowidget.cpp
    src/ui/devicelistdialog.cpp
    src/ui/settingsdialog.cpp
    src/ui/toolbarwidget.cpp
    src/adb/adbprocess.cpp
    src/adb/devicemanager.cpp
    src/adb/devicediscovery.cpp
    src/adb/shortcuts.cpp
    src/adb/volumecontroller.cpp
    src/decoder/decoder.cpp
    src/stream/videostream.cpp
    src/stream/controlstream.cpp
    src/input/inputhandler.cpp
    src/input/controlmessage.cpp
    src/clipboard/clipboardmanager.cpp
    src/filetransfer/filetransfer.cpp
    src/server/servermanager.cpp
)

# 头文件
set(HEADERS
    src/ui/mainwindow.h
    src/ui/videowidget.h
    src/ui/devicelistdialog.h
    src/ui/settingsdialog.h
    src/ui/toolbarwidget.h
    src/adb/adbprocess.h
    src/adb/devicemanager.h
    src/adb/devicediscovery.h
    src/adb/shortcuts.h
    src/adb/volumecontroller.h
    src/decoder/decoder.h
    src/stream/videostream.h
    src/stream/controlstream.h
    src/input/inputhandler.h
    src/input/controlmessage.h
    src/clipboard/clipboardmanager.h
    src/filetransfer/filetransfer.h
    src/server/servermanager.h
)

# 资源文件
set(RESOURCES
    resources/resources.qrc
)

# 可执行文件
add_executable(${PROJECT_NAME} WIN32
    ${SOURCES}
    ${HEADERS}
    ${RESOURCES}
)

# 链接库
target_link_libraries(${PROJECT_NAME} PRIVATE
    Qt6::Core
    Qt6::Gui
    Qt6::Widgets
    Qt6::Network
    Qt6::Multimedia
    avcodec
    avformat
    avutil
    swscale
)

# Windows 特定设置
if(WIN32)
    # 复制 FFmpeg DLL 到输出目录
    add_custom_command(TARGET ${PROJECT_NAME} POST_BUILD
        COMMAND ${CMAKE_COMMAND} -E copy_directory
        "${FFMPEG_BIN_DIR}"
        $<TARGET_FILE_DIR:${PROJECT_NAME}>
    )
    
    # 复制 ADB 到输出目录
    add_custom_command(TARGET ${PROJECT_NAME} POST_BUILD
        COMMAND ${CMAKE_COMMAND} -E copy_directory
        "${CMAKE_SOURCE_DIR}/third_party/adb"
        $<TARGET_FILE_DIR:${PROJECT_NAME}>/adb
    )
    
    # 复制 scrcpy-server 到输出目录
    add_custom_command(TARGET ${PROJECT_NAME} POST_BUILD
        COMMAND ${CMAKE_COMMAND} -E copy
        "${CMAKE_SOURCE_DIR}/resources/scrcpy-server"
        $<TARGET_FILE_DIR:${PROJECT_NAME}>/scrcpy-server
    )
endif()

# 安装规则
install(TARGETS ${PROJECT_NAME}
    RUNTIME DESTINATION bin
)

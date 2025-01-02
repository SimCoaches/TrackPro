cmake_minimum_required(VERSION 3.16)
project(GUI VERSION 0.1 LANGUAGES CXX)

set(CMAKE_AUTOUIC ON)
set(CMAKE_AUTOMOC ON)
set(CMAKE_AUTORCC ON)
set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)

# Find Qt packages
find_package(QT NAMES Qt6 Qt5 REQUIRED COMPONENTS Widgets Charts)
find_package(Qt${QT_VERSION_MAJOR} REQUIRED COMPONENTS Widgets Charts)

# Project sources
set(PROJECT_SOURCES
    mainwindow.cpp
    mainwindow.h
    mainwindow.ui
    ../src/CalibrationHandler.h
    ../src/RegistryHandler.h


    ../src/RegistryHandler.cpp
)

# Define executable
if(${QT_VERSION_MAJOR} GREATER_EQUAL 6)
    qt_add_executable(GUI
        MANUAL_FINALIZATION
        ${PROJECT_SOURCES}
        main.cpp
        ../src/CalibrationHandler.h ../src/RegistryHandler.h
        # Removed advancedwindow files
    )
else()
    if(ANDROID)
        add_library(GUI SHARED
            ${PROJECT_SOURCES}
        )
    else()
        add_executable(GUI
            ${PROJECT_SOURCES}
            main.cpp
        )
    endif()
endif()

target_link_libraries(GUI PRIVATE
    Qt${QT_VERSION_MAJOR}::Widgets
    Qt${QT_VERSION_MAJOR}::Charts
    dinput8
    dxguid
)

# Adjust for macOS if needed
if(${QT_VERSION} VERSION_LESS 6.1.0)
  set(BUNDLE_ID_OPTION MACOSX_BUNDLE_GUI_IDENTIFIER com.example.GUI)
endif()

set_target_properties(GUI PROPERTIES
    ${BUNDLE_ID_OPTION}
    MACOSX_BUNDLE_BUNDLE_VERSION ${PROJECT_VERSION}
    MACOSX_BUNDLE_SHORT_VERSION_STRING ${PROJECT_VERSION_MAJOR}.${PROJECT_VERSION_MINOR}
    MACOSX_BUNDLE TRUE
    WIN32_EXECUTABLE TRUE
)

include_directories(
    ../src
)

# Add deployment steps if on Windows
if(WIN32)
    set(DEBUG_SUFFIX)
    if(MSVC AND CMAKE_BUILD_TYPE MATCHES "Debug")
        set(DEBUG_SUFFIX "d")
    endif()
    set(QT_INSTALL_PATH "${CMAKE_PREFIX_PATH}")
    if(NOT EXISTS "${QT_INSTALL_PATH}")
        set(QT_INSTALL_PATH "${Qt${QT_VERSION_MAJOR}_DIR}/..")
    endif()
    if(EXISTS "${QT_INSTALL_PATH}/plugins/platforms/qwindows${DEBUG_SUFFIX}.dll")
        add_custom_command(TARGET GUI POST_BUILD
            COMMAND ${CMAKE_COMMAND} -E make_directory
                "$<TARGET_FILE_DIR:GUI>/plugins/platforms/")
        add_custom_command(TARGET GUI POST_BUILD
            COMMAND ${CMAKE_COMMAND} -E copy
                "${QT_INSTALL_PATH}/plugins/platforms/qwindows${DEBUG_SUFFIX}.dll"
                "$<TARGET_FILE_DIR:GUI>/plugins/platforms/")
    endif()
    foreach(Plugin Charts)
        add_custom_command(TARGET GUI POST_BUILD
            COMMAND ${CMAKE_COMMAND} -E copy
                "${QT_INSTALL_PATH}/bin/Qt${QT_VERSION_MAJOR}${Plugin}${DEBUG_SUFFIX}.dll"
                "$<TARGET_FILE_DIR:GUI>/")
    endforeach()
endif()

if(QT_VERSION_MAJOR EQUAL 6)
    qt_finalize_executable(GUI)
endif()

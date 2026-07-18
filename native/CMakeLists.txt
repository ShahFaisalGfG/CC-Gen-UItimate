cmake_minimum_required(VERSION 3.25)
project(ccgen_native VERSION 1.0.0 LANGUAGES CXX)

if(NOT WIN32)
    message(FATAL_ERROR "ccgen_native is a Windows-only target")
endif()

# ── Shell extension COM DLL (Windows 11 first-level context menu) ─────────────
# No external dependencies — pure Win32/COM, so no vcpkg toolchain is needed.

add_library(ccgen_shell SHARED src/shell_extension.cpp src/ccgen_shell.def)

set_target_properties(ccgen_shell PROPERTIES
    CXX_STANDARD 17
    CXX_STANDARD_REQUIRED ON
    PREFIX ""
    SUFFIX ".dll"
)

target_link_libraries(ccgen_shell PRIVATE ole32 shell32 uuid)

set(_SHELL_OUT_DIR "${PROJECT_SOURCE_DIR}/../build/shell")

foreach(_CONFIG Debug Release RelWithDebInfo MinSizeRel)
    set_target_properties(ccgen_shell PROPERTIES
        "RUNTIME_OUTPUT_DIRECTORY_${_CONFIG}" "${_SHELL_OUT_DIR}"
    )
endforeach()
set_target_properties(ccgen_shell PROPERTIES
    RUNTIME_OUTPUT_DIRECTORY "${_SHELL_OUT_DIR}"
)

# VS multi-config generators still append the config sub-folder, so copy the
# final DLL to the flat _SHELL_OUT_DIR explicitly.
add_custom_command(TARGET ccgen_shell POST_BUILD
    COMMAND ${CMAKE_COMMAND} -E copy_if_different
        "$<TARGET_FILE:ccgen_shell>"
        "${_SHELL_OUT_DIR}/ccgen_shell.dll"
)

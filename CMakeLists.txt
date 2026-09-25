cmake_minimum_required(VERSION 3.20)

# ChrononTemplate — the composition/template module of the Chronon stack.
#
# It is the sibling of ChrononMotion, whose motion primitives it consumes, and
# of Chronon3d, the renderer. This module owns recipes: composition presets and
# the social/web template catalog. It owns no renderer, no content bytes and no
# font layout — text and image identifiers stay opaque `ContentRef`s.
#
# `include/chrononmotion/templates/` is deliberately part of this module: the
# template catalog was moved out of the motion core and keeps its namespace.

project(ChrononTemplate
        VERSION 0.1.0
        DESCRIPTION "Composition presets and templates built on ChrononMotion"
        LANGUAGES CXX)

if(NOT CMAKE_SYSTEM_NAME STREQUAL "Linux")
    message(FATAL_ERROR "ChrononTemplate is Linux-only")
endif()

option(CHRONONTEMPLATE_BUILD_TESTS "Build the ChrononTemplate test binaries" ${PROJECT_IS_TOP_LEVEL})
option(CHRONONTEMPLATE_WERROR "Turn compiler warnings into errors" OFF)
option(CHRONONTEMPLATE_BUILD_LIVE_ADAPTER_TEST "Link the live adapter test against Chronon3D" OFF)
set(CHRONONTEMPLATE_CHRONON3D_LIBRARY "" CACHE FILEPATH
    "Chronon3D library used by the optional live adapter test")
set(CHRONONTEMPLATE_CHRONONMOTION_DIR "${CMAKE_CURRENT_SOURCE_DIR}/../ChrononMotion3D"
    CACHE PATH "ChrononMotion checkout used when the chrononmotion target is not already defined")
set(CHRONONTEMPLATE_CHRONONMOTION_PREBUILT_LIBRARY "" CACHE FILEPATH
    "Prebuilt libchrononmotion.a; when set, the core is not rebuilt from source")
set(CHRONONTEMPLATE_CHRONONMOTION_INCLUDE_DIR "${CHRONONTEMPLATE_CHRONONMOTION_DIR}/include" CACHE PATH
    "Include directory of the prebuilt ChrononMotion core")

if(PROJECT_IS_TOP_LEVEL AND NOT CMAKE_BUILD_TYPE AND NOT CMAKE_CONFIGURATION_TYPES)
    set(CMAKE_BUILD_TYPE Release CACHE STRING "Build type" FORCE)
endif()

# ── Motion primitives: the one hard dependency ────────────────────────────────
#
# A consumer that already builds the core (the Chronon build, a super project)
# defines the target first and this block is a no-op.

if(NOT TARGET ChrononMotion::chrononmotion)
    if(CHRONONTEMPLATE_CHRONONMOTION_PREBUILT_LIBRARY)
        # A hardware-neutral way to build this module alone: consume a core that
        # was already built, instead of recompiling the whole primary library in
        # this build tree. Both artefacts must come from the same core revision.
        if(NOT EXISTS "${CHRONONTEMPLATE_CHRONONMOTION_PREBUILT_LIBRARY}")
            message(FATAL_ERROR "CHRONONTEMPLATE_CHRONONMOTION_PREBUILT_LIBRARY not found: "
                                "${CHRONONTEMPLATE_CHRONONMOTION_PREBUILT_LIBRARY}")
        endif()
        add_library(ChrononMotion::chrononmotion STATIC IMPORTED GLOBAL)
        set_target_properties(ChrononMotion::chrononmotion PROPERTIES
                IMPORTED_LOCATION "${CHRONONTEMPLATE_CHRONONMOTION_PREBUILT_LIBRARY}"
                INTERFACE_INCLUDE_DIRECTORIES "${CHRONONTEMPLATE_CHRONONMOTION_INCLUDE_DIR}"
                INTERFACE_COMPILE_FEATURES cxx_std_20)
    elseif(EXISTS "${CHRONONTEMPLATE_CHRONONMOTION_DIR}/CMakeLists.txt")
        add_subdirectory("${CHRONONTEMPLATE_CHRONONMOTION_DIR}"
                         "${CMAKE_BINARY_DIR}/chrononmotion"
                         EXCLUDE_FROM_ALL)
    else()
        message(FATAL_ERROR
                "ChrononTemplate needs the `chrononmotion` target. No ChrononMotion checkout at "
                "'${CHRONONTEMPLATE_CHRONONMOTION_DIR}': set CHRONONTEMPLATE_CHRONONMOTION_DIR to one, or "
                "point CHRONONTEMPLATE_CHRONONMOTION_PREBUILT_LIBRARY at an already-built libchrononmotion.a.")
    endif()
endif()

add_library(chronontemplate STATIC
        # composition recipes on top of the motion primitives
        src/chronontemplate/Presets.cpp
        # the orchestration layer: bindings, the bridge, the template API
        src/chronontemplate/ContentBinding.cpp
        src/chronontemplate/MotionBridge.cpp
        src/chronontemplate/ChrononMotionContract.cpp
        src/chronontemplate/ChrononRenderAdapter.cpp
        src/chronontemplate/TemplateScene.cpp
        src/chronontemplate/ImageAnimationPack.cpp
        src/chronontemplate/ImportantPhrasePack.cpp
        src/chronontemplate/ClassicPhrasePack.cpp
        src/chronontemplate/TypewriterPhrasePack.cpp
        src/chronontemplate/Typewriter3DPhrasePack.cpp
        src/chronontemplate/ApplePhrasePack.cpp
        # the packs a template author starts from
        src/chronontemplate/templates/YouTubeSubscribe.cpp
        # the template catalog that used to live inside the motion core
        src/chrononmotion/templates/Templates.cpp)

add_library(ChrononTemplate::chronontemplate ALIAS chronontemplate)

# This module's include/ comes first on purpose: `chrononmotion/templates/` is
# owned here, while `chrononmotion/motion/` comes from the core.
target_include_directories(chronontemplate PUBLIC
        $<BUILD_INTERFACE:${CMAKE_CURRENT_SOURCE_DIR}/include>
        $<BUILD_INTERFACE:${CMAKE_CURRENT_SOURCE_DIR}/../Chronon3d/include>
        $<INSTALL_INTERFACE:include>)

target_link_libraries(chronontemplate PUBLIC ChrononMotion::chrononmotion)
target_compile_features(chronontemplate PUBLIC cxx_std_20)

target_compile_options(chronontemplate PRIVATE -Wall -Wextra)
if(CHRONONTEMPLATE_WERROR)
    target_compile_options(chronontemplate PRIVATE -Werror)
endif()

# ── Canonical catalog emitter ────────────────────────────────────────────────
#
# The catalog the renderer consumes is produced here rather than maintained by
# hand: this target validates `catalog/motion_catalog.v1.json` and merges the
# lists that are genuinely C++-owned (the template catalog and the composition
# presets). It needs a header-only JSON parser; point
# CHRONONTEMPLATE_NLOHMANN_JSON_INCLUDE_DIR at one when it is not on the
# default search path. The tool is a development artifact — the emitted file is
# what a consumer reads — so a checkout without the parser can still build the
# library by switching CHRONONTEMPLATE_BUILD_CATALOG_TOOL off.
option(CHRONONTEMPLATE_BUILD_CATALOG_TOOL "Build the canonical catalog emitter" ON)
set(CHRONONTEMPLATE_NLOHMANN_JSON_INCLUDE_DIR
    "${CMAKE_CURRENT_SOURCE_DIR}/../Chronon3d/vcpkg_installed/linux-fast-dev/x64-linux/include"
    CACHE PATH "Directory containing nlohmann/json.hpp (catalog emitter only)")

if(CHRONONTEMPLATE_BUILD_CATALOG_TOOL)
    find_path(CHRONONTEMPLATE_NLOHMANN_JSON_DIR nlohmann/json.hpp
              HINTS "${CHRONONTEMPLATE_NLOHMANN_JSON_INCLUDE_DIR}")
    if(NOT CHRONONTEMPLATE_NLOHMANN_JSON_DIR)
        message(FATAL_ERROR
                "chronontemplate_emit_catalog needs nlohmann/json.hpp. Set "
                "CHRONONTEMPLATE_NLOHMANN_JSON_INCLUDE_DIR to a directory containing it, "
                "or configure with -DCHRONONTEMPLATE_BUILD_CATALOG_TOOL=OFF.")
    endif()
    add_executable(chronontemplate_emit_catalog tools/emit_catalog.cpp)
    target_link_libraries(chronontemplate_emit_catalog PRIVATE chronontemplate)
    target_include_directories(chronontemplate_emit_catalog PRIVATE "${CHRONONTEMPLATE_NLOHMANN_JSON_DIR}")
    target_compile_definitions(chronontemplate_emit_catalog PRIVATE
            CHRONONTEMPLATE_CATALOG_FILE="${CMAKE_CURRENT_SOURCE_DIR}/catalog/motion_catalog.v1.json")
    target_compile_options(chronontemplate_emit_catalog PRIVATE -Wall -Wextra)
    if(CHRONONTEMPLATE_WERROR)
        target_compile_options(chronontemplate_emit_catalog PRIVATE -Werror)
    endif()

    # The Classic important-phrase pack lowers its fifteen C++ animations to
    # chronon.render-plan.v2 plans; the renderer draws the glow and the glyphs.
    add_executable(chronontemplate_emit_important_phrase_plans
            tools/emit_important_phrase_classic.cpp)
    target_link_libraries(chronontemplate_emit_important_phrase_plans PRIVATE chronontemplate)
    target_include_directories(chronontemplate_emit_important_phrase_plans PRIVATE
            "${CHRONONTEMPLATE_NLOHMANN_JSON_DIR}")
    target_compile_options(chronontemplate_emit_important_phrase_plans PRIVATE -Wall -Wextra)
    if(CHRONONTEMPLATE_WERROR)
        target_compile_options(chronontemplate_emit_important_phrase_plans PRIVATE -Werror)
    endif()

endif()

if(CHRONONTEMPLATE_BUILD_TESTS)
    enable_testing()

    add_executable(chronontemplate_templates_test tests/motion_templates.cpp)
    target_link_libraries(chronontemplate_templates_test PRIVATE chronontemplate)
    target_include_directories(chronontemplate_templates_test PRIVATE ${CMAKE_CURRENT_SOURCE_DIR}/tests)
    add_test(NAME chronontemplate_templates_test COMMAND chronontemplate_templates_test)

    add_executable(chronontemplate_presets_test tests/presets.cpp)
    target_link_libraries(chronontemplate_presets_test PRIVATE chronontemplate)
    target_include_directories(chronontemplate_presets_test PRIVATE ${CMAKE_CURRENT_SOURCE_DIR}/tests)
    add_test(NAME chronontemplate_presets_test COMMAND chronontemplate_presets_test)

    # The orchestration contract: bindings, controller layers, determinism, the
    # camera the bridge samples, and the staleness check the fingerprints exist for.
    add_executable(chronontemplate_scene_test tests/template_scene.cpp)
    target_link_libraries(chronontemplate_scene_test PRIVATE chronontemplate)
    target_include_directories(chronontemplate_scene_test PRIVATE ${CMAKE_CURRENT_SOURCE_DIR}/tests)
    add_test(NAME chronontemplate_scene_test COMMAND chronontemplate_scene_test)

    add_executable(chronontemplate_image_animation_pack_test tests/image_animation_pack.cpp)
    target_link_libraries(chronontemplate_image_animation_pack_test PRIVATE chronontemplate)
    target_include_directories(chronontemplate_image_animation_pack_test PRIVATE ${CMAKE_CURRENT_SOURCE_DIR}/tests)
    add_test(NAME chronontemplate_image_animation_pack_test COMMAND chronontemplate_image_animation_pack_test)

    # The important-phrase families, one file per family: the shared
    # white-on-black look + fourteen Classic definitions, and the fifteen
    # Typewriter definitions with their underscore cursor.
    add_executable(chronontemplate_classic_phrase_pack_test tests/classic_phrase_pack.cpp)
    target_link_libraries(chronontemplate_classic_phrase_pack_test PRIVATE chronontemplate)
    target_include_directories(chronontemplate_classic_phrase_pack_test PRIVATE ${CMAKE_CURRENT_SOURCE_DIR}/tests)
    add_test(NAME chronontemplate_classic_phrase_pack_test COMMAND chronontemplate_classic_phrase_pack_test)

    add_executable(chronontemplate_typewriter_phrase_pack_test tests/typewriter_phrase_pack.cpp)
    target_link_libraries(chronontemplate_typewriter_phrase_pack_test PRIVATE chronontemplate)
    target_include_directories(chronontemplate_typewriter_phrase_pack_test PRIVATE ${CMAKE_CURRENT_SOURCE_DIR}/tests)
    add_test(NAME chronontemplate_typewriter_phrase_pack_test COMMAND chronontemplate_typewriter_phrase_pack_test)

    add_executable(chronontemplate_typewriter_3d_pack_test tests/typewriter_3d_pack.cpp)
    target_link_libraries(chronontemplate_typewriter_3d_pack_test PRIVATE chronontemplate)
    target_include_directories(chronontemplate_typewriter_3d_pack_test PRIVATE ${CMAKE_CURRENT_SOURCE_DIR}/tests)
    add_test(NAME chronontemplate_typewriter_3d_pack_test COMMAND chronontemplate_typewriter_3d_pack_test)

    add_executable(chronontemplate_apple_phrase_pack_test tests/apple_phrase_pack.cpp)
    target_link_libraries(chronontemplate_apple_phrase_pack_test PRIVATE chronontemplate)
    target_include_directories(chronontemplate_apple_phrase_pack_test PRIVATE ${CMAKE_CURRENT_SOURCE_DIR}/tests)
    add_test(NAME chronontemplate_apple_phrase_pack_test COMMAND chronontemplate_apple_phrase_pack_test)

    # The first pack: the subscribe card, its controller-driven entrance/exit and
    # the click pulse that only holds because a preset appends keys.
    add_executable(chronontemplate_youtube_subscribe_test tests/youtube_subscribe.cpp)
    target_link_libraries(chronontemplate_youtube_subscribe_test PRIVATE chronontemplate)
    target_include_directories(chronontemplate_youtube_subscribe_test PRIVATE ${CMAKE_CURRENT_SOURCE_DIR}/tests)
    add_test(NAME chronontemplate_youtube_subscribe_test COMMAND chronontemplate_youtube_subscribe_test)

    add_executable(chronontemplate_chronon_motion_contract_test tests/chronon_motion_contract.cpp)
    target_link_libraries(chronontemplate_chronon_motion_contract_test PRIVATE chronontemplate)
    target_include_directories(chronontemplate_chronon_motion_contract_test PRIVATE ${CMAKE_CURRENT_SOURCE_DIR}/tests)
    add_test(NAME chronontemplate_chronon_motion_contract_test COMMAND chronontemplate_chronon_motion_contract_test)

    if(CHRONONTEMPLATE_BUILD_LIVE_ADAPTER_TEST)
        if(NOT EXISTS "${CHRONONTEMPLATE_CHRONON3D_LIBRARY}")
            message(FATAL_ERROR
                    "CHRONONTEMPLATE_BUILD_LIVE_ADAPTER_TEST requires "
                    "CHRONONTEMPLATE_CHRONON3D_LIBRARY")
        endif()
        add_executable(chronontemplate_chronon_render_adapter_test tests/chronon_render_adapter.cpp)
        target_link_libraries(chronontemplate_chronon_render_adapter_test PRIVATE
                chronontemplate "${CHRONONTEMPLATE_CHRONON3D_LIBRARY}")
        target_include_directories(chronontemplate_chronon_render_adapter_test PRIVATE ${CMAKE_CURRENT_SOURCE_DIR}/tests)
        add_test(NAME chronontemplate_chronon_render_adapter_test COMMAND chronontemplate_chronon_render_adapter_test)
    endif()
endif()

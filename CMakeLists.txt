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
set(CHRONONTEMPLATE_NLOHMANN_JSON_INCLUDE_DIR
    "${CMAKE_CURRENT_SOURCE_DIR}/../Chronon3d/vcpkg_installed/linux-fast-dev/x64-linux/include"
    CACHE PATH "Directory containing nlohmann/json.hpp")
find_path(CHRONONTEMPLATE_NLOHMANN_JSON_DIR nlohmann/json.hpp
          HINTS "${CHRONONTEMPLATE_NLOHMANN_JSON_INCLUDE_DIR}")
if(NOT CHRONONTEMPLATE_NLOHMANN_JSON_DIR)
    message(FATAL_ERROR "ChrononTemplate native plan builders require nlohmann/json.hpp")
endif()
set(CHRONONTEMPLATE_EDITORIAL_RENDERER_CLI "${CMAKE_CURRENT_SOURCE_DIR}/../Chronon3d/build/chronon/linux-video-test/apps/chronon3d_cli/chronon3d_cli"
    CACHE FILEPATH "Chronon3D CLI used to validate the editorial benchmark plans")
set(CHRONONTEMPLATE_CHRONON3D_LIBRARY "" CACHE FILEPATH
    "Chronon3D library used by the optional live adapter test")
# ── Renderer checkout: the one explicit Chronon3D dependency ─────────────────
#
# A headless template build still reads the renderer's neutral value types
# (`chronon/abi.h`, `chronon3d/graphics/*`) from this checkout. It is a
# checkout dependency, not a silent sibling-folder assumption: every
# `../Chronon3d` reference below goes through this variable, and a missing
# checkout fails here with the fix instead of a stray header error later.
if(EXISTS "${CMAKE_CURRENT_SOURCE_DIR}/../Chronon3d")
    set(CHRONONTEMPLATE_CHRONON3D_DEFAULT "${CMAKE_CURRENT_SOURCE_DIR}/../Chronon3d")
elseif(EXISTS "${CMAKE_CURRENT_SOURCE_DIR}/../Chronon3D")
    set(CHRONONTEMPLATE_CHRONON3D_DEFAULT "${CMAKE_CURRENT_SOURCE_DIR}/../Chronon3D")
else()
    set(CHRONONTEMPLATE_CHRONON3D_DEFAULT "${CMAKE_CURRENT_SOURCE_DIR}/../Chronon3d")
endif()
set(CHRONONTEMPLATE_CHRONON3D_DIR "${CHRONONTEMPLATE_CHRONON3D_DEFAULT}"
    CACHE PATH "Chronon3D checkout providing chronon/abi.h and chronon3d/graphics/*")
if(NOT EXISTS "${CHRONONTEMPLATE_CHRONON3D_DIR}/include/chronon/abi.h")
    message(FATAL_ERROR
            "ChrononTemplate needs chronon/abi.h from a Chronon3D checkout at "
            "'${CHRONONTEMPLATE_CHRONON3D_DIR}': set CHRONONTEMPLATE_CHRONON3D_DIR to one "
            "(CI checks out Marcuss-ops/Chronon3d next to this repo).")
endif()
if(NOT EXISTS "${CHRONONTEMPLATE_CHRONON3D_DIR}/include/chronon3d/graphics/field2d.hpp")
    message(FATAL_ERROR
            "ChrononTemplate needs chronon3d/graphics/field2d.hpp from a Chronon3D checkout at "
            "'${CHRONONTEMPLATE_CHRONON3D_DIR}'.")
endif()
# GLM comes from the system first (CI: libglm-dev); the Chronon3D vcpkg tree
# is the fallback so a checkout without system headers still configures.
find_path(CHRONONTEMPLATE_GLM_DIR glm/glm.hpp
          HINTS "${CHRONONTEMPLATE_CHRONON3D_DIR}/vcpkg_installed/linux-fast-dev/x64-linux/include")
if(NOT CHRONONTEMPLATE_GLM_DIR)
    message(FATAL_ERROR
            "ChrononTemplate needs glm/glm.hpp (CI installs libglm-dev): no system GLM found "
            "and no vendored copy under '${CHRONONTEMPLATE_CHRONON3D_DIR}/vcpkg_installed'.")
endif()
# magic_enum layout: upstream and vcpkg use `magic_enum/magic_enum.hpp`, but the
# Ubuntu package (`libmagicenum-dev`) ships a flat `magic_enum.hpp`. Prefer the
# real layout; otherwise generate a one-line compat header so Chronon3D's
# `core/enum_utils.hpp` keeps compiling without a vendored third-party copy.
find_path(CHRONONTEMPLATE_MAGIC_ENUM_DIR magic_enum/magic_enum.hpp
          HINTS "${CHRONONTEMPLATE_CHRONON3D_DIR}/vcpkg_installed/linux-fast-dev/x64-linux/include")
find_path(CHRONONTEMPLATE_MAGIC_ENUM_FLAT_DIR magic_enum.hpp)
if(CHRONONTEMPLATE_MAGIC_ENUM_DIR)
    set(CHRONONTEMPLATE_MAGIC_ENUM_INCLUDE_DIR "${CHRONONTEMPLATE_MAGIC_ENUM_DIR}")
    message(STATUS "ChrononTemplate: using magic_enum layout at ${CHRONONTEMPLATE_MAGIC_ENUM_INCLUDE_DIR}")
elseif(CHRONONTEMPLATE_MAGIC_ENUM_FLAT_DIR)
    file(MAKE_DIRECTORY "${CMAKE_BINARY_DIR}/chronontemplate_compat/magic_enum")
    file(WRITE "${CMAKE_BINARY_DIR}/chronontemplate_compat/magic_enum/magic_enum.hpp"
        "// Generated by ChrononTemplate: Ubuntu ships magic_enum flat, Chronon3D\n"
        "// includes the upstream magic_enum/magic_enum.hpp layout.\n"
        "#pragma once\n"
        "#include <magic_enum.hpp>\n")
    set(CHRONONTEMPLATE_MAGIC_ENUM_INCLUDE_DIR "${CMAKE_BINARY_DIR}/chronontemplate_compat")
    message(STATUS "ChrononTemplate: bridging flat magic_enum.hpp via generated compat header")
else()
    message(FATAL_ERROR
            "ChrononTemplate needs magic_enum (CI installs libmagicenum-dev): neither "
            "magic_enum/magic_enum.hpp nor a flat magic_enum.hpp was found.")
endif()
# stb layout, same story: vcpkg ships a flat `stb_image_write.h`, Ubuntu ships
# `stb/stb_image_write.h`, and the camera tool includes the flat path.
find_path(CHRONONTEMPLATE_STB_FLAT_DIR stb_image_write.h
          HINTS "${CHRONONTEMPLATE_CHRONON3D_DIR}/vcpkg_installed/linux-video-fast-dev/x64-linux/include")
find_path(CHRONONTEMPLATE_STB_SUBDIR_DIR stb/stb_image_write.h)
if(CHRONONTEMPLATE_STB_FLAT_DIR)
    message(STATUS "ChrononTemplate: using flat stb headers at ${CHRONONTEMPLATE_STB_FLAT_DIR}")
elseif(CHRONONTEMPLATE_STB_SUBDIR_DIR)
    file(MAKE_DIRECTORY "${CMAKE_BINARY_DIR}/chronontemplate_compat")
    file(WRITE "${CMAKE_BINARY_DIR}/chronontemplate_compat/stb_image_write.h"
        "// Generated by ChrononTemplate: Ubuntu ships stb under stb/, the camera\n"
        "// tool includes the flat vcpkg path.\n"
        "#pragma once\n"
        "#include <stb/stb_image_write.h>\n")
    message(STATUS "ChrononTemplate: bridging stb/stb_image_write.h via generated compat header")
else()
    message(FATAL_ERROR
            "ChrononTemplate needs stb_image_write.h (CI installs libstb-dev): no flat "
            "nor stb/-prefixed copy was found.")
endif()
if(EXISTS "${CMAKE_CURRENT_SOURCE_DIR}/../ChrononMotion3D")
    set(CHRONONTEMPLATE_CHRONONMOTION_DEFAULT "${CMAKE_CURRENT_SOURCE_DIR}/../ChrononMotion3D")
else()
    set(CHRONONTEMPLATE_CHRONONMOTION_DEFAULT "${CMAKE_CURRENT_SOURCE_DIR}/../ChrononMotion3d")
endif()
set(CHRONONTEMPLATE_CHRONONMOTION_DIR "${CHRONONTEMPLATE_CHRONONMOTION_DEFAULT}"
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
        src/chronontemplate/core/Presets.cpp
        src/chronontemplate/core/NativePrimitives.cpp
        # the orchestration layer: bindings, the bridge, the template API
        # (the live C-ABI handoff lives in chronontemplate_live_adapter below,
        # so the pure template core has no renderer-link dependency)
        src/chronontemplate/core/ContentBinding.cpp
        src/chronontemplate/core/MotionBridge.cpp
        src/chronontemplate/core/TemplateScene.cpp
        src/chronontemplate/core/PlanLowering.cpp
        src/chronontemplate/core/RenderPlanContentHost.cpp
        # Optional offline RenderPlan bridge lives outside the Motion core.
        "${CHRONONTEMPLATE_CHRONONMOTION_DIR}/src/chrononmotion/motion/RenderPlanLowering.cpp"
        src/chronontemplate/single_images/ImageAnimationPack.cpp
        src/chronontemplate/investigation_board/InvestigationBoardPack.cpp
        src/chronontemplate/single_images/PixelGridPack.cpp
        src/chronontemplate/single_images/EdgeStrokePack.cpp
        src/chronontemplate/single_images/GlowPack.cpp
        src/chronontemplate/single_images/RGBSplitPack.cpp
        src/chronontemplate/elements/ElementsCommon.cpp
        src/chronontemplate/elements/TimelineElements.cpp
        src/chronontemplate/elements/AnnotationElements.cpp
        src/chronontemplate/elements/HighlightingV2.cpp
        src/chronontemplate/elements/WebElements.cpp
        src/chronontemplate/elements/DocumentaryElements.cpp
        src/chronontemplate/elements/DiagramElements.cpp
        src/chronontemplate/vintage_documentary/VintageDocumentaryPack.cpp
        src/chronontemplate/vintage_documentary/VintageDocumentaryTitle01Pack.cpp
        src/chronontemplate/documentary_effects/MagnifierLoupePack.cpp
        src/chronontemplate/documentary_effects/RedactedPack.cpp
        src/chronontemplate/documentary_effects/FilmLeaderPack.cpp
        src/chronontemplate/documentary_effects/DepthParallaxPack.cpp
        src/chronontemplate/documentary_effects/RouteDrawingPack.cpp
        src/chronontemplate/documentary_effects/ArchivalTimelinePack.cpp
        src/chronontemplate/documentary_effects/BeforeAfterPack.cpp
        src/chronontemplate/documentary_effects/AnimatedCountersPack.cpp
        src/chronontemplate/camera_roll/TitleCameraPack.cpp
        src/chronontemplate/camera_roll/WordLensPack.cpp
        src/chronontemplate/bullet_list/BulletListPack.cpp
        src/chronontemplate/effects/EffectsPack.cpp
        src/chronontemplate/camera_roll/SceneCameraPack.cpp
        src/chronontemplate/camera_roll/CameraMotionPack.cpp
        include/chronontemplate/camera_roll/CameraMotionPresets.def
        src/chronontemplate/ui_camera/UiCameraChoreography.cpp
        src/chronontemplate/entities_with_text/DocumentarySnapshotPack.cpp
        src/chronontemplate/date_groups/DateGroupsPack.cpp
        src/chronontemplate/date_timeline/DateTimelinePack.cpp
        src/chronontemplate/fast_intro/FastIntroPack.cpp
        src/chronontemplate/entities_with_text/EntityFilmstripPack.cpp
        src/chronontemplate/important_phrases/ImportantPhrasePack.cpp
        src/chronontemplate/important_phrases/apple/ApplePhrasePack.cpp
        src/chronontemplate/important_phrases/highlight/HighlightPhrasePack.cpp
        src/chronontemplate/important_phrases/didone/DidoneTitlesPack.cpp
        # the category packs: many images in one scene, full-frame backgrounds, modern map compositions
        src/chronontemplate/multiple_images/MultiImagePack.cpp
        src/chronontemplate/backgrounds/BackgroundPack.cpp
        src/chronontemplate/backgrounds/ProceduralBackground.cpp
        src/chronontemplate/map/ModernMapPack.cpp
        # the short-phrase family: surviving recipes plus the star bumper
        src/chronontemplate/short_phrases/ShortPhrasePack.cpp
        include/chronontemplate/short_phrases/ShortPhraseRecipes.def
        src/chronontemplate/short_phrases/animations/BlurOutUp.cpp
        src/chronontemplate/short_phrases/animations/BottomUpLetters.cpp
        src/chronontemplate/short_phrases/animations/FocusBlurResolve.cpp
        src/chronontemplate/short_phrases/animations/KineticCenterBuild.cpp
        src/chronontemplate/short_phrases/animations/PerWordRise.cpp
        src/chronontemplate/short_phrases/animations/PerspectiveMarquee.cpp
        src/chronontemplate/short_phrases/animations/StrikethroughReplace.cpp
        src/chronontemplate/short_phrases/animations/TextMatchCut.cpp
        src/chronontemplate/short_phrases/animations/TextShimmer.cpp
        src/chronontemplate/short_phrases/animations/ChromaticFringeTitle.cpp
        src/chronontemplate/short_phrases/animations/MaskedHeading.cpp
        src/chronontemplate/short_phrases/animations/SplitFlapText.cpp
        src/chronontemplate/short_phrases/animations/ScrollReveal.cpp
        src/chronontemplate/short_phrases/animations/ScrambledText.cpp
        src/chronontemplate/short_phrases/animations/GradualBlur.cpp
        # the packs a template author starts from
        src/chronontemplate/entities_with_text/YouTubeSubscribe.cpp
        # the native web-page family: complete page + highlight 3D + blurred phrases
        src/chronontemplate/web/WebPageHighlightPack.cpp
        src/chronontemplate/web/WebHeadlineHighlightPack.cpp
        src/chronontemplate/web/WebTextLayout.cpp
        src/chronontemplate/web/ArticleEvidenceReveal.cpp
        # second generation: radians-safe fold, distinct recipes, reworked hierarchy
        src/chronontemplate/web/WebPageV2Pack.cpp
        # native layout composers: flex rows, columns and grids plus FLIP moves
        src/chronontemplate/composers/LayoutComposer.cpp
        # declarative transitions (BACKLOG item 4): sweep/dip/blinds/iris/glitch/leak
        src/chronontemplate/transitions/TransitionPack.cpp
        # captions + data-viz (BACKLOG item 5): PCM beat grid, captions, bar chart
        src/chronontemplate/captions_dataviz/CaptionsDataVizPack.cpp
        # modern, semantically qualified chart recipes
        src/chronontemplate/charts/ChartsPack.cpp
        # the template catalog that used to live inside the motion core
        src/chrononmotion/templates/Templates.cpp)

add_library(ChrononTemplate::chronontemplate ALIAS chronontemplate)


include(${CMAKE_CURRENT_SOURCE_DIR}/cmake/Tools.cmake)

add_executable(chronontemplate_emit_beast_land_subject_reframe
        tools/documentary_effects/emit_beast_land_subject_reframe.cpp)
target_link_libraries(chronontemplate_emit_beast_land_subject_reframe PRIVATE chronontemplate)
target_include_directories(chronontemplate_emit_beast_land_subject_reframe PRIVATE
        "${CMAKE_CURRENT_SOURCE_DIR}/include"
        "${CMAKE_CURRENT_SOURCE_DIR}/../Chronon3d/include"
        "${CHRONONTEMPLATE_NLOHMANN_JSON_DIR}")
target_compile_options(chronontemplate_emit_beast_land_subject_reframe PRIVATE -Wall -Wextra)

add_executable(chronontemplate_resolve_camera_samples
        tools/camera_roll/resolve_camera_samples.cpp)
target_link_libraries(chronontemplate_resolve_camera_samples PRIVATE chronontemplate)
target_include_directories(chronontemplate_resolve_camera_samples PRIVATE
        ${CMAKE_CURRENT_SOURCE_DIR}/include
        ${CHRONONTEMPLATE_NLOHMANN_JSON_DIR})
target_compile_options(chronontemplate_resolve_camera_samples PRIVATE -Wall -Wextra)

add_executable(chronontemplate_emit_screen_recording_camera_recreation
        tools/camera_roll/emit_screen_recording_camera_recreation.cpp)
target_link_libraries(chronontemplate_emit_screen_recording_camera_recreation PRIVATE ChrononMotion::chrononmotion)
target_include_directories(chronontemplate_emit_screen_recording_camera_recreation PRIVATE
        "${CHRONONTEMPLATE_NLOHMANN_JSON_DIR}")
target_compile_options(chronontemplate_emit_screen_recording_camera_recreation PRIVATE -Wall -Wextra)

add_executable(chronontemplate_emit_ai_tabletop_camera
        tools/camera_roll/emit_ai_tabletop_camera.cpp)
target_link_libraries(chronontemplate_emit_ai_tabletop_camera PRIVATE ChrononMotion::chrononmotion)
target_include_directories(chronontemplate_emit_ai_tabletop_camera PRIVATE
        "${CHRONONTEMPLATE_NLOHMANN_JSON_DIR}")
target_compile_options(chronontemplate_emit_ai_tabletop_camera PRIVATE -Wall -Wextra)

add_executable(chronontemplate_emit_bounded_box
        tools/web_presets/emit_bounded_box.cpp)
target_link_libraries(chronontemplate_emit_bounded_box PRIVATE chronontemplate)
target_include_directories(chronontemplate_emit_bounded_box PRIVATE
        "${CHRONONTEMPLATE_NLOHMANN_JSON_DIR}")
target_compile_options(chronontemplate_emit_bounded_box PRIVATE -Wall -Wextra)

add_executable(chronontemplate_emit_camera_bullet_focus
        tools/web_presets/emit_camera_bullet_focus.cpp)
target_link_libraries(chronontemplate_emit_camera_bullet_focus PRIVATE ChrononMotion::chrononmotion)
# CameraRig's resolved-sample lowering (bakeResolvedCameraSamples,
# cameraSamplesToJson) lives in CM3D's optional Chronon3d adapter. Use it when
# this build provides the target, otherwise compile the single lowering TU in.
# CM3D's RenderPlanLowering (pulled in by CameraRig) uses the Chronon3d
# render-plan contract types, so this target needs the sibling include tree.
if(TARGET chrononmotion_chronon3d_adapter)
    target_link_libraries(chronontemplate_emit_camera_bullet_focus
            PRIVATE chrononmotion_chronon3d_adapter)
else()
    target_sources(chronontemplate_emit_camera_bullet_focus PRIVATE
        "${CHRONONTEMPLATE_CHRONONMOTION_DIR}/src/chrononmotion/motion/RenderPlanLowering.cpp")
    target_include_directories(chronontemplate_emit_camera_bullet_focus PRIVATE
        "${CHRONONTEMPLATE_CHRONONMOTION_DIR}/include"
        "${CHRONONTEMPLATE_CHRONON3D_DIR}/include")
endif()
target_include_directories(chronontemplate_emit_camera_bullet_focus PRIVATE
        "${CMAKE_CURRENT_SOURCE_DIR}/../Chronon3d/include"
        "${CHRONONTEMPLATE_NLOHMANN_JSON_DIR}")
target_compile_options(chronontemplate_emit_camera_bullet_focus PRIVATE -Wall -Wextra)

add_executable(chronontemplate_emit_bullet_camera_10
        tools/bulletpoints_3d/emit_bullet_camera_10.cpp)
target_link_libraries(chronontemplate_emit_bullet_camera_10 PRIVATE chronontemplate)
target_include_directories(chronontemplate_emit_bullet_camera_10 PRIVATE
        "${CMAKE_CURRENT_SOURCE_DIR}/../Chronon3d/include")
target_compile_options(chronontemplate_emit_bullet_camera_10 PRIVATE -Wall -Wextra)

add_executable(chronontemplate_emit_web_article_fold
        tools/web_presets/emit_web_article_fold.cpp)
target_include_directories(chronontemplate_emit_web_article_fold PRIVATE
        "${CHRONONTEMPLATE_NLOHMANN_JSON_DIR}")
target_compile_options(chronontemplate_emit_web_article_fold PRIVATE -Wall -Wextra)

# The native web-page family: three recipes x two themes, all pure C++ V3
# plans — no Pillow plate, no browser, no screenshot.
add_executable(chronontemplate_emit_web_page_highlight
        tools/web_presets/emit_web_page_highlight.cpp)
target_link_libraries(chronontemplate_emit_web_page_highlight PRIVATE chronontemplate)
target_compile_options(chronontemplate_emit_web_page_highlight PRIVATE -Wall -Wextra)

# The headline highlighter looks (statement page, marker sweep, stepped
# highlight) recreated from the supplied reference frames as native V3 plans.
add_executable(chronontemplate_emit_web_headline_highlight
        tools/web_presets/emit_web_headline_highlight.cpp)
target_link_libraries(chronontemplate_emit_web_headline_highlight PRIVATE chronontemplate)
target_compile_options(chronontemplate_emit_web_headline_highlight PRIVATE -Wall -Wextra)

# Reference web phrase rebuilds are direct native render-plan V3 data. The
# provided screenshots supply copy and composition references only.
add_executable(chronontemplate_emit_reference_web_phrases
        tools/web_presets/emit_reference_web_phrases.cpp)
target_link_libraries(chronontemplate_emit_reference_web_phrases PRIVATE chronontemplate)
target_include_directories(chronontemplate_emit_reference_web_phrases PRIVATE
        "${CHRONONTEMPLATE_NLOHMANN_JSON_DIR}")
target_compile_options(chronontemplate_emit_reference_web_phrases PRIVATE -Wall -Wextra)

# Ten-photo NBA corkboard Fast Intro with native editable camera and note layers.
add_executable(chronontemplate_emit_fast_intro_board_10
        tools/nba_rivalry/emit_fast_intro_board_10.cpp)
target_include_directories(chronontemplate_emit_fast_intro_board_10 PRIVATE
        "${CHRONONTEMPLATE_NLOHMANN_JSON_DIR}")
target_compile_options(chronontemplate_emit_fast_intro_board_10 PRIVATE -Wall -Wextra)

# Parametric investigation board: JSON input -> native corkboard, cards, pins,
# red strings and a baked camera pan.
add_executable(chronontemplate_emit_investigation_board
        tools/investigation_board/emit_investigation_board.cpp)
target_include_directories(chronontemplate_emit_investigation_board PRIVATE
        "${CHRONONTEMPLATE_NLOHMANN_JSON_DIR}")
target_compile_options(chronontemplate_emit_investigation_board PRIVATE -Wall -Wextra)

add_executable(chronontemplate_emit_web_classic_home
        tools/web_presets/emit_web_classic_home.cpp)
target_link_libraries(chronontemplate_emit_web_classic_home PRIVATE chronontemplate)
target_compile_options(chronontemplate_emit_web_classic_home PRIVATE -Wall -Wextra)

add_executable(chronontemplate_emit_classic_web_pages
        tools/web_presets/emit_classic_web_pages.cpp)
target_include_directories(chronontemplate_emit_classic_web_pages PRIVATE
        "${CHRONONTEMPLATE_NLOHMANN_JSON_DIR}")
target_compile_options(chronontemplate_emit_classic_web_pages PRIVATE -Wall -Wextra)

# Guardian article uses the established reference layout, which matches the supplied classic-page image.
add_executable(chronontemplate_emit_reference_article_shots
        tools/web_presets/emit_reference_article_shots.cpp)
target_include_directories(chronontemplate_emit_reference_article_shots PRIVATE
        "${CHRONONTEMPLATE_NLOHMANN_JSON_DIR}")
target_compile_options(chronontemplate_emit_reference_article_shots PRIVATE -Wall -Wextra)

# Second generation: radians-safe fold, distinct recipes, reworked hierarchy.
add_executable(chronontemplate_emit_web_page_v2
        tools/web_presets/emit_web_page_v2.cpp)
target_link_libraries(chronontemplate_emit_web_page_v2 PRIVATE chronontemplate)
target_compile_options(chronontemplate_emit_web_page_v2 PRIVATE -Wall -Wextra)

# Single-frame archive triptych, authored as a native RenderPlan V3 in C++.
add_executable(chronontemplate_emit_web_archive_triptych
        tools/web_presets/emit_web_archive_triptych.cpp)
target_include_directories(chronontemplate_emit_web_archive_triptych PRIVATE
        "${CHRONONTEMPLATE_NLOHMANN_JSON_DIR}")
target_compile_options(chronontemplate_emit_web_archive_triptych PRIVATE -Wall -Wextra)

# Three individual stills matching the remaining supplied web references.
add_executable(chronontemplate_emit_web_reference_stills
        tools/web_presets/emit_web_reference_stills.cpp)
target_include_directories(chronontemplate_emit_web_reference_stills PRIVATE
        "${CHRONONTEMPLATE_NLOHMANN_JSON_DIR}")
target_compile_options(chronontemplate_emit_web_reference_stills PRIVATE -Wall -Wextra)

# Static full-resolution stills for the existing image-effect treatments.
add_executable(chronontemplate_emit_image_effect_samples
        tools/web_presets/emit_image_effect_samples.cpp)
target_include_directories(chronontemplate_emit_image_effect_samples PRIVATE
        "${CHRONONTEMPLATE_NLOHMANN_JSON_DIR}")
target_compile_options(chronontemplate_emit_image_effect_samples PRIVATE -Wall -Wextra)


# This module's include/ comes first on purpose: `chrononmotion/templates/` is
# owned here, while `chrononmotion/motion/` comes from the core.
target_include_directories(chronontemplate PUBLIC
        $<BUILD_INTERFACE:${CMAKE_CURRENT_SOURCE_DIR}/include>
        $<BUILD_INTERFACE:${CHRONONTEMPLATE_CHRONON3D_DIR}/include>
        $<BUILD_INTERFACE:${CHRONONTEMPLATE_GLM_DIR}>
        $<BUILD_INTERFACE:${CHRONONTEMPLATE_MAGIC_ENUM_INCLUDE_DIR}>
        $<BUILD_INTERFACE:${CHRONONTEMPLATE_NLOHMANN_JSON_DIR}>
        $<INSTALL_INTERFACE:include>)

target_link_libraries(chronontemplate PUBLIC ChrononMotion::chrononmotion)
# ── Live Chronon3D adapter: the pure/adapter boundary ────────────────────────
#
# Pure template recipes (the library above) never link the renderer. The two
# C-ABI handoff units sit in this adapter target instead: it links the pure
# core above and the Chronon3D headers, and only it mentions the live
# `chronon_engine`/`chronon_plan` handles. Headless builds (CI) compile and
# test the core without ever needing a Chronon3D library binary.
add_library(chronontemplate_live_adapter STATIC
        src/chronontemplate/core/ChrononMotionContract.cpp
        src/chronontemplate/core/ChrononRenderAdapter.cpp)
add_library(ChrononTemplate::live_adapter ALIAS chronontemplate_live_adapter)
target_link_libraries(chronontemplate_live_adapter PUBLIC chronontemplate)
target_include_directories(chronontemplate_live_adapter PUBLIC
        $<BUILD_INTERFACE:${CMAKE_CURRENT_SOURCE_DIR}/include>
        $<BUILD_INTERFACE:${CHRONONTEMPLATE_CHRONON3D_DIR}/include>
        $<BUILD_INTERFACE:${CHRONONTEMPLATE_GLM_DIR}>
        $<BUILD_INTERFACE:${CHRONONTEMPLATE_MAGIC_ENUM_INCLUDE_DIR}>
        $<BUILD_INTERFACE:${CHRONONTEMPLATE_NLOHMANN_JSON_DIR}>
        $<INSTALL_INTERFACE:include>)
target_compile_features(chronontemplate_live_adapter PUBLIC cxx_std_20)
target_compile_options(chronontemplate_live_adapter PRIVATE -Wall -Wextra)
if(CHRONONTEMPLATE_WERROR)
    target_compile_options(chronontemplate_live_adapter PRIVATE -Werror)
endif()
target_compile_features(chronontemplate PUBLIC cxx_std_20)

target_compile_options(chronontemplate PRIVATE -Wall -Wextra)
if(CHRONONTEMPLATE_WERROR)
    target_compile_options(chronontemplate PRIVATE -Werror)
endif()


include(${CMAKE_CURRENT_SOURCE_DIR}/cmake/Tests.cmake)

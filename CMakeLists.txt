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
        src/chronontemplate/core/ContentBinding.cpp
        src/chronontemplate/core/MotionBridge.cpp
        src/chronontemplate/core/ChrononMotionContract.cpp
        src/chronontemplate/core/ChrononRenderAdapter.cpp
        src/chronontemplate/core/TemplateScene.cpp
        src/chronontemplate/core/PlanLowering.cpp
        src/chronontemplate/core/RenderPlanContentHost.cpp
        # Optional offline RenderPlan bridge lives outside the Motion core.
        "${CHRONONTEMPLATE_CHRONONMOTION_DIR}/src/chrononmotion/motion/RenderPlanLowering.cpp"
        src/chronontemplate/single_images/ImageAnimationPack.cpp
        src/chronontemplate/camera_roll/TitleCameraPack.cpp
        src/chronontemplate/camera_roll/SceneCameraPack.cpp
        src/chronontemplate/entities_with_text/DocumentarySnapshotPack.cpp
        src/chronontemplate/entities_with_text/EntityFilmstripPack.cpp
        src/chronontemplate/important_phrases/ImportantPhrasePack.cpp
        src/chronontemplate/important_phrases/classic/ClassicPhrasePack.cpp
        src/chronontemplate/important_phrases/typewriter/TypewriterPhrasePack.cpp
        src/chronontemplate/important_phrases/typewriter_3d/Typewriter3DPhrasePack.cpp
        src/chronontemplate/important_phrases/apple/ApplePhrasePack.cpp
        src/chronontemplate/important_phrases/highlight/PhraseHighlightPack.cpp
        src/chronontemplate/important_phrases/didone/DidoneTitlesPack.cpp
        # the category packs: many images in one scene, full-frame backgrounds, modern map compositions
        src/chronontemplate/multiple_images/MultiImagePack.cpp
        src/chronontemplate/backgrounds/BackgroundPack.cpp
        src/chronontemplate/map/ModernMapPack.cpp
        # the short-phrase family: one vocabulary, twelve archetypes, plus the star bumper
        src/chronontemplate/short_phrases/ShortPhrasePack.cpp
        src/chronontemplate/short_phrases/animations/BlurOutUp.cpp
        src/chronontemplate/short_phrases/animations/BottomUpLetters.cpp
        src/chronontemplate/short_phrases/animations/FocusBlurResolve.cpp
        src/chronontemplate/short_phrases/animations/KineticCenterBuild.cpp
        src/chronontemplate/short_phrases/animations/LineByLineSlide.cpp
        src/chronontemplate/short_phrases/animations/PerWordRise.cpp
        src/chronontemplate/short_phrases/animations/PerspectiveMarquee.cpp
        src/chronontemplate/short_phrases/animations/ScanBand.cpp
        src/chronontemplate/short_phrases/animations/ScrambleReveal.cpp
        src/chronontemplate/short_phrases/animations/StrikethroughReplace.cpp
        src/chronontemplate/short_phrases/animations/TextMatchCut.cpp
        src/chronontemplate/short_phrases/animations/TextShimmer.cpp
        src/chronontemplate/short_phrases/animations/WeightWave.cpp
        src/chronontemplate/short_phrases/animations/ChromaticFringeTitle.cpp
        src/chronontemplate/short_phrases/animations/MaskedHeading.cpp
        src/chronontemplate/short_phrases/animations/SplitFlapText.cpp
        src/chronontemplate/short_phrases/animations/WarpText.cpp
        src/chronontemplate/short_phrases/animations/FoldText.cpp
        src/chronontemplate/short_phrases/animations/DecryptedText.cpp
        src/chronontemplate/short_phrases/animations/ScrollReveal.cpp
        src/chronontemplate/short_phrases/animations/ScrambledText.cpp
        src/chronontemplate/short_phrases/animations/GlareHover.cpp
        src/chronontemplate/short_phrases/animations/GlowCursor.cpp
        src/chronontemplate/short_phrases/animations/GradualBlur.cpp
        src/chronontemplate/short_phrases/animations/ShapeBlur.cpp
        # the packs a template author starts from
        src/chronontemplate/entities_with_text/YouTubeSubscribe.cpp
        # native layout composers: flex rows, columns and grids plus FLIP moves
        src/chronontemplate/composers/LayoutComposer.cpp
        # declarative transitions (BACKLOG item 4): sweep/dip/blinds/iris/glitch/leak
        src/chronontemplate/transitions/TransitionPack.cpp
        # captions + data-viz (BACKLOG item 5): PCM beat grid, captions, bar chart
        src/chronontemplate/captions_dataviz/CaptionsDataVizPack.cpp
        # the template catalog that used to live inside the motion core
        src/chrononmotion/templates/Templates.cpp)

add_library(ChrononTemplate::chronontemplate ALIAS chronontemplate)

add_executable(chronontemplate_dump_title_camera_poses tools/camera_roll/dump_title_camera_poses.cpp)
target_link_libraries(chronontemplate_dump_title_camera_poses PRIVATE chronontemplate)

add_executable(chronontemplate_dump_scene_camera_poses tools/camera_roll/dump_scene_camera_poses.cpp)
target_link_libraries(chronontemplate_dump_scene_camera_poses PRIVATE chronontemplate)

add_executable(chronontemplate_sequence_from_json tools/camera_roll/sequence_from_json.cpp)
target_link_libraries(chronontemplate_sequence_from_json PRIVATE chronontemplate)
target_include_directories(chronontemplate_sequence_from_json PRIVATE "${CHRONONTEMPLATE_NLOHMANN_JSON_DIR}")

add_executable(chronontemplate_emit_entity_filmstrip_reference
        tools/entities_with_text/emit_entity_filmstrip_reference.cpp)
target_link_libraries(chronontemplate_emit_entity_filmstrip_reference PRIVATE chronontemplate)
if(TARGET chrononmotion_chronon3d_adapter)
    target_link_libraries(chronontemplate_emit_entity_filmstrip_reference PRIVATE chrononmotion_chronon3d_adapter)
else()
    set(CHRONONTEMPLATE_RENDER_PLAN_EMISSION_DIR
        "${CHRONONTEMPLATE_CHRONONMOTION_DIR}/src/chrononmotion/motion")
    target_sources(chronontemplate_emit_entity_filmstrip_reference PRIVATE
        "${CHRONONTEMPLATE_RENDER_PLAN_EMISSION_DIR}/RenderPlanEmission.cpp"
        "${CHRONONTEMPLATE_RENDER_PLAN_EMISSION_DIR}/RenderPlanEmissionCommon.cpp"
        "${CHRONONTEMPLATE_RENDER_PLAN_EMISSION_DIR}/RenderPlanEmissionValidation.cpp")
    target_include_directories(chronontemplate_emit_entity_filmstrip_reference PRIVATE
        "${CHRONONTEMPLATE_CHRONONMOTION_DIR}/include"
        "${CMAKE_CURRENT_SOURCE_DIR}/../Chronon3d/include"
        "${CHRONONTEMPLATE_NLOHMANN_JSON_DIR}")
endif()
target_compile_options(chronontemplate_emit_entity_filmstrip_reference PRIVATE -Wall -Wextra)

add_executable(chronontemplate_dump_documentary_snapshot_pose
        tools/entities_with_text/dump_documentary_snapshot_pose.cpp)
target_link_libraries(chronontemplate_dump_documentary_snapshot_pose PRIVATE chronontemplate)

# The full native CLI canary needs ChrononMotion's optional typed JSON writer.
if(TARGET chrononmotion_chronon3d_adapter)
    add_executable(chronontemplate_dump_documentary_snapshot_plan
            tools/entities_with_text/dump_documentary_snapshot_plan.cpp)
    target_link_libraries(chronontemplate_dump_documentary_snapshot_plan
            PRIVATE chronontemplate chrononmotion_chronon3d_adapter)
endif()

# This module's include/ comes first on purpose: `chrononmotion/templates/` is
# owned here, while `chrononmotion/motion/` comes from the core.
target_include_directories(chronontemplate PUBLIC
        $<BUILD_INTERFACE:${CMAKE_CURRENT_SOURCE_DIR}/include>
        $<BUILD_INTERFACE:${CMAKE_CURRENT_SOURCE_DIR}/../Chronon3d/include>
        $<BUILD_INTERFACE:${CHRONONTEMPLATE_NLOHMANN_JSON_DIR}>
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

if(CHRONONTEMPLATE_BUILD_CATALOG_TOOL)
    add_executable(chronontemplate_emit_catalog tools/emit_catalog.cpp)
    target_link_libraries(chronontemplate_emit_catalog PRIVATE chronontemplate)
    target_include_directories(chronontemplate_emit_catalog PRIVATE "${CHRONONTEMPLATE_NLOHMANN_JSON_DIR}")
    target_compile_definitions(chronontemplate_emit_catalog PRIVATE
            CHRONONTEMPLATE_CATALOG_FILE="${CMAKE_CURRENT_SOURCE_DIR}/catalog/motion_catalog.v1.json"
            CHRONONTEMPLATE_ENTITY_PRESENTATION_FILE="${CMAKE_CURRENT_SOURCE_DIR}/catalog/entity_presentation.v1.json")
    target_compile_options(chronontemplate_emit_catalog PRIVATE -Wall -Wextra)
    if(CHRONONTEMPLATE_WERROR)
        target_compile_options(chronontemplate_emit_catalog PRIVATE -Werror)
    endif()

    # The Classic important-phrase pack lowers its fifteen C++ animations to
    # chronon.render-plan.v2 plans; the renderer draws the glow and the glyphs.
    add_executable(chronontemplate_emit_important_phrase_plans
            tools/important_phrases/emit_important_phrase_classic.cpp)
    target_link_libraries(chronontemplate_emit_important_phrase_plans PRIVATE chronontemplate)
    target_include_directories(chronontemplate_emit_important_phrase_plans PRIVATE
            "${CHRONONTEMPLATE_NLOHMANN_JSON_DIR}")
    target_compile_options(chronontemplate_emit_important_phrase_plans PRIVATE -Wall -Wextra)
    if(CHRONONTEMPLATE_WERROR)
        target_compile_options(chronontemplate_emit_important_phrase_plans PRIVATE -Werror)
    endif()

    # The short-phrase catalog: twelve archetypes + the decor bumper, projected
    # from the C++ pack into catalog/short_phrase_motion.v1.json.
    add_executable(chronontemplate_emit_short_phrase_catalog
            tools/short_phrases/emit_short_phrase_catalog.cpp)
    target_link_libraries(chronontemplate_emit_short_phrase_catalog PRIVATE chronontemplate)
    target_include_directories(chronontemplate_emit_short_phrase_catalog PRIVATE
            "${CHRONONTEMPLATE_NLOHMANN_JSON_DIR}")
    target_compile_options(chronontemplate_emit_short_phrase_catalog PRIVATE -Wall -Wextra)
    if(CHRONONTEMPLATE_WERROR)
        target_compile_options(chronontemplate_emit_short_phrase_catalog PRIVATE -Werror)
    endif()

    # The short-phrase render plans: one chronon.render-plan.v2 per archetype,
    # ready for the Chronon3D GPU CLI. See render_short_phrases.sh.
    add_executable(chronontemplate_emit_short_phrase_plans
            tools/short_phrases/emit_short_phrase_plans.cpp)
    target_link_libraries(chronontemplate_emit_short_phrase_plans PRIVATE chronontemplate)
    target_include_directories(chronontemplate_emit_short_phrase_plans PRIVATE
            "${CHRONONTEMPLATE_NLOHMANN_JSON_DIR}")
    target_compile_options(chronontemplate_emit_short_phrase_plans PRIVATE -Wall -Wextra)
    if(CHRONONTEMPLATE_WERROR)
        target_compile_options(chronontemplate_emit_short_phrase_plans PRIVATE -Werror)
    endif()

endif()

add_executable(chronontemplate_emit_blackboard_torture_v1
        tools/emit_blackboard_torture_v1.cpp)
target_link_libraries(chronontemplate_emit_blackboard_torture_v1 PRIVATE chronontemplate)
target_compile_options(chronontemplate_emit_blackboard_torture_v1 PRIVATE -Wall -Wextra)
if(CHRONONTEMPLATE_WERROR)
    target_compile_options(chronontemplate_emit_blackboard_torture_v1 PRIVATE -Werror)
endif()

# Optional native-plan canary for deterministic BackgroundPack V3 emission.
add_executable(chronontemplate_background_canary_v1 tools/backgrounds/background_canary_v1.cpp)
target_link_libraries(chronontemplate_background_canary_v1 PRIVATE chronontemplate)
if(TARGET chrononmotion_chronon3d_adapter)
    target_link_libraries(chronontemplate_background_canary_v1 PRIVATE chrononmotion_chronon3d_adapter)
else()
    set(CHRONONTEMPLATE_RENDER_PLAN_EMISSION_DIR
        "${CHRONONTEMPLATE_CHRONONMOTION_DIR}/src/chrononmotion/motion")
    target_sources(chronontemplate_background_canary_v1 PRIVATE
        "${CHRONONTEMPLATE_RENDER_PLAN_EMISSION_DIR}/RenderPlanEmission.cpp"
        "${CHRONONTEMPLATE_RENDER_PLAN_EMISSION_DIR}/RenderPlanEmissionCommon.cpp"
        "${CHRONONTEMPLATE_RENDER_PLAN_EMISSION_DIR}/RenderPlanEmissionValidation.cpp")
    target_include_directories(chronontemplate_background_canary_v1 PRIVATE
        "${CHRONONTEMPLATE_CHRONONMOTION_DIR}/include"
        "${CMAKE_CURRENT_SOURCE_DIR}/../Chronon3d/include"
        "${CHRONONTEMPLATE_NLOHMANN_JSON_DIR}")
endif()
target_compile_options(chronontemplate_background_canary_v1 PRIVATE -Wall -Wextra)

# Optional native-plan canary for rapid transition frame-range validation.
add_executable(chronontemplate_transition_canary_v1 tools/transitions/transition_canary_v1.cpp)
target_link_libraries(chronontemplate_transition_canary_v1 PRIVATE chronontemplate)
if(TARGET chrononmotion_chronon3d_adapter)
    target_link_libraries(chronontemplate_transition_canary_v1 PRIVATE chrononmotion_chronon3d_adapter)
else()
    set(CHRONONTEMPLATE_RENDER_PLAN_EMISSION_DIR
        "${CHRONONTEMPLATE_CHRONONMOTION_DIR}/src/chrononmotion/motion")
    target_sources(chronontemplate_transition_canary_v1 PRIVATE
        "${CHRONONTEMPLATE_RENDER_PLAN_EMISSION_DIR}/RenderPlanEmission.cpp"
        "${CHRONONTEMPLATE_RENDER_PLAN_EMISSION_DIR}/RenderPlanEmissionCommon.cpp"
        "${CHRONONTEMPLATE_RENDER_PLAN_EMISSION_DIR}/RenderPlanEmissionValidation.cpp")
    target_include_directories(chronontemplate_transition_canary_v1 PRIVATE
        "${CHRONONTEMPLATE_CHRONONMOTION_DIR}/include"
        "${CMAKE_CURRENT_SOURCE_DIR}/../Chronon3d/include"
        "${CHRONONTEMPLATE_NLOHMANN_JSON_DIR}")
endif()

if(CHRONONTEMPLATE_BUILD_TESTS)
    enable_testing()

    find_package(Python3 COMPONENTS Interpreter QUIET)
    if(Python3_Interpreter_FOUND)
        add_test(NAME chronontemplate_multi_image_duo_contract
            COMMAND "${Python3_EXECUTABLE}"
                    "${CMAKE_CURRENT_SOURCE_DIR}/tools/multiple_images/test_multi_image_duo_v1.py")
        add_test(NAME chronontemplate_named_multi_entity_duo_contract
            COMMAND "${Python3_EXECUTABLE}"
                    "${CMAKE_CURRENT_SOURCE_DIR}/tools/multiple_images/test_named_multi_entity_duo_v1.py")
        add_test(NAME chronontemplate_kit_contract
            COMMAND "${Python3_EXECUTABLE}"
                    "${CMAKE_CURRENT_SOURCE_DIR}/tools/test_kit_contract.py")
        add_test(NAME chronontemplate_multi_image_trio_v2_contract
            COMMAND "${Python3_EXECUTABLE}"
                    "${CMAKE_CURRENT_SOURCE_DIR}/tools/multiple_images/test_multi_image_trio_v2.py")
        add_test(NAME chronontemplate_entity_presentation_contract
            COMMAND "${Python3_EXECUTABLE}"
                    "${CMAKE_CURRENT_SOURCE_DIR}/tools/entities_with_text/test_entity_presentation_v1.py")
        add_test(NAME chronontemplate_kinetic_type_editorial_contract
            COMMAND "${Python3_EXECUTABLE}"
                    "${CMAKE_CURRENT_SOURCE_DIR}/tools/important_phrases/test_kinetic_type_editorial_v1.py")
        add_test(NAME chronontemplate_social_motion_pack_contract
            COMMAND "${Python3_EXECUTABLE}"
                    "${CMAKE_CURRENT_SOURCE_DIR}/tools/important_phrases/test_social_motion_pack_v1.py")
        add_test(NAME chronontemplate_text_depth_focus_contract
            COMMAND "${Python3_EXECUTABLE}"
                    "${CMAKE_CURRENT_SOURCE_DIR}/tools/important_phrases/test_text_depth_focus_v1.py")
        add_test(NAME chronontemplate_saas_kinetic_typography_contract
            COMMAND "${Python3_EXECUTABLE}"
                    "${CMAKE_CURRENT_SOURCE_DIR}/tools/important_phrases/test_saas_kinetic_typography_v1.py")
        add_test(NAME chronontemplate_rgb_motion_v1_contract
            COMMAND "${Python3_EXECUTABLE}"
                    "${CMAKE_CURRENT_SOURCE_DIR}/tools/backgrounds/test_rgb_motion_v1.py")
        add_test(NAME chronontemplate_map_motion_family_contract
            COMMAND "${Python3_EXECUTABLE}"
                    "${CMAKE_CURRENT_SOURCE_DIR}/tools/map/test_map_motion_family_v1.py")
    endif()
    if(Python3_Interpreter_FOUND AND EXISTS "${CHRONONTEMPLATE_EDITORIAL_RENDERER_CLI}")
        add_test(NAME chronontemplate_editorial_benchmark_contract
            COMMAND "${Python3_EXECUTABLE}"
                    "${CMAKE_CURRENT_SOURCE_DIR}/tools/important_phrases/editorial_benchmark_suite.py"
                    --validate-only
                    --cli "${CHRONONTEMPLATE_EDITORIAL_RENDERER_CLI}"
                    --output-dir "${CMAKE_CURRENT_BINARY_DIR}/editorial_benchmark_contract")
        add_test(NAME chronontemplate_kinetic_type_editorial_renderer_contract
            COMMAND "${Python3_EXECUTABLE}"
                    "${CMAKE_CURRENT_SOURCE_DIR}/tools/important_phrases/build_kinetic_type_editorial_v1.py"
                    --validate-only
                    --cli "${CHRONONTEMPLATE_EDITORIAL_RENDERER_CLI}"
                    --out "${CMAKE_CURRENT_BINARY_DIR}/kinetic_type_editorial_contract")
    endif()

    add_executable(chronontemplate_templates_test tests/motion_templates.cpp)
    target_link_libraries(chronontemplate_templates_test PRIVATE chronontemplate)
    target_include_directories(chronontemplate_templates_test PRIVATE ${CMAKE_CURRENT_SOURCE_DIR}/tests)
    add_test(NAME chronontemplate_templates_test COMMAND chronontemplate_templates_test)

    add_executable(chronontemplate_native_primitives_test tests/native_primitives.cpp)
    target_link_libraries(chronontemplate_native_primitives_test PRIVATE chronontemplate)
    add_test(NAME chronontemplate_native_primitives_test COMMAND chronontemplate_native_primitives_test)

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

    add_executable(chronontemplate_plan_lowering_test tests/plan_lowering.cpp)
    target_link_libraries(chronontemplate_plan_lowering_test PRIVATE chronontemplate)
    target_include_directories(chronontemplate_plan_lowering_test PRIVATE ${CMAKE_CURRENT_SOURCE_DIR}/tests)
    add_test(NAME chronontemplate_plan_lowering_test COMMAND chronontemplate_plan_lowering_test)

    add_executable(chronontemplate_image_animation_pack_test tests/image_animation_pack.cpp)
    target_link_libraries(chronontemplate_image_animation_pack_test PRIVATE chronontemplate)
    target_include_directories(chronontemplate_image_animation_pack_test PRIVATE ${CMAKE_CURRENT_SOURCE_DIR}/tests)
    add_test(NAME chronontemplate_image_animation_pack_test COMMAND chronontemplate_image_animation_pack_test)

    # The title-camera documentary family: the title never animates, the camera
    # is the only authored motion, and the eight family gates hold for all
    # twenty title_camera_* presets.
    add_executable(chronontemplate_title_camera_pack_test tests/title_camera_pack.cpp)
    target_link_libraries(chronontemplate_title_camera_pack_test PRIVATE chronontemplate)
    target_include_directories(chronontemplate_title_camera_pack_test PRIVATE ${CMAKE_CURRENT_SOURCE_DIR}/tests)
    add_test(NAME chronontemplate_title_camera_pack_test COMMAND chronontemplate_title_camera_pack_test)

    # The scene-camera sequencer family: the subjects never animate, the camera
    # carries the frame from hold to hold, every leg lands exactly on the next
    # rest, and the framing gate holds for all eight scene_camera_* transitions.
    add_executable(chronontemplate_scene_camera_pack_test tests/scene_camera_pack.cpp)
    target_link_libraries(chronontemplate_scene_camera_pack_test PRIVATE chronontemplate)
    target_include_directories(chronontemplate_scene_camera_pack_test PRIVATE ${CMAKE_CURRENT_SOURCE_DIR}/tests)
    add_test(NAME chronontemplate_scene_camera_pack_test COMMAND chronontemplate_scene_camera_pack_test)

    if(Python3_Interpreter_FOUND)
        add_test(NAME chronontemplate_scene_sequence_json_contract
            COMMAND "${Python3_EXECUTABLE}"
                    "${CMAKE_CURRENT_SOURCE_DIR}/tools/camera_roll/test_scene_sequence_json.py"
                    --tool "$<TARGET_FILE:chronontemplate_sequence_from_json>")
    endif()

    # The short-phrase catalog contract: the emitter is fail-closed and the
    # committed catalog must be exactly what the C++ pack emits today.
    if(Python3_Interpreter_FOUND AND TARGET chronontemplate_emit_short_phrase_catalog)
        add_test(NAME chronontemplate_short_phrase_catalog_contract
            COMMAND "${Python3_EXECUTABLE}"
                    "${CMAKE_CURRENT_SOURCE_DIR}/tools/short_phrases/test_short_phrase_catalog.py"
                    --tool "$<TARGET_FILE:chronontemplate_emit_short_phrase_catalog>"
                    --catalog "${CMAKE_CURRENT_SOURCE_DIR}/catalog/short_phrase_motion.v1.json")
    endif()

    # Title-to-snapshot documentary scenes are ordinary text/image layers with
    # narrative recipes resolved onto the shared CameraRig.
    add_executable(chronontemplate_entity_filmstrip_pack_test
            tests/entity_filmstrip_pack.cpp)
    target_link_libraries(chronontemplate_entity_filmstrip_pack_test PRIVATE chronontemplate)
    target_include_directories(chronontemplate_entity_filmstrip_pack_test PRIVATE ${CMAKE_CURRENT_SOURCE_DIR}/tests)
    add_test(NAME chronontemplate_entity_filmstrip_pack_test
            COMMAND chronontemplate_entity_filmstrip_pack_test)

    add_executable(chronontemplate_documentary_snapshot_pack_test
            tests/documentary_snapshot_pack.cpp)
    target_link_libraries(chronontemplate_documentary_snapshot_pack_test PRIVATE chronontemplate)
    target_include_directories(chronontemplate_documentary_snapshot_pack_test PRIVATE ${CMAKE_CURRENT_SOURCE_DIR}/tests)
    add_test(NAME chronontemplate_documentary_snapshot_pack_test
            COMMAND chronontemplate_documentary_snapshot_pack_test)

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

    add_executable(chronontemplate_didone_titles_pack_test tests/didone_titles_pack.cpp)
    target_link_libraries(chronontemplate_didone_titles_pack_test PRIVATE chronontemplate)
    target_include_directories(chronontemplate_didone_titles_pack_test PRIVATE ${CMAKE_CURRENT_SOURCE_DIR}/tests)
    add_test(NAME chronontemplate_didone_titles_pack_test COMMAND chronontemplate_didone_titles_pack_test)

    # The category packs: the multi-image board, full-frame backgrounds and the
    # replacement modern map composition API (styled labels + camera movement).
    add_executable(chronontemplate_multi_image_pack_test tests/multi_image_pack.cpp)
    target_link_libraries(chronontemplate_multi_image_pack_test PRIVATE chronontemplate)
    target_include_directories(chronontemplate_multi_image_pack_test PRIVATE ${CMAKE_CURRENT_SOURCE_DIR}/tests)
    add_test(NAME chronontemplate_multi_image_pack_test COMMAND chronontemplate_multi_image_pack_test)

    add_executable(chronontemplate_background_pack_test tests/background_pack.cpp)
    target_link_libraries(chronontemplate_background_pack_test PRIVATE chronontemplate)
    target_include_directories(chronontemplate_background_pack_test PRIVATE ${CMAKE_CURRENT_SOURCE_DIR}/tests)
    add_test(NAME chronontemplate_background_pack_test COMMAND chronontemplate_background_pack_test)
        add_test(NAME chronontemplate_background_plan_contract
            COMMAND $<TARGET_FILE:chronontemplate_background_canary_v1>
                    "${CMAKE_CURRENT_BINARY_DIR}/background-canary")


    # The declarative transition family: every look covers or washes its cut on
    # the authored midpoint, clears by the end, and stays a pure function of
    # (scene, frame).
    add_executable(chronontemplate_transitions_pack_test tests/transitions_pack.cpp)
    target_link_libraries(chronontemplate_transitions_pack_test PRIVATE chronontemplate)
    target_include_directories(chronontemplate_transitions_pack_test PRIVATE ${CMAKE_CURRENT_SOURCE_DIR}/tests)
    add_test(NAME chronontemplate_transitions_pack_test COMMAND chronontemplate_transitions_pack_test)
    add_executable(chronontemplate_composer_pack_test tests/composer_pack.cpp)
    target_link_libraries(chronontemplate_composer_pack_test PRIVATE chronontemplate)
    target_include_directories(chronontemplate_composer_pack_test PRIVATE ${CMAKE_CURRENT_SOURCE_DIR}/tests)
    add_test(NAME chronontemplate_composer_pack_test COMMAND chronontemplate_composer_pack_test)
    # The caption/data-viz family: the PCM beat grid is deterministic, captions
    # line up one per beat, the chart grows staggered and lands on its peak.
    add_executable(chronontemplate_captions_dataviz_pack_test tests/captions_dataviz_pack.cpp)
    target_link_libraries(chronontemplate_captions_dataviz_pack_test PRIVATE chronontemplate)
    target_include_directories(chronontemplate_captions_dataviz_pack_test PRIVATE ${CMAKE_CURRENT_SOURCE_DIR}/tests)
    add_test(NAME chronontemplate_captions_dataviz_pack_test COMMAND chronontemplate_captions_dataviz_pack_test)

    add_executable(chronontemplate_modern_map_pack_test tests/modern_map_pack.cpp)
    target_link_libraries(chronontemplate_modern_map_pack_test PRIVATE chronontemplate)
    target_include_directories(chronontemplate_modern_map_pack_test PRIVATE ${CMAKE_CURRENT_SOURCE_DIR}/tests)
    add_test(NAME chronontemplate_modern_map_pack_test COMMAND chronontemplate_modern_map_pack_test)

    # The short-phrase family: the twelve archetypes, the semantic emphasis, the
    # exit modes and the star decor bumper.
    add_executable(chronontemplate_short_phrase_pack_test tests/short_phrase_pack.cpp)
    target_link_libraries(chronontemplate_short_phrase_pack_test PRIVATE chronontemplate)
    target_include_directories(chronontemplate_short_phrase_pack_test PRIVATE ${CMAKE_CURRENT_SOURCE_DIR}/tests)
    add_test(NAME chronontemplate_short_phrase_pack_test COMMAND chronontemplate_short_phrase_pack_test)

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

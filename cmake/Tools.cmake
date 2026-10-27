# ChrononTemplate tools (extracted from CMakeLists.txt; no new targets).
# Demo/showcase emitters, the canonical catalog emitter and the canaries.
# Included after the `chronontemplate` + `chronontemplate_live_adapter` targets.
add_executable(chronontemplate_emit_text_depth_focus
        tools/important_phrases/emit_text_depth_focus.cpp)
target_link_libraries(chronontemplate_emit_text_depth_focus PRIVATE chronontemplate)
target_include_directories(chronontemplate_emit_text_depth_focus PRIVATE
        "${CMAKE_CURRENT_SOURCE_DIR}/include"
        "${CHRONONTEMPLATE_NLOHMANN_JSON_DIR}")
target_compile_features(chronontemplate_emit_text_depth_focus PRIVATE cxx_std_20)
target_compile_options(chronontemplate_emit_text_depth_focus PRIVATE -Wall -Wextra)

add_executable(chronontemplate_dump_title_camera_poses tools/camera_roll/dump_title_camera_poses.cpp)
target_link_libraries(chronontemplate_dump_title_camera_poses PRIVATE chronontemplate)

add_executable(chronontemplate_dump_scene_camera_poses tools/camera_roll/dump_scene_camera_poses.cpp)
target_link_libraries(chronontemplate_dump_scene_camera_poses PRIVATE chronontemplate)

add_executable(chronontemplate_emit_title_camera_v2 tools/camera_roll/emit_title_camera_v2.cpp)
target_link_libraries(chronontemplate_emit_title_camera_v2 PRIVATE chronontemplate)
target_include_directories(chronontemplate_emit_title_camera_v2 PRIVATE "${CHRONONTEMPLATE_NLOHMANN_JSON_DIR}")
target_compile_options(chronontemplate_emit_title_camera_v2 PRIVATE -Wall -Wextra)

add_executable(chronontemplate_emit_word_lens_reference
        tools/camera_roll/emit_word_lens_reference.cpp)
target_link_libraries(chronontemplate_emit_word_lens_reference PRIVATE chronontemplate)
if(TARGET chrononmotion_chronon3d_adapter)
    target_link_libraries(chronontemplate_emit_word_lens_reference
            PRIVATE chrononmotion_chronon3d_adapter)
else()
    set(CHRONONTEMPLATE_RENDER_PLAN_EMISSION_DIR
        "${CHRONONTEMPLATE_CHRONONMOTION_DIR}/src/chrononmotion/motion")
    target_sources(chronontemplate_emit_word_lens_reference PRIVATE
        "${CHRONONTEMPLATE_RENDER_PLAN_EMISSION_DIR}/RenderPlanEmission.cpp"
        "${CHRONONTEMPLATE_RENDER_PLAN_EMISSION_DIR}/RenderPlanEmissionCommon.cpp"
        "${CHRONONTEMPLATE_RENDER_PLAN_EMISSION_DIR}/RenderPlanEmissionValidation.cpp")
    target_include_directories(chronontemplate_emit_word_lens_reference PRIVATE
        "${CHRONONTEMPLATE_CHRONONMOTION_DIR}/include"
        "${CHRONONTEMPLATE_CHRONON3D_DIR}/include"
        "${CHRONONTEMPLATE_NLOHMANN_JSON_DIR}")
endif()
target_compile_options(chronontemplate_emit_word_lens_reference PRIVATE -Wall -Wextra)

add_executable(chronontemplate_sequence_from_json tools/camera_roll/sequence_from_json.cpp)
target_link_libraries(chronontemplate_sequence_from_json PRIVATE chronontemplate)
target_include_directories(chronontemplate_sequence_from_json PRIVATE "${CHRONONTEMPLATE_NLOHMANN_JSON_DIR}")

add_executable(chronontemplate_emit_ui_choreography_canary tools/ui_camera/emit_ui_choreography_canary.cpp)
target_link_libraries(chronontemplate_emit_ui_choreography_canary PRIVATE chronontemplate)
if(TARGET chrononmotion_chronon3d_adapter)
    target_link_libraries(chronontemplate_emit_ui_choreography_canary PRIVATE chrononmotion_chronon3d_adapter)
else()
    set(CHRONONTEMPLATE_RENDER_PLAN_EMISSION_DIR
        "${CHRONONTEMPLATE_CHRONONMOTION_DIR}/src/chrononmotion/motion")
    target_sources(chronontemplate_emit_ui_choreography_canary PRIVATE
        "${CHRONONTEMPLATE_RENDER_PLAN_EMISSION_DIR}/RenderPlanEmission.cpp"
        "${CHRONONTEMPLATE_RENDER_PLAN_EMISSION_DIR}/RenderPlanEmissionCommon.cpp"
        "${CHRONONTEMPLATE_RENDER_PLAN_EMISSION_DIR}/RenderPlanEmissionValidation.cpp")
    target_include_directories(chronontemplate_emit_ui_choreography_canary PRIVATE
        "${CHRONONTEMPLATE_CHRONONMOTION_DIR}/include"
        "${CHRONONTEMPLATE_CHRONON3D_DIR}/include"
        "${CHRONONTEMPLATE_NLOHMANN_JSON_DIR}")
endif()
target_compile_options(chronontemplate_emit_ui_choreography_canary PRIVATE -Wall -Wextra)

add_executable(chronontemplate_emit_camera_1950_story tools/camera_roll/emit_camera_1950_story.cpp)
target_link_libraries(chronontemplate_emit_camera_1950_story PRIVATE chronontemplate)
target_include_directories(chronontemplate_emit_camera_1950_story PRIVATE
    "${CHRONONTEMPLATE_NLOHMANN_JSON_DIR}"
    "${CHRONONTEMPLATE_CHRONON3D_DIR}/vcpkg_installed/linux-video-fast-dev/x64-linux/include")

add_executable(chronontemplate_emit_synthetic_cannabis_native
        tools/web_presets/emit_synthetic_cannabis_native.cpp)
target_link_libraries(chronontemplate_emit_synthetic_cannabis_native PRIVATE chronontemplate)
target_compile_options(chronontemplate_emit_synthetic_cannabis_native PRIVATE -Wall -Wextra)

add_executable(chronontemplate_emit_dark_nba_article_native
        tools/web_presets/emit_dark_nba_article_native.cpp)
target_link_libraries(chronontemplate_emit_dark_nba_article_native PRIVATE chronontemplate)
target_compile_options(chronontemplate_emit_dark_nba_article_native PRIVATE -Wall -Wextra)

add_executable(chronontemplate_generate_image_25d_clean_v1
        tools/single_images/generate_image_25d_clean_v1.cpp)
target_link_libraries(chronontemplate_generate_image_25d_clean_v1 PRIVATE chronontemplate)
target_compile_options(chronontemplate_generate_image_25d_clean_v1 PRIVATE -Wall -Wextra)

add_executable(chronontemplate_emit_cinematic_documentary_narrative
        tools/entities_with_text/emit_cinematic_documentary_narrative.cpp)
target_link_libraries(chronontemplate_emit_cinematic_documentary_narrative PRIVATE chronontemplate)
target_compile_options(chronontemplate_emit_cinematic_documentary_narrative PRIVATE -Wall -Wextra)

# Native C++ examples for the vector-map, date-marker, and fading-image samples.
add_executable(chronontemplate_emit_oil_crisis_reference_plans
        tools/showcases/emit_oil_crisis_reference_plans.cpp)
target_include_directories(chronontemplate_emit_oil_crisis_reference_plans PRIVATE
        "${CHRONONTEMPLATE_NLOHMANN_JSON_DIR}")
target_compile_features(chronontemplate_emit_oil_crisis_reference_plans PRIVATE cxx_std_20)
target_compile_options(chronontemplate_emit_oil_crisis_reference_plans PRIVATE -Wall -Wextra)

# Native C++ emitter for the Example Svg reference recreation (drive_downloads/ExampleSvg).
add_executable(chronontemplate_emit_example_svg_recreation_plans
        tools/showcases/emit_example_svg_recreation_plans.cpp)
target_include_directories(chronontemplate_emit_example_svg_recreation_plans PRIVATE
        "${CHRONONTEMPLATE_NLOHMANN_JSON_DIR}")
target_compile_features(chronontemplate_emit_example_svg_recreation_plans PRIVATE cxx_std_20)
target_compile_options(chronontemplate_emit_example_svg_recreation_plans PRIVATE -Wall -Wextra)

add_executable(chronontemplate_emit_svg_grain_perlin_showcase
        tools/showcases/emit_svg_grain_perlin_showcase.cpp)
target_link_libraries(chronontemplate_emit_svg_grain_perlin_showcase PRIVATE chronontemplate)
if(TARGET chrononmotion_chronon3d_adapter)
    target_link_libraries(chronontemplate_emit_svg_grain_perlin_showcase PRIVATE chrononmotion_chronon3d_adapter)
else()
    set(CHRONONTEMPLATE_RENDER_PLAN_EMISSION_DIR
        "${CHRONONTEMPLATE_CHRONONMOTION_DIR}/src/chrononmotion/motion")
    target_sources(chronontemplate_emit_svg_grain_perlin_showcase PRIVATE
        "${CHRONONTEMPLATE_RENDER_PLAN_EMISSION_DIR}/RenderPlanEmission.cpp"
        "${CHRONONTEMPLATE_RENDER_PLAN_EMISSION_DIR}/RenderPlanEmissionCommon.cpp"
        "${CHRONONTEMPLATE_RENDER_PLAN_EMISSION_DIR}/RenderPlanEmissionValidation.cpp")
    target_include_directories(chronontemplate_emit_svg_grain_perlin_showcase PRIVATE
        "${CHRONONTEMPLATE_CHRONONMOTION_DIR}/include"
        "${CHRONONTEMPLATE_CHRONON3D_DIR}/include"
        "${CHRONONTEMPLATE_NLOHMANN_JSON_DIR}")
endif()
target_compile_options(chronontemplate_emit_svg_grain_perlin_showcase PRIVATE -Wall -Wextra)

add_executable(chronontemplate_emit_truett_cathy_legacy_v1
        tools/entities_with_text/emit_truett_cathy_legacy_v1.cpp)
target_link_libraries(chronontemplate_emit_truett_cathy_legacy_v1 PRIVATE chronontemplate)
if(TARGET chrononmotion_chronon3d_adapter)
    target_link_libraries(chronontemplate_emit_truett_cathy_legacy_v1 PRIVATE chrononmotion_chronon3d_adapter)
else()
    set(CHRONONTEMPLATE_RENDER_PLAN_EMISSION_DIR
        "${CHRONONTEMPLATE_CHRONONMOTION_DIR}/src/chrononmotion/motion")
    target_sources(chronontemplate_emit_truett_cathy_legacy_v1 PRIVATE
        "${CHRONONTEMPLATE_RENDER_PLAN_EMISSION_DIR}/RenderPlanEmission.cpp"
        "${CHRONONTEMPLATE_RENDER_PLAN_EMISSION_DIR}/RenderPlanEmissionCommon.cpp"
        "${CHRONONTEMPLATE_RENDER_PLAN_EMISSION_DIR}/RenderPlanEmissionValidation.cpp")
    target_include_directories(chronontemplate_emit_truett_cathy_legacy_v1 PRIVATE
        "${CHRONONTEMPLATE_CHRONONMOTION_DIR}/include"
        "${CHRONONTEMPLATE_CHRONON3D_DIR}/include"
        "${CHRONONTEMPLATE_NLOHMANN_JSON_DIR}")
endif()
target_compile_options(chronontemplate_emit_truett_cathy_legacy_v1 PRIVATE -Wall -Wextra)

add_executable(chronontemplate_emit_usa_atmospheric_backlight_v1
        tools/map/emit_usa_atmospheric_backlight_v1.cpp)
target_link_libraries(chronontemplate_emit_usa_atmospheric_backlight_v1 PRIVATE chronontemplate)
if(TARGET chrononmotion_chronon3d_adapter)
    target_link_libraries(chronontemplate_emit_usa_atmospheric_backlight_v1 PRIVATE chrononmotion_chronon3d_adapter)
else()
    target_sources(chronontemplate_emit_usa_atmospheric_backlight_v1 PRIVATE
        "${CHRONONTEMPLATE_RENDER_PLAN_EMISSION_DIR}/RenderPlanEmission.cpp"
        "${CHRONONTEMPLATE_RENDER_PLAN_EMISSION_DIR}/RenderPlanEmissionCommon.cpp"
        "${CHRONONTEMPLATE_RENDER_PLAN_EMISSION_DIR}/RenderPlanEmissionValidation.cpp")
    target_include_directories(chronontemplate_emit_usa_atmospheric_backlight_v1 PRIVATE
        "${CHRONONTEMPLATE_CHRONONMOTION_DIR}/include"
        "${CHRONONTEMPLATE_CHRONON3D_DIR}/include"
        "${CHRONONTEMPLATE_NLOHMANN_JSON_DIR}")
endif()
target_compile_options(chronontemplate_emit_usa_atmospheric_backlight_v1 PRIVATE -Wall -Wextra)

add_executable(chronontemplate_emit_bullet_list_demo
        tools/bullet_list/emit_bullet_list_demo.cpp)
target_link_libraries(chronontemplate_emit_bullet_list_demo PRIVATE chronontemplate)
if(TARGET chrononmotion_chronon3d_adapter)
    target_link_libraries(chronontemplate_emit_bullet_list_demo PRIVATE chrononmotion_chronon3d_adapter)
else()
    set(CHRONONTEMPLATE_RENDER_PLAN_EMISSION_DIR
        "${CHRONONTEMPLATE_CHRONONMOTION_DIR}/src/chrononmotion/motion")
    target_sources(chronontemplate_emit_bullet_list_demo PRIVATE
        "${CHRONONTEMPLATE_RENDER_PLAN_EMISSION_DIR}/RenderPlanEmission.cpp"
        "${CHRONONTEMPLATE_RENDER_PLAN_EMISSION_DIR}/RenderPlanEmissionCommon.cpp"
        "${CHRONONTEMPLATE_RENDER_PLAN_EMISSION_DIR}/RenderPlanEmissionValidation.cpp")
    target_include_directories(chronontemplate_emit_bullet_list_demo PRIVATE
        "${CHRONONTEMPLATE_CHRONONMOTION_DIR}/include"
        "${CHRONONTEMPLATE_CHRONON3D_DIR}/include"
        "${CHRONONTEMPLATE_NLOHMANN_JSON_DIR}")
endif()
target_compile_options(chronontemplate_emit_bullet_list_demo PRIVATE -Wall -Wextra)

add_executable(chronontemplate_emit_archival_timeline_reveal
        tools/documentary_effects/emit_archival_timeline_reveal.cpp)
target_link_libraries(chronontemplate_emit_archival_timeline_reveal PRIVATE chronontemplate)
if(TARGET chrononmotion_chronon3d_adapter)
    target_link_libraries(chronontemplate_emit_archival_timeline_reveal PRIVATE chrononmotion_chronon3d_adapter)
else()
    set(CHRONONTEMPLATE_RENDER_PLAN_EMISSION_DIR
        "${CHRONONTEMPLATE_CHRONONMOTION_DIR}/src/chrononmotion/motion")
    target_sources(chronontemplate_emit_archival_timeline_reveal PRIVATE
        "${CHRONONTEMPLATE_RENDER_PLAN_EMISSION_DIR}/RenderPlanEmission.cpp"
        "${CHRONONTEMPLATE_RENDER_PLAN_EMISSION_DIR}/RenderPlanEmissionCommon.cpp"
        "${CHRONONTEMPLATE_RENDER_PLAN_EMISSION_DIR}/RenderPlanEmissionValidation.cpp")
    target_include_directories(chronontemplate_emit_archival_timeline_reveal PRIVATE
        "${CHRONONTEMPLATE_CHRONONMOTION_DIR}/include"
        "${CHRONONTEMPLATE_CHRONON3D_DIR}/include"
        "${CHRONONTEMPLATE_NLOHMANN_JSON_DIR}")
endif()
target_compile_options(chronontemplate_emit_archival_timeline_reveal PRIVATE -Wall -Wextra)

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
        "${CHRONONTEMPLATE_CHRONON3D_DIR}/include"
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

add_executable(chronontemplate_emit_dataviz_sample
        tools/captions_dataviz/emit_dataviz_sample.cpp)
target_link_libraries(chronontemplate_emit_dataviz_sample PRIVATE chronontemplate)
if(TARGET chrononmotion_chronon3d_adapter)
    target_link_libraries(chronontemplate_emit_dataviz_sample
            PRIVATE chrononmotion_chronon3d_adapter)
else()
    set(CHRONONTEMPLATE_DATAVIZ_EMISSION_DIR
        "${CHRONONTEMPLATE_CHRONONMOTION_DIR}/src/chrononmotion/motion")
    target_sources(chronontemplate_emit_dataviz_sample PRIVATE
        "${CHRONONTEMPLATE_DATAVIZ_EMISSION_DIR}/RenderPlanEmission.cpp"
        "${CHRONONTEMPLATE_DATAVIZ_EMISSION_DIR}/RenderPlanEmissionCommon.cpp"
        "${CHRONONTEMPLATE_DATAVIZ_EMISSION_DIR}/RenderPlanEmissionValidation.cpp")
    target_include_directories(chronontemplate_emit_dataviz_sample PRIVATE
        "${CHRONONTEMPLATE_CHRONONMOTION_DIR}/include"
        "${CHRONONTEMPLATE_CHRONON3D_DIR}/include"
        "${CHRONONTEMPLATE_NLOHMANN_JSON_DIR}")
endif()

add_executable(chronontemplate_emit_chart_corpus
        tools/charts/emit_chart_corpus.cpp)
target_link_libraries(chronontemplate_emit_chart_corpus PRIVATE chronontemplate)
if(TARGET chrononmotion_chronon3d_adapter)
    target_link_libraries(chronontemplate_emit_chart_corpus
            PRIVATE chrononmotion_chronon3d_adapter)
else()
    set(CHRONONTEMPLATE_CHARTS_EMISSION_DIR
        "${CHRONONTEMPLATE_CHRONONMOTION_DIR}/src/chrononmotion/motion")
    target_sources(chronontemplate_emit_chart_corpus PRIVATE
        "${CHRONONTEMPLATE_CHARTS_EMISSION_DIR}/RenderPlanEmission.cpp"
        "${CHRONONTEMPLATE_CHARTS_EMISSION_DIR}/RenderPlanEmissionCommon.cpp"
        "${CHRONONTEMPLATE_CHARTS_EMISSION_DIR}/RenderPlanEmissionValidation.cpp")
    target_include_directories(chronontemplate_emit_chart_corpus PRIVATE
        "${CHRONONTEMPLATE_CHRONONMOTION_DIR}/include"
        "${CHRONONTEMPLATE_CHRONON3D_DIR}/include"
        "${CHRONONTEMPLATE_NLOHMANN_JSON_DIR}")
endif()

add_executable(chronontemplate_emit_graph_recreations
        tools/charts/emit_graph_recreations.cpp)
target_link_libraries(chronontemplate_emit_graph_recreations PRIVATE chronontemplate)
if(TARGET chrononmotion_chronon3d_adapter)
    target_link_libraries(chronontemplate_emit_graph_recreations
            PRIVATE chrononmotion_chronon3d_adapter)
else()
    set(CHRONONTEMPLATE_GRAPHS_EMISSION_DIR
        "${CHRONONTEMPLATE_CHRONONMOTION_DIR}/src/chrononmotion/motion")
    target_sources(chronontemplate_emit_graph_recreations PRIVATE
        "${CHRONONTEMPLATE_GRAPHS_EMISSION_DIR}/RenderPlanEmission.cpp"
        "${CHRONONTEMPLATE_GRAPHS_EMISSION_DIR}/RenderPlanEmissionCommon.cpp"
        "${CHRONONTEMPLATE_GRAPHS_EMISSION_DIR}/RenderPlanEmissionValidation.cpp")
    target_include_directories(chronontemplate_emit_graph_recreations PRIVATE
        "${CHRONONTEMPLATE_CHRONONMOTION_DIR}/include"
        "${CHRONONTEMPLATE_CHRONON3D_DIR}/include"
        "${CHRONONTEMPLATE_NLOHMANN_JSON_DIR}")
endif()

add_executable(chronontemplate_emit_effects_overlays tools/effects_overlays/emit_effects_overlays.cpp)
target_link_libraries(chronontemplate_emit_effects_overlays PRIVATE chronontemplate)
if(TARGET chrononmotion_chronon3d_adapter)
    target_link_libraries(chronontemplate_emit_effects_overlays PRIVATE chrononmotion_chronon3d_adapter)
else()
    set(CHRONONTEMPLATE_EFFECTS_EMISSION_DIR
        "${CHRONONTEMPLATE_CHRONONMOTION_DIR}/src/chrononmotion/motion")
    target_sources(chronontemplate_emit_effects_overlays PRIVATE
        "${CHRONONTEMPLATE_EFFECTS_EMISSION_DIR}/RenderPlanEmission.cpp"
        "${CHRONONTEMPLATE_EFFECTS_EMISSION_DIR}/RenderPlanEmissionCommon.cpp"
        "${CHRONONTEMPLATE_EFFECTS_EMISSION_DIR}/RenderPlanEmissionValidation.cpp")
    target_include_directories(chronontemplate_emit_effects_overlays PRIVATE
        "${CHRONONTEMPLATE_CHRONONMOTION_DIR}/include"
        "${CHRONONTEMPLATE_CHRONON3D_DIR}/include"
        "${CHRONONTEMPLATE_NLOHMANN_JSON_DIR}")
endif()

add_executable(chronontemplate_emit_date_groups tools/date_groups/emit_date_groups.cpp)
target_link_libraries(chronontemplate_emit_date_groups PRIVATE chronontemplate)
if(TARGET chrononmotion_chronon3d_adapter)
    target_link_libraries(chronontemplate_emit_date_groups PRIVATE chrononmotion_chronon3d_adapter)
else()
    set(CHRONONTEMPLATE_DATE_GROUPS_EMISSION_DIR
        "${CHRONONTEMPLATE_CHRONONMOTION_DIR}/src/chrononmotion/motion")
    target_sources(chronontemplate_emit_date_groups PRIVATE
        "${CHRONONTEMPLATE_DATE_GROUPS_EMISSION_DIR}/RenderPlanEmission.cpp"
        "${CHRONONTEMPLATE_DATE_GROUPS_EMISSION_DIR}/RenderPlanEmissionCommon.cpp"
        "${CHRONONTEMPLATE_DATE_GROUPS_EMISSION_DIR}/RenderPlanEmissionValidation.cpp")
    target_include_directories(chronontemplate_emit_date_groups PRIVATE
        "${CHRONONTEMPLATE_CHRONONMOTION_DIR}/include"
        "${CHRONONTEMPLATE_CHRONON3D_DIR}/include"
        "${CHRONONTEMPLATE_NLOHMANN_JSON_DIR}")
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
            CHRONONTEMPLATE_ENTITY_PRESENTATION_FILE="${CMAKE_CURRENT_SOURCE_DIR}/catalog/entity_presentation.v1.json"
            CHRONONTEMPLATE_ANIMATION_SECTIONS_FILE="${CMAKE_CURRENT_SOURCE_DIR}/catalog/animation_sections.v1.json")
    target_compile_options(chronontemplate_emit_catalog PRIVATE -Wall -Wextra)
    if(CHRONONTEMPLATE_WERROR)
        target_compile_options(chronontemplate_emit_catalog PRIVATE -Werror)
    endif()

    # The important-phrase plans: Typewriter, Highlight and Apple families
    # lowered to chronon.render-plan.v2 plans; the renderer draws the glow.
    add_executable(chronontemplate_emit_important_phrase_plans
            tools/important_phrases/emit_important_phrase_plans.cpp)
    target_link_libraries(chronontemplate_emit_important_phrase_plans PRIVATE chronontemplate)
    target_include_directories(chronontemplate_emit_important_phrase_plans PRIVATE
            "${CHRONONTEMPLATE_NLOHMANN_JSON_DIR}")
    target_compile_options(chronontemplate_emit_important_phrase_plans PRIVATE -Wall -Wextra)
    if(CHRONONTEMPLATE_WERROR)
        target_compile_options(chronontemplate_emit_important_phrase_plans PRIVATE -Werror)
    endif()

    # The short-phrase catalog: surviving recipes + the decor bumper, projected
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

add_executable(chronontemplate_emit_procedural_documentary_v2 tools/showcases/emit_procedural_documentary_v2.cpp)
target_link_libraries(chronontemplate_emit_procedural_documentary_v2 PRIVATE chronontemplate)

# Independent native C++ starter plans: Fast Intro and classic date timeline.
add_executable(chronontemplate_emit_fast_intro_and_date_timeline
        tools/fast_intro/emit_fast_intro_and_date_timeline.cpp)
target_link_libraries(chronontemplate_emit_fast_intro_and_date_timeline PRIVATE chronontemplate)
target_compile_options(chronontemplate_emit_fast_intro_and_date_timeline PRIVATE -Wall -Wextra)

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
        "${CHRONONTEMPLATE_CHRONON3D_DIR}/include"
        "${CHRONONTEMPLATE_NLOHMANN_JSON_DIR}")
endif()
target_compile_options(chronontemplate_background_canary_v1 PRIVATE -Wall -Wextra)

# Native render-plan preview for the investigation board pack.
add_executable(chronontemplate_investigation_board_preview tools/investigation_board/investigation_board_preview.cpp)
target_link_libraries(chronontemplate_investigation_board_preview PRIVATE chronontemplate)
if(TARGET chrononmotion_chronon3d_adapter)
    target_link_libraries(chronontemplate_investigation_board_preview PRIVATE chrononmotion_chronon3d_adapter)
else()
    set(CHRONONTEMPLATE_RENDER_PLAN_EMISSION_DIR
        "${CHRONONTEMPLATE_CHRONONMOTION_DIR}/src/chrononmotion/motion")
    target_sources(chronontemplate_investigation_board_preview PRIVATE
        "${CHRONONTEMPLATE_RENDER_PLAN_EMISSION_DIR}/RenderPlanEmission.cpp"
        "${CHRONONTEMPLATE_RENDER_PLAN_EMISSION_DIR}/RenderPlanEmissionCommon.cpp"
        "${CHRONONTEMPLATE_RENDER_PLAN_EMISSION_DIR}/RenderPlanEmissionValidation.cpp")
    target_include_directories(chronontemplate_investigation_board_preview PRIVATE
        "${CHRONONTEMPLATE_CHRONONMOTION_DIR}/include"
        "${CHRONONTEMPLATE_CHRONON3D_DIR}/include"
        "${CHRONONTEMPLATE_NLOHMANN_JSON_DIR}")
endif()
target_compile_options(chronontemplate_investigation_board_preview PRIVATE -Wall -Wextra)

# Styled multi-image boards (archive, sepia torn, polaroid fan) lowered to
# native render-plan V3 through the same path as the investigation preview.
add_executable(chronontemplate_emit_multi_image_styles tools/multiple_images/emit_multi_image_styles.cpp)
target_link_libraries(chronontemplate_emit_multi_image_styles PRIVATE chronontemplate)
if(TARGET chrononmotion_chronon3d_adapter)
    target_link_libraries(chronontemplate_emit_multi_image_styles PRIVATE chrononmotion_chronon3d_adapter)
else()
    set(CHRONONTEMPLATE_RENDER_PLAN_EMISSION_DIR
        "${CHRONONTEMPLATE_CHRONONMOTION_DIR}/src/chrononmotion/motion")
    target_sources(chronontemplate_emit_multi_image_styles PRIVATE
        "${CHRONONTEMPLATE_RENDER_PLAN_EMISSION_DIR}/RenderPlanEmission.cpp"
        "${CHRONONTEMPLATE_RENDER_PLAN_EMISSION_DIR}/RenderPlanEmissionCommon.cpp"
        "${CHRONONTEMPLATE_RENDER_PLAN_EMISSION_DIR}/RenderPlanEmissionValidation.cpp"
        "${CHRONONTEMPLATE_RENDER_PLAN_EMISSION_DIR}/RenderPlanEmissionValidationBounds.cpp")
    target_include_directories(chronontemplate_emit_multi_image_styles PRIVATE
        "${CHRONONTEMPLATE_CHRONONMOTION_DIR}/include"
        "${CHRONONTEMPLATE_CHRONON3D_DIR}/include"
        "${CHRONONTEMPLATE_NLOHMANN_JSON_DIR}")
endif()
target_compile_options(chronontemplate_emit_multi_image_styles PRIVATE -Wall -Wextra)

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
        "${CHRONONTEMPLATE_CHRONON3D_DIR}/include"
        "${CHRONONTEMPLATE_NLOHMANN_JSON_DIR}")
endif()

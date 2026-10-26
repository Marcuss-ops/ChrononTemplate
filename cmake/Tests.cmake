# ChrononTemplate tests (extracted from CMakeLists.txt; identical targets).
# Included at the end of CMakeLists.txt.
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
        add_test(NAME chronontemplate_entity_with_text_v2_contract
            COMMAND "${Python3_EXECUTABLE}"
                    "${CMAKE_CURRENT_SOURCE_DIR}/tools/entities_with_text/test_entity_with_text_v2.py")
        add_test(NAME chronontemplate_kinetic_type_editorial_contract
            COMMAND "${Python3_EXECUTABLE}"
                    "${CMAKE_CURRENT_SOURCE_DIR}/tools/important_phrases/test_kinetic_type_editorial_v1.py")
        add_test(NAME chronontemplate_social_motion_pack_contract
            COMMAND "${Python3_EXECUTABLE}"
                    "${CMAKE_CURRENT_SOURCE_DIR}/tools/important_phrases/test_social_motion_pack_v1.py")
        add_test(NAME chronontemplate_text_depth_focus_contract
            COMMAND "${Python3_EXECUTABLE}"
                    "${CMAKE_CURRENT_SOURCE_DIR}/tools/important_phrases/test_text_depth_focus_v1.py")
        add_test(NAME chronontemplate_native_phrase_enter_contract
            COMMAND "${Python3_EXECUTABLE}"
                    "${CMAKE_CURRENT_SOURCE_DIR}/tools/important_phrases/test_native_phrase_enter.py")
        add_test(NAME chronontemplate_saas_kinetic_typography_contract
            COMMAND "${Python3_EXECUTABLE}"
                    "${CMAKE_CURRENT_SOURCE_DIR}/tools/important_phrases/test_saas_kinetic_typography_v1.py")
        add_test(NAME chronontemplate_rgb_motion_v1_contract
            COMMAND "${Python3_EXECUTABLE}"
                    "${CMAKE_CURRENT_SOURCE_DIR}/tools/backgrounds/test_rgb_motion_v1.py")
        add_test(NAME chronontemplate_vintage_documentary_title_01_plan_contract
            COMMAND "${Python3_EXECUTABLE}"
                    "${CMAKE_CURRENT_SOURCE_DIR}/tools/backgrounds/test_vintage_documentary_title_01.py"
                    --catalog "${CMAKE_CURRENT_SOURCE_DIR}/catalog/vintage_documentary_title_01"
                    --assets-root "${CMAKE_CURRENT_SOURCE_DIR}/.."
                    --cli "${CMAKE_CURRENT_SOURCE_DIR}/../Chronon3d/build/chronon/linux-video-fast-dev/apps/chronon3d_cli/chronon3d_cli")
        add_test(NAME chronontemplate_map_motion_family_contract
            COMMAND "${Python3_EXECUTABLE}"
                    "${CMAKE_CURRENT_SOURCE_DIR}/tools/map/test_map_motion_family_v1.py")
        add_test(NAME chronontemplate_geo_places_contract
            COMMAND "${Python3_EXECUTABLE}"
                    "${CMAKE_CURRENT_SOURCE_DIR}/tools/map/test_geo_places.py")
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

    add_executable(chronontemplate_procedural_documentary_v2_test tests/procedural_documentary_v2.cpp)
    target_link_libraries(chronontemplate_procedural_documentary_v2_test PRIVATE chronontemplate)
    add_test(NAME chronontemplate_procedural_documentary_v2_test COMMAND chronontemplate_procedural_documentary_v2_test)

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

    add_executable(chronontemplate_bullet_list_pack_test tests/bullet_list_pack.cpp)
    target_link_libraries(chronontemplate_bullet_list_pack_test PRIVATE chronontemplate)
    target_include_directories(chronontemplate_bullet_list_pack_test PRIVATE ${CMAKE_CURRENT_SOURCE_DIR}/tests)
    add_test(NAME chronontemplate_bullet_list_pack_test COMMAND chronontemplate_bullet_list_pack_test)

    add_executable(chronontemplate_investigation_board_pack_test tests/investigation_board_pack.cpp)
    target_link_libraries(chronontemplate_investigation_board_pack_test PRIVATE chronontemplate)
    target_include_directories(chronontemplate_investigation_board_pack_test PRIVATE ${CMAKE_CURRENT_SOURCE_DIR}/tests)
    add_test(NAME chronontemplate_investigation_board_pack_test COMMAND chronontemplate_investigation_board_pack_test)

    add_executable(chronontemplate_image_animation_pack_test tests/image_animation_pack.cpp)
    target_link_libraries(chronontemplate_image_animation_pack_test PRIVATE chronontemplate)
    target_include_directories(chronontemplate_image_animation_pack_test PRIVATE ${CMAKE_CURRENT_SOURCE_DIR}/tests)
    add_test(NAME chronontemplate_image_animation_pack_test COMMAND chronontemplate_image_animation_pack_test)

    add_executable(chronontemplate_image_style_packs_test tests/image_style_packs.cpp)
    target_link_libraries(chronontemplate_image_style_packs_test PRIVATE chronontemplate)
    target_include_directories(chronontemplate_image_style_packs_test PRIVATE ${CMAKE_CURRENT_SOURCE_DIR}/tests)
    add_test(NAME chronontemplate_image_style_packs_test COMMAND chronontemplate_image_style_packs_test)

    add_executable(chronontemplate_elements_timeline_test tests/elements_timeline.cpp)
    target_link_libraries(chronontemplate_elements_timeline_test PRIVATE chronontemplate)
    target_include_directories(chronontemplate_elements_timeline_test PRIVATE ${CMAKE_CURRENT_SOURCE_DIR}/tests)
    add_test(NAME chronontemplate_elements_timeline_test COMMAND chronontemplate_elements_timeline_test)

    add_executable(chronontemplate_date_groups_pack_test tests/date_groups_pack.cpp)
    target_link_libraries(chronontemplate_date_groups_pack_test PRIVATE chronontemplate)
    target_include_directories(chronontemplate_date_groups_pack_test PRIVATE ${CMAKE_CURRENT_SOURCE_DIR}/tests)
    add_test(NAME chronontemplate_date_groups_pack_test COMMAND chronontemplate_date_groups_pack_test)

    add_executable(chronontemplate_elements_annotation_test tests/elements_annotation.cpp)
    target_link_libraries(chronontemplate_elements_annotation_test PRIVATE chronontemplate)
    target_include_directories(chronontemplate_elements_annotation_test PRIVATE ${CMAKE_CURRENT_SOURCE_DIR}/tests)
    add_test(NAME chronontemplate_elements_annotation_test COMMAND chronontemplate_elements_annotation_test)

    add_executable(chronontemplate_elements_web_test tests/elements_web.cpp)
    target_link_libraries(chronontemplate_elements_web_test PRIVATE chronontemplate)
    target_include_directories(chronontemplate_elements_web_test PRIVATE ${CMAKE_CURRENT_SOURCE_DIR}/tests)
    add_test(NAME chronontemplate_elements_web_test COMMAND chronontemplate_elements_web_test)

    # The native web-page family: theme inversion, blur on context text only,
    # the sharp important center phrase, and fail-closed spec defects.
    add_executable(chronontemplate_web_page_highlight_pack_test tests/web_page_highlight_pack.cpp)
    target_link_libraries(chronontemplate_web_page_highlight_pack_test PRIVATE chronontemplate)
    target_include_directories(chronontemplate_web_page_highlight_pack_test PRIVATE ${CMAKE_CURRENT_SOURCE_DIR}/tests)
    add_test(NAME chronontemplate_web_page_highlight_pack_test COMMAND chronontemplate_web_page_highlight_pack_test)

    # The headline highlighter looks: statement page, marker sweep and stepped
    # highlight, one pure plan per recipe with a mid-clip sweep.
    add_executable(chronontemplate_web_headline_highlight_pack_test tests/web_headline_highlight_pack.cpp)
    target_link_libraries(chronontemplate_web_headline_highlight_pack_test PRIVATE chronontemplate)
    target_include_directories(chronontemplate_web_headline_highlight_pack_test PRIVATE ${CMAKE_CURRENT_SOURCE_DIR}/tests)
    add_test(NAME chronontemplate_web_headline_highlight_pack_test COMMAND chronontemplate_web_headline_highlight_pack_test)

    add_executable(chronontemplate_web_text_layout_test tests/web_text_layout.cpp)
    target_link_libraries(chronontemplate_web_text_layout_test PRIVATE chronontemplate)
    add_test(NAME chronontemplate_web_text_layout_test COMMAND chronontemplate_web_text_layout_test)

    # Second generation: six plans build, fold rotation stays in radians
    # (V1 authored degrees and killed video exports), recipes differ.
    add_executable(chronontemplate_web_page_v2_pack_test tests/web_page_v2_pack.cpp)
    target_link_libraries(chronontemplate_web_page_v2_pack_test PRIVATE chronontemplate)
    target_include_directories(chronontemplate_web_page_v2_pack_test PRIVATE ${CMAKE_CURRENT_SOURCE_DIR}/tests)
    add_test(NAME chronontemplate_web_page_v2_pack_test COMMAND chronontemplate_web_page_v2_pack_test)

    add_executable(chronontemplate_elements_documentary_test tests/elements_documentary.cpp)
    target_link_libraries(chronontemplate_elements_documentary_test PRIVATE chronontemplate)
    target_include_directories(chronontemplate_elements_documentary_test PRIVATE ${CMAKE_CURRENT_SOURCE_DIR}/tests)
    add_test(NAME chronontemplate_elements_documentary_test COMMAND chronontemplate_elements_documentary_test)

    add_executable(chronontemplate_elements_diagram_test tests/elements_diagram.cpp)
    target_link_libraries(chronontemplate_elements_diagram_test PRIVATE chronontemplate)
    target_include_directories(chronontemplate_elements_diagram_test PRIVATE ${CMAKE_CURRENT_SOURCE_DIR}/tests)
    add_test(NAME chronontemplate_elements_diagram_test COMMAND chronontemplate_elements_diagram_test)

    add_executable(chronontemplate_vintage_documentary_pack_test tests/vintage_documentary_pack.cpp)
    target_link_libraries(chronontemplate_vintage_documentary_pack_test PRIVATE chronontemplate)
    target_include_directories(chronontemplate_vintage_documentary_pack_test PRIVATE ${CMAKE_CURRENT_SOURCE_DIR}/tests)
    add_test(NAME chronontemplate_vintage_documentary_pack_test COMMAND chronontemplate_vintage_documentary_pack_test)

    add_executable(chronontemplate_vintage_documentary_title_01_pack_test tests/vintage_documentary_title_01_pack.cpp)
    target_link_libraries(chronontemplate_vintage_documentary_title_01_pack_test PRIVATE chronontemplate)
    target_include_directories(chronontemplate_vintage_documentary_title_01_pack_test PRIVATE ${CMAKE_CURRENT_SOURCE_DIR}/tests)
    add_test(NAME chronontemplate_vintage_documentary_title_01_pack_test COMMAND chronontemplate_vintage_documentary_title_01_pack_test)

    add_executable(chronontemplate_archival_lens_look_test tests/archival_lens_look.cpp)
    target_link_libraries(chronontemplate_archival_lens_look_test PRIVATE chronontemplate)
    target_include_directories(chronontemplate_archival_lens_look_test PRIVATE ${CMAKE_CURRENT_SOURCE_DIR}/tests)
    add_test(NAME chronontemplate_archival_lens_look_test COMMAND chronontemplate_archival_lens_look_test)

    add_executable(chronontemplate_archival_card_pack_test tests/archival_card_pack.cpp)
    target_link_libraries(chronontemplate_archival_card_pack_test PRIVATE chronontemplate)
    target_include_directories(chronontemplate_archival_card_pack_test PRIVATE ${CMAKE_CURRENT_SOURCE_DIR}/tests)
    add_test(NAME chronontemplate_archival_card_pack_test COMMAND chronontemplate_archival_card_pack_test)

    add_executable(chronontemplate_doc_effects_camera_test tests/doc_effects_camera.cpp)
    target_link_libraries(chronontemplate_doc_effects_camera_test PRIVATE chronontemplate)
    target_include_directories(chronontemplate_doc_effects_camera_test PRIVATE ${CMAKE_CURRENT_SOURCE_DIR}/tests)
    add_test(NAME chronontemplate_doc_effects_camera_test COMMAND chronontemplate_doc_effects_camera_test)

    add_executable(chronontemplate_doc_effects_graphic_test tests/doc_effects_graphic.cpp)
    target_link_libraries(chronontemplate_doc_effects_graphic_test PRIVATE chronontemplate)
    target_include_directories(chronontemplate_doc_effects_graphic_test PRIVATE ${CMAKE_CURRENT_SOURCE_DIR}/tests)
    add_test(NAME chronontemplate_doc_effects_graphic_test COMMAND chronontemplate_doc_effects_graphic_test)

    add_executable(chronontemplate_archival_timeline_pack_test tests/archival_timeline_pack.cpp)
    target_link_libraries(chronontemplate_archival_timeline_pack_test PRIVATE chronontemplate)
    target_include_directories(chronontemplate_archival_timeline_pack_test PRIVATE ${CMAKE_CURRENT_SOURCE_DIR}/tests)
    add_test(NAME chronontemplate_archival_timeline_pack_test COMMAND chronontemplate_archival_timeline_pack_test)

    add_executable(chronontemplate_effects_pack_test tests/effects_pack.cpp)
    target_link_libraries(chronontemplate_effects_pack_test PRIVATE chronontemplate)
    target_include_directories(chronontemplate_effects_pack_test PRIVATE ${CMAKE_CURRENT_SOURCE_DIR}/tests)
    add_test(NAME chronontemplate_effects_pack_test COMMAND chronontemplate_effects_pack_test)

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

    # The camera motion pack: fifty narrative presets as data, one resolver,
    # single-shot PoseTracks plus two-shot ShotTimelines, the spec selection
    # table and the 0.5 / 1.0 / 1.5 intensity ladder, pinned for all presets.
    add_executable(chronontemplate_camera_motion_pack_test tests/camera_motion_pack.cpp)
    target_link_libraries(chronontemplate_camera_motion_pack_test PRIVATE chronontemplate)
    target_include_directories(chronontemplate_camera_motion_pack_test PRIVATE ${CMAKE_CURRENT_SOURCE_DIR}/tests)
    add_test(NAME chronontemplate_camera_motion_pack_test COMMAND chronontemplate_camera_motion_pack_test)

    # The camera motion catalog emitter: fifty spec rows projected to JSON.
    add_executable(chronontemplate_emit_camera_motion_catalog
            tools/camera_roll/emit_camera_motion_catalog.cpp)
    target_link_libraries(chronontemplate_emit_camera_motion_catalog PRIVATE chronontemplate)
    target_include_directories(chronontemplate_emit_camera_motion_catalog PRIVATE
            ${CHRONONTEMPLATE_NLOHMANN_JSON_DIR})
    target_compile_options(chronontemplate_emit_camera_motion_catalog PRIVATE -Wall -Wextra)

    # Certification plans for the spec's priority thirteen: rig-sampled
    # camera channels over the shared canary, ready for chronon3d_cli.
    add_executable(chronontemplate_emit_camera_motion_certification
            tools/camera_roll/emit_camera_motion_certification.cpp)
    target_link_libraries(chronontemplate_emit_camera_motion_certification PRIVATE chronontemplate)
    target_include_directories(chronontemplate_emit_camera_motion_certification PRIVATE
            ${CHRONONTEMPLATE_NLOHMANN_JSON_DIR})
    target_compile_options(chronontemplate_emit_camera_motion_certification PRIVATE -Wall -Wextra)

    # The UI + smooth-camera choreography: one Null controller carries the
    # panel, the camera push/drift/settle rides the rig, framing fits the
    # measured bounds, and the 90-frame canary lowers to RenderPlan V3.
    add_executable(chronontemplate_ui_camera_choreography_test tests/ui_camera_choreography.cpp)
    target_link_libraries(chronontemplate_ui_camera_choreography_test PRIVATE chronontemplate)
    target_include_directories(chronontemplate_ui_camera_choreography_test PRIVATE ${CMAKE_CURRENT_SOURCE_DIR}/tests)
    add_test(NAME chronontemplate_ui_camera_choreography_test COMMAND chronontemplate_ui_camera_choreography_test)

    if(Python3_Interpreter_FOUND)
        add_test(NAME chronontemplate_scene_sequence_json_contract
            COMMAND "${Python3_EXECUTABLE}"
                    "${CMAKE_CURRENT_SOURCE_DIR}/tools/camera_roll/test_scene_sequence_json.py"
                    --tool "$<TARGET_FILE:chronontemplate_sequence_from_json>")
    endif()

    # The short-phrase catalog contract: the emitter is fail-closed and the
    # committed catalog must be exactly what the C++ pack emits today.
    if(Python3_Interpreter_FOUND AND TARGET chronontemplate_emit_camera_motion_catalog)
        add_test(NAME chronontemplate_camera_motion_catalog_contract
            COMMAND "${Python3_EXECUTABLE}"
                    "${CMAKE_CURRENT_SOURCE_DIR}/tools/camera_roll/test_camera_motion_catalog.py"
                    --tool "$<TARGET_FILE:chronontemplate_emit_camera_motion_catalog>"
                    --catalog "${CMAKE_CURRENT_SOURCE_DIR}/catalog/camera_motion_pack.v1.json")
    endif()
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

    add_executable(chronontemplate_apple_phrase_pack_test tests/apple_phrase_pack.cpp)
    target_link_libraries(chronontemplate_apple_phrase_pack_test PRIVATE chronontemplate)
    target_include_directories(chronontemplate_apple_phrase_pack_test PRIVATE ${CMAKE_CURRENT_SOURCE_DIR}/tests)
    add_test(NAME chronontemplate_apple_phrase_pack_test COMMAND chronontemplate_apple_phrase_pack_test)

    add_executable(chronontemplate_highlight_phrase_pack_test tests/highlight_phrase_pack.cpp)
    target_link_libraries(chronontemplate_highlight_phrase_pack_test PRIVATE chronontemplate)
    target_include_directories(chronontemplate_highlight_phrase_pack_test PRIVATE ${CMAKE_CURRENT_SOURCE_DIR}/tests)
    add_test(NAME chronontemplate_highlight_phrase_pack_test COMMAND chronontemplate_highlight_phrase_pack_test)

    # The first pack: the subscribe card, its controller-driven entrance/exit and
    # the click pulse that only holds because a preset appends keys.
    add_executable(chronontemplate_youtube_subscribe_test tests/youtube_subscribe.cpp)
    target_link_libraries(chronontemplate_youtube_subscribe_test PRIVATE chronontemplate)
    target_include_directories(chronontemplate_youtube_subscribe_test PRIVATE ${CMAKE_CURRENT_SOURCE_DIR}/tests)
    add_test(NAME chronontemplate_youtube_subscribe_test COMMAND chronontemplate_youtube_subscribe_test)

    add_executable(chronontemplate_chronon_motion_contract_test tests/chronon_motion_contract.cpp)
    target_link_libraries(chronontemplate_chronon_motion_contract_test PRIVATE chronontemplate_live_adapter)
    target_include_directories(chronontemplate_chronon_motion_contract_test PRIVATE ${CMAKE_CURRENT_SOURCE_DIR}/tests)
    add_test(NAME chronontemplate_chronon_motion_contract_test COMMAND chronontemplate_chronon_motion_contract_test)

    # The didone acceptance suite was removed: its font gate pinned the
    # Bodoni72-BookItalic.ttf asset that no longer ships in any renderer
    # checkout (the didone family was retired with the other phrase families).
    # The pack sources stay in the library for the catalog data they publish.
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
                chronontemplate_live_adapter "${CHRONONTEMPLATE_CHRONON3D_LIBRARY}")
        target_include_directories(chronontemplate_chronon_render_adapter_test PRIVATE ${CMAKE_CURRENT_SOURCE_DIR}/tests)
        add_test(NAME chronontemplate_chronon_render_adapter_test COMMAND chronontemplate_chronon_render_adapter_test)
    endif()
endif()


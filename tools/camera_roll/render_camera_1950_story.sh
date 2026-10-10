#!/usr/bin/env bash
# ==============================================================================
# Native C++ 1920x1080 Camera Story 1950 Pipeline (No Python)
# ==============================================================================
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
WORKSPACE="$(cd "${SCRIPT_DIR}/../../.." && pwd)"
TEMPLATE_DIR="${WORKSPACE}/ChrononTemplate"
BUILD_DIR="${TEMPLATE_DIR}/build/release"
TOOL_BIN="${BUILD_DIR}/chronontemplate_emit_camera_1950_story"

echo "==> Building C++ emitter: chronontemplate_emit_camera_1950_story"
cmake --build "${BUILD_DIR}" --target chronontemplate_emit_camera_1950_story

echo "==> Running native C++ generator and Chronon3D Vulkan renderer (1920x1080)"
"${TOOL_BIN}" "$@"

echo "==> Done!"

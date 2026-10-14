#include "chronontemplate/elements/AnnotationElements.hpp"

#include <algorithm>

namespace chronontemplate::elements {

    LayerHandle& addGlowBrushTrace(TemplateScene& scene, const GlowBrushTraceSpec& spec) {
        require(spec.length > 0.f, "addGlowBrushTrace: a positive length is required");
        require(spec.width > 0.f, "addGlowBrushTrace: a positive width is required");
        require(!spec.color.empty(), "addGlowBrushTrace: a color is required");
        LayerHandle& root = scene.group(spec.name);
        root.alive(0, 150);
        // Halo plate first (renderer blooms it), sharp core above, hot head.
        // Radii are clamped to half the smallest side per the shape contract.
        const float haloR = std::min(spec.width * 2.f, spec.length * 0.5f);
        LayerHandle& halo = addBar(scene, root.id(), spec.name + "_halo",
                                   spec.length, spec.width * 4.f, 0.f, 0.f,
                                   spec.color, haloR);
        halo.opacity(0.35f);
        applyElementMotion(halo, spec.motion, scene.fps());
        const float coreR = std::min(spec.width * 0.5f, spec.length * 0.5f);
        LayerHandle& core = addBar(scene, root.id(), spec.name + "_core",
                                   spec.length, spec.width, 0.f, 0.f,
                                   "#FFFFFF", coreR);
        applyElementMotion(core, spec.motion, scene.fps(), 1);
        LayerHandle& head = scene.shape(ShapeSpec{
                .size = chrononmotion::Vector2(spec.width * 3.f, spec.width * 3.f),
                .fillColor = "#FFFFFF",
                .name = spec.name + "_head",
                .cornerRadius = spec.width * 1.5f,
                .geometry = ShapeGeometry::Ellipse});
        head.parent(root.id());
        head.position(spec.length * 0.5f, 0.f);
        head.alive(0, 150);
        applyElementMotion(head, spec.motion, scene.fps(), 2);
        if (spec.trail) {
            const float trailR = std::min(spec.width, spec.length * 0.35f * 0.5f);
            LayerHandle& trail = addBar(scene, root.id(), spec.name + "_trail",
                                        spec.length * 0.35f, spec.width * 2.f,
                                        -spec.length * 0.28f, 0.f, spec.color,
                                        trailR);
            trail.opacity(0.5f);
            applyElementMotion(trail, spec.motion, scene.fps(), 1);
        }
        return root;
    }

    LayerHandle& addBrushUnderline(TemplateScene& scene, const BrushUnderlineSpec& spec) {
        require(!spec.text.empty(), "addBrushUnderline: a word is required");
        require(spec.fontSize > 0.f, "addBrushUnderline: a positive font size is required");
        require(spec.strokeWidth > 0.f, "addBrushUnderline: a positive stroke width is required");
        const ElementPalette pal = paletteFor(spec.style);
        LayerHandle& root = scene.group(spec.name);
        root.alive(0, 150);
        LayerHandle& word = addText(scene, root.id(), spec.name + "_word",
                                    spec.text, spec.fontSize, pal.ink, 0.f, -30.f);
        applyElementMotion(word, spec.motion, scene.fps());
        // Organic stroke: two overlapping rounded bars with a slight skew.
        const float width = static_cast<float>(spec.text.size()) * spec.fontSize * 0.52f;
        const float strokeR = std::min(spec.strokeWidth * 0.5f, width * 0.5f);
        LayerHandle& stroke = addBar(scene, root.id(), spec.name + "_stroke",
                                     width, spec.strokeWidth, -8.f, spec.fontSize * 0.42f,
                                     spec.color, strokeR);
        applyElementMotion(stroke, ElementMotion{.preset = ElementMotionPreset::DrawOn,
                                                 .startFrame = spec.motion.startFrame,
                                                 .endFrame = spec.motion.endFrame,
                                                 .staggerStep = spec.motion.staggerStep},
                           scene.fps());
        const float raggedR = std::min({spec.strokeWidth * 0.3f, width * 0.55f * 0.5f,
                                         spec.strokeWidth * 0.55f * 0.5f});
        LayerHandle& ragged = addBar(scene, root.id(), spec.name + "_ragged",
                                     width * 0.55f, spec.strokeWidth * 0.55f,
                                     width * 0.16f, spec.fontSize * 0.42f + 3.f,
                                     spec.color, raggedR);
        applyElementMotion(ragged, spec.motion, scene.fps(), 1);
        return root;
    }

    LayerHandle& addTextMarkerHighlight(TemplateScene& scene,
                                        const TextMarkerHighlightSpec& spec) {
        require(!spec.text.empty(), "addTextMarkerHighlight: a phrase is required");
        require(spec.fontSize > 0.f, "addTextMarkerHighlight: a positive font size is required");
        LayerHandle& root = scene.group(spec.name);
        root.alive(0, 150);
        // The stripe lives in the native text background so its geometry
        // stays synchronized with the shaped phrase.
        LayerHandle& phrase = scene.text(TextSpec{
                .text = spec.text, .fontSize = spec.fontSize, .color = spec.textColor,
                .name = spec.name + "_phrase",
                .background = TextBackgroundStyle{.color = spec.markerColor, .opacity = 0.92f,
                                                  .radius = 8.f,
                                                  .padding = chrononmotion::Vector2(18.f, 10.f)}});
        phrase.parent(root.id());
        phrase.position(0.f, 0.f);
        phrase.alive(0, 150);
        applyElementMotion(phrase, spec.motion, scene.fps());
        return root;
    }

    LayerHandle& addRoughCircleAnnotation(TemplateScene& scene,
                                          const RoughCircleAnnotationSpec& spec) {
        require(spec.diameter > 0.f, "addRoughCircleAnnotation: a positive diameter is required");
        require(spec.strokeWidth > 0.f, "addRoughCircleAnnotation: a positive stroke is required");
        LayerHandle& root = scene.group(spec.name);
        root.alive(0, 150);
        // Hand-drawn feel: two slightly rotated ellipse strokes, open look
        // via a small gap bar in paper tone over the top.
        LayerHandle& ring = scene.shape(ShapeSpec{
                .size = chrononmotion::Vector2(spec.diameter, spec.diameter * 0.94f),
                .fillColor = spec.color,
                .name = spec.name + "_ring",
                .geometry = ShapeGeometry::Ellipse,
                .strokeColor = spec.color,
                .strokeWidth = spec.strokeWidth});
        ring.parent(root.id());
        ring.position(0.f, 0.f);
        ring.alive(0, 150);
        applyElementMotion(ring, spec.motion, scene.fps());
        LayerHandle& wobble = scene.shape(ShapeSpec{
                .size = chrononmotion::Vector2(spec.diameter * 1.04f, spec.diameter * 0.98f),
                .fillColor = spec.color,
                .name = spec.name + "_wobble",
                .geometry = ShapeGeometry::Ellipse,
                .strokeColor = spec.color,
                .strokeWidth = spec.strokeWidth * 0.6f});
        wobble.parent(root.id());
        wobble.position(4.f, -3.f);
        wobble.alive(0, 150);
        applyElementMotion(wobble, spec.motion, scene.fps(), 1);
        if (!spec.label.empty()) {
            LayerHandle& label = addText(scene, root.id(), spec.name + "_label",
                                         spec.label, 32.f, spec.color, 0.f,
                                         spec.diameter * 0.5f + 44.f);
            applyElementMotion(label, spec.motion, scene.fps(), 2);
        }
        return root;
    }

    LayerHandle& addCurvedArrowPointer(TemplateScene& scene, const CurvedArrowPointerSpec& spec) {
        require(spec.length > 0.f, "addCurvedArrowPointer: a positive length is required");
        require(spec.thickness > 0.f, "addCurvedArrowPointer: a positive thickness is required");
        LayerHandle& root = scene.group(spec.name);
        root.alive(0, 150);
        LayerHandle& shaft = addBar(scene, root.id(), spec.name + "_shaft",
                                    spec.length, spec.thickness, 0.f, 0.f,
                                    spec.color, spec.thickness * 0.5f);
        applyElementMotion(shaft, ElementMotion{.preset = ElementMotionPreset::DrawOn,
                                                .startFrame = spec.motion.startFrame,
                                                .endFrame = spec.motion.endFrame,
                                                .staggerStep = spec.motion.staggerStep},
                           scene.fps());
        // Angled head: two short bars forming the arrow tip at the target.
        const float tipX = spec.length * 0.5f;
        LayerHandle& headA = addBar(scene, root.id(), spec.name + "_head_a",
                                    spec.thickness * 3.2f, spec.thickness,
                                    tipX - spec.thickness * 1.1f, -spec.thickness * 1.3f,
                                    spec.color, spec.thickness * 0.5f);
        applyElementMotion(headA, spec.motion, scene.fps(), 1);
        LayerHandle& headB = addBar(scene, root.id(), spec.name + "_head_b",
                                    spec.thickness * 3.2f, spec.thickness,
                                    tipX - spec.thickness * 1.1f, spec.thickness * 1.3f,
                                    spec.color, spec.thickness * 0.5f);
        applyElementMotion(headB, spec.motion, scene.fps(), 1);
        if (!spec.label.empty()) {
            LayerHandle& label = addText(scene, root.id(), spec.name + "_label",
                                         spec.label, 32.f, spec.color,
                                         -spec.length * 0.5f, -44.f);
            applyElementMotion(label, spec.motion, scene.fps(), 2);
        }
        return root;
    }

    LayerHandle& addFocusBracket(TemplateScene& scene, const FocusBracketSpec& spec) {
        require(spec.width > 0.f && spec.height > 0.f,
                "addFocusBracket: positive dimensions are required");
        require(spec.corner > 0.f, "addFocusBracket: a positive corner length is required");
        const float hx = spec.width * 0.5f;
        const float hy = spec.height * 0.5f;
        const float c = spec.corner;
        const float t = spec.strokeWidth;
        LayerHandle& root = scene.group(spec.name);
        root.alive(0, 150);
        struct Corner { const char* tag; float x; float y; int sx; int sy; };
        const Corner corners[] = {
            {"tl", -hx, -hy, 1, 1}, {"tr", hx, -hy, -1, 1},
            {"bl", -hx, hy, 1, -1}, {"br", hx, hy, -1, -1},
        };
        for (int i = 0; i < 4; ++i) {
            const Corner& corner = corners[i];
            LayerHandle& barH = addBar(scene, root.id(),
                                       spec.name + "_corner_" + corner.tag + "_h",
                                       c, t, corner.x + corner.sx * c * 0.5f, corner.y,
                                       spec.color, t * 0.5f);
            applyElementMotion(barH, spec.motion, scene.fps(), i);
            LayerHandle& barV = addBar(scene, root.id(),
                                       spec.name + "_corner_" + corner.tag + "_v",
                                       t, c, corner.x, corner.y + corner.sy * c * 0.5f,
                                       spec.color, t * 0.5f);
            applyElementMotion(barV, spec.motion, scene.fps(), i);
        }
        if (!spec.label.empty()) {
            LayerHandle& label = addText(scene, root.id(), spec.name + "_label",
                                         spec.label, 30.f, spec.color, 0.f, -hy - 44.f);
            applyElementMotion(label, spec.motion, scene.fps(), 4);
        }
        return root;
    }

    LayerHandle& addGlowLine(TemplateScene& scene, const GlowLineSpec& spec) {
        require(spec.length > 0.f, "addGlowLine: a positive length is required");
        require(spec.coreWidth > 0.f, "addGlowLine: a positive core width is required");
        require(!spec.coreColor.empty(), "addGlowLine: a core color is required");
        require(!spec.haloColor.empty(), "addGlowLine: a halo color is required");

        LayerHandle& root = scene.group(spec.name);
        root.alive(0, 150);

        // 1. Wide diffuse halo layer (ambient dispersion / soft aura)
        const float wideR = std::min(spec.wideHaloWidth * 0.5f, spec.length * 0.5f);
        LayerHandle& wideHalo = addBar(scene, root.id(), spec.name + "_wide_halo",
                                       spec.length, spec.wideHaloWidth, 0.f, 0.f,
                                       spec.wideHaloColor, wideR);
        wideHalo.opacity(0.24f);
        applyElementMotion(wideHalo, spec.motion, scene.fps(), 0);

        // 2. Tight luminous halo layer (vibrant color concentration)
        const float haloR = std::min(spec.haloWidth * 0.5f, spec.length * 0.5f);
        LayerHandle& halo = addBar(scene, root.id(), spec.name + "_halo",
                                   spec.length, spec.haloWidth, 0.f, 0.f,
                                   spec.haloColor, haloR);
        halo.opacity(0.68f);
        applyElementMotion(halo, spec.motion, scene.fps(), 1);

        // 3. Ultra-sharp white core layer (structural razor-sharp center)
        const float coreR = std::min(spec.coreWidth * 0.5f, spec.length * 0.5f);
        LayerHandle& core = addBar(scene, root.id(), spec.name + "_core",
                                   spec.length, spec.coreWidth, 0.f, 0.f,
                                   spec.coreColor, coreR);
        core.opacity(1.0f);
        applyElementMotion(core, spec.motion, scene.fps(), 2);

        // 4. Leading light head (energy flare at tip)
        if (spec.headEnabled) {
            // Hot halo on head
            LayerHandle& headHalo = scene.shape(ShapeSpec{
                    .size = chrononmotion::Vector2(spec.headRadius * 4.f, spec.headRadius * 4.f),
                    .fillColor = spec.haloColor,
                    .name = spec.name + "_head_halo",
                    .cornerRadius = spec.headRadius * 2.f,
                    .geometry = ShapeGeometry::Ellipse});
            headHalo.parent(root.id());
            headHalo.position(spec.length * 0.5f, 0.f);
            headHalo.opacity(0.75f);
            headHalo.alive(0, 150);
            applyElementMotion(headHalo, spec.motion, scene.fps(), 3);

            // Diamond white core head
            LayerHandle& headCore = scene.shape(ShapeSpec{
                    .size = chrononmotion::Vector2(spec.headRadius * 2.f, spec.headRadius * 2.f),
                    .fillColor = spec.coreColor,
                    .name = spec.name + "_head_core",
                    .cornerRadius = spec.headRadius,
                    .geometry = ShapeGeometry::Ellipse});
            headCore.parent(root.id());
            headCore.position(spec.length * 0.5f, 0.f);
            headCore.opacity(1.0f);
            headCore.alive(0, 150);
            applyElementMotion(headCore, spec.motion, scene.fps(), 3);
        }

        return root;
    }

}// namespace chronontemplate::elements


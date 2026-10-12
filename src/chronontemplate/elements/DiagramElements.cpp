#include "chronontemplate/elements/DiagramElements.hpp"

namespace chronontemplate::elements {

    LayerHandle& addGeoLocationMarker(TemplateScene& scene, const GeoLocationMarkerSpec& spec) {
        require(spec.radius > 0.f, "addGeoLocationMarker: a positive radius is required");
        LayerHandle& root = scene.group(spec.name);
        root.alive(0, 150);
        LayerHandle& ring = scene.shape(ShapeSpec{
                .size = chrononmotion::Vector2(spec.radius * 2.f, spec.radius * 2.f),
                .fillColor = spec.color, .name = spec.name + "_ring",
                .geometry = ShapeGeometry::Ellipse,
                .strokeColor = spec.color, .strokeWidth = 6.f});
        ring.parent(root.id());
        ring.position(0.f, 0.f);
        ring.alive(0, 150);
        applyElementMotion(ring, spec.motion, scene.fps());
        LayerHandle& core = scene.shape(ShapeSpec{
                .size = chrononmotion::Vector2(20.f, 20.f), .fillColor = spec.color,
                .name = spec.name + "_core", .cornerRadius = 10.f,
                .geometry = ShapeGeometry::Ellipse});
        core.parent(root.id());
        core.position(0.f, 0.f);
        core.alive(0, 150);
        applyElementMotion(core, spec.motion, scene.fps(), 1);
        if (!spec.label.empty()) {
            LayerHandle& label = addText(scene, root.id(), spec.name + "_label",
                                         spec.label, 32.f, "#F2EFE6", 0.f,
                                         spec.radius + 44.f);
            applyElementMotion(label, spec.motion, scene.fps(), 2);
        }
        return root;
    }

    LayerHandle& addRegionBoundaryHighlight(TemplateScene& scene,
                                            const RegionBoundaryHighlightSpec& spec) {
        require(spec.width > 0.f && spec.height > 0.f,
                "addRegionBoundaryHighlight: positive dimensions are required");
        LayerHandle& root = scene.group(spec.name);
        root.alive(0, 150);
        // Fill plate, hexagonal boundary stroke, glow-side bar, label.
        LayerHandle& fill = scene.shape(ShapeSpec{
                .size = chrononmotion::Vector2(spec.width, spec.height),
                .fillColor = spec.color, .name = spec.name + "_fill", .cornerRadius = 18.f});
        fill.parent(root.id());
        fill.position(0.f, 0.f);
        fill.alive(0, 150);
        fill.opacity(0.18f);
        applyElementMotion(fill, spec.motion, scene.fps());
        LayerHandle& boundary = scene.shape(ShapeSpec{
                .size = chrononmotion::Vector2(spec.width, spec.height),
                .fillColor = spec.color, .name = spec.name + "_boundary",
                .geometry = ShapeGeometry::Polygon,
                .strokeColor = spec.color, .strokeWidth = 5.f,
                .polygonPoints = 6});
        boundary.parent(root.id());
        boundary.position(0.f, 0.f);
        boundary.alive(0, 150);
        applyElementMotion(boundary, spec.motion, scene.fps(), 1);
        LayerHandle& glowSide = addBar(scene, root.id(), spec.name + "_glow_side",
                                       8.f, spec.height * 0.7f, -spec.width * 0.5f - 14.f, 0.f,
                                       spec.color, 4.f);
        applyElementMotion(glowSide, spec.motion, scene.fps(), 2);
        if (!spec.label.empty()) {
            LayerHandle& label = addText(scene, root.id(), spec.name + "_label",
                                         spec.label, 34.f, spec.color, 0.f,
                                         spec.height * 0.5f + 48.f);
            applyElementMotion(label, spec.motion, scene.fps(), 3);
        }
        return root;
    }

    LayerHandle& addRouteStrokeLegend(TemplateScene& scene, const RouteStrokeLegendSpec& spec) {
        require(!spec.routeName.empty(), "addRouteStrokeLegend: a route name is required");
        LayerHandle& root = scene.group(spec.name);
        root.alive(0, 150);
        LayerHandle& halo = addBar(scene, root.id(), spec.name + "_halo",
                                   300.f, 20.f, -80.f, 0.f, spec.color, 10.f);
        halo.opacity(0.35f);
        applyElementMotion(halo, spec.motion, scene.fps());
        LayerHandle& line = addBar(scene, root.id(), spec.name + "_line",
                                   300.f, 6.f, -80.f, 0.f, "#FFFFFF", 3.f);
        applyElementMotion(line, spec.motion, scene.fps(), 1);
        LayerHandle& head = addBar(scene, root.id(), spec.name + "_head",
                                   34.f, 6.f, 82.f, -9.f, spec.color, 3.f);
        applyElementMotion(head, spec.motion, scene.fps(), 2);
        LayerHandle& route = addText(scene, root.id(), spec.name + "_route",
                                     spec.routeName, 36.f, "#F2EFE6", -80.f, 60.f);
        applyElementMotion(route, spec.motion, scene.fps(), 2);
        LayerHandle& swatchA = addBar(scene, root.id(), spec.name + "_swatch_a",
                                      44.f, 16.f, -200.f, 120.f, spec.color, 8.f);
        applyElementMotion(swatchA, spec.motion, scene.fps(), 3);
        LayerHandle& swatchB = addBar(scene, root.id(), spec.name + "_swatch_b",
                                      44.f, 16.f, -140.f, 120.f, spec.altColor, 8.f);
        applyElementMotion(swatchB, spec.motion, scene.fps(), 4);
        return root;
    }

    LayerHandle& addRelationConnector(TemplateScene& scene, const RelationConnectorSpec& spec) {
        require(!spec.leftLabel.empty() && !spec.rightLabel.empty(),
                "addRelationConnector: both endpoint labels are required");
        require(!spec.relation.empty(), "addRelationConnector: a relation is required");
        require(spec.span > 0.f, "addRelationConnector: a positive span is required");
        const ElementPalette pal = paletteFor(spec.style);
        LayerHandle& root = scene.group(spec.name);
        root.alive(0, 150);
        const float hx = spec.span * 0.5f;
        for (int side = 0; side < 2; ++side) {
            const float x = side == 0 ? -hx : hx;
            const std::string tag = side == 0 ? "left" : "right";
            LayerHandle& dot = scene.shape(ShapeSpec{
                    .size = chrononmotion::Vector2(30.f, 30.f), .fillColor = pal.accent,
                    .name = spec.name + "_dot_" + tag, .cornerRadius = 15.f,
                    .geometry = ShapeGeometry::Ellipse});
            dot.parent(root.id());
            dot.position(x, 0.f);
            dot.alive(0, 150);
            applyElementMotion(dot, spec.motion, scene.fps(), side);
            LayerHandle& label = addText(scene, root.id(), spec.name + "_" + tag + "_label",
                                         side == 0 ? spec.leftLabel : spec.rightLabel,
                                         34.f, pal.ink, x, 70.f);
            applyElementMotion(label, spec.motion, scene.fps(), side + 1);
        }
        LayerHandle& link = addBar(scene, root.id(), spec.name + "_link",
                                   spec.span, 4.f, 0.f, 0.f, pal.line, 2.f);
        applyElementMotion(link, ElementMotion{.preset = ElementMotionPreset::DrawOn,
                                               .startFrame = spec.motion.startFrame,
                                               .endFrame = spec.motion.endFrame,
                                               .staggerStep = spec.motion.staggerStep},
                           scene.fps());
        LayerHandle& relation = addText(scene, root.id(), spec.name + "_relation",
                                        spec.relation, 30.f, pal.accent, 0.f, -52.f);
        applyElementMotion(relation, spec.motion, scene.fps(), 3);
        return root;
    }

    LayerHandle& addBeforeAfterSplit(TemplateScene& scene, const BeforeAfterSplitSpec& spec) {
        require(!spec.beforePath.empty() && !spec.afterPath.empty(),
                "addBeforeAfterSplit: both image paths are required");
        require(spec.split > 0.f && spec.split < 1.f,
                "addBeforeAfterSplit: split must sit inside (0, 1)");
        require(spec.width > 0.f && spec.height > 0.f,
                "addBeforeAfterSplit: positive dimensions are required");
        LayerHandle& root = scene.group(spec.name);
        root.alive(0, 150);
        LayerHandle& before = scene.image(ImageSpec{
                .path = spec.beforePath, .name = spec.name + "_before"});
        before.parent(root.id());
        before.position(-spec.width * 0.25f, 0.f);
        before.alive(0, 150);
        applyElementMotion(before, spec.motion, scene.fps());
        LayerHandle& after = scene.image(ImageSpec{
                .path = spec.afterPath, .name = spec.name + "_after"});
        after.parent(root.id());
        after.position(spec.width * 0.25f, 0.f);
        after.alive(0, 150);
        applyElementMotion(after, spec.motion, scene.fps(), 1);
        const float splitX = (spec.split - 0.5f) * spec.width;
        LayerHandle& divider = addBar(scene, root.id(), spec.name + "_divider",
                                      6.f, spec.height, splitX, 0.f, "#F2EFE6", 3.f);
        applyElementMotion(divider, spec.motion, scene.fps(), 2);
        LayerHandle& beforeTag = addText(scene, root.id(), spec.name + "_before_tag",
                                         "BEFORE", 30.f, "#F2EFE6",
                                         -spec.width * 0.5f + 90.f, -spec.height * 0.5f + 44.f);
        applyElementMotion(beforeTag, spec.motion, scene.fps(), 3);
        LayerHandle& afterTag = addText(scene, root.id(), spec.name + "_after_tag",
                                        "AFTER", 30.f, "#F2EFE6",
                                        spec.width * 0.5f - 90.f, -spec.height * 0.5f + 44.f);
        applyElementMotion(afterTag, spec.motion, scene.fps(), 3);
        return root;
    }

    LayerHandle& addFlowDiagramNode(TemplateScene& scene, const FlowDiagramNodeSpec& spec) {
        require(!spec.title.empty(), "addFlowDiagramNode: a title is required");
        require(spec.width > 0.f && spec.height > 0.f,
                "addFlowDiagramNode: positive dimensions are required");
        const ElementPalette pal = paletteFor(spec.style);
        LayerHandle& root = scene.group(spec.name);
        root.alive(0, 150);
        LayerHandle& body = scene.shape(ShapeSpec{
                .size = chrononmotion::Vector2(spec.width, spec.height),
                .fillColor = "#17171D", .name = spec.name + "_body", .cornerRadius = 16.f});
        body.parent(root.id());
        body.position(0.f, 0.f);
        body.alive(0, 150);
        applyElementMotion(body, spec.motion, scene.fps());
        LayerHandle& accent = addBar(scene, root.id(), spec.name + "_accent",
                                     spec.width, 8.f, 0.f, -spec.height * 0.5f + 4.f,
                                     spec.accent, 4.f);
        applyElementMotion(accent, spec.motion, scene.fps(), 1);
        LayerHandle& title = addText(scene, root.id(), spec.name + "_title",
                                     spec.title, 44.f, pal.ink, -spec.width * 0.5f + 40.f, -30.f);
        applyElementMotion(title, spec.motion, scene.fps(), 2);
        if (!spec.subtitle.empty()) {
            LayerHandle& subtitle = addText(scene, root.id(), spec.name + "_subtitle",
                                            spec.subtitle, 30.f, pal.muted,
                                            -spec.width * 0.5f + 40.f, 40.f);
            applyElementMotion(subtitle, spec.motion, scene.fps(), 3);
        }
        LayerHandle& stubIn = addBar(scene, root.id(), spec.name + "_stub_in",
                                     40.f, 6.f, -spec.width * 0.5f - 20.f, 0.f, pal.line, 3.f);
        applyElementMotion(stubIn, spec.motion, scene.fps(), 3);
        LayerHandle& stubOut = addBar(scene, root.id(), spec.name + "_stub_out",
                                      40.f, 6.f, spec.width * 0.5f + 20.f, 0.f, pal.line, 3.f);
        applyElementMotion(stubOut, spec.motion, scene.fps(), 4);
        return root;
    }

}// namespace chronontemplate::elements

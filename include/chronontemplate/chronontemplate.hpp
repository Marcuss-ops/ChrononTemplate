// ChrononTemplate — the module in one include.
//
//   presets::           the composition recipes built on the motion primitives
//   ContentHost        what this module asks Chronon for
//   BindingRegistry    layer -> content
//   MotionBridge       the one-directional conversion
//   TemplateScene      the API a template author writes against
//   templates::        the packs a template starts from

#ifndef CHRONONTEMPLATE_HPP
#define CHRONONTEMPLATE_HPP

#include "chronontemplate/core/ChrononMotionContract.hpp"
#include "chronontemplate/core/ChrononRenderAdapter.hpp"
#include "chronontemplate/core/ContentBinding.hpp"
#include "chronontemplate/core/ContentHost.hpp"
#include "chronontemplate/core/FrameSubmission.hpp"
#include "chronontemplate/core/MotionBridge.hpp"
#include "chronontemplate/core/NativePrimitives.hpp"
#include "chronontemplate/core/PlanLowering.hpp"
#include "chronontemplate/core/RenderPlanContentHost.hpp"
#include "chronontemplate/short_phrases/ShortPhrasePack.hpp"
#include "chronontemplate/core/Presets.hpp"
#include "chronontemplate/transitions/TransitionPack.hpp"
#include "chronontemplate/core/StyleTokens.hpp"
#include "chronontemplate/core/TemplateScene.hpp"
#include "chronontemplate/single_images/ImageAnimationPack.hpp"
#include "chronontemplate/single_images/PixelGridPack.hpp"
#include "chronontemplate/single_images/EdgeStrokePack.hpp"
#include "chronontemplate/single_images/GlowPack.hpp"
#include "chronontemplate/single_images/RGBSplitPack.hpp"
#include "chronontemplate/elements/ElementsCommon.hpp"
#include "chronontemplate/elements/TimelineElements.hpp"
#include "chronontemplate/elements/AnnotationElements.hpp"
#include "chronontemplate/elements/WebElements.hpp"
#include "chronontemplate/elements/DocumentaryElements.hpp"
#include "chronontemplate/elements/DiagramElements.hpp"
#include "chronontemplate/single_images/ArchivalLensLook.hpp"
#include "chronontemplate/multiple_images/MultiImagePack.hpp"
#include "chronontemplate/backgrounds/BackgroundPack.hpp"
#include "chronontemplate/map/ModernMapPack.hpp"
#include "chronontemplate/camera_roll/TitleCameraPack.hpp"
#include "chronontemplate/camera_roll/SceneCameraPack.hpp"
#include "chronontemplate/ui_camera/UiCameraChoreography.hpp"
#include "chronontemplate/vintage_documentary/VintageDocumentaryPack.hpp"
#include "chronontemplate/vintage_documentary/VintageDocumentaryTitle01Pack.hpp"
#include "chronontemplate/documentary_effects/MagnifierLoupePack.hpp"
#include "chronontemplate/documentary_effects/RedactedPack.hpp"
#include "chronontemplate/documentary_effects/FilmLeaderPack.hpp"
#include "chronontemplate/documentary_effects/DepthParallaxPack.hpp"
#include "chronontemplate/documentary_effects/RouteDrawingPack.hpp"
#include "chronontemplate/documentary_effects/BeforeAfterPack.hpp"
#include "chronontemplate/documentary_effects/AnimatedCountersPack.hpp"
#include "chronontemplate/entities_with_text/DocumentarySnapshotPack.hpp"
#include "chronontemplate/date_groups/DateGroupsPack.hpp"
#include "chronontemplate/entities_with_text/EntityFilmstripPack.hpp"
#include "chronontemplate/core/UiPrimitives.hpp"
#include "chronontemplate/entities_with_text/YouTubeSubscribe.hpp"

#endif//CHRONONTEMPLATE_HPP

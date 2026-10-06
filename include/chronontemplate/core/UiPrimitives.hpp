// ChrononTemplate — reusable web composition primitives.
//
// These are declarative composition data. ChrononTemplate owns the design
// vocabulary; the Chronon content host/renderer owns rasterization. Motion3D
// receives only the resulting layers and never depends on these types.
#ifndef CHRONONTEMPLATE_UI_PRIMITIVES_HPP
#define CHRONONTEMPLATE_UI_PRIMITIVES_HPP

#include <cmath>
#include <stdexcept>
#include <string>

namespace chronontemplate::ui {

    struct RoundedRect {
        float width{0.f};
        float height{0.f};
        float radius{0.f};

        void validate() const {
            if (!(width > 0.f) || !(height > 0.f) || !std::isfinite(width) ||
                !std::isfinite(height) || !std::isfinite(radius) || radius < 0.f ||
                radius > width * 0.5f || radius > height * 0.5f) {
                throw std::invalid_argument("RoundedRect: invalid dimensions or radius");
            }
        }
    };

    struct Shadow {
        float blur{0.f};
        float offsetX{0.f};
        float offsetY{0.f};
        float opacity{0.f};

        void validate() const {
            if (!std::isfinite(blur) || blur < 0.f || !std::isfinite(offsetX) ||
                !std::isfinite(offsetY) || !std::isfinite(opacity) || opacity < 0.f ||
                opacity > 1.f) {
                throw std::invalid_argument("Shadow: invalid blur, offset or opacity");
            }
        }
    };

    struct Button {
        RoundedRect shape{};
        Shadow shadow{};
        std::string label{};
        std::string assetPath{};

        void validate() const {
            shape.validate();
            shadow.validate();
            if (label.empty() && assetPath.empty()) {
                throw std::invalid_argument("Button: label or assetPath is required");
            }
        }
    };

    struct AvatarCircle {
        float diameter{0.f};
        std::string assetPath{};

        void validate() const {
            if (!(diameter > 0.f) || !std::isfinite(diameter) || assetPath.empty()) {
                throw std::invalid_argument("AvatarCircle: positive diameter and assetPath are required");
            }
        }
    };

    struct Border {
        float width{0.f};
        std::string color{"#FFFFFF"};

        void validate() const {
            if (!std::isfinite(width) || width < 0.f || color.empty()) {
                throw std::invalid_argument("Border: width and color are invalid");
            }
        }
    };

    struct IconSlot {
        float width{0.f};
        float height{0.f};
        std::string assetPath{};

        void validate() const {
            if (!(width > 0.f) || !(height > 0.f) || !std::isfinite(width) ||
                !std::isfinite(height) || assetPath.empty()) {
                throw std::invalid_argument("IconSlot: positive dimensions and assetPath are required");
            }
        }
    };

    struct Gap {
        float value{0.f};

        void validate() const {
            if (!std::isfinite(value) || value < 0.f) {
                throw std::invalid_argument("Gap: value must be finite and non-negative");
            }
        }
    };

    struct Padding {
        float top{0.f};
        float right{0.f};
        float bottom{0.f};
        float left{0.f};

        void validate() const {
            if (!std::isfinite(top) || !std::isfinite(right) || !std::isfinite(bottom) ||
                !std::isfinite(left) || top < 0.f || right < 0.f || bottom < 0.f || left < 0.f) {
                throw std::invalid_argument("Padding: values must be finite and non-negative");
            }
        }
    };

    struct Align {
        enum class Axis { Start, Center, End, Stretch };
        Axis horizontal{Axis::Start};
        Axis vertical{Axis::Start};
    };

    struct Row {
        Gap gap{};
        Padding padding{};
        Align align{};

        void validate() const { gap.validate(); padding.validate(); }
    };

    struct Column {
        Gap gap{};
        Padding padding{};
        Align align{};

        void validate() const { gap.validate(); padding.validate(); }
    };

    struct Stack {
        Padding padding{};
        Align align{};

        void validate() const { padding.validate(); }
    };

    struct Badge {
        RoundedRect shape{.width = 96.f, .height = 32.f, .radius = 16.f};
        std::string label{};
        std::string fill{"#FFFFFF"};

        void validate() const {
            shape.validate();
            if (label.empty() || fill.empty()) {
                throw std::invalid_argument("Badge: label and fill are required");
            }
        }
    };

    struct Separator {
        float length{0.f};
        float thickness{1.f};
        std::string color{"#FFFFFF"};

        void validate() const {
            if (!(length > 0.f) || !(thickness > 0.f) || !std::isfinite(length) ||
                !std::isfinite(thickness) || color.empty()) {
                throw std::invalid_argument("Separator: positive dimensions and color are required");
            }
        }
    };

}// namespace chronontemplate::ui

#endif//CHRONONTEMPLATE_UI_PRIMITIVES_HPP

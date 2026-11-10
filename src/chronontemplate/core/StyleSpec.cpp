#include "chronontemplate/core/StyleSpec.hpp"

#include <nlohmann/json.hpp>

#include <cmath>
#include <istream>
#include <iterator>
#include <stdexcept>
#include <string>

namespace chronontemplate {

    namespace {

        constexpr std::string_view kSchema = "chronon.style.v1";

        bool blank(const std::string& value) {
            for (const char c : value) {
                if (c != ' ' && c != '\t' && c != '\n' && c != '\r') return false;
            }
            return true;
        }

    }// namespace

    void StyleSpec::validate() const {

        if (blank(id)) {
            throw std::invalid_argument("StyleSpec: id must not be empty");
        }
        if (fps < 1 || fps > 120) {
            throw std::invalid_argument("StyleSpec: fps must be in [1, 120]");
        }
        look.validate();
    }

    StyleSpec parseStyle(std::string_view json) {

        nlohmann::json document;
        try {
            document = nlohmann::json::parse(json.begin(), json.end());
        } catch (const nlohmann::json::exception& error) {
            throw std::invalid_argument(std::string("StyleSpec: invalid JSON: ") + error.what());
        }

        if (!document.is_object()) {
            throw std::invalid_argument("StyleSpec: expected a JSON object");
        }

        for (const auto& [key, value] : document.items()) {
            (void) value;
            if (key != "schema" && key != "id" && key != "look" && key != "fps") {
                throw std::invalid_argument("StyleSpec: unknown field '" + key + "'");
            }
        }

        if (!document.contains("schema") || !document.at("schema").is_string()) {
            throw std::invalid_argument("StyleSpec: schema must be a string");
        }
        if (document.at("schema").get<std::string>() != kSchema) {
            throw std::invalid_argument("StyleSpec: unsupported schema '" +
                                        document.at("schema").get<std::string>() + "'");
        }

        if (!document.contains("id") || !document.at("id").is_string()) {
            throw std::invalid_argument("StyleSpec: id must be a string");
        }
        if (!document.contains("look") || !document.at("look").is_string()) {
            throw std::invalid_argument("StyleSpec: look must be a string");
        }
        if (!document.contains("fps") || !document.at("fps").is_number_integer()) {
            throw std::invalid_argument("StyleSpec: fps must be an integer");
        }

        StyleSpec style;
        style.id = document.at("id").get<std::string>();
        style.look.kind = parseLook(document.at("look").get<std::string>());
        const auto fps = document.at("fps").get<long long>();
        if (fps < 1 || fps > 120) {
            throw std::invalid_argument("StyleSpec: fps must be in [1, 120]");
        }
        style.fps = static_cast<int>(fps);
        style.validate();
        return style;
    }

    StyleSpec readStyle(std::istream& input) {

        const std::string json{std::istreambuf_iterator<char>(input),
                               std::istreambuf_iterator<char>()};
        if (json.empty()) {
            throw std::invalid_argument("StyleSpec: empty document");
        }
        return parseStyle(json);
    }

    std::string styleFingerprint(const StyleSpec& style) {

        style.validate();
        return std::string(kSchema) + "|" + style.id + "|" +
               std::string(lookId(style.look.kind)) + "|" + std::to_string(style.fps) + "|" +
               std::to_string(static_cast<int>(style.look.intensity * 1000000.f));
    }

}// namespace chronontemplate

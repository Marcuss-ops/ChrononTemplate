#pragma once

#include <string>
#include <vector>
#include <cctype>
#include <cmath>
#include <sstream>
#include <fstream>
#include <iostream>
#include <blend2d.h>
#include <chronontemplate/vector_diagram/TopologicalPathMorpher.hpp>

namespace chronontemplate::vector_diagram {

class SvgPathParser {
public:
    static bool parsePathString(const std::string& d, BLPath& outBlPath, std::vector<Point2D>& outPoints) {
        size_t i = 0;
        const size_t len = d.size();

        double curX = 0.0, curY = 0.0;
        double startX = 0.0, startY = 0.0;
        double lastCtrlX = 0.0, lastCtrlY = 0.0;
        char lastCmd = ' ';

        auto skipSeparators = [&]() {
            while (i < len && (d[i] == ' ' || d[i] == ',' || d[i] == '\t' || d[i] == '\r' || d[i] == '\n')) {
                ++i;
            }
        };

        auto readNumber = [&](double& val) -> bool {
            skipSeparators();
            if (i >= len) return false;

            size_t start = i;
            if (d[i] == '+' || d[i] == '-') ++i;

            bool hasDigits = false;
            while (i < len && std::isdigit(static_cast<unsigned char>(d[i]))) {
                hasDigits = true;
                ++i;
            }
            if (i < len && d[i] == '.') {
                ++i;
                while (i < len && std::isdigit(static_cast<unsigned char>(d[i]))) {
                    hasDigits = true;
                    ++i;
                }
            }
            if (!hasDigits) {
                i = start;
                return false;
            }
            if (i < len && (d[i] == 'e' || d[i] == 'E')) {
                size_t eStart = i;
                ++i;
                if (i < len && (d[i] == '+' || d[i] == '-')) ++i;
                bool hasExpDigits = false;
                while (i < len && std::isdigit(static_cast<unsigned char>(d[i]))) {
                    hasExpDigits = true;
                    ++i;
                }
                if (!hasExpDigits) i = eStart;
            }

            try {
                val = std::stod(d.substr(start, i - start));
                return true;
            } catch (...) {
                i = start;
                return false;
            }
        };

        skipSeparators();
        char cmd = ' ';

        while (i < len) {
            skipSeparators();
            if (i >= len) break;

            if (std::isalpha(static_cast<unsigned char>(d[i]))) {
                cmd = d[i++];
            } else if (cmd == 'M') {
                cmd = 'L';
            } else if (cmd == 'm') {
                cmd = 'l';
            }

            skipSeparators();

            switch (cmd) {
                case 'M':
                case 'm': {
                    double x, y;
                    if (!readNumber(x) || !readNumber(y)) break;
                    if (cmd == 'm') { x += curX; y += curY; }
                    curX = x; curY = y;
                    startX = x; startY = y;
                    outBlPath.moveTo(curX, curY);
                    outPoints.push_back({ curX, curY });
                    lastCtrlX = curX; lastCtrlY = curY;
                    break;
                }
                case 'L':
                case 'l': {
                    double x, y;
                    if (!readNumber(x) || !readNumber(y)) break;
                    if (cmd == 'l') { x += curX; y += curY; }
                    curX = x; curY = y;
                    outBlPath.lineTo(curX, curY);
                    outPoints.push_back({ curX, curY });
                    lastCtrlX = curX; lastCtrlY = curY;
                    break;
                }
                case 'H':
                case 'h': {
                    double x;
                    if (!readNumber(x)) break;
                    if (cmd == 'h') x += curX;
                    curX = x;
                    outBlPath.lineTo(curX, curY);
                    outPoints.push_back({ curX, curY });
                    lastCtrlX = curX; lastCtrlY = curY;
                    break;
                }
                case 'V':
                case 'v': {
                    double y;
                    if (!readNumber(y)) break;
                    if (cmd == 'v') y += curY;
                    curY = y;
                    outBlPath.lineTo(curX, curY);
                    outPoints.push_back({ curX, curY });
                    lastCtrlX = curX; lastCtrlY = curY;
                    break;
                }
                case 'C':
                case 'c': {
                    double x1, y1, x2, y2, x, y;
                    if (!readNumber(x1) || !readNumber(y1) ||
                        !readNumber(x2) || !readNumber(y2) ||
                        !readNumber(x)  || !readNumber(y)) break;
                    if (cmd == 'c') {
                        x1 += curX; y1 += curY;
                        x2 += curX; y2 += curY;
                        x  += curX; y  += curY;
                    }
                    outBlPath.cubicTo(x1, y1, x2, y2, x, y);

                    // Adaptive polyline sampling for ArcLengthPath
                    const int steps = 16;
                    for (int s = 1; s <= steps; ++s) {
                        double u = s / (double)steps;
                        double om = 1.0 - u;
                        double px = om*om*om*curX + 3.0*om*om*u*x1 + 3.0*om*u*u*x2 + u*u*u*x;
                        double py = om*om*om*curY + 3.0*om*om*u*y1 + 3.0*om*u*u*y2 + u*u*u*y;
                        outPoints.push_back({ px, py });
                    }

                    curX = x; curY = y;
                    lastCtrlX = x2; lastCtrlY = y2;
                    break;
                }
                case 'S':
                case 's': {
                    double x2, y2, x, y;
                    if (!readNumber(x2) || !readNumber(y2) ||
                        !readNumber(x)  || !readNumber(y)) break;
                    if (cmd == 's') {
                        x2 += curX; y2 += curY;
                        x  += curX; y  += curY;
                    }
                    double x1 = curX, y1 = curY;
                    if (lastCmd == 'C' || lastCmd == 'c' || lastCmd == 'S' || lastCmd == 's') {
                        x1 = 2.0 * curX - lastCtrlX;
                        y1 = 2.0 * curY - lastCtrlY;
                    }
                    outBlPath.cubicTo(x1, y1, x2, y2, x, y);

                    const int steps = 16;
                    for (int s = 1; s <= steps; ++s) {
                        double u = s / (double)steps;
                        double om = 1.0 - u;
                        double px = om*om*om*curX + 3.0*om*om*u*x1 + 3.0*om*u*u*x2 + u*u*u*x;
                        double py = om*om*om*curY + 3.0*om*om*u*y1 + 3.0*om*u*u*y2 + u*u*u*y;
                        outPoints.push_back({ px, py });
                    }

                    curX = x; curY = y;
                    lastCtrlX = x2; lastCtrlY = y2;
                    break;
                }
                case 'Q':
                case 'q': {
                    double x1, y1, x, y;
                    if (!readNumber(x1) || !readNumber(y1) ||
                        !readNumber(x)  || !readNumber(y)) break;
                    if (cmd == 'q') {
                        x1 += curX; y1 += curY;
                        x  += curX; y  += curY;
                    }
                    outBlPath.quadTo(x1, y1, x, y);

                    const int steps = 12;
                    for (int s = 1; s <= steps; ++s) {
                        double u = s / (double)steps;
                        double om = 1.0 - u;
                        double px = om*om*curX + 2.0*om*u*x1 + u*u*x;
                        double py = om*om*curY + 2.0*om*u*y1 + u*u*y;
                        outPoints.push_back({ px, py });
                    }

                    curX = x; curY = y;
                    lastCtrlX = x1; lastCtrlY = y1;
                    break;
                }
                case 'Z':
                case 'z': {
                    curX = startX; curY = startY;
                    outBlPath.close();
                    if (!outPoints.empty() && outPoints.back().distance_to({ curX, curY }) > 1e-4) {
                        outPoints.push_back({ curX, curY });
                    }
                    lastCtrlX = curX; lastCtrlY = curY;
                    break;
                }
                default:
                    ++i;
                    break;
            }
            lastCmd = cmd;
        }
        return !outPoints.empty();
    }

    // Loads a raw SVG file from disk and parses all path definitions into an ArcLengthPath
    static bool loadSvgFile(const std::string& filepath, ArcLengthPath& outPath, BLPath& outBlPath) {
        std::ifstream file(filepath);
        if (!file.is_open()) {
            std::cerr << "[SvgPathParser] Error opening SVG: " << filepath << "\n";
            return false;
        }

        std::string content((std::istreambuf_iterator<char>(file)),
                             std::istreambuf_iterator<char>());
        file.close();

        std::vector<Point2D> collectedPoints;

        // Find all <path d="..." occurrences
        size_t pos = 0;
        while ((pos = content.find("<path", pos)) != std::string::npos) {
            size_t tagEnd = content.find(">", pos);
            if (tagEnd == std::string::npos) break;

            size_t dPos = content.find("d=\"", pos);
            if (dPos != std::string::npos && dPos < tagEnd) {
                size_t dStart = dPos + 3;
                size_t dEnd = content.find("\"", dStart);
                if (dEnd != std::string::npos) {
                    std::string dStr = content.substr(dStart, dEnd - dStart);
                    parsePathString(dStr, outBlPath, collectedPoints);
                }
            }
            pos = tagEnd + 1;
        }

        // Also handle <circle cx="..." cy="..." r="...">
        pos = 0;
        while ((pos = content.find("<circle", pos)) != std::string::npos) {
            size_t tagEnd = content.find(">", pos);
            if (tagEnd == std::string::npos) break;
            std::string tag = content.substr(pos, tagEnd - pos + 1);

            auto extractAttr = [&](const std::string& attr) -> double {
                size_t aPos = tag.find(attr + "=\"");
                if (aPos == std::string::npos) return 0.0;
                size_t aStart = aPos + attr.length() + 2;
                size_t aEnd = tag.find("\"", aStart);
                if (aEnd == std::string::npos) return 0.0;
                try { return std::stod(tag.substr(aStart, aEnd - aStart)); } catch(...) { return 0.0; }
            };

            double cx = extractAttr("cx");
            double cy = extractAttr("cy");
            double r = extractAttr("r");
            if (r > 0.0) {
                outBlPath.addCircle(BLCircle(cx, cy, r));
                const int steps = 32;
                for (int s = 0; s < steps; ++s) {
                    double ang = (s / (double)steps) * 2.0 * 3.14159265358979323846;
                    collectedPoints.push_back({ cx + r * std::cos(ang), cy + r * std::sin(ang) });
                }
            }
            pos = tagEnd + 1;
        }

        if (collectedPoints.empty()) return false;

        // Auto-normalize and center coordinates around (0, 0)
        double minX = 1e9, maxX = -1e9, minY = 1e9, maxY = -1e9;
        for (const auto& p : collectedPoints) {
            minX = std::min(minX, p.x); maxX = std::max(maxX, p.x);
            minY = std::min(minY, p.y); maxY = std::max(maxY, p.y);
        }

        double width = maxX - minX;
        double height = maxY - minY;
        double maxDim = std::max(width, height);
        if (maxDim <= 1e-6) maxDim = 1.0;

        double scale = 360.0 / maxDim; // Normalize to standard ~360px viewport
        double midX = (minX + maxX) * 0.5;
        double midY = (minY + maxY) * 0.5;

        std::vector<Point2D> centeredPoints;
        centeredPoints.reserve(collectedPoints.size());
        for (const auto& p : collectedPoints) {
            centeredPoints.push_back({ (p.x - midX) * scale, (p.y - midY) * scale });
        }

        outPath.build_from_points(centeredPoints, true);
        return true;
    }
};

} // namespace chronontemplate::vector_diagram

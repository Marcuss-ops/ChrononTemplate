#pragma once

#include <vector>
#include <cmath>
#include <cstddef>
#include <algorithm>
#include <limits>

namespace chronontemplate::vector_diagram {

struct Point2D {
    double x = 0.0;
    double y = 0.0;

    Point2D() = default;
    Point2D(double x_, double y_) : x(x_), y(y_) {}

    Point2D operator+(const Point2D& o) const { return { x + o.x, y + o.y }; }
    Point2D operator-(const Point2D& o) const { return { x - o.x, y - o.y }; }
    Point2D operator*(double s) const { return { x * s, y * s }; }

    double distance_to(const Point2D& o) const {
        return std::hypot(x - o.x, y - o.y);
    }

    double distance_sq_to(const Point2D& o) const {
        double dx = x - o.x;
        double dy = y - o.y;
        return dx * dx + dy * dy;
    }
};

class ArcLengthPath {
public:
    struct SegmentSample {
        double cumulative_length;
        Point2D pt;
    };

    std::vector<SegmentSample> samples;
    double total_length = 0.0;
    bool is_closed = true;

    void build_from_points(const std::vector<Point2D>& raw_pts, bool closed = true) {
        samples.clear();
        total_length = 0.0;
        is_closed = closed;
        if (raw_pts.empty()) return;

        samples.push_back({ 0.0, raw_pts[0] });
        for (size_t i = 1; i < raw_pts.size(); ++i) {
            double d = raw_pts[i].distance_to(raw_pts[i - 1]);
            total_length += d;
            samples.push_back({ total_length, raw_pts[i] });
        }

        if (closed && raw_pts.size() > 1) {
            double d = raw_pts[0].distance_to(raw_pts.back());
            if (d > 1e-6) {
                total_length += d;
                samples.push_back({ total_length, raw_pts[0] });
            }
        }
    }

    Point2D evaluate_normalized(double u) const {
        if (samples.empty()) return { 0.0, 0.0 };
        if (samples.size() == 1 || total_length <= 1e-7) return samples[0].pt;

        double target = std::clamp(u, 0.0, 1.0) * total_length;

        for (size_t i = 1; i < samples.size(); ++i) {
            if (samples[i].cumulative_length >= target) {
                double prev_l = samples[i - 1].cumulative_length;
                double span = samples[i].cumulative_length - prev_l;
                double t = (span > 1e-7) ? (target - prev_l) / span : 0.0;
                return {
                    samples[i - 1].pt.x + t * (samples[i].pt.x - samples[i - 1].pt.x),
                    samples[i - 1].pt.y + t * (samples[i].pt.y - samples[i - 1].pt.y)
                };
            }
        }
        return samples.back().pt;
    }

    std::vector<Point2D> resample_uniform(size_t N) const {
        std::vector<Point2D> result;
        if (N == 0) return result;
        result.reserve(N);

        for (size_t i = 0; i < N; ++i) {
            double u = (N > 1) ? (double)i / (double)N : 0.0;
            result.push_back(evaluate_normalized(u));
        }
        return result;
    }
};

class TopologicalPathMorpher {
public:
    struct MorphMetrics {
        double min_energy = 0.0;
        int optimal_shift = 0;
        bool is_flipped = false;
        size_t sample_count = 0;
    };

private:
    std::vector<Point2D> pts_a;
    std::vector<Point2D> pts_b_aligned;
    MorphMetrics metrics;

public:
    TopologicalPathMorpher() = default;

    void initialize(const ArcLengthPath& path_a, const ArcLengthPath& path_b, size_t N = 256) {
        pts_a = path_a.resample_uniform(N);
        std::vector<Point2D> raw_b = path_b.resample_uniform(N);

        metrics.sample_count = N;
        if (N == 0 || pts_a.empty() || raw_b.empty()) return;

        // Solve Optimal Vertex Pairing & Phase Shift to minimize total deformation energy:
        // E(k, flip) = sum_i || A[i] - B[(flip ? -i : +i) + k] ||^2
        double best_energy = std::numeric_limits<double>::infinity();
        int best_k = 0;
        bool best_flip = false;

        for (int flip = 0; flip <= 1; ++flip) {
            bool is_flip = (flip == 1);
            for (int k = 0; k < (int)N; ++k) {
                double energy = 0.0;
                for (size_t i = 0; i < N; ++i) {
                    int b_idx;
                    if (!is_flip) {
                        b_idx = ((int)i + k) % (int)N;
                    } else {
                        b_idx = (k - (int)i) % (int)N;
                        if (b_idx < 0) b_idx += (int)N;
                    }
                    energy += pts_a[i].distance_sq_to(raw_b[b_idx]);
                }
                energy /= (double)N;

                if (energy < best_energy) {
                    best_energy = energy;
                    best_k = k;
                    best_flip = is_flip;
                }
            }
        }

        metrics.min_energy = best_energy;
        metrics.optimal_shift = best_k;
        metrics.is_flipped = best_flip;

        // Build aligned version of path B matching pts_a index by index
        pts_b_aligned.resize(N);
        for (size_t i = 0; i < N; ++i) {
            int b_idx;
            if (!best_flip) {
                b_idx = ((int)i + best_k) % (int)N;
            } else {
                b_idx = (best_k - (int)i) % (int)N;
                if (b_idx < 0) b_idx += (int)N;
            }
            pts_b_aligned[i] = raw_b[b_idx];
        }
    }

    // Evaluate interpolated morph at parameter tau in [0.0, 1.0]
    std::vector<Point2D> evaluate_morph(double tau) const {
        double clamped_tau = std::clamp(tau, 0.0, 1.0);
        size_t N = pts_a.size();
        std::vector<Point2D> out(N);

        for (size_t i = 0; i < N; ++i) {
            out[i].x = (1.0 - clamped_tau) * pts_a[i].x + clamped_tau * pts_b_aligned[i].x;
            out[i].y = (1.0 - clamped_tau) * pts_a[i].y + clamped_tau * pts_b_aligned[i].y;
        }
        return out;
    }

    const std::vector<Point2D>& get_pts_a() const { return pts_a; }
    const std::vector<Point2D>& get_pts_b_aligned() const { return pts_b_aligned; }
    const MorphMetrics& get_metrics() const { return metrics; }
};

} // namespace chronontemplate::vector_diagram

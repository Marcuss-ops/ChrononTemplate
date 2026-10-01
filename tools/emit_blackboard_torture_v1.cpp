#include "chronontemplate/NativePrimitives.hpp"

#include <fstream>
#include <iostream>
#include <stdexcept>

int main(int argc, char** argv) {
    try {
        const std::string path = argc > 1 ? argv[1] : "golden_plans/blackboard_torture_v1.plan.json";
        std::ofstream output(path);
        if (!output) throw std::runtime_error("could not open output plan: " + path);
        output << chronontemplate::native::buildBlackboardTortureV1().dump(2) << '\n';
        std::cout << path << '\n';
        return 0;
    } catch (const std::exception& error) {
        std::cerr << "blackboard plan generation failed: " << error.what() << '\n';
        return 1;
    }
}

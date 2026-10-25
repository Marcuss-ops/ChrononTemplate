// Emit the four native documentary-reference stills from the ChrononTemplate Web pack.
#include "chronontemplate/web/DocumentaryReferenceStills.hpp"

#include <filesystem>
#include <fstream>
#include <iostream>
#include <stdexcept>

int main(int argc, char** argv) try {
    if (argc != 2) throw std::runtime_error("usage: emit_web_documentary_reference_stills <output-dir>");
    const std::filesystem::path output = std::filesystem::absolute(argv[1]);
    std::filesystem::create_directories(output);
    for (const auto& plan : chronontemplate::web::buildDocumentaryReferenceStillPlans()) {
        const auto id = plan.at("job_id").get<std::string>();
        const auto path = output / (id + ".plan.json");
        std::ofstream file(path);
        if (!file) throw std::runtime_error("cannot write plan: " + path.string());
        file << plan.dump(2) << '\n';
        std::cout << path << '\n';
    }
    return 0;
} catch (const std::exception& error) {
    std::cerr << error.what() << '\n';
    return 1;
}

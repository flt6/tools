#include <iostream>
#include <sstream>
#include <fstream>
#include <stdexcept>
#include <vector>
#include <string>
#include <cstdlib>
#include <cstdio>
#include <filesystem>
#include <algorithm>

#ifdef _WIN32
    const std::string DEVNULL = "NUL";
#else
    const std::string DEVNULL = "/dev/null";
#endif


using namespace std;
namespace fs = std::filesystem;

void runCommand(const string& command,const bool output=false) {
    int ret;
    if (!output)
        ret = system((command + " > " + DEVNULL + " 2>&1").c_str());
    else
        ret = system(command.c_str());
    if (ret != 0) {
        cerr << "Command '" << command << "' failed." << endl;
        exit(-1);
    }
}

int main(int argc, char* argv[]) {
    try {
        runCommand("ffprobe -version");
        runCommand("ffmpeg -version");
    } catch (const exception& e) {
        cerr << "'ffmpeg' or 'ffprobe' not installed." << endl;
        exit(-1);
    }

    fs::path src;
    if (argc == 3) {
        string arg1 = argv[1];
        if (arg1.front() == '"' && arg1.back() == '"')
            src = fs::path(string(argv[2]).substr(1, string(argv[2]).size() - 2));
        else
            src = fs::path(argv[2]);
    } else {
        src = fs::path("/.NOT_EXIST_FILE.");
    }

    while (!fs::exists(src)) {
        string ipt;
        cout << "Enter the path to the source file: ";
        getline(cin, ipt);
        if (ipt.front() == '"' && ipt.back() == '"')
            src = fs::path(ipt.substr(1, ipt.size() - 2));
        else
            src = fs::path(ipt);
    }

    string targetTime;
    while (true) {
        cout << "Enter the target time: ";
        getline(cin, targetTime);
        if (all_of(targetTime.begin(), targetTime.end(), ::isdigit))
            break;
    }
    float targetTimeFloat = stof(targetTime);

    string outputFile;
    cout << "Output file (Default out.mp4): ";
    getline(cin, outputFile);
    if (outputFile.empty()) outputFile = "out.mp4";

    string extraCMD;
    cout << "Extra cmd: ";
    getline(cin, extraCMD);

    stringstream command;
    command << "ffprobe -i " << src << " -show_entries format=duration -v quiet -of csv=p=0";
    FILE* pipe = popen(command.str().c_str(), "r");
    if (!pipe) {
        cerr << "Error while invoking ffprobe." << endl;
        return -1;
    }
    float srcTime;
    if (fscanf(pipe, "%f", &srcTime) != 1) {
        cerr << "Error reading output from ffprobe." << endl;
        pclose(pipe);
        return -1;
    }
    pclose(pipe);

    float rate = targetTimeFloat / srcTime;

    command.str("");
    command << "ffmpeg -hide_banner -t " << srcTime << " -i " << src << " -vf setpts=PTS*" << rate
            << " -r 30 -t " << targetTimeFloat << " " << extraCMD << " " << outputFile;
    runCommand(command.str(),true);

    return 0;
}

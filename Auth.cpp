#include "Auth.h"
#include <fstream>
#include <iostream>

// ASSIGNED TO: MEMBER 1

long long Auth::simpleHash(std::string pass) {
    // TODO: Implement a shift-add-XOR hash
    long long hash = 5381;
    for (char c : pass) {
        hash = ((hash << 5) + hash) + c;
    }
    return hash;
}

bool Auth::login(std::string inputPass) {
    // TODO: Check against file "security.bin"
    // If file doesn't exist, allow default "admin"
    return true; // Placeholder
}

void Auth::changePassword(std::string newPass) {
    // TODO: Hash newPass and save to "security.bin"
}
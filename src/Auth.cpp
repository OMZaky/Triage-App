#include "Auth.h"

using namespace std;

AuthSystem::AuthSystem(string filename) {
    dbFilename = filename;
    ensureAdminExists();
}

// DJB2 Hash Algorithm (Simple, Fast, and Deterministic)
unsigned long AuthSystem::computeHash(string str) {
    unsigned long hash = HASH_SEED;
    for (char c : str) {
        hash = ((hash << 5) + hash) + c; /* hash * 33 + c */
    }
    return hash;
}

void AuthSystem::ensureAdminExists() {
    ifstream infile(dbFilename);
    if (!infile.good()) {
        // File doesn't exist, create default admin
        ofstream outfile(dbFilename);
        outfile << "admin " << computeHash("admin") << endl;
        outfile.close();
    }
    infile.close();
}

bool AuthSystem::login(string username, string password) {
    ifstream file(dbFilename);
    string u;
    unsigned long h;
    
    unsigned long inputHash = computeHash(password);
    
    while (file >> u >> h) {
        if (u == username) {
            if (h == inputHash) return true; // Match
            else return false; // Wrong password
        }
    }
    return false; // User not found
}

bool AuthSystem::changePassword(string username, string oldPass, string newPass) {
    
    ifstream file(dbFilename);
    string u;
    unsigned long h;
    
    string tempFilename = dbFilename + ".tmp";
    ofstream tempFile(tempFilename);
    
    bool foundAndVerified = false;
    unsigned long oldHashInput = computeHash(oldPass);
    unsigned long newHash = computeHash(newPass);

    while (file >> u >> h) {
        if (u == username) {
            if (h == oldHashInput) {
                // Found user and password matches! Write NEW hash.
                tempFile << u << " " << newHash << endl;
                foundAndVerified = true;
            } else {
                // Wrong password, keep old data
                tempFile << u << " " << h << endl;
            }
        } else {
            // Just copy other users
            tempFile << u << " " << h << endl;
        }
    }
    
    file.close();
    tempFile.close();
    
        // Replace old DB with new DB
    remove(dbFilename.c_str());
    rename(tempFilename.c_str(), dbFilename.c_str());
    
    return foundAndVerified;
}
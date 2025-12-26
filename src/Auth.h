#ifndef AUTH_H
#define AUTH_H

#include <string>
#include <iostream>
#include <fstream>

// A constant specific to the custom hash function
const unsigned long HASH_SEED = 5381; 

struct User {
    std::string username;
    unsigned long passwordHash; // We store the hash, not the text
};

class AuthSystem {
private:
    std::string dbFilename;
    
    // Custom deterministic hash function (DJB2 Algorithm)
    // We use this because std::hash can change between program runs.
    unsigned long computeHash(std::string str);

public:
    AuthSystem(std::string filename = "users_db.txt");
    
    // Core Logic
    bool login(std::string username, std::string password);
    bool changePassword(std::string username, std::string oldPass, std::string newPass);
    void ensureAdminExists(); // Creates default admin if file missing
};

#endif
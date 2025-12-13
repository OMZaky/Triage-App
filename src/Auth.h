#ifndef AUTH_H
#define AUTH_H

#include <string>

// ASSIGNED TO: MEMBER 1
class Auth {
private:
    long long simpleHash(std::string pass); // Custom hash function
    void saveHash(long long hash);
    long long loadHash();

public:
    // Returns true if password matches stored hash
    bool login(std::string inputPass);
    
    // Updates the stored hash
    void changePassword(std::string newPass);
};

#endif
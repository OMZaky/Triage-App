#ifndef SYSTEM_H
#define SYSTEM_H

#include "FibHeap.h"
#include "Auth.h"
#include <string>

// ASSIGNED TO: MEMBER 5
class System {
private:
    FibonacciHeap heap;
    Auth auth;
    bool isLoggedIn;
    int nextId;

    void processCommand(std::string cmd);

public:
    System();
    void run(); // The main loop
};

#endif
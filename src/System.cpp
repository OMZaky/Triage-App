#include "System.h"
#include <iostream>
#include <fstream>
#include <sstream>

// ASSIGNED TO: MEMBER 5

System::System() {
    isLoggedIn = false;

    nextId = 1; // Default start ID

    // --- PERSISTENCE: LOAD DATA ON STARTUP ---
    // We try to open the database file. If it exists, we rebuild the heap.
    std::ifstream file("patients_data.txt");
    if (file.is_open()) {
        int id, prio, age;
        std::string name, desc;
        
        // Read line by line: [ID] [PRIORITY] [NAME]
        // Note: This assumes names don't have spaces for simplicity. 
        // If names have spaces, we'd need std::getline.
        while (file >> id >> prio >> age >> name >> desc) {
            heap.insert(id, prio, age, name, desc);

            if (id >= nextId) {
                nextId = id + 1;
            }
        }
        file.close();
        // We don't print anything here to avoid confusing the Python GUI during startup
    }
}

void System::run() {
    std::string command;

    // --- MAIN LOOP ---
    // Waits for text commands from Python via Standard Input (std::cin)
    while (std::cin >> command) {
        
        // 1. LOGIN COMMAND (Always allowed)
        if (command == "LOGIN") {
            std::string pass;
            std::cin >> pass;
            
            if (auth.login(pass)) {
                isLoggedIn = true;
                std::cout << "SUCCESS_LOGIN" << std::endl;
            } else {
                std::cout << "ERROR_LOGIN" << std::endl;
            }
        }
        
        // 2. EXIT COMMAND (Always allowed)
        // Triggers the Save functionality
        else if (command == "EXIT") {
            heap.saveToFile("patients_data.txt");
            std::cout << "SUCCESS_EXIT" << std::endl;
            break; // Terminate the C++ backend
        }
        
        // 3. PING (Heartbeat check)
        else if (command == "PING") {
            std::cout << "PONG" << std::endl;
        }

        // 4. RESTRICTED COMMANDS (Must be Logged In)
        else {
            if (!isLoggedIn) {
                // If not logged in, we must consume the arguments so the stream doesn't desync.
                // E.g. if user sent "ADD 101 5 John", we need to eat "101 5 John"
                std::string garbage;
                std::getline(std::cin, garbage);
                
                std::cout << "ERROR_AUTH" << std::endl;
            }
            else {
                // User is logged in, process the actual heap operations
                processCommand(command);
            }
        }

        // CRITICAL: Flush output so Python receives it immediately
        std::cout.flush();
    }
}

void System::processCommand(std::string cmd) {
    
    if (cmd == "ADD") {
        int prio, age;
        std::string name, desc;
        // Expects: ADD [ID] [PRIORITY] [NAME]
        std::cin >> prio >> age >> name >> desc;

        if (prio < 1 || prio > 10) {
            std::cout << "ERROR: Priority must be 1-10" << std::endl;
            return;
        }
        
        heap.insert(nextId, prio, age, name, desc);
        std::cout << "SUCCESS_ADD " << name << " ID:" << nextId << std::endl;
        
        nextId++; // Increment for next patient
    }
    
    // CRITICAL: Member 2's extractMin() returns a pointer. 
    // We must delete it here to prevent memory leaks.
    else if (cmd == "EXTRACT") {
        Node* n = heap.extractMin();
        if (n) {
            // Output: DATA [ID] [PRIO] [AGE] [NAME] [DESC]
            std::cout << "DATA " << n->id << " " 
                      << n->priority << " " 
                      << n->age << " "
                      << n->name << " " 
                      << n->description << std::endl;

            // CRITICAL: Member 2's extractMin() returns a pointer. 
            // We must delete it here to prevent memory leaks.

            delete n;
        } else {
            std::cout << "EMPTY" << std::endl;
        }
    }
    
    else if (cmd == "PEEK") {
        Node* minNode = heap.peek();
        if (minNode) {
            std::cout << "DATA " << minNode->id << " " 
                      << minNode->priority << " " 
                      << minNode->name << std::endl;
        } else {
            std::cout << "EMPTY" << std::endl;
        }
    }

    else if (cmd == "UPDATE") {
        int id, newPrio;
        // Expects: UPDATE [ID] [NEW_PRIORITY]
        std::cin >> id >> newPrio;
        
        // Note: decreaseKey returns void. We assume it works or prints its own error.
        // Ideally, decreaseKey should return a bool (true=found, false=not found).
        // For now, we assume success.
        heap.decreaseKey(id, newPrio); 
        std::cout << "SUCCESS_UPDATE" << std::endl;
    }
    
    else if (cmd == "CHANGE_PASS") {
        std::string newPass;
        std::cin >> newPass;
        auth.changePassword(newPass);
        std::cout << "SUCCESS_PASS_CHANGE" << std::endl;
    }

    else {
        // Unknown command
        std::cout << "ERROR_UNKNOWN" << std::endl;
        // Clear line to be safe
        std::string garbage; std::getline(std::cin, garbage);
    }
}
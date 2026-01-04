#include "System.h"
#include <iostream>
#include <fstream>
#include <sstream>

// CONSTRUCTOR
// Loads existing data and sets the auto-increment ID
System::System() {
    isLoggedIn = false;
    nextId = 1; 

    std::ifstream file("patients_data.txt");
    if (file.is_open()) {
        int id, prio, age;
        std::string name, desc;
        
        while (file >> id >> prio >> age >> name >> desc) {
            heap.insert(id, prio, age, name, desc);

            // Ensure nextId is higher than any existing ID
            if (id >= nextId) {
                nextId = id + 1;
            }
        }
        file.close();
    }
}

// DESTRUCTOR (Added for Safety)

System::~System() {
    heap.saveToFile("patients_data.txt");
}

void System::run() {
    std::string command;

    // --- MAIN LOOP ---
    while (std::cin >> command) {
        
        // 1. LOGIN
        if (command == "LOGIN") {
            std::string line;
            std::getline(std::cin, line);
            std::istringstream iss(line);
            
            std::string user, pass;
            if (!(iss >> user >> pass)) {
                std::cout << "ERROR_LOGIN" << std::endl;
                continue;
            }
            
            if (auth.login(user, pass)) {
                isLoggedIn = true;
                std::cout << "SUCCESS_LOGIN" << std::endl;
            } else {
                std::cout << "ERROR_LOGIN" << std::endl;
            }
        }
        
        // 2. CHANGE PASSWORD
        else if (command == "CHANGE_PASS") {
            std::string line;
            std::getline(std::cin, line);
            std::istringstream iss(line);
            
            std::string user, oldPass, newPass;
            if (!(iss >> user >> oldPass >> newPass)) {
                std::cout << "ERROR_PASS_CHANGE" << std::endl;
                continue;
            }
            
            if (auth.changePassword(user, oldPass, newPass)) {
                std::cout << "SUCCESS_PASS_CHANGE" << std::endl;
            } else {
                std::cout << "ERROR_PASS_CHANGE" << std::endl;
            }
        }

        // 3. EXIT
        else if (command == "EXIT") {
            heap.saveToFile("patients_data.txt");
            std::cout << "SUCCESS_EXIT" << std::endl;
            break; 
        }
        
        // 4. PING
        else if (command == "PING") {
            std::cout << "PONG" << std::endl;
        }

        // 5. RESTRICTED COMMANDS
        else {
            if (!isLoggedIn) {
                std::string garbage;
                std::getline(std::cin, garbage);
                std::cout << "ERROR_AUTH" << std::endl;
            }
            else {
                processCommand(command);
            }
        }

        std::cout.flush();
    }
}

void System::processCommand(std::string cmd) {
    
    // --- ADD PATIENT ---
    if (cmd == "ADD") {
        std::string line;
        std::getline(std::cin, line);
        std::istringstream iss(line);
        
        int prio, age;
        std::string name, desc;
        
        if (!(iss >> prio >> age >> name >> desc)) {
            std::cout << "ERROR: Invalid ADD format. Expected: ADD <prio> <age> <name> <desc>" << std::endl;
            return;
        }

        if (prio < 1 || prio > 10) {
            std::cout << "ERROR: Priority must be 1-10" << std::endl;
            return;
        }
        
        // Use auto-increment ID
        heap.insert(nextId, prio, age, name, desc);
        std::cout << "SUCCESS_ADD " << name << " ID:" << nextId << std::endl;
        
        nextId++; 
    }
    
    // --- EXTRACT ---
    else if (cmd == "EXTRACT") {
        Node* n = heap.extractMin();
        if (n) {
            std::cout << "DATA " << n->id << " " 
                      << n->priority << " " 
                      << n->age << " "
                      << n->name << " " 
                      << n->description << std::endl;

            delete n; // Prevent memory leak
        } else {
            std::cout << "EMPTY" << std::endl;
        }
    }
    
    // --- PEEK ---
    else if (cmd == "PEEK") {
        Node* minNode = heap.peek();
        if (minNode) {
            std::cout << "DATA " << minNode->id << " " 
                      << minNode->priority << " " 
                      << minNode->age << " "
                      << minNode->name << " " 
                      << minNode->description << std::endl;
        } else {
            std::cout << "EMPTY" << std::endl;
        }
    }

    // --- STATS ---
    else if (cmd == "STATS") {
        int count = heap.getNumNodes();
        int waitTime = count * 15; 
        std::cout << "STATS COUNT:" << count << " WAIT:" << waitTime << std::endl;
    }

    // --- LIST ---
    else if (cmd == "LIST") {
        heap.printAll();
    }

    // --- UPDATE ---
    else if (cmd == "UPDATE") {
        std::string line;
        std::getline(std::cin, line);
        std::istringstream iss(line);
        
        int id, newPrio;
        if (!(iss >> id >> newPrio)) {
            std::cout << "ERROR: Invalid UPDATE format" << std::endl;
            return;
        }
        heap.updatePriority(id, newPrio); 
        std::cout << "SUCCESS_UPDATE" << std::endl;
    }

    // --- LEAVE ---
    else if (cmd == "LEAVE") {
        std::string line;
        std::getline(std::cin, line);
        std::istringstream iss(line);
        
        int id;
        if (!(iss >> id)) {
            std::cout << "ERROR: Invalid LEAVE format" << std::endl;
            return;
        }
        heap.removePatient(id);
        std::cout << "SUCCESS_REMOVE " << id << std::endl;
    }

    // --- MERGE (Robust Version) ---
    else if (cmd == "MERGE") {
        std::string line;
        std::getline(std::cin, line);
        
        // Trim leading whitespace and get the full filename (handles paths with spaces)
        std::string filename = line;
        size_t start = filename.find_first_not_of(" \t");
        if (start == std::string::npos) {
            std::cout << "ERROR: Invalid MERGE format" << std::endl;
            return;
        }
        filename = filename.substr(start);
        
        std::ifstream file(filename);
        if (file.is_open()) {
            int id, prio, age;
            std::string name, desc;
            
            // SECURITY UPGRADE:
            // Instead of blindly merging (which risks ID collisions),
            // we insert patients one by one.
            // This utilizes the duplicate check we added to heap.insert().
            while (file >> id >> prio >> age >> name >> desc) {
                heap.insert(id, prio, age, name, desc);
                
                // CRITICAL: Update nextId so future manual adds don't collide
                if (id >= nextId) {
                    nextId = id + 1;
                }
            }
            file.close();
            std::cout << "SUCCESS_MERGE" << std::endl;
        } else {
            std::cout << "ERROR_FILE_NOT_FOUND" << std::endl;
        }
    }

    else {
        std::cout << "ERROR_UNKNOWN_COMMAND" << std::endl;
        std::string garbage; std::getline(std::cin, garbage);
    }
}
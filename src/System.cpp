#include "System.h"
#include <iostream>
#include <fstream>
#include <sstream>


System::System() {
    isLoggedIn = false;
    nextId = 1; 

    // We try to open the database file. If it exists, we rebuild the heap.
    std::ifstream file("patients_data.txt");
    if (file.is_open()) {
        int id, prio, age;
        std::string name, desc;
        
        // Read line by line: [ID] [PRIORITY] [AGE] [NAME] [DESC]
        while (file >> id >> prio >> age >> name >> desc) {
            heap.insert(id, prio, age, name, desc);

            // Ensure our auto-increment ID is always higher than the highest loaded ID
            if (id >= nextId) {
                nextId = id + 1;
            }
        }
        file.close();
    }
}

void System::run() {
    std::string command;

    // --- MAIN LOOP ---
    // Waits for text commands from Python via Standard Input (std::cin)
    while (std::cin >> command) {
        
        // 1. LOGIN COMMAND (Public)
        // Format: LOGIN <username> <password>
        if (command == "LOGIN") {
            std::string user, pass;
            std::cin >> user >> pass;
            
            if (auth.login(user, pass)) {
                isLoggedIn = true;
                std::cout << "SUCCESS_LOGIN" << std::endl;
            } else {
                std::cout << "ERROR_LOGIN" << std::endl;
            }
        }
        
        // 2. CHANGE PASSWORD (Public)
        // Format: CHANGE_PASS <username> <old_pass> <new_pass>
        else if (command == "CHANGE_PASS") {
            std::string user, oldPass, newPass;
            std::cin >> user >> oldPass >> newPass;
            
            if (auth.changePassword(user, oldPass, newPass)) {
                std::cout << "SUCCESS_PASS_CHANGE" << std::endl;
            } else {
                std::cout << "ERROR_PASS_CHANGE" << std::endl;
            }
        }

        // 3. EXIT COMMAND (Always allowed)
        else if (command == "EXIT") {
            heap.saveToFile("patients_data.txt");
            std::cout << "SUCCESS_EXIT" << std::endl;
            break; // Terminate the C++ backend
        }
        
        // 4. PING (Heartbeat check for Python)
        else if (command == "PING") {
            std::cout << "PONG" << std::endl;
        }

        // 5. RESTRICTED COMMANDS (Must be Logged In)
        else {
            if (!isLoggedIn) {
                // If not logged in, consume arguments to prevent stream desync.
                // Otherwise, the next word in the buffer might be interpreted as a command.
                std::string garbage;
                std::getline(std::cin, garbage);
                std::cout << "ERROR_AUTH" << std::endl;
            }
            else {
                // User is logged in, process the actual medical operations
                processCommand(command);
            }
        }

        // CRITICAL: Flush output so Python receives it immediately
        std::cout.flush();
    }
}

void System::processCommand(std::string cmd) {
    
    // --- ADD PATIENT ---
    if (cmd == "ADD") {
        int prio, age;
        std::string name, desc;
        // Expects: ADD [PRIORITY] [AGE] [NAME] [DESC]
        // Note: nextId is generated automatically
        std::cin >> prio >> age >> name >> desc;

        if (prio < 1 || prio > 10) {
            std::cout << "ERROR: Priority must be 1-10" << std::endl;
            return;
        }
        
        heap.insert(nextId, prio, age, name, desc);
        std::cout << "SUCCESS_ADD " << name << " ID:" << nextId << std::endl;
        
        nextId++; 
    }
    
    // --- EXTRACT (Treat Next Patient) ---
    else if (cmd == "EXTRACT") {
        Node* n = heap.extractMin();
        if (n) {
            // Output: DATA [ID] [PRIO] [AGE] [NAME] [DESC]
            std::cout << "DATA " << n->id << " " 
                      << n->priority << " " 
                      << n->age << " "
                      << n->name << " " 
                      << n->description << std::endl;

            // CRITICAL: Prevent memory leak by deleting the extracted node
            delete n;
        } else {
            std::cout << "EMPTY" << std::endl;
        }
    }
    
    // --- PEEK (View Next Patient) ---
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

    // --- STATS (Dashboard Data) ---
    else if (cmd == "STATS") {
        int count = heap.getNumNodes();
        // Estimation: 15 mins per patient
        int waitTime = count * 15; 
        std::cout << "STATS COUNT:" << count << " WAIT:" << waitTime << std::endl;
    }

    // --- LIST (Dump All Patients for GUI Sync) ---
    else if (cmd == "LIST") {
        heap.printAll();
    }

    // --- UPDATE PRIORITY (Dynamic Deterioration) ---
    // Usage: When a patient's condition worsens.
    else if (cmd == "UPDATE") {
        int id, newPrio;
        std::cin >> id >> newPrio;
        
        // This calls our safety wrapper in FibHeap.cpp which checks the array bounds
        heap.updatePriority(id, newPrio); 
        std::cout << "SUCCESS_UPDATE" << std::endl;
    }

    // --- LEAVE (LWBS - Left Without Being Seen) ---
    // Usage: When a patient walks out.
    else if (cmd == "LEAVE") {
        int id;
        std::cin >> id;
        heap.removePatient(id);
        std::cout << "SUCCESS_REMOVE " << id << std::endl;
    }

    // --- MERGE (Mass Casualty Event) ---
    // Usage: Merges an external list (e.g., from an ambulance) into the main heap instantly.
    else if (cmd == "MERGE") {
        std::string filename;
        std::cin >> filename;
        
        FibonacciHeap tempHeap;
        std::ifstream file(filename);
        
        if (file.is_open()) {
            int id, prio, age;
            std::string name, desc;
            while (file >> id >> prio >> age >> name >> desc) {
                // In a real system, we would re-map IDs to avoid collisions.
                // For this project, we assume the file contains unique IDs.
                tempHeap.insert(id, prio, age, name, desc);
            }
            file.close();
            
            // Perform the O(1) merge operation
            heap.merge(tempHeap);
            std::cout << "SUCCESS_MERGE" << std::endl;
        } else {
            std::cout << "ERROR_FILE_NOT_FOUND" << std::endl;
        }
    }

    else {
        std::cout << "ERROR_UNKNOWN_COMMAND" << std::endl;
        // Clear the line to prevent infinite loops if garbage is sent
        std::string garbage; std::getline(std::cin, garbage);
    }
}
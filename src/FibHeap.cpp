#include "FibHeap.h"
#include <iostream>
#include <fstream> // <--- ADD THIS LINE

// ASSIGNED TO: MEMBERS 2, 3, 4

FibonacciHeap::FibonacciHeap() {
    minNode = nullptr;
    numNodes = 0;
}

FibonacciHeap::~FibonacciHeap() {
    // TODO: Member 2 - Recursive cleanup
}

void FibonacciHeap::insert(int id, int priority, std::string name) {
    // TODO: Member 2 - Create node, addSibling to minNode
}

Node* FibonacciHeap::extractMin() {
    // TODO: Member 2 & 3 - Remove min, promote children, consolidate
    return nullptr; // Placeholder
}

void FibonacciHeap::consolidate() {
    // TODO: Member 3 - Use Node* A[50] array to track degrees
}

void FibonacciHeap::decreaseKey(int id, int newPriority) {
    // TODO: Member 4 - Find node, decrease val, cut if heap violated
}

// FibHeap.cpp

// Public function called by System
void FibonacciHeap::saveToFile(std::string filename) {
    std::ofstream file(filename);
    if (!file.is_open()) return;

    if (minNode != nullptr) {
        // The root list is circular, so we need to be careful not to loop forever
        Node* start = minNode;
        Node* current = start;
        
        do {
            _saveRecursive(current, file);
            current = current->right;
        } while (current != start && current != nullptr);
    }
    file.close();
}

// Private helper (Depth First Search)
void FibonacciHeap::_saveRecursive(Node* node, std::ofstream& file) {
    if (node == nullptr) return;

    // 1. Save this node's data
    // Format: ID PRIORITY NAME
    file << node->id << " " << node->priority << " " << node->name << "\n";

    // 2. Recursively save all children
    if (node->child != nullptr) {
        Node* start = node->child;
        Node* current = start;
        do {
            _saveRecursive(current, file);
            current = current->right;
        } while (current != start);
    }
}
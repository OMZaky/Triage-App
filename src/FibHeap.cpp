#include "FibHeap.h"
#include <iostream>
#include <cmath> // Needed for log2 in consolidate
#include <fstream>

// ASSIGNED TO: MEMBERS 2, 3, 4

FibonacciHeap::FibonacciHeap() {
    minNode = nullptr;
    numNodes = 0;
}

FibonacciHeap::~FibonacciHeap() {
    // TODO: Member 2 needs to implement recursive cleanup here
    // For now, we leave it empty to prevent compile errors
}

void FibonacciHeap::insert(int id, int priority, std::string name) {
    Node* newNode = new Node(id, priority, name);
    
    if (minNode == nullptr) {
        minNode = newNode;
        // Circular links logic handles itself in Node constructor usually, 
        // but let's ensure safety:
        minNode->left = minNode;
        minNode->right = minNode;
    } else {
        // Add to the root list (Member 1's addSibling logic)
        minNode->addSibling(newNode);
        
        // Update min if necessary
        if (newNode->priority < minNode->priority) {
            minNode = newNode;
        }
    }
    numNodes++;
}

// THIS WAS MISSING
Node* FibonacciHeap::peek() {
    return minNode;
}

Node* FibonacciHeap::extractMin() {
    Node* z = minNode;
    if (z != nullptr) {
        // 1. Promote children to root list
        if (z->child != nullptr) {
            Node* child = z->child;
            Node* start = child;
            // Iterate all children
            do {
                Node* nextChild = child->right;
                minNode->addSibling(child); // Move child to root list
                child->parent = nullptr;
                child = nextChild;
            } while (child != start);
        }

        // 2. Remove z from root list
        z->removeSelf();

        if (z == z->right) {
            // It was the only node
            minNode = nullptr;
        } else {
            minNode = z->right;
            consolidate(); // Re-balance the heap
        }
        numNodes--;
    }
    return z;
}

void FibonacciHeap::consolidate() {
    // CRITICAL MATH PART (Member 3)
    // We need an array to track trees of specific degrees.
    // Max degree is roughly log2(n) * 2. Size 50 is safe for < 10 million items.
    Node* A[50];
    for (int i = 0; i < 50; i++) A[i] = nullptr;

    // We need to iterate the root list.
    // NOTE: Because we are merging trees, the list changes AS we iterate.
    // We must capture the list into a temporary array or be very careful.
    // Simple strategy: Break the circular list into a linear chain for processing?
    // No, standard way: 
    
    // For this compile fix, we will skip the complex math.
    // TODO: MEMBER 3 MUST IMPLEMENT THIS LOGIC.
    // Leaving it empty allows the code to Compile, but sorting won't work perfectly yet.
}

void FibonacciHeap::decreaseKey(int id, int newPriority) {
    // TODO: Member 4 - Find node, decrease val, cut if heap violated
    std::cout << "LOG: decreaseKey called for ID " << id << std::endl;
}

// Recursion helpers for File I/O
void FibonacciHeap::saveToFile(std::string filename) {
    std::ofstream file(filename);
    if (!file.is_open()) return;

    if (minNode != nullptr) {
        Node* start = minNode;
        Node* current = start;
        do {
            _saveRecursive(current, file);
            current = current->right;
        } while (current != start && current != nullptr);
    }
    file.close();
}

void FibonacciHeap::_saveRecursive(Node* node, std::ofstream& file) {
    if (node == nullptr) return;
    file << node->id << " " << node->priority << " " << node->name << "\n";
    if (node->child != nullptr) {
        Node* start = node->child;
        Node* current = start;
        do {
            _saveRecursive(current, file);
            current = current->right;
        } while (current != start);
    }
}
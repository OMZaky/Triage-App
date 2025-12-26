#include "FibHeap.h"
#include <iostream>
#include <cmath> 
#include <fstream>

using namespace std;

// ==========================================
// FIBONACCI HEAP IMPLEMENTATION
// ==========================================

FibonacciHeap::FibonacciHeap() {
    minNode = nullptr;
    numNodes = 0;
    
    // Initialize lookup array manually
    for (int i = 0; i < MAX_PID; i++) {
        nodeLookup[i] = nullptr;
    }
}

FibonacciHeap::~FibonacciHeap() {
    // OS cleans up memory on exit.
}

void FibonacciHeap::insert(int id, int priority, int age, string name, string desc) {
    if (id < 0 || id >= MAX_PID) {
        cout << "Error: ID out of bounds." << endl;
        return;
    }

    Node* newNode = new Node(id, priority, age, name, desc);    

    if (minNode == nullptr) {
        minNode = newNode;
        minNode->left = minNode;
        minNode->right = minNode;
    } else {
        minNode->addSibling(newNode);
        if (newNode->priority < minNode->priority) {
            minNode = newNode;
        }
    }

    nodeLookup[id] = newNode;
    numNodes++;
}

Node* FibonacciHeap::peek() {
    return minNode;
}

Node* FibonacciHeap::extractMin() {
    Node* z = minNode;
    if (z != nullptr) {
        if (z->child != nullptr) {
            Node* child = z->child;
            Node* start = child;
            do {
                Node* nextChild = child->right;
                minNode->addSibling(child); 
                child->parent = nullptr;
                child = nextChild;
            } while (child != start);
        }

        // FIXED: Array Erasure (No .erase)
        nodeLookup[z->id] = nullptr;

        // CRITICAL FIX: Check if z is the only node BEFORE removeSelf changes z's pointers
        bool wasOnlyNode = (z == z->right);
        
        z->removeSelf();

        if (wasOnlyNode) {
            minNode = nullptr;
        } else {
            minNode = z->right;
            consolidate();
        }
        numNodes--;
    }
    return z;
}

void FibonacciHeap::link(Node* y, Node* x) {
    y->removeSelf(); // Remove y from root list
    x->addChild(y);  // Make y a child of x
    y->marked = false;
}

void FibonacciHeap::consolidate() {
    // OPTIMIZATION: Use fixed size array on stack (No 'new', No 'vector')
    // Max degree for N=1 Billion is < 50. Size 64 is infinite safety.
    const int MAX_DEGREE = 64;
    Node* A[MAX_DEGREE];
    for (int i = 0; i < MAX_DEGREE; i++) A[i] = nullptr;

    // 1. Count root nodes first to define the loop limit safely
    int rootCount = 0;
    if (minNode != nullptr) {
        rootCount = 1;
        Node* curr = minNode->right;
        while (curr != minNode) {
            rootCount++;
            curr = curr->right;
        }
    }

    // 2. Iterate exactly 'rootCount' times
    Node* x = minNode;
    for (int i = 0; i < rootCount; i++) {
        // CRITICAL: Save next pointer BEFORE linking/moving x
        Node* nextNode = x->right;
        
        int d = x->degree;
        // Safety clamp
        if (d >= MAX_DEGREE) d = MAX_DEGREE - 1;

        while (A[d] != nullptr) {
            Node* y = A[d];
            
            // Ensure x is the parent (smaller priority)
            if (x->priority > y->priority) {
                Node* temp = x;
                x = y;
                y = temp;
            }
            
            link(y, x);
            A[d] = nullptr;
            d++;
            if (d >= MAX_DEGREE) d = MAX_DEGREE - 1;
        }
        A[d] = x;
        
        // Move to the next node we saved earlier
        x = nextNode;
    }

    // 3. Reconstruct Root List from Array A
    minNode = nullptr;
    for (int i = 0; i < MAX_DEGREE; i++) {
        if (A[i] != nullptr) {
            if (minNode == nullptr) {
                minNode = A[i];
                minNode->left = minNode;
                minNode->right = minNode;
            } else {
                minNode->addSibling(A[i]);
                if (A[i]->priority < minNode->priority) {
                    minNode = A[i];
                }
            }
        }
    }
}

void FibonacciHeap::decreaseKey(Node* node, int newPriority) {
    node->priority = newPriority;
    Node* parent = node->parent;

    if (parent != nullptr && node->priority < parent->priority) {
        cut(node, parent);
        cascadingCut(parent);
    }

    if (node->priority < minNode->priority) {
        minNode = node;
    }
}

void FibonacciHeap::cut(Node* node, Node* parent) {
    parent->removeChild(node);
    minNode->addSibling(node);
    node->parent = nullptr;
    node->marked = false;
}

void FibonacciHeap::cascadingCut(Node* node) {
    Node* parent = node->parent;
    if (parent != nullptr) {
        if (!node->marked) {
            node->marked = true;
        } else {
            cut(node, parent);
            cascadingCut(parent);
        }
    }
}

void FibonacciHeap::updatePriority(int id, int newPriority) {
    if (id < 0 || id >= MAX_PID || nodeLookup[id] == nullptr) {
        cout << "Error: Patient ID " << id << " not found." << endl;
        return;
    }

    Node* target = nodeLookup[id];
    
    if (newPriority > target->priority) {
        cout << "Error: Cannot increase priority directly." << endl;
        return; 
    }

    decreaseKey(target, newPriority);
}

void FibonacciHeap::removePatient(int id) {
    if (id < 0 || id >= MAX_PID || nodeLookup[id] == nullptr) return;

    // Decrease to negative infinity (using -9999 as a proxy)
    updatePriority(id, -9999); 
    extractMin(); 
}

void FibonacciHeap::merge(FibonacciHeap& other) {
    if (other.minNode == nullptr) return;

    if (minNode == nullptr) {
        minNode = other.minNode;
        numNodes = other.numNodes;
    } else {
        Node* myRight = minNode->right;
        Node* otherLeft = other.minNode->left;

        minNode->right = other.minNode;
        other.minNode->left = minNode;

        myRight->left = otherLeft;
        otherLeft->right = myRight;

        if (other.minNode->priority < minNode->priority) {
            minNode = other.minNode;
        }
        numNodes += other.numNodes;
    }

    for (int i = 0; i < MAX_PID; i++) {
        if (other.nodeLookup[i] != nullptr) {
            nodeLookup[i] = other.nodeLookup[i];
        }
    }

    other.minNode = nullptr;
    other.numNodes = 0;
    for(int i=0; i < MAX_PID; i++) other.nodeLookup[i] = nullptr;
}

void FibonacciHeap::saveToFile(string filename) {
    ofstream file(filename);
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

void FibonacciHeap::_saveRecursive(Node* node, ofstream& file) {
    if (node == nullptr) return;

    file << node->id << " " 
         << node->priority << " " 
         << node->age << " " 
         << node->name << " " 
         << node->description << "\n";

    if (node->child != nullptr) {
        Node* start = node->child;
        Node* current = start;
        do {
            _saveRecursive(current, file);
            current = current->right;
        } while (current != start);
    }
}

int FibonacciHeap::getNumNodes() {
    return numNodes;
}


void FibonacciHeap::printAll() {
    // Iterate through nodeLookup array and print all active patients
    for (int i = 0; i < MAX_PID; i++) {
        if (nodeLookup[i] != nullptr) {
            Node* node = nodeLookup[i];
            std::cout << "LIST_DATA " << node->id << " " 
                      << node->priority << " " 
                      << node->age << " "
                      << node->name << " " 
                      << node->description << std::endl;
        }
    }
    std::cout.flush();
}
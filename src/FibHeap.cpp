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

void FibonacciHeap::insert(int id, int priority, int age, std::string name, std::string desc) {



Node* newNode = new Node(id, priority, age, name, desc);    

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

    nodeLookup[id] = newNode;

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

        nodeLookup.erase(minNode->id);

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

void FibonacciHeap::link(Node* y, Node* x) {
    // Remove y from root list
    y->removeSelf();
    
    // Make y a child of x
    x->addChild(y); // Ensure Node.cpp has addChild
    
    y->marked = false;
}

void FibonacciHeap::consolidate() {
    float phi = (1 + sqrt(5)) / 2;
    int maxDegree = (int)(log(numNodes) / log(phi)) + 1; // Approx max degree
    
    // Use vector instead of raw array for safety
    std::vector<Node*> A(maxDegree + 5, nullptr);

    // 1. We must iterate over the root list. 
    // Since the list changes as we link, we collect nodes into a static list first.
    std::vector<Node*> rootNodes;
    Node* x = minNode;
    if (x) {
        do {
            rootNodes.push_back(x);
            x = x->right;
        } while (x != minNode && x != nullptr);
    }

    // 2. Process every node in root list
    for (Node* w : rootNodes) {
        x = w;
        int d = x->degree;
        
        while (A[d] != nullptr) {
            Node* y = A[d];
            // Swap so x is always the smaller priority (parent)
            if (x->priority > y->priority) {
                Node* temp = x;
                x = y;
                y = temp;
            }
            link(y, x);
            A[d] = nullptr;
            d++;
        }
        A[d] = x;
    }

    // 3. Reconstruct Root List from Array A
    minNode = nullptr;
    for (Node* node : A) {
        if (node != nullptr) {
            if (minNode == nullptr) {
                minNode = node;
                minNode->left = minNode;
                minNode->right = minNode;
            } else {
                minNode->addSibling(node);
                if (node->priority < minNode->priority) {
                    minNode = node;
                }
            }
        }
    }
}

void FibonacciHeap::decreaseKey(Node* node, int newPriority) {
    node->priority = newPriority;
    Node* parent = node->parent;

    // If heap property is violated (child is now more urgent than parent)
    if (parent != nullptr && node->priority < parent->priority) {
        cut(node, parent);
        cascadingCut(parent);
    }

    // Update global min if needed
    if (node->priority < minNode->priority) {
        minNode = node;
    }
}

void FibonacciHeap::cut(Node* node, Node* parent) {
    // 1. Remove node from parent's child list
    parent->removeChild(node); // You need to ensure Node.cpp has this, or implement manual pointer logic here
    
    // 2. Add node to root list
    minNode->addSibling(node);
    
    // 3. Clear parent pointer and mark
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

// Merges 'other' heap into 'this' heap
void FibonacciHeap::merge(FibonacciHeap& other) {
    if (other.minNode == nullptr) return; // Other is empty

    if (minNode == nullptr) {
        // If we are empty, just steal their minNode
        minNode = other.minNode;
        numNodes = other.numNodes;
    } else {
        // 1. SPLICE the two circular linked lists together
        // Connect this->min->right to other->min->left
        Node* myRight = minNode->right;
        Node* otherLeft = other.minNode->left;

        minNode->right = other.minNode;
        other.minNode->left = minNode;

        myRight->left = otherLeft;
        otherLeft->right = myRight;

        // 2. Update Min Pointer if necessary
        if (other.minNode->priority < minNode->priority) {
            minNode = other.minNode;
        }
        
        // 3. Combine counts
        numNodes += other.numNodes;
    }

    // 4. Merge the lookup maps (so we can still find the new patients)
    // Note: This part is O(M) where M is the other heap size, but unavoidable if we want lookups.
    for (auto const& [id, node] : other.nodeLookup) {
        nodeLookup[id] = node;
    }

    // 5. Clear the other heap so it doesn't delete nodes when it dies
    other.minNode = nullptr;
    other.numNodes = 0;
    other.nodeLookup.clear();
}

// SAFETY WRAPPER: Checks if ID exists before trying to change it
void FibonacciHeap::updatePriority(int id, int newPriority) {
    if (nodeLookup.find(id) == nodeLookup.end()) {
        std::cout << "Error: Patient ID " << id << " not found." << std::endl;
        return;
    }

    Node* target = nodeLookup[id];
    
    // Standard Fibonacci limitation: You can usually only DECREASE (make more urgent).
    // If you need to INCREASE (make less urgent), the standard way is to 
    // delete and re-insert, but for this project, let's just focus on decrease.
    if (newPriority > target->priority) {
        std::cout << "Error: Cannot increase priority directly." << std::endl;
        return; 
    }

    decreaseKey(target, newPriority);
}

void FibonacciHeap::removePatient(int id) {
    if (nodeLookup.find(id) == nodeLookup.end()) return;

    // Step 1: Force them to be the most critical patient instantly
    // We use a reserved value like -9999 or simply min_int
    updatePriority(id, -9999); 

    // Step 2: Now they are at the root (minNode), so just extract them
    extractMin(); 
}


int FibonacciHeap::getNumNodes() {
    return numNodes;
}
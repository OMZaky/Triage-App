#include "FibHeap.h"
#include <iostream>
#include <cmath> 
#include <fstream>

// ==========================================
// 1. CUSTOM VECTOR STRUCT (Replaces std::vector)
// ==========================================
struct NodeVector {
    Node** data;
    int capacity;
    int size;

    NodeVector(int initCap = 20) {
        capacity = initCap;
        size = 0;
        data = new Node*[capacity];
    }

    ~NodeVector() {
        delete[] data;
    }

    void push_back(Node* val) {
        if (size == capacity) {
            // Resize: Double the capacity
            int newCap = capacity * 2;
            Node** newData = new Node*[newCap];
            for (int i = 0; i < size; i++) {
                newData[i] = data[i];
            }
            delete[] data;
            data = newData;
            capacity = newCap;
        }
        data[size] = val;
        size++;
    }

    Node* operator[](int index) {
        if (index < 0 || index >= size) return nullptr;
        return data[index];
    }
    
    int length() { return size; }
};

// ==========================================
// 2. FIBONACCI HEAP IMPLEMENTATION
// ==========================================

FibonacciHeap::FibonacciHeap() {
    minNode = nullptr;
    numNodes = 0;
    
    // FIXED: Manually initialize array (Maps do this auto, Arrays don't)
    for (int i = 0; i < MAX_PID; i++) {
        nodeLookup[i] = nullptr;
    }
}

FibonacciHeap::~FibonacciHeap() {
    // OS cleans up memory on exit. 
}

void FibonacciHeap::insert(int id, int priority, int age, std::string name, std::string desc) {
    // Safety check for Array bounds
    if (id < 0 || id >= MAX_PID) {
        cout << "Error: ID out of bounds (0-" << MAX_PID-1 << ")" << endl;
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

    // FIXED: Direct Array Assignment (No .insert)
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

        z->removeSelf();

        if (z == z->right) {
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
    y->removeSelf();
    x->addChild(y); 
    y->marked = false;
}

void FibonacciHeap::consolidate() {
    float phi = (1 + sqrt(5)) / 2;
    int maxDegree = (int)(log(numNodes) / log(phi)) + 1; 
    
    // FIXED: Use raw dynamic array instead of std::vector
    int arraySize = maxDegree + 10; // Buffer
    Node** A = new Node*[arraySize];
    for(int i = 0; i < arraySize; i++) A[i] = nullptr;

    // FIXED: Use custom NodeVector instead of std::vector
    NodeVector rootNodes;
    Node* start = minNode;
    if (start) {
        do {
            rootNodes.push_back(start);
            start = start->right;
        } while (start != minNode);
    }

    // Process Nodes
    for (int i = 0; i < rootNodes.length(); i++) {
        Node* w = rootNodes[i];
        Node* x = w;
        int d = x->degree;
        
        while (A[d] != nullptr) {
            Node* y = A[d];
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

    // Reconstruct
    minNode = nullptr;
    for (int i = 0; i < arraySize; i++) {
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
    delete[] A; // Clean up manual array
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

// FIXED: Use Array Bounds Check (No .find)
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

// FIXED: Use Array Bounds Check
void FibonacciHeap::removePatient(int id) {
    if (id < 0 || id >= MAX_PID || nodeLookup[id] == nullptr) return;

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

    // FIXED: Iterate Array Indices (No Map Iterator)
    for (int i = 0; i < MAX_PID; i++) {
        if (other.nodeLookup[i] != nullptr) {
            nodeLookup[i] = other.nodeLookup[i];
        }
    }

    // Reset other
    other.minNode = nullptr;
    other.numNodes = 0;
    // Clear other's lookup
    for(int i=0; i < MAX_PID; i++) other.nodeLookup[i] = nullptr;
}

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

int FibonacciHeap::getNumNodes() {
    return numNodes;
}
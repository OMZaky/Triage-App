#ifndef FIBHEAP_H
#define FIBHEAP_H

#include "Node.h"

class FibonacciHeap {
private:
    Node* minNode; // Pointer to the highest priority task
    int numNodes;

    // --- ALGORITHM HELPERS ---
    // Member 3: Merges trees of same degree
    void consolidate(); 
    
    // Member 3: Links tree 'y' as a child of tree 'x'
    void link(Node* y, Node* x);
    
    // Member 4: Cuts 'x' from 'y'
    void cut(Node* x, Node* y);
    
    // Member 4: Recursive cut up the tree
    void cascadingCut(Node* y);
    
    // Helper to find a node by ID (Manual DFS search)
    Node* findNode(Node* start, int id);

    void _saveRecursive(Node* node, std::ofstream& file);

public:
    FibonacciHeap();
    ~FibonacciHeap(); // Member 2: Must delete all nodes!

    int getNumNodes();

    // Member 2
void insert(int id, int priority, int age, std::string name, std::string desc);    

    // Member 2
    Node* peek(); 
    
    // Member 2 & 3
    Node* extractMin();
    
    // Member 4
    void decreaseKey(int id, int newPriority);

    void saveToFile(std::string filename);
};

#endif
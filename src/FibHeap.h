#ifndef FIBHEAP_H
#define FIBHEAP_H

#include <iostream>
#include <cmath>
#include <string>
#include <fstream>
#include "Node.h"

using namespace std;

// Maximum Patient ID allowed. 
const int MAX_PID = 10001; 

class FibonacciHeap {
private:
    Node* minNode;
    int numNodes;
    
    // REPLACEMENT FOR MAP: A raw array of pointers
    // Index = Patient ID, Value = Pointer to Node
    Node* nodeLookup[MAX_PID]; 

    // Internal Helpers
    void cut(Node* node, Node* parent);
    void cascadingCut(Node* node);
    void link(Node* y, Node* x);
    void decreaseKey(Node* node, int newPriority); 
    void _saveRecursive(Node* node, ofstream& file);
    
    // MISSING FUNCTION ADDED HERE:
    void consolidate(); 

public:
    FibonacciHeap();
    ~FibonacciHeap();

    // Main Functions
    void insert(int id, int priority, int age, string name, string desc);
    Node* peek();
    Node* extractMin();
    
    // Advanced Features
    void updatePriority(int id, int newPriority); 
    void removePatient(int id);                   
    void merge(FibonacciHeap& other);             
    
    int getNumNodes();
    void saveToFile(string filename);
};

#endif
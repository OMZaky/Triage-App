#ifndef FIBHEAP_H
#define FIBHEAP_H
#include "Node.h"
#include <unordered_map>


class FibonacciHeap {
private:
    Node* minNode; // Pointer to the highest priority task
    int numNodes;

    std::unordered_map<int, Node*> nodeLookup; // THE MAP
    
    Node* findNode(Node* start, int id);


    void consolidate(); 
    void cut(Node* node, Node* parent);
    void cascadingCut(Node* node);
    void link(Node* y, Node* x);
    void decreaseKey(Node* node, int newPriority); 
    void _saveRecursive(Node* node, std::ofstream& file);


public:
    FibonacciHeap();
    ~FibonacciHeap(); 

    int getNumNodes();


    Node* peek(); 
    Node* extractMin();
    
    void insert(int id, int priority, int age, std::string name, std::string desc);    
    void merge(FibonacciHeap& other);
    void removePatient(int id);
    void updatePriority(int id, int newPriority);
    void decreaseKey(int id, int newPriority);
    void saveToFile(std::string filename);
};

#endif
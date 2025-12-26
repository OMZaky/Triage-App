#ifndef NODE_H
#define NODE_H

#include <string>

// ASSIGNED TO: MEMBER 1
// The Building Block of the Heap
struct Node {
    int id;
    int priority;
    int age;            
    std::string name;
    std::string description; 

    // Pointers
    Node *left, *right, *parent, *child;
    
    int degree;         // Number of children
    bool marked;          // Lost a child since last made a child?

    // Constructor
Node(int _id, int _priority, int _age, std::string _name, std::string _desc);
    
    // --- CDLL Operations (Member 1 implements these in Node.cpp) ---
    // Adds 'other' node to the right of 'this' node
    void addSibling(Node* other);
    
    // Removes 'this' node from the list (re-links left and right)
    void removeSelf();

    void addChild(Node* newChild);
    void removeChild(Node* target);

};

#endif
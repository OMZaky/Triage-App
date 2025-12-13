#ifndef NODE_H
#define NODE_H

#include <string>

// ASSIGNED TO: MEMBER 1
// The Building Block of the Heap
struct Node {
    int id;
    int priority;       // Lower value = Higher urgency
    std::string name;   // Patient Name

    // Pointers for Circular Doubly Linked List
    Node* left;
    Node* right;

    // Pointers for Tree Hierarchy
    Node* parent;
    Node* child;

    int degree;         // Number of children
    bool mark;          // Lost a child since last made a child?

    // Constructor
    Node(int _id, int _priority, std::string _name);

    // --- CDLL Operations (Member 1 implements these in Node.cpp) ---
    // Adds 'other' node to the right of 'this' node
    void addSibling(Node* other);
    
    // Removes 'this' node from the list (re-links left and right)
    void removeSelf();
};

#endif
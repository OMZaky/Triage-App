#include "Node.h"

// ASSIGNED TO: MEMBER 1

Node::Node(int _id, int _priority, int _age, std::string _name, std::string _desc) {
    id = _id;
    priority = _priority;
    age = _age;          // <--- NEW
    name = _name;
    description = _desc; // <--- NEW
    
    // Pointers (Circle of 1)
    left = this;
    right = this;
    parent = nullptr;
    child = nullptr;
    degree = 0;
    mark = false;
}

void Node::addSibling(Node* other) {
    // TODO: Member 1 - Implement circular insertion logic
    // Logic: Insert 'other' between 'this' and 'this->right'
}

void Node::removeSelf() {
    // TODO: Member 1 - Implement circular deletion logic
    // Logic: Connect this->left to this->right, bypassing 'this'
}
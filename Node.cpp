#include "Node.h"

// ASSIGNED TO: MEMBER 1

Node::Node(int _id, int _priority, std::string _name) {
    id = _id;
    priority = _priority;
    name = _name;
    
    // Circular logic: Point to self initially
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
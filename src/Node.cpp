#include "Node.h"

// ASSIGNED TO: MEMBER 1

Node::Node(int _id, int _priority, int _age, std::string _name, std::string _desc) {
    id = _id;
    priority = _priority;
    age = _age;
    name = _name;
    description = _desc;
    
    // Initialize Circular Pointers (Point to self)
    left = this;
    right = this;
    parent = nullptr;
    child = nullptr;
    
    degree = 0;
    marked = false; 
}

void Node::addSibling(Node* other) {
    if (other == nullptr) return;

    // 1. Link other to current neighbors
    other->left = this;
    other->right = this->right;
    
    // 2. Link neighbors to other
    this->right->left = other;
    this->right = other;
    
    // 3. Siblings share the same parent
    other->parent = this->parent; 
}

void Node::removeSelf() {
    // 1. Connect left neighbor to right neighbor
    this->left->right = this->right;
    
    // 2. Connect right neighbor to left neighbor
    this->right->left = this->left;
    
    // (Optional safety) Reset own pointers so it doesn't point to old list
    this->left = this;
    this->right = this;
}

// --- NEW FUNCTIONS REQUIRED FOR FIB HEAP ---

void Node::addChild(Node* newChild) {
    if (newChild == nullptr) return;

    if (child == nullptr) {
        // First child: it forms a circle of one
        child = newChild;
        newChild->right = newChild;
        newChild->left = newChild;
        newChild->parent = this;
    } else {
        // Existing children: add as sibling to the current child pointer
        child->addSibling(newChild);
        newChild->parent = this;
    }
    degree++;
}

void Node::removeChild(Node* target) {
    if (target == nullptr || child == nullptr) return;

    // Special Case: If the target is the one our 'child' pointer points to
    if (child == target) {
        if (target->right == target) {
            // It was the ONLY child
            child = nullptr;
        } else {
            // There are others, just move the pointer to the neighbor
            child = target->right;
        }
    }

    target->removeSelf(); // Unlink from siblings
    target->parent = nullptr;
    target->marked = false; // Reset mark when cut
    degree--;
}
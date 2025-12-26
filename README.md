# 🏥 TriageOS: Critical Care Patient Flow System

![C++](https://img.shields.io/badge/Backend-C++17-blue.svg)
![Python](https://img.shields.io/badge/Frontend-Python%20Tkinter-yellow.svg)
![Algorithm](https://img.shields.io/badge/Data%20Structure-Fibonacci%20Heap-red.svg)
![License](https://img.shields.io/badge/License-MIT-green.svg)

**TriageOS** is a high-performance hybrid medical software solution designed to optimize Emergency Room (ER) throughput. It combines a raw **C++ Backend** (for $O(1)$ priority logic) with a modern **Python Dashboard** (for real-time vitals monitoring).

> **The Problem:** Hospital "bottlenecks" occur when critical patients are stuck behind less urgent cases.  
> **The Solution:** A mathematically optimal queuing system that instantly re-prioritizes patients based on live vitals.

---

## 🚀 Key Features

### 🏥 Medical Functionalities
* **Smart Triage Queue:** Automatically sorts patients based on severity (1=Critical, 10=Non-Urgent).
* **Dynamic Deterioration:** Instantly updates a patient's priority if their vitals crash (e.g., changing from Prio 4 to Prio 1).
* **Mass Casualty Protocol:** Instantly merges a secondary list (e.g., ambulance convoy) into the main queue without lag.
* **Live Vitals Monitor:** Visualizes Heart Rate (BPM), BP, and SpO2 with a real-time animated EKG graph.
* **LWBS Tracking:** Efficiently removes patients who "Leave Without Being Seen" to maintain queue accuracy.

### ⚙️ Technical Engineering
* **Fibonacci Heap Architecture:** Utilizes the advanced Fibonacci Heap data structure to achieve **$O(1)$** performance for critical operations.
* **No-STL Implementation:** Built strictly using **Raw C++ Arrays** and manual memory management (No `std::vector` or `std::map`).
* **Secure Authentication:** Implements a salted SHA-256 style hashing algorithm (DJB2) for secure login.
* **Hybrid Bridge:** Uses a custom `subprocess` pipeline to bridge Python visualization with C++ memory operations.

---

## 📂 Project Structure

```text
TriageOS/
├── src/                    # C++ Backend Source Code
│   ├── Auth.cpp            # Security & Hashing Logic
│   ├── FibHeap.cpp         # Core Fibonacci Heap & Custom Arrays
│   ├── Node.cpp            # Patient Node (Circular Linked Lists)
│   ├── System.cpp          # Command Processor
│   └── main.cpp            # Entry Point
│
├── medical_gui.py          # Python Frontend (The Dashboard)
├── users_db.txt            # Encrypted User Credentials
├── patients_data.txt       # Patient Persistence File
└── README.md               # Documentation



# 🏥 TriageOS: Advanced Patient Flow & Critical Care System

![Backend](https://img.shields.io/badge/Backend-C%2B%2B17-00599C?style=for-the-badge&logo=c%2B%2B&logoColor=white)
![Frontend](https://img.shields.io/badge/Frontend-Python_Tkinter-3776AB?style=for-the-badge&logo=python&logoColor=white)
![Architecture](https://img.shields.io/badge/Data_Structure-Fibonacci_Heap-FF4B4B?style=for-the-badge)
![License](https://img.shields.io/badge/License-MIT-green.svg?style=for-the-badge)

**TriageOS** is a hybrid medical software solution designed to solve the "ER Bottleneck" problem. It combines a **high-performance C++ backend** (optimized for mathematical sorting efficiency) with a **modern Python dashboard** (for real-time visualization).

Unlike standard hospital systems that use basic First-In-First-Out (FIFO) or simple Priority Queues, TriageOS utilizes a **Fibonacci Heap** data structure to achieve **$O(1)$ constant-time complexity** for critical operations, ensuring that patient care is never delayed by software lag during mass casualty surges.

---

## 🚀 Key Functionalities

### 🩺 Medical Features
* **Smart Triage Queue:** Automatically prioritizes patients based on the Emergency Severity Index (ESI) (1=Critical to 10=Non-Urgent).
* **Dynamic Deterioration Engine:** Allows instant re-triage. If a patient in the waiting room (Priority 4) suffers a cardiac arrest, their priority can be updated to Priority 1 instantly.
* **Mass Casualty "Merge" Protocol:** In the event of a disaster (e.g., bus crash), the system can merge a secondary list of incoming ambulance patients into the main hospital queue in **$O(1)$** time.
* **Live Vitals Monitor:** Visualizes real-time patient status including Heart Rate (BPM), Blood Pressure, and SpO2 with an animated EKG graph.
* **LWBS (Left Without Being Seen):** Efficiently handles patients who walk out, removing them from the queue to maintain accurate wait-time statistics.

### ⚙️ Technical Engineering
* **Hybrid Architecture:** Uses a custom `subprocess` bridge to allow Python to visualize low-level C++ memory operations in real-time.
* **"No-STL" Compliance:** Built strictly using **Raw C++ Arrays** and manual memory management.
    * *No `std::vector`:* Replaced with a custom `NodeVector` struct with dynamic resizing logic.
    * *No `std::unordered_map`:* Replaced with a Direct Address Table (`nodeLookup[10001]`) for instant $O(1)$ access without hash collisions.
* **Secure Authentication:** Implements a salted **DJB2 Hashing Algorithm** to secure user credentials (passwords are never stored in plain text).

---

## 📐 Algorithmic Efficiency

Why use a Fibonacci Heap? In a high-volume ER, seconds matter. Standard Binary Heaps slow down as the queue grows.

| Operation | Standard System (Binary Heap) | **TriageOS (Fibonacci Heap)** | Real-World Scenario |
| :--- | :--- | :--- | :--- |
| **Insert Patient** | $O(\log n)$ | **$O(1)$** (Instant) | 50 patients arrive at once during a surge. |
| **Update Priority** | $O(\log n)$ | **$O(1)$** (Instant) | A patient's appendix bursts while waiting. |
| **Merge Queues** | $O(n)$ | **$O(1)$** (Instant) | Integrating an ambulance convoy list. |
| **Discharge (Extract)** | $O(\log n)$ | **$O(\log n)$** | Doctor treats the next most critical patient. |

---

## 📂 Project Structure

```text
TriageOS/
├── src/                    # THE C++ ENGINE
│   ├── Auth.cpp            # Security & Hashing Logic
│   ├── Auth.h              # Header for Auth
│   ├── FibHeap.cpp         # The Core Fibonacci Heap Algorithms
│   ├── FibHeap.h           # Header for Heap
│   ├── Node.cpp            # Patient Logic (Circular Linked Lists)
│   ├── Node.h              # Header for Node
│   ├── System.cpp          # Command Processor & Bridge Logic
│   └── System.h            # Header for System
│
├── medical_gui.py          # THE PYTHON DASHBOARD (Frontend)
├── users_db.txt            # Encrypted User Database
├── patients_data.txt       # Patient Persistence File
└── README.md               # Documentation

# PROJECT OPTIMUS: Behavioral Intelligence & Interview Integrity

## 1. The Problem: The Modern Interview Integrity Crisis (The Pain Point)

In the post-pandemic world, remote hiring has become the industry standard. However, this has birthed a massive "Cheating Economy." The current pain points are:

*   **AI Overlays & Copilots**: Candidates use specialized AI tools that read the interview screen and provide real-time answers in a hidden overlay.
*   **The "Proxy" Interviewer**: Remote desktop tools allow a different person to take the technical test or interview while the candidate merely lips-syncs.
*   **Invasive Proctoring Failure**: Traditional proctoring (recording screen/webcam) is easily bypassed by external devices or virtual webcams, and it creates a hostile, "Big Brother" atmosphere for honest candidates.
*   **Metadata Blindness**: Most platforms only monitor the active tab. They are blind to background system activity, network requests to AI domains, and suspicious clipboard bursts.

**Project Optimus** solves this by moving beyond "recording" and into **Active Behavioral Intelligence.**

---

## 2. Proposed Solution: The "Invisible Shield" Architecture

Optimus is a multi-layered integrity platform that builds a **Behavioral Intelligence Fingerprint** of a candidate in real-time. Instead of just recording, it **routes, monitors, and analyzes** the very environment the candidate is working in.

### Core Solution Pillars:
1.  **Strict Environment Isolation**: Routes ALL system traffic through a secure, monitored AWS tunnel.
2.  **Metadata Intelligence**: Analyzes DNS and TLS traffic patterns to detect AI usage without reading private content.
3.  **Cross-Signal Correlation**: Uses an Anomaly Engine to find links between physical behavior (gaze) and digital behavior (network requests).

---

## 3. The Developer's Engineering Journey (The Creation Process)

The creation of Optimus was an iterative engineering challenge that required solving deep infrastructure and networking hurdles. Here is the developer's journey to the final solution:

### Step 1: Infrastructure & The Gateway Foundation
The first challenge was creating a "middle-man" that couldn't be bypassed. 
*   **Action**: Provisioned a hardened **AWS EC2 (Ubuntu 22.04)** gateway.
*   **Complexity**: Configured a specialized **WireGuard** interface. Unlike standard VPNs, this required a custom FastAPI backend to manage ephemeral keys and dynamic peer registration (`wg set`) for every new interview session.

### Step 2: The Network "Eyes" (Packet Extraction)
Passive monitoring isn't enough; the system needed to "see" traffic.
*   **Action**: Implemented a **PyShark/TShark** capture engine on the EC2 interface.
*   **The Breakthrough**: Discovered that different `tshark` versions provided inconsistent DNS field mappings (standard vs. nested). Developed a **Dynamic Field-Introspection** logic that handles nested `dns.queries` automatically, ensuring the system never misses a query regardless of the server environment.

### Step 3: Integrating the Brain (AI Enrichment)
A list of domain names is just data; we needed intelligence.
*   **Action**: Integrated the **Sarvam AI (LLM)** enrichment pipeline.
*   **Logic**: Built a multi-stage classification system:
    1.  **Rule-based**: Instant detection of known AI helpers.
    2.  **Intelligence Cache**: A local SQLite-backed search engine for rapid sub-millisecond lookups.
    3.  **LLM Deep Enrichment**: Using Sarvam AI to categorize unknown or obfuscated domains on the fly.

### Step 4: Building the "Armor" (The Desktop Client)
The transition from a simple browser extension to a full Desktop App was critical for OS-level integrity.
*   **Action**: Engineered the **Electron + Node.js** client.
*   **Bridge Logic**: Built a secure **Python-Node bridge** that allows a cross-platform desktop app to spawn and control the OS-level WireGuard tunnel via `wg-quick` or `wireguard.exe`, routing every single packet from the machine through the EC2 brain.

---

## 4. The Candidate's User Journey (The Experience)

### Stage 1: The Secure Onboarding
*   **Invitation**: The candidate receives an interview link and launches the **Optimus Desktop App**.
*   **Environment Check**: The app performs a "Process Fingerprint" to ensure no blacklisted tools (Remote Desktop, AI Overlays) are running.

### Stage 2: The Secure Session (The Tunnel)
*   **Handshake**: The candidate enters the session code. The app establishes a session-specific **WireGuard tunnel**.
*   **Native Experience**: The candidate uses their own IDE and browser, but the underlying network "pipe" is being intelligently monitored by the EC2 Gateway.

### Stage 3: Dynamic Detection & Closure
*   **Invisible Monitoring**: The Gateway analyzes traffic in the background. The interviewer sees a live **Integrity Score**.
*   **Insightful Closure**: Once finished, the tunnel is revoked, temporary OS configs are purged, and a comprehensive **Integrity Report** is generated for the HR team.

---

## 5. Tools & Technology Stack

| Layer | Technology | Role |
| :--- | :--- | :--- |
| **Desktop Shell** | **Electron (Node.js)** | Window management and bridge to OS logic. |
| **Secure Tunneling** | **WireGuard / wg-quick** | Full-system traffic routing. |
| **Gateway Backend** | **FastAPI (Python 3.12)** | Session lifecycle and API management on AWS. |
| **Traffic Capture** | **PyShark / TShark** | Metadata-level packet analysis (DNS/SNI). |
| **Categorization AI** | **Sarvam AI (2B Model)** | Real-time classification of unknown traffic. |
| **Infrastructure** | **AWS EC2** | High-performance Intelligence Gateway. |

---

## 6. Target Audience

*   **Tech Enterprises (FAANG level)**: Companies scaling remote technical interviews.
*   **Recruitment Agencies**: Firms requiring a verified quality-assurance layer.
*   **Gov & Defense Contractors**: Entities requiring maximum candidate integrity.

---
*Project Optimus: The Next Generation of Hiring Integrity.*

# Rigid Origami Thickener

A Python-based parametric CAD tool designed to convert theoretical 2D zero-thickness `.fold` files into physically 3D-printable rigid origami models. 

## 🤖 AI Onboarding Context
> **Note to AI Assistants:** If you are reading this, act as a senior CAD automation and computational geometry engineer. 
> 
> **Project Goal:** Translate 2D JSON `.fold` crease patterns into 3D printable solid bodies (STL/STEP) that account for material thickness, hinge kinematics, and collision avoidance.
> 
> **Tech Stack:**
> * **UI:** `customtkinter` (Modern, minimalist Tkinter wrapper).
> * **CAD Engine:** `build123d` (Boundary Representation / B-rep solid modeling). **Crucial constraint:** Do not suggest standard mesh libraries like `trimesh` or `open3d` for the core logic, as they fail at the complex booleans and chamfers required for thick-panel rigid origami. 
> * **Data Parsing:** Standard Python `json` library.
> 
> **Core Geometric Operations Required:**
> 1.  **Panel Extrusion:** Parse 2D coplanar vertices into wires, convert to faces, and extrude to user-defined thickness (Z).
> 2.  **Vertex Clearance Holes:** Identify internal vertices shared by 3 or more faces. Generate cylinders at these points and use Boolean Difference to cut stress-relief holes into the adjacent panels.
> 3.  **Crease Beveling (Collision Avoidance):**
>     * *Mountain Folds:* Select the top shared edge of the gap; apply a chamfer.
>     * *Valley Folds:* Select the bottom shared edge of the gap; apply a chamfer.
> 4.  **Hinge Generation:**
>     * *Living Hinge:* Generate a thin (0.2mm - 0.4mm) rectangular solid bridging the gap.
>     * *Print-in-Place:* Generate alternating interlocking knuckle cylinders along the crease vector, subtract alternating knuckles from respective panels, and generate a central pin.

---

## 📂 Project Architecture

The application follows a strict Separation of Concerns, isolating the UI from the heavy computational geometry.

origami_thickener/
│
├── src/                      
│   ├── __init__.py
│   ├── main.py               # Application entry point
│   │
│   ├── ui/
│   │   ├── __init__.py
│   │   └── app_window.py     # CustomTkinter layout and state management
│   │
│   ├── core/
│   │   ├── __init__.py
│   │   └── fold_parser.py    # Reads .fold JSON and formats vertex/face/edge data
│   │
│   ├── geometry/
│   │   ├── __init__.py
│   │   ├── panels.py         # Extrusion, vertex hole booleans, and edge chamfering
│   │   └── hinges.py         # Logic for bridging panels (Living vs. Print-in-Place)
│   │
│   └── export/
│       ├── __init__.py
│       └── mesh_export.py    # Handles outputting the final build123d assembly to STL/STEP
│
├── sample_files/             # Test .fold files
├── requirements.txt          # Dependencies (customtkinter, build123d)
└── README.md


## 🚀 Setup & Installation

1. Clone the repository and navigate to the project root.
2. Create a virtual environment:
   `python -m venv venv`
3. Activate the environment:
   * **Windows:** `venv\Scripts\activate`
   * **macOS/Linux:** `source venv/bin/activate`
4. Install dependencies:
   `pip install -r requirements.txt`
5. Run the application:
   `python src/main.py`

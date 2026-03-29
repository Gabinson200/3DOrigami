# src/ui/app_window.py
import customtkinter as ctk
import tkinter as tk
from tkinter import filedialog
import os

from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from matplotlib.figure import Figure
from mpl_toolkits.mplot3d.art3d import Poly3DCollection
from matplotlib.colors import LightSource
from stl import mesh

from src.core.fold_parser import FoldParser
from src.geometry.panels import PanelGenerator

ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("dark-blue")

class OrigamiThickenerUI(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("Rigid Origami Thickener")
        self.geometry("900x600")
        
        self.loaded_filepath = None
        self.fold_data = None
        self._build_ui()

    def _build_ui(self):
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)

        self.control_frame = ctk.CTkFrame(self, corner_radius=10, width=300)
        self.control_frame.grid(row=0, column=0, padx=20, pady=20, sticky="nsew")
        self.control_frame.grid_propagate(False)

        self.header_label = ctk.CTkLabel(self.control_frame, text="Origami to Solid", font=ctk.CTkFont(size=20, weight="bold"))
        self.header_label.pack(pady=(20, 10))

        self.btn_load = ctk.CTkButton(self.control_frame, text="Load .fold Pattern", command=self.load_file)
        self.btn_load.pack(pady=(10, 5))

        self.lbl_filename = ctk.CTkLabel(self.control_frame, text="No file selected", text_color="gray", font=ctk.CTkFont(size=12))
        self.lbl_filename.pack(pady=(0, 20))

        self.lbl_thickness = ctk.CTkLabel(self.control_frame, text="Panel Thickness (mm)")
        self.lbl_thickness.pack(anchor="w", padx=20)
        self.entry_thickness = ctk.CTkEntry(self.control_frame, justify="center")
        self.entry_thickness.insert(0, "3.0")
        self.entry_thickness.pack(pady=(0, 15), padx=20, fill="x")

        self.lbl_hinge = ctk.CTkLabel(self.control_frame, text="Hinge Topology")
        self.lbl_hinge.pack(anchor="w", padx=20)
        self.combo_hinge = ctk.CTkComboBox(self.control_frame, values=["Print-in-Place (Knuckle)", "Living Hinge (Bridged)"])
        self.combo_hinge.pack(pady=(0, 30), padx=20, fill="x")

        self.btn_generate = ctk.CTkButton(self.control_frame, text="Generate 3D Mesh", command=self.generate_mesh, height=40, font=ctk.CTkFont(weight="bold"))
        self.btn_generate.pack(pady=10, padx=20, fill="x")

        self.tabview = ctk.CTkTabview(self)
        self.tabview.grid(row=0, column=1, padx=(0, 20), pady=20, sticky="nsew")
        
        self.tab_2d = self.tabview.add("2D Pattern")
        self.tab_3d = self.tabview.add("3D Preview")

        self.canvas = tk.Canvas(self.tab_2d, bg="#1E1E1E", highlightthickness=0)
        self.canvas.pack(fill="both", expand=True)
        self.canvas.bind("<Configure>", self.on_canvas_resize)

        self.fig = Figure(figsize=(5, 5), dpi=100, facecolor='#2B2B2B')
        self.ax = self.fig.add_subplot(111, projection='3d')
        self.ax.set_facecolor('#2B2B2B')
        self.ax.axis('off') 
        
        self.canvas_3d = FigureCanvasTkAgg(self.fig, master=self.tab_3d)
        self.canvas_3d.get_tk_widget().pack(fill="both", expand=True)

    def load_file(self):
        filepath = filedialog.askopenfilename(filetypes=[("Fold Format", "*.fold"), ("JSON Files", "*.json")])
        if filepath:
            self.loaded_filepath = filepath
            self.lbl_filename.configure(text=os.path.basename(filepath), text_color="#00FF00")
            self.fold_data = FoldParser(self.loaded_filepath).parse()
            self.tabview.set("2D Pattern")
            self.draw_pattern()

    def on_canvas_resize(self, event):
        if self.fold_data:
            self.draw_pattern()

    def draw_pattern(self):
        self.canvas.delete("all")
        if not self.fold_data or not self.fold_data.get('vertices'): return

        vertices, edges, assignments = self.fold_data['vertices'], self.fold_data['edges'], self.fold_data['assignments']
        min_x, max_x = min(v[0] for v in vertices), max(v[0] for v in vertices)
        min_y, max_y = min(v[1] for v in vertices), max(v[1] for v in vertices)
        sw, sh = max(max_x - min_x, 1), max(max_y - min_y, 1)

        c_width, c_height = self.canvas.winfo_width(), self.canvas.winfo_height()
        scale = min((c_width - 80) / sw, (c_height - 80) / sh)
        off_x, off_y = (c_width - (sw * scale)) / 2, (c_height - (sh * scale)) / 2

        color_map = {'M': '#FF4444', 'V': '#4444FF', 'B': '#FFFFFF', 'U': '#888888', 'F': '#888888'}
        for idx, edge in enumerate(edges):
            v1, v2 = vertices[edge[0]], vertices[edge[1]]
            assign = assignments[idx] if idx < len(assignments) else 'U'
            self.canvas.create_line(
                off_x + (v1[0] - min_x) * scale, off_y + (max_y - v1[1]) * scale,
                off_x + (v2[0] - min_x) * scale, off_y + (max_y - v2[1]) * scale,
                fill=color_map.get(assign, '#888888'), width=2
            )

    def generate_mesh(self):
        if not self.fold_data:
            self.lbl_filename.configure(text="Please load a file first!", text_color="#FF4444")
            return
        
        self.btn_generate.configure(text="Generating...", state="disabled")
        self.update() 
        
        thickness = float(self.entry_thickness.get())
        
        generator = PanelGenerator(self.fold_data, thickness)
        assembly, stl_path = generator.generate_base_panels()
        
        self.render_3d_preview(stl_path, thickness)
        
        self.tabview.set("3D Preview") 
        self.btn_generate.configure(text="Generate 3D Mesh", state="normal")

    def render_3d_preview(self, stl_filepath, thickness):
        self.ax.clear()
        self.ax.axis('off')
        
        your_mesh = mesh.Mesh.from_file(stl_filepath)
        ls = LightSource(azdeg=315, altdeg=45)
        
        collection = Poly3DCollection(
            your_mesh.vectors, 
            facecolors='#DDDDDD',
            linewidths=0, 
            alpha=1.0,
            shade=True,
            lightsource=ls
        )
        self.ax.add_collection3d(collection)
        
        vertices = self.fold_data['vertices']
        edges = self.fold_data['edges']
        assignments = self.fold_data['assignments']
        
        for i, edge in enumerate(edges):
            if i >= len(assignments): continue
            
            assign = assignments[i]
            if assign in ['M', 'V']:
                v1 = vertices[edge[0]]
                v2 = vertices[edge[1]]
                
                # Align lines tightly to the flush faces
                if assign == 'M':
                    z = thickness + 0.05 
                    color = '#FF4444' # Red on top
                else:
                    z = -0.05
                    color = '#4444FF' # Blue on bottom
                    
                self.ax.plot(
                    [v1[0], v2[0]], 
                    [v1[1], v2[1]], 
                    [z, z], 
                    color=color, linewidth=2.5
                )
        
        # THE FIX: Real-World Aspect Ratio Locking
        all_x = [v[0] for v in vertices]
        all_y = [v[1] for v in vertices]
        
        min_x, max_x = min(all_x), max(all_x)
        min_y, max_y = min(all_y), max(all_y)
        
        self.ax.set_xlim(min_x, max_x)
        self.ax.set_ylim(min_y, max_y)
        self.ax.set_zlim(-2, thickness + 2)
        
        x_range = max_x - min_x
        y_range = max_y - min_y
        z_range = thickness + 4.0 
        
        # Force Matplotlib to render true physical proportions
        self.ax.set_box_aspect((x_range, y_range, z_range))
        
        self.canvas_3d.draw()

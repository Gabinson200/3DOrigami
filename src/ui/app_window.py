import customtkinter as ctk
import tkinter as tk
from tkinter import filedialog
import os
import threading
import numpy as np

from src.core.fold_parser import FoldParser
from src.geometry.panels import PanelGenerator

try:
    import pyvista as pv
except Exception:
    pv = None

ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("dark-blue")


class OrigamiThickenerUI(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("Rigid Origami Thickener")
        self.geometry("980x650")

        self.loaded_filepath = None
        self.fold_data = None

        self.current_stl_path = None
        self.current_thickness = None
        self.viewer_plotter = None
        self.viewer_thread = None

        self._build_ui()

    def _build_ui(self):
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)

        self.control_frame = ctk.CTkFrame(self, corner_radius=10, width=300)
        self.control_frame.grid(row=0, column=0, padx=20, pady=20, sticky="nsew")
        self.control_frame.grid_propagate(False)

        self.header_label = ctk.CTkLabel(
            self.control_frame,
            text="Origami to Solid",
            font=ctk.CTkFont(size=20, weight="bold")
        )
        self.header_label.pack(pady=(20, 10))

        self.btn_load = ctk.CTkButton(
            self.control_frame,
            text="Load .fold Pattern",
            command=self.load_file
        )
        self.btn_load.pack(pady=(10, 5))

        self.lbl_filename = ctk.CTkLabel(
            self.control_frame,
            text="No file selected",
            text_color="gray",
            font=ctk.CTkFont(size=12)
        )
        self.lbl_filename.pack(pady=(0, 20))

        self.lbl_thickness = ctk.CTkLabel(
            self.control_frame,
            text="Panel Thickness (mm)"
        )
        self.lbl_thickness.pack(anchor="w", padx=20)

        self.entry_thickness = ctk.CTkEntry(self.control_frame, justify="center")
        self.entry_thickness.insert(0, "3.0")
        self.entry_thickness.pack(pady=(0, 15), padx=20, fill="x")

        self.lbl_hinge = ctk.CTkLabel(self.control_frame, text="Hinge Topology")
        self.lbl_hinge.pack(anchor="w", padx=20)

        self.combo_hinge = ctk.CTkComboBox(
            self.control_frame,
            values=["Print-in-Place (Knuckle)", "Living Hinge (Bridged)"]
        )
        self.combo_hinge.pack(pady=(0, 15), padx=20, fill="x")

        self.switch_show_folds = ctk.CTkSwitch(
            self.control_frame,
            text="Show Fold Lines",
            command=self.refresh_external_preview
        )
        self.switch_show_folds.select()
        self.switch_show_folds.pack(pady=(0, 12), padx=20, anchor="w")

        self.btn_generate = ctk.CTkButton(
            self.control_frame,
            text="Generate 3D Mesh",
            command=self.generate_mesh,
            height=40,
            font=ctk.CTkFont(weight="bold")
        )
        self.btn_generate.pack(pady=10, padx=20, fill="x")

        self.btn_open_preview = ctk.CTkButton(
            self.control_frame,
            text="Open 3D Preview Window",
            command=self.open_external_preview,
            state="disabled"
        )
        self.btn_open_preview.pack(pady=(0, 10), padx=20, fill="x")

        self.tabview = ctk.CTkTabview(self)
        self.tabview.grid(row=0, column=1, padx=(0, 20), pady=20, sticky="nsew")

        self.tab_2d = self.tabview.add("2D Pattern")
        self.tab_3d = self.tabview.add("3D Preview")

        self.canvas = tk.Canvas(self.tab_2d, bg="#1E1E1E", highlightthickness=0)
        self.canvas.pack(fill="both", expand=True)
        self.canvas.bind("<Configure>", self.on_canvas_resize)

        preview_wrap = ctk.CTkFrame(self.tab_3d, corner_radius=0, fg_color="transparent")
        preview_wrap.pack(fill="both", expand=True, padx=20, pady=20)

        title = ctk.CTkLabel(
            preview_wrap,
            text="Interactive 3D Preview",
            font=ctk.CTkFont(size=22, weight="bold")
        )
        title.pack(pady=(10, 12))

        self.preview_status = ctk.CTkLabel(
            preview_wrap,
            text=(
                "Generate a mesh, then open the VTK/PyVista preview window.\n\n"
                "This avoids Matplotlib's 3D rendering artifacts and uses a real 3D renderer instead."
            ),
            justify="center"
        )
        self.preview_status.pack(pady=(0, 18))

        self.btn_open_preview_tab = ctk.CTkButton(
            preview_wrap,
            text="Open 3D Preview Window",
            command=self.open_external_preview,
            state="disabled",
            height=42
        )
        self.btn_open_preview_tab.pack(pady=(0, 18))

        self.preview_hint = ctk.CTkTextbox(preview_wrap, height=220)
        self.preview_hint.pack(fill="both", expand=True)
        self.preview_hint.insert(
            "1.0",
            "Why this uses a separate window:\n\n"
            "• The pip/binary VTK packages do not ship the old Tk rendering bridge needed by vtkTkRenderWindowInteractor on Windows.\n"
            "• A separate PyVista window still uses VTK underneath, but avoids the missing vtkRenderingTk DLL problem.\n"
            "• It also gives you real depth buffering, better shading, and no Matplotlib triangle flicker.\n\n"
            "Viewer controls:\n"
            "• Left drag: rotate\n"
            "• Middle drag / Shift+Left: pan\n"
            "• Scroll: zoom\n"
            "• Press r: reset camera\n"
        )
        self.preview_hint.configure(state="disabled")

    def load_file(self):
        filepath = filedialog.askopenfilename(
            filetypes=[("Fold Format", "*.fold"), ("JSON Files", "*.json")]
        )
        if filepath:
            self.loaded_filepath = filepath
            self.lbl_filename.configure(
                text=os.path.basename(filepath),
                text_color="#00FF00"
            )
            self.fold_data = FoldParser(self.loaded_filepath).parse()
            self.current_stl_path = None
            self.current_thickness = None
            self.btn_open_preview.configure(state="disabled")
            self.btn_open_preview_tab.configure(state="disabled")
            self.preview_status.configure(
                text="Pattern loaded. Generate a mesh to open the interactive 3D preview."
            )
            self.tabview.set("2D Pattern")
            self.draw_pattern()

    def on_canvas_resize(self, event):
        if self.fold_data:
            self.draw_pattern()

    def draw_pattern(self):
        self.canvas.delete("all")
        if not self.fold_data or not self.fold_data.get("vertices"):
            return

        vertices = self.fold_data["vertices"]
        edges = self.fold_data["edges"]
        assignments = self.fold_data["assignments"]

        min_x, max_x = min(v[0] for v in vertices), max(v[0] for v in vertices)
        min_y, max_y = min(v[1] for v in vertices), max(v[1] for v in vertices)
        sw, sh = max(max_x - min_x, 1), max(max_y - min_y, 1)

        c_width, c_height = self.canvas.winfo_width(), self.canvas.winfo_height()
        scale = min((c_width - 80) / sw, (c_height - 80) / sh)
        off_x = (c_width - (sw * scale)) / 2
        off_y = (c_height - (sh * scale)) / 2

        color_map = {
            "M": "#FF4444",
            "V": "#4444FF",
            "B": "#FFFFFF",
            "U": "#888888",
            "F": "#888888"
        }

        for idx, edge in enumerate(edges):
            v1, v2 = vertices[edge[0]], vertices[edge[1]]
            assign = assignments[idx] if idx < len(assignments) else "U"

            self.canvas.create_line(
                off_x + (v1[0] - min_x) * scale,
                off_y + (max_y - v1[1]) * scale,
                off_x + (v2[0] - min_x) * scale,
                off_y + (max_y - v2[1]) * scale,
                fill=color_map.get(assign, "#888888"),
                width=5
            )

    def generate_mesh(self):
        if not self.fold_data:
            self.lbl_filename.configure(
                text="Please load a file first!",
                text_color="#FF4444"
            )
            return

        try:
            thickness = float(self.entry_thickness.get())
        except ValueError:
            self.lbl_filename.configure(
                text="Thickness must be a number.",
                text_color="#FF4444"
            )
            return

        self.btn_generate.configure(text="Generating...", state="disabled")
        self.update_idletasks()

        try:
            generator = PanelGenerator(self.fold_data, thickness)
            _, stl_path = generator.generate_base_panels()

            self.current_stl_path = stl_path
            self.current_thickness = thickness

            self.btn_open_preview.configure(state="normal")
            self.btn_open_preview_tab.configure(state="normal")
            self.preview_status.configure(
                text="Mesh generated. Open the interactive 3D preview window."
            )
            self.tabview.set("3D Preview")
            self.refresh_external_preview(auto_open=True)
        finally:
            self.btn_generate.configure(text="Generate 3D Mesh", state="normal")

    def _build_fold_polydata(self, assignment_filter, z_value):
        if pv is None or not self.fold_data:
            return None

        vertices = self.fold_data["vertices"]
        edges = self.fold_data["edges"]
        assignments = self.fold_data["assignments"]

        points = []
        lines = []
        point_index = 0

        for i, edge in enumerate(edges):
            if i >= len(assignments) or assignments[i] != assignment_filter:
                continue

            v1 = vertices[edge[0]]
            v2 = vertices[edge[1]]
            points.append([v1[0], v1[1], z_value])
            points.append([v2[0], v2[1], z_value])
            lines.append([2, point_index, point_index + 1])
            point_index += 2

        if not points:
            return None

        poly = pv.PolyData()
        poly.points = np.array(points, dtype=float)
        poly.lines = np.array(lines, dtype=np.int64).ravel()
        return poly

    def _make_tube(self, poly, radius):
        if poly is None:
            return None
        return poly.tube(radius=radius, n_sides=18, capping=True)

    def _open_plotter(self):
        if pv is None:
            self.preview_status.configure(
                text="PyVista is not installed. Run: pip install pyvista"
            )
            return

        if not self.current_stl_path or not os.path.exists(self.current_stl_path):
            self.preview_status.configure(
                text="Generate a mesh first before opening the preview."
            )
            return

        try:
            solid = pv.read(self.current_stl_path)
        except Exception as exc:
            self.preview_status.configure(text=f"Could not open STL: {exc}")
            return

        pl = pv.Plotter(title="Origami Thickener Preview", window_size=(1100, 850))

        try:
            pl.enable_anti_aliasing("fxaa")
        except Exception:
            pass

        try:
            pl.enable_ssao(radius=0.04)
        except Exception:
            pass

        solid_actor = pl.add_mesh(
            solid,
            color="#d9d9d9",
            smooth_shading=True,
            split_sharp_edges=True,
            show_edges=False,
            specular=0.18,
            specular_power=18,
            ambient=0.20,
            diffuse=0.85,
        )

        if self.switch_show_folds.get() == 1 and self.current_thickness is not None:
            lift = max(0.30, 0.10 * float(self.current_thickness))
            tube_radius = max(0.35, 0.18 * float(self.current_thickness))
            halo_radius = tube_radius * 1.9

            m_poly = self._build_fold_polydata("M", float(self.current_thickness) + lift)
            v_poly = self._build_fold_polydata("V", -lift)

            m_halo = self._make_tube(m_poly, halo_radius)
            v_halo = self._make_tube(v_poly, halo_radius)
            m_tube = self._make_tube(m_poly, tube_radius)
            v_tube = self._make_tube(v_poly, tube_radius)

            if m_halo is not None:
                pl.add_mesh(m_halo, color="black", lighting=False)
            if v_halo is not None:
                pl.add_mesh(v_halo, color="black", lighting=False)
            if m_tube is not None:
                pl.add_mesh(m_tube, color="#ff3b30", lighting=False)
            if v_tube is not None:
                pl.add_mesh(v_tube, color="#2d7fff", lighting=False)

        pl.set_background("#2B2B2B")
        pl.add_axes(line_width=2, color="white")
        pl.show_grid(color="#666666")
        pl.camera_position = "iso"
        pl.camera.zoom(1.15)
        pl.show()

    def open_external_preview(self):
        if pv is None:
            self.preview_status.configure(
                text="PyVista is not installed. Run: pip install pyvista"
            )
            return

        self._open_plotter()

    def refresh_external_preview(self, auto_open=False):
        if auto_open and self.current_stl_path and pv is not None:
            self.after(100, self.open_external_preview)



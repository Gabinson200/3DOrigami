import customtkinter as ctk
import tkinter as tk
from tkinter import filedialog
import os
import numpy as np

from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from matplotlib.figure import Figure
from matplotlib.collections import LineCollection
from matplotlib.lines import Line2D
from mpl_toolkits.mplot3d.art3d import Poly3DCollection
from mpl_toolkits.mplot3d import proj3d
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

        self.current_stl_path = None
        self.current_thickness = None

        self.preview_vectors = None
        self.preview_bounds = None
        self.preview_m_lines = []
        self.preview_v_lines = []

        self.overlay_artists = []
        self._dragging_3d = False

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
            command=self._refresh_overlay_only
        )
        self.switch_show_folds.select()
        self.switch_show_folds.pack(pady=(0, 20), padx=20, anchor="w")

        self.btn_generate = ctk.CTkButton(
            self.control_frame,
            text="Generate 3D Mesh",
            command=self.generate_mesh,
            height=40,
            font=ctk.CTkFont(weight="bold")
        )
        self.btn_generate.pack(pady=10, padx=20, fill="x")

        self.tabview = ctk.CTkTabview(self)
        self.tabview.grid(row=0, column=1, padx=(0, 20), pady=20, sticky="nsew")

        self.tab_2d = self.tabview.add("2D Pattern")
        self.tab_3d = self.tabview.add("3D Preview")

        self.canvas = tk.Canvas(self.tab_2d, bg="#1E1E1E", highlightthickness=0)
        self.canvas.pack(fill="both", expand=True)
        self.canvas.bind("<Configure>", self.on_canvas_resize)

        self.fig = Figure(figsize=(5, 5), dpi=100, facecolor="#2B2B2B")
        self.fig.subplots_adjust(left=0, right=1, bottom=0, top=1)

        self.ax = self.fig.add_subplot(111, projection="3d")
        self.ax.set_facecolor("#2B2B2B")
        self.ax.axis("off")
        self.ax.view_init(elev=28, azim=-58)

        self.canvas_3d = FigureCanvasTkAgg(self.fig, master=self.tab_3d)
        self.canvas_3d.get_tk_widget().pack(fill="both", expand=True)

        self.canvas_3d.mpl_connect("button_press_event", self._on_3d_press)
        self.canvas_3d.mpl_connect("button_release_event", self._on_3d_release)
        self.canvas_3d.mpl_connect("resize_event", self._on_3d_resize)
        self.canvas_3d.mpl_connect("scroll_event", self._on_3d_scroll)

    def _on_3d_press(self, event):
        if event.inaxes == self.ax:
            self._dragging_3d = True
            self._clear_overlay()
            self.canvas_3d.draw_idle()

    def _on_3d_release(self, event):
        if self._dragging_3d:
            self._dragging_3d = False
            self._refresh_overlay_only()

    def _on_3d_resize(self, event):
        self._refresh_overlay_only()

    def _on_3d_scroll(self, event):
        self._refresh_overlay_only()

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
            self.preview_vectors = None
            self.preview_bounds = None
            self.preview_m_lines = []
            self.preview_v_lines = []

            self._clear_overlay()

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

    def _load_preview_mesh(self):
        if not self.current_stl_path or not os.path.exists(self.current_stl_path):
            return

        preview_mesh = mesh.Mesh.from_file(self.current_stl_path)
        self.preview_vectors = np.array(preview_mesh.vectors, copy=True)

        pts = self.preview_vectors.reshape(-1, 3)
        self.preview_bounds = (pts.min(axis=0), pts.max(axis=0))

        self._build_preview_line_cache()

    def _build_preview_line_cache(self):
        self.preview_m_lines = []
        self.preview_v_lines = []

        if not self.fold_data or self.current_thickness is None:
            return

        vertices = self.fold_data["vertices"]
        edges = self.fold_data["edges"]
        assignments = self.fold_data["assignments"]

        lift = max(0.6, 0.15 * float(self.current_thickness))
        top_z = float(self.current_thickness) + lift
        bottom_z = -lift

        for i, edge in enumerate(edges):
            if i >= len(assignments):
                continue

            assign = assignments[i]
            if assign not in ("M", "V"):
                continue

            v1 = vertices[edge[0]]
            v2 = vertices[edge[1]]

            segment = [
                (v1[0], v1[1], top_z if assign == "M" else bottom_z),
                (v2[0], v2[1], top_z if assign == "M" else bottom_z),
            ]

            if assign == "M":
                self.preview_m_lines.append(segment)
            else:
                self.preview_v_lines.append(segment)

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

            self._load_preview_mesh()
            self.update_3d_view()

            self.tabview.set("3D Preview")
        finally:
            self.btn_generate.configure(text="Generate 3D Mesh", state="normal")

    def _clear_overlay(self):
        for artist in self.overlay_artists:
            try:
                artist.remove()
            except Exception:
                pass
        self.overlay_artists = []

    def _project_segments_to_figure(self, segments):
        if not segments:
            return []

        projected = []

        for seg in segments:
            (x1, y1, z1), (x2, y2, z2) = seg

            x1p, y1p, _ = proj3d.proj_transform(x1, y1, z1, self.ax.get_proj())
            x2p, y2p, _ = proj3d.proj_transform(x2, y2, z2, self.ax.get_proj())

            p1_disp = self.ax.transData.transform((x1p, y1p))
            p2_disp = self.ax.transData.transform((x2p, y2p))

            p1_fig = self.fig.transFigure.inverted().transform(p1_disp)
            p2_fig = self.fig.transFigure.inverted().transform(p2_disp)

            projected.append([p1_fig, p2_fig])

        return projected

    def _add_overlay_collection(self, segments_2d, color, halo_color, halo_width, line_width):
        if not segments_2d:
            return

        halo = LineCollection(
            segments_2d,
            colors=[halo_color],
            linewidths=halo_width,
            capstyle="round",
            joinstyle="round",
            transform=self.fig.transFigure
        )
        halo.set_clip_on(False)

        line = LineCollection(
            segments_2d,
            colors=[color],
            linewidths=line_width,
            capstyle="round",
            joinstyle="round",
            transform=self.fig.transFigure
        )
        line.set_clip_on(False)

        self.fig.add_artist(halo)
        self.fig.add_artist(line)

        self.overlay_artists.append(halo)
        self.overlay_artists.append(line)

    def _draw_overlay_fold_lines(self):
        self._clear_overlay()

        if self.switch_show_folds.get() != 1:
            return

        m2d = self._project_segments_to_figure(self.preview_m_lines)
        v2d = self._project_segments_to_figure(self.preview_v_lines)

        self._add_overlay_collection(
            m2d,
            color="#FF3B30",
            halo_color=(0.02, 0.02, 0.02, 0.98),
            halo_width=8.0,
            line_width=4.5
        )

        self._add_overlay_collection(
            v2d,
            color="#2D7FFF",
            halo_color=(0.02, 0.02, 0.02, 0.98),
            halo_width=8.0,
            line_width=4.5
        )

    def _refresh_overlay_only(self):
        if self.preview_vectors is None:
            return
        self._draw_overlay_fold_lines()
        self.canvas_3d.draw_idle()

    def update_3d_view(self):
        if self.preview_vectors is None:
            self._load_preview_mesh()
        if self.preview_vectors is None:
            return

        self._clear_overlay()

        self.ax.clear()
        self.ax.set_facecolor("#2B2B2B")
        self.ax.axis("off")
        self.ax.view_init(elev=28, azim=-58)

        ls = LightSource(azdeg=315, altdeg=38)

        collection = Poly3DCollection(
            self.preview_vectors,
            facecolors=(0.86, 0.86, 0.86, 1.0),
            edgecolors=(0.0, 0.0, 0.0, 0.0),
            linewidths=0.0,
            antialiased=False,
            shade=True,
            lightsource=ls
        )
        self.ax.add_collection3d(collection)

        mins, maxs = self.preview_bounds
        dx, dy, dz = maxs - mins
        pad = max(1.0, 0.03 * max(dx, dy, dz, 1.0))

        self.ax.set_xlim(mins[0] - pad, maxs[0] + pad)
        self.ax.set_ylim(mins[1] - pad, maxs[1] + pad)
        self.ax.set_zlim(mins[2] - pad, maxs[2] + pad)

        self.ax.set_box_aspect((
            max(dx, 1.0),
            max(dy, 1.0),
            max(dz, 1.0)
        ))

        self._draw_overlay_fold_lines()
        self.canvas_3d.draw_idle()

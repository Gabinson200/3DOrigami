# src/core/fold_parser.py
import json

class FoldParser:
    def __init__(self, filepath):
        self.filepath = filepath
        self.vertices = []
        self.faces = []
        self.edges = []
        self.edge_assignments = []

    def parse(self):
        with open(self.filepath, 'r') as f:
            raw_data = json.load(f)

        raw_verts = raw_data.get("vertices_coords", [])

        # --- THE FIX: Scale theoretical 1x1 unit square to a physical 150mm print size ---
        if raw_verts:
            min_x = min(v[0] for v in raw_verts)
            max_x = max(v[0] for v in raw_verts)
            min_y = min(v[1] for v in raw_verts)
            max_y = max(v[1] for v in raw_verts)

            width = max_x - min_x
            height = max_y - min_y
            max_dim = max(width, height)

            scale = 150.0 / max_dim if max_dim > 0 else 1.0
            cx = (max_x + min_x) / 2.0
            cy = (max_y + min_y) / 2.0

            self.vertices = [[(v[0] - cx) * scale, (v[1] - cy) * scale] for v in raw_verts]
        else:
            self.vertices = []

        self.faces = raw_data.get("faces_vertices", [])
        self.edges = raw_data.get("edges_vertices", [])
        self.edge_assignments = raw_data.get("edges_assignment", [])

        return {
            "vertices": self.vertices,
            "faces": self.faces,
            "edges": self.edges,
            "assignments": self.edge_assignments
        }

from build123d import (
    BuildPart,
    BuildSketch,
    BuildLine,
    Polyline,
    make_face,
    extrude,
    Compound,
    export_stl,
    chamfer,
    Location,
    Locations,
    Cylinder,
)
import os


class PanelGenerator:
    def __init__(self, fold_data, thickness, hole_radius=3.5):
        self.fold_data = fold_data
        self.vertices = fold_data["vertices"]
        self.faces = fold_data["faces"]
        self.thickness = thickness
        self.hole_radius = hole_radius

        vertex_face_count = {i: 0 for i in range(len(self.vertices))}
        for face in self.faces:
            for vertex_idx in face:
                vertex_face_count[vertex_idx] += 1

        self.interior_indices = {
            v_idx for v_idx, count in vertex_face_count.items() if count >= 3
        }

    @staticmethod
    def _segment_key(p1, p2, ndigits=2):
        a = (round(float(p1[0]), ndigits), round(float(p1[1]), ndigits))
        b = (round(float(p2[0]), ndigits), round(float(p2[1]), ndigits))
        return (a, b) if a <= b else (b, a)

    def generate_base_panels(self):
        parts = []
        edges = self.fold_data["edges"]
        assignments = self.fold_data["assignments"]
        tol = 1e-2
        chamfer_amount = (self.thickness / 2.0) - 0.05

        m_segment_keys = set()
        v_segment_keys = set()
        for i, edge in enumerate(edges):
            if i >= len(assignments):
                continue
            assign = assignments[i]
            if assign not in ("M", "V"):
                continue
            key = self._segment_key(self.vertices[edge[0]], self.vertices[edge[1]])
            if assign == "M":
                m_segment_keys.add(key)
            else:
                v_segment_keys.add(key)

        for face_indices in self.faces:
            raw_coords = [(self.vertices[idx][0], self.vertices[idx][1]) for idx in face_indices]

            with BuildPart() as panel:
                with BuildSketch():
                    with BuildLine():
                        Polyline(*raw_coords, close=True)
                    make_face()

                extrude(amount=self.thickness, dir=(0, 0, 1))

                edges_to_chamfer = []
                for e in panel.edges():
                    verts = e.vertices()
                    if len(verts) != 2:
                        continue

                    p1, p2 = verts[0], verts[1]
                    edge_key = self._segment_key((p1.X, p1.Y), (p2.X, p2.Y))

                    if abs(p1.Z) < tol and abs(p2.Z) < tol:
                        if edge_key in m_segment_keys:
                            edges_to_chamfer.append(e)
                    elif abs(p1.Z - self.thickness) < tol and abs(p2.Z - self.thickness) < tol:
                        if edge_key in v_segment_keys:
                            edges_to_chamfer.append(e)

                if chamfer_amount > 0 and edges_to_chamfer:
                    chamfer(edges_to_chamfer, length=chamfer_amount)

            final_part = panel.part

            face_hole_indices = [idx for idx in face_indices if idx in self.interior_indices]
            if face_hole_indices:
                with BuildPart() as local_tool_builder:
                    with Locations(*[
                        Location((self.vertices[idx][0], self.vertices[idx][1], self.thickness / 2.0))
                        for idx in face_hole_indices
                    ]):
                        Cylinder(radius=self.hole_radius, height=self.thickness * 4)
                final_part -= local_tool_builder.part

            parts.append(final_part)

        assembly = Compound(children=parts)
        temp_filepath = os.path.abspath("temp_preview.stl")
        export_stl(assembly, temp_filepath)
        return assembly, temp_filepath

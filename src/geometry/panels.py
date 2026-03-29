# src/geometry/panels.py
from build123d import BuildPart, BuildSketch, Polyline, BuildLine, make_face, extrude, Compound, export_stl, chamfer
import os

class PanelGenerator:
    def __init__(self, fold_data, thickness):
        self.fold_data = fold_data
        self.vertices = fold_data['vertices']
        self.faces = fold_data['faces']
        self.thickness = thickness

    def generate_base_panels(self):
        parts = []
        
        # Target segments for precise coordinate matching
        m_segments = [] # Mountains -> Bottom V-groove
        v_segments = [] # Valleys -> Top V-groove
        
        edges = self.fold_data['edges']
        assignments = self.fold_data['assignments']
        
        for i, edge in enumerate(edges):
            if i >= len(assignments): continue
            assign = assignments[i]
            if assign in ['M', 'V']:
                v1 = self.vertices[edge[0]]
                v2 = self.vertices[edge[1]]
                if assign == 'M':
                    m_segments.append((v1, v2))
                elif assign == 'V':
                    v_segments.append((v1, v2))

        TOL = 1e-2 
        chamfer_amount = (self.thickness / 2.0) - 0.05 

        def is_match(p1, p2, segments):
            for seg in segments:
                sv1, sv2 = seg
                # Match endpoints in either direction
                match_1 = abs(p1.X - sv1[0]) < TOL and abs(p1.Y - sv1[1]) < TOL and abs(p2.X - sv2[0]) < TOL and abs(p2.Y - sv2[1]) < TOL
                match_2 = abs(p1.X - sv2[0]) < TOL and abs(p1.Y - sv2[1]) < TOL and abs(p2.X - sv1[0]) < TOL and abs(p2.Y - sv1[1]) < TOL
                if match_1 or match_2: return True
            return False

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
                    if len(verts) != 2: continue
                    p1, p2 = verts[0], verts[1]
                    
                    # Bottom edges (Z=0) match to Mountains
                    if abs(p1.Z) < TOL and abs(p2.Z) < TOL:
                        if is_match(p1, p2, m_segments):
                            edges_to_chamfer.append(e)
                            
                    # Top edges (Z=thickness) match to Valleys
                    elif abs(p1.Z - self.thickness) < TOL and abs(p2.Z - self.thickness) < TOL:
                        if is_match(p1, p2, v_segments):
                            edges_to_chamfer.append(e)
                
                if chamfer_amount > 0 and edges_to_chamfer:
                    chamfer(edges_to_chamfer, length=chamfer_amount)
                
            parts.append(panel.part)
            
        assembly = Compound(children=parts)
        temp_filepath = os.path.abspath("temp_preview.stl")
        export_stl(assembly, temp_filepath)
        
        return assembly, temp_filepath

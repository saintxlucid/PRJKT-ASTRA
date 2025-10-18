"""
ASTRA 3D Neural Browser
Desktop visualization of memory graph using PySide6 and Qt3D

Features:
- 3D node/edge rendering of memory graph
- Real-time pulsing for active memories
- Mode-based color overlays
- Interactive camera controls
- Memory detail inspection
"""

import sys
from pathlib import Path
from typing import Dict, List, Optional
import json

# Add project root to path
project_root = Path(__file__).parent.parent.parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

try:
    from PySide6.QtCore import Qt, QTimer, QPointF, QUrl, Signal, Slot
    from PySide6.QtWidgets import (
        QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
        QLabel, QPushButton, QSlider, QTextEdit, QSplitter, QGroupBox
    )
    from PySide6.QtGui import QVector3D, QColor, QQuaternion
    from PySide6.Qt3DCore import Qt3DCore
    from PySide6.Qt3DRender import Qt3DRender
    from PySide6.Qt3DExtras import Qt3DExtras
    from PySide6.Qt3DInput import Qt3DInput
except ImportError:
    print("❌ PySide6 not installed. Install with: pip install PySide6")
    sys.exit(1)

try:
    from src.astra.visualization.memory_graph_service import (
        MemoryGraphService, MemoryNode, MemoryEdge
    )
except ImportError:
    from astra.visualization.memory_graph_service import (
        MemoryGraphService, MemoryNode, MemoryEdge
    )


class NeuralBrowserWindow(QMainWindow):
    """Main window for 3D neural browser"""
    
    def __init__(self):
        super().__init__()
        
        self.setWindowTitle("ASTRA 3D Neural Browser - 333 ∞")
        self.setGeometry(100, 100, 1400, 900)
        
        # Graph data
        self.graph_service = MemoryGraphService()
        self.nodes: List[MemoryNode] = []
        self.edges: List[MemoryEdge] = []
        
        # 3D entities
        self.node_entities: Dict[str, Qt3DCore.QEntity] = {}
        self.edge_entities: List[Qt3DCore.QEntity] = []
        
        # UI state
        self.selected_node: Optional[MemoryNode] = None
        self.pulse_timer: Optional[QTimer] = None
        self.pulse_phase = 0.0
        
        self._init_ui()
        self._load_graph()
        self._start_pulse_animation()
    
    def _init_ui(self):
        """Initialize UI layout"""
        # Central widget with splitter
        central = QWidget()
        self.setCentralWidget(central)
        
        layout = QHBoxLayout(central)
        
        # Splitter: 3D view | sidebar
        splitter = QSplitter(Qt.Horizontal)
        layout.addWidget(splitter)
        
        # Left: 3D view
        self.view_3d = self._create_3d_view()
        splitter.addWidget(self.view_3d)
        
        # Right: sidebar
        sidebar = self._create_sidebar()
        splitter.addWidget(sidebar)
        
        # Set splitter sizes (80% 3D, 20% sidebar)
        splitter.setSizes([1120, 280])
        
        # Status bar
        self.statusBar().showMessage("Ready - Load graph to begin")
    
    def _create_3d_view(self) -> Qt3DExtras.Qt3DWindow:
        """Create Qt3D rendering view"""
        # Create 3D window
        view = Qt3DExtras.Qt3DWindow()
        view.defaultFrameGraph().setClearColor(QColor(10, 10, 20))  # Dark space
        
        # Root entity
        self.root_entity = Qt3DCore.QEntity()
        
        # Camera
        camera = view.camera()
        camera.lens().setPerspectiveProjection(45.0, 16.0/9.0, 0.1, 1000.0)
        camera.setPosition(QVector3D(0, 30, 100))
        camera.setViewCenter(QVector3D(0, 0, 0))
        
        # Camera controller
        self.cam_controller = Qt3DExtras.QOrbitCameraController(self.root_entity)
        self.cam_controller.setLinearSpeed(50.0)
        self.cam_controller.setLookSpeed(180.0)
        self.cam_controller.setCamera(camera)
        
        # Light
        light_entity = Qt3DCore.QEntity(self.root_entity)
        light = Qt3DRender.QPointLight(light_entity)
        light.setColor(QColor(255, 255, 255))
        light.setIntensity(1.0)
        light_entity.addComponent(light)
        
        light_transform = Qt3DCore.QTransform(light_entity)
        light_transform.setTranslation(QVector3D(0, 50, 100))
        light_entity.addComponent(light_transform)
        
        # Set root entity
        view.setRootEntity(self.root_entity)
        
        # Wrap in container widget
        container = QWidget.createWindowContainer(view)
        container.setMinimumSize(800, 600)
        
        return container
    
    def _create_sidebar(self) -> QWidget:
        """Create right sidebar with controls and info"""
        sidebar = QWidget()
        sidebar.setMaximumWidth(350)
        
        layout = QVBoxLayout(sidebar)
        
        # Title
        title = QLabel("🧠 ASTRA Neural Browser")
        title.setStyleSheet("font-size: 16px; font-weight: bold; color: #8866ff;")
        layout.addWidget(title)
        
        # Sacred code
        sacred = QLabel("333 ∞")
        sacred.setStyleSheet("font-size: 14px; color: #ff66ff; margin-bottom: 10px;")
        sacred.setAlignment(Qt.AlignCenter)
        layout.addWidget(sacred)
        
        # Controls group
        controls_group = QGroupBox("Controls")
        controls_layout = QVBoxLayout()
        
        # Load button
        load_btn = QPushButton("🔄 Refresh Graph")
        load_btn.clicked.connect(self._load_graph)
        controls_layout.addWidget(load_btn)
        
        # Node limit slider
        slider_layout = QVBoxLayout()
        slider_label = QLabel("Max Nodes: 100")
        self.node_slider = QSlider(Qt.Horizontal)
        self.node_slider.setMinimum(10)
        self.node_slider.setMaximum(500)
        self.node_slider.setValue(100)
        self.node_slider.valueChanged.connect(
            lambda v: slider_label.setText(f"Max Nodes: {v}")
        )
        slider_layout.addWidget(slider_label)
        slider_layout.addWidget(self.node_slider)
        controls_layout.addLayout(slider_layout)
        
        # Similarity threshold
        sim_layout = QVBoxLayout()
        sim_label = QLabel("Similarity: 0.30")
        self.sim_slider = QSlider(Qt.Horizontal)
        self.sim_slider.setMinimum(10)
        self.sim_slider.setMaximum(90)
        self.sim_slider.setValue(30)
        self.sim_slider.valueChanged.connect(
            lambda v: sim_label.setText(f"Similarity: {v/100:.2f}")
        )
        sim_layout.addWidget(sim_label)
        sim_layout.addWidget(self.sim_slider)
        controls_layout.addLayout(sim_layout)
        
        controls_group.setLayout(controls_layout)
        layout.addWidget(controls_group)
        
        # Stats group
        stats_group = QGroupBox("Graph Statistics")
        stats_layout = QVBoxLayout()
        
        self.stats_label = QLabel("No graph loaded")
        self.stats_label.setStyleSheet("font-family: monospace;")
        stats_layout.addWidget(self.stats_label)
        
        stats_group.setLayout(stats_layout)
        layout.addWidget(stats_group)
        
        # Active modes group
        modes_group = QGroupBox("🎯 Operational Modes")
        modes_layout = QVBoxLayout()
        
        self.mode_labels = {}
        for mode in ["Music", "Film", "Cognition", "Emotion Coach", "Empire Builder", "Dream"]:
            label = QLabel(f"○ {mode}")
            label.setStyleSheet("color: #666;")
            self.mode_labels[mode] = label
            modes_layout.addWidget(label)
        
        modes_group.setLayout(modes_layout)
        layout.addWidget(modes_group)
        
        # Memory detail group
        detail_group = QGroupBox("Memory Detail")
        detail_layout = QVBoxLayout()
        
        self.detail_text = QTextEdit()
        self.detail_text.setReadOnly(True)
        self.detail_text.setMaximumHeight(200)
        self.detail_text.setPlaceholderText("Click a node to view details...")
        detail_layout.addWidget(self.detail_text)
        
        detail_group.setLayout(detail_layout)
        layout.addWidget(detail_group)
        
        # Stretch to push everything up
        layout.addStretch()
        
        return sidebar
    
    def _load_graph(self):
        """Load memory graph from service"""
        self.statusBar().showMessage("Loading memory graph...")
        
        # Get parameters
        max_nodes = self.node_slider.value()
        similarity = self.sim_slider.value() / 100.0
        
        # Build graph
        try:
            self.nodes, self.edges = self.graph_service.build_graph(
                max_nodes=max_nodes,
                similarity_threshold=similarity,
                include_temporal_edges=True
            )
            
            # Update stats
            self._update_stats()
            
            # Render graph
            self._render_graph()
            
            self.statusBar().showMessage(
                f"Loaded {len(self.nodes)} nodes, {len(self.edges)} edges"
            )
            
        except Exception as e:
            self.statusBar().showMessage(f"Error loading graph: {e}")
            print(f"❌ Error: {e}")
    
    def _update_stats(self):
        """Update statistics display"""
        # Count by type
        by_type = {}
        for node in self.nodes:
            by_type[node.memory_type] = by_type.get(node.memory_type, 0) + 1
        
        stats_text = f"Nodes: {len(self.nodes)}\n"
        stats_text += f"Edges: {len(self.edges)}\n\n"
        stats_text += "By Type:\n"
        for mem_type, count in by_type.items():
            stats_text += f"  {mem_type}: {count}\n"
        
        self.stats_label.setText(stats_text)
    
    def _render_graph(self):
        """Render graph in 3D view"""
        # Clear existing entities
        for entity in self.node_entities.values():
            entity.setParent(None)
        for entity in self.edge_entities:
            entity.setParent(None)
        
        self.node_entities.clear()
        self.edge_entities.clear()
        
        # Render nodes
        for node in self.nodes:
            entity = self._create_node_entity(node)
            self.node_entities[node.id] = entity
        
        # Render edges
        for edge in self.edges:
            entity = self._create_edge_entity(edge)
            self.edge_entities.append(entity)
        
        print(f"   ✓ Rendered {len(self.node_entities)} nodes and {len(self.edge_entities)} edges")
    
    def _create_node_entity(self, node: MemoryNode) -> Qt3DCore.QEntity:
        """Create 3D entity for a memory node"""
        entity = Qt3DCore.QEntity(self.root_entity)
        
        # Sphere mesh
        mesh = Qt3DExtras.QSphereMesh()
        mesh.setRadius(node.size)
        mesh.setRings(16)
        mesh.setSlices(16)
        
        # Material
        material = Qt3DExtras.QPhongMaterial()
        color = QColor.fromRgbF(*node.color)
        material.setDiffuse(color)
        material.setAmbient(color.darker(150))
        material.setSpecular(QColor(255, 255, 255))
        material.setShininess(50.0)
        
        # Transform
        transform = Qt3DCore.QTransform()
        transform.setTranslation(QVector3D(*node.position))
        
        # Add components
        entity.addComponent(mesh)
        entity.addComponent(material)
        entity.addComponent(transform)
        
        # Store node reference
        entity.setProperty("node_id", node.id)
        
        return entity
    
    def _create_edge_entity(self, edge: MemoryEdge) -> Qt3DCore.QEntity:
        """Create 3D entity for an edge"""
        # Find node positions
        source_node = next((n for n in self.nodes if n.id == edge.source_id), None)
        target_node = next((n for n in self.nodes if n.id == edge.target_id), None)
        
        if not source_node or not target_node:
            return None
        
        entity = Qt3DCore.QEntity(self.root_entity)
        
        # Cylinder mesh (line between nodes)
        mesh = Qt3DExtras.QCylinderMesh()
        mesh.setRadius(0.1 * edge.weight)
        mesh.setLength(1.0)  # Will scale via transform
        mesh.setRings(2)
        mesh.setSlices(8)
        
        # Material
        material = Qt3DExtras.QPhongMaterial()
        material.setDiffuse(QColor(80, 80, 120, 100))  # Semi-transparent
        
        # Calculate position and orientation
        source_pos = QVector3D(*source_node.position)
        target_pos = QVector3D(*target_node.position)
        
        midpoint = (source_pos + target_pos) / 2.0
        direction = target_pos - source_pos
        length = direction.length()
        
        transform = Qt3DCore.QTransform()
        transform.setTranslation(midpoint)
        transform.setScale(length)
        
        # Rotation to align cylinder with direction
        # (Simplified - may need quaternion calculation for accuracy)
        
        # Add components
        entity.addComponent(mesh)
        entity.addComponent(material)
        entity.addComponent(transform)
        
        return entity
    
    def _start_pulse_animation(self):
        """Start animation timer for pulsing active nodes"""
        self.pulse_timer = QTimer()
        self.pulse_timer.timeout.connect(self._update_pulse)
        self.pulse_timer.start(50)  # 20 FPS
    
    def _update_pulse(self):
        """Update pulse animation for active nodes"""
        import math
        
        self.pulse_phase += 0.1
        if self.pulse_phase > 2 * math.pi:
            self.pulse_phase = 0.0
        
        pulse_scale = 1.0 + 0.2 * math.sin(self.pulse_phase)
        
        # Update active nodes
        for node in self.nodes:
            if node.active:
                entity = self.node_entities.get(node.id)
                if entity:
                    # Get transform component
                    for component in entity.components():
                        if isinstance(component, Qt3DCore.QTransform):
                            # Pulse scale
                            component.setScale(node.size * pulse_scale)
    
    def activate_mode(self, mode: str):
        """Activate an operational mode"""
        if mode in self.mode_labels:
            self.mode_labels[mode].setText(f"● {mode}")
            self.mode_labels[mode].setStyleSheet("color: #66ff66; font-weight: bold;")
    
    def deactivate_mode(self, mode: str):
        """Deactivate an operational mode"""
        if mode in self.mode_labels:
            self.mode_labels[mode].setText(f"○ {mode}")
            self.mode_labels[mode].setStyleSheet("color: #666;")
    
    def select_node(self, node_id: str):
        """Select a node and show details"""
        node = next((n for n in self.nodes if n.id == node_id), None)
        if not node:
            return
        
        self.selected_node = node
        
        # Show details
        detail_html = f"""
        <h3 style="color: #8866ff;">{node.memory_type.upper()}</h3>
        <p><strong>Importance:</strong> {node.importance:.2f}</p>
        <p><strong>Timestamp:</strong> {node.timestamp or 'N/A'}</p>
        <hr>
        <p>{node.content}</p>
        """
        
        if node.metadata:
            detail_html += "<hr><p><strong>Metadata:</strong></p><ul>"
            for key, value in node.metadata.items():
                detail_html += f"<li><strong>{key}:</strong> {value}</li>"
            detail_html += "</ul>"
        
        self.detail_text.setHtml(detail_html)


def main():
    """Launch neural browser"""
    app = QApplication(sys.argv)
    
    # Set dark theme
    app.setStyle("Fusion")
    
    # Main window
    window = NeuralBrowserWindow()
    window.show()
    
    sys.exit(app.exec())


if __name__ == "__main__":
    main()

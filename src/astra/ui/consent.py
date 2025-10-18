"""
ASTRA Consent UI
PyQt6-based consent dialogs for ASTRA actions.
Created: October 16, 2025
"""
from typing import Optional, List, Dict, Any
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel,
    QPushButton, QTextEdit, QCheckBox, QFrame
)
from PyQt6.QtCore import Qt, pyqtSignal
import json
import structlog

logger = structlog.get_logger()

class ConsentDialog(QDialog):
    """Dialog for obtaining user consent for actions"""
    def __init__(
        self,
        action: Dict[str, Any],
        consent_level: str,
        parent=None
    ):
        super().__init__(parent)
        self.action = action
        self.consent_level = consent_level
        self.setup_ui()
        
    def setup_ui(self):
        """Setup dialog UI"""
        self.setWindowTitle("ASTRA Action Consent")
        self.setMinimumWidth(500)
        
        layout = QVBoxLayout()
        
        # Header
        header = QLabel("Action Requires Consent")
        header.setStyleSheet("font-size: 14pt; font-weight: bold;")
        layout.addWidget(header)
        
        # Consent level indicator
        level_label = QLabel(f"Consent Level: {self.consent_level}")
        level_label.setStyleSheet(
            f"color: {'red' if self.consent_level == 'explicit_with_backup' else 'orange'};"
        )
        layout.addWidget(level_label)
        
        # Action details
        details = QFrame()
        details.setFrameStyle(QFrame.Shape.Box | QFrame.Shadow.Sunken)
        details_layout = QVBoxLayout()
        
        tool_label = QLabel(f"Tool: {self.action['tool']}")
        tool_label.setStyleSheet("font-weight: bold;")
        details_layout.addWidget(tool_label)
        
        args_text = QTextEdit()
        args_text.setPlainText(
            json.dumps(self.action["args"], indent=2)
        )
        args_text.setReadOnly(True)
        args_text.setMaximumHeight(100)
        details_layout.addWidget(args_text)
        
        if "alignment_note" in self.action:
            note = QLabel(f"Rationale: {self.action['alignment_note']}")
            note.setWordWrap(True)
            details_layout.addWidget(note)
            
        details.setLayout(details_layout)
        layout.addWidget(details)
        
        # Safety measures
        if self.consent_level == "explicit_with_backup":
            backup_note = QLabel(
                "🔒 A backup will be created before this action"
            )
            backup_note.setStyleSheet("color: green;")
            layout.addWidget(backup_note)
            
        # Confirmation checkbox
        self.confirm_check = QCheckBox(
            "I understand the implications of this action"
        )
        layout.addWidget(self.confirm_check)
        
        # Buttons
        button_layout = QHBoxLayout()
        
        self.approve_btn = QPushButton("Approve")
        self.approve_btn.setEnabled(False)
        self.approve_btn.clicked.connect(self.accept)
        
        cancel_btn = QPushButton("Cancel")
        cancel_btn.clicked.connect(self.reject)
        
        button_layout.addWidget(self.approve_btn)
        button_layout.addWidget(cancel_btn)
        
        layout.addLayout(button_layout)
        self.setLayout(layout)
        
        # Connect checkbox to button enable
        self.confirm_check.stateChanged.connect(self.toggle_approve)
        
    def toggle_approve(self, state):
        """Toggle approve button based on checkbox"""
        self.approve_btn.setEnabled(state == Qt.CheckState.Checked)

class BatchConsentDialog(QDialog):
    """Dialog for batch approving multiple actions"""
    def __init__(
        self,
        actions: List[Dict[str, Any]],
        parent=None
    ):
        super().__init__(parent)
        self.actions = actions
        self.setup_ui()
        
    def setup_ui(self):
        """Setup dialog UI"""
        self.setWindowTitle("ASTRA Batch Action Consent")
        self.setMinimumWidth(600)
        
        layout = QVBoxLayout()
        
        # Header
        header = QLabel(f"Review {len(self.actions)} Actions")
        header.setStyleSheet("font-size: 14pt; font-weight: bold;")
        layout.addWidget(header)
        
        # Action list
        for i, action in enumerate(self.actions, 1):
            action_frame = QFrame()
            action_frame.setFrameStyle(
                QFrame.Shape.Box | QFrame.Shadow.Sunken
            )
            action_layout = QVBoxLayout()
            
            # Action header
            header = QLabel(f"Action {i}: {action['tool']}")
            header.setStyleSheet("font-weight: bold;")
            action_layout.addWidget(header)
            
            # Args
            args_text = QTextEdit()
            args_text.setPlainText(
                json.dumps(action["args"], indent=2)
            )
            args_text.setReadOnly(True)
            args_text.setMaximumHeight(80)
            action_layout.addWidget(args_text)
            
            if "alignment_note" in action:
                note = QLabel(f"Rationale: {action['alignment_note']}")
                note.setWordWrap(True)
                action_layout.addWidget(note)
                
            action_frame.setLayout(action_layout)
            layout.addWidget(action_frame)
            
        # Confirmation
        self.confirm_check = QCheckBox(
            "I understand and approve all actions above"
        )
        layout.addWidget(self.confirm_check)
        
        # Buttons
        button_layout = QHBoxLayout()
        
        self.approve_all_btn = QPushButton("Approve All")
        self.approve_all_btn.setEnabled(False)
        self.approve_all_btn.clicked.connect(self.accept)
        
        review_individually_btn = QPushButton("Review Individually")
        review_individually_btn.clicked.connect(self.reject)
        
        button_layout.addWidget(self.approve_all_btn)
        button_layout.addWidget(review_individually_btn)
        
        layout.addLayout(button_layout)
        self.setLayout(layout)
        
        # Connect checkbox
        self.confirm_check.stateChanged.connect(self.toggle_approve)
        
    def toggle_approve(self, state):
        """Toggle approve button based on checkbox"""
        self.approve_all_btn.setEnabled(
            state == Qt.CheckState.Checked
        )

class BackupRestorationDialog(QDialog):
    """Dialog for managing backup restoration"""
    restore_requested = pyqtSignal(str, str)
    
    def __init__(
        self,
        backups: List[Dict[str, Any]],
        parent=None
    ):
        super().__init__(parent)
        self.backups = backups
        self.setup_ui()
        
    def setup_ui(self):
        """Setup dialog UI"""
        self.setWindowTitle("Restore from Backup")
        self.setMinimumWidth(500)
        
        layout = QVBoxLayout()
        
        # Header
        header = QLabel("Available Backups")
        header.setStyleSheet("font-size: 14pt; font-weight: bold;")
        layout.addWidget(header)
        
        # Backup list
        for backup in self.backups:
            backup_frame = QFrame()
            backup_frame.setFrameStyle(
                QFrame.Shape.Box | QFrame.Shadow.Sunken
            )
            backup_layout = QVBoxLayout()
            
            # Backup details
            path = QLabel(f"Path: {backup['backup_path']}")
            path.setWordWrap(True)
            backup_layout.addWidget(path)
            
            timestamp = QLabel(f"Created: {backup['timestamp']}")
            backup_layout.addWidget(timestamp)
            
            # Restore button
            restore_btn = QPushButton("Restore")
            restore_btn.clicked.connect(
                lambda checked, b=backup: self.request_restore(b)
            )
            backup_layout.addWidget(restore_btn)
            
            backup_frame.setLayout(backup_layout)
            layout.addWidget(backup_frame)
            
        # Close button
        close_btn = QPushButton("Close")
        close_btn.clicked.connect(self.reject)
        layout.addWidget(close_btn)
        
        self.setLayout(layout)
        
    def request_restore(self, backup: Dict[str, Any]):
        """Emit signal for restore request"""
        self.restore_requested.emit(
            backup["backup_path"],
            backup.get("original_path", "")
        )
        self.accept()
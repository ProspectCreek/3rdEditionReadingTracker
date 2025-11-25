# dialogs/create_anchor_dialog.py
import sys
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QFormLayout, QLineEdit, QTextEdit,
    QComboBox, QCheckBox, QDialogButtonBox, QLabel, QPushButton,
    QMessageBox, QHBoxLayout
)
from PySide6.QtCore import Qt

# Import PdfLinkDialog for node selection
try:
    from dialogs.pdf_link_dialog import PdfLinkDialog
except ImportError:
    PdfLinkDialog = None


class CreateAnchorDialog(QDialog):
    """
    A dialog for creating or editing a synthesis anchor.
    Replaced "Optional Comment" with "Add PDF Node".
    """

    def __init__(self, selected_text, project_tags_list=None, current_data=None, db=None, parent=None):
        super().__init__(parent)
        self.db = db
        self.setWindowTitle("Create Synthesis Anchor")
        if current_data:
            self.setWindowTitle("Edit Synthesis Anchor")

        self.project_tags = project_tags_list if project_tags_list else []
        self.current_data = current_data if current_data else {}

        # Store selected PDF node details
        self.selected_pdf_node_id = self.current_data.get('pdf_node_id')
        self._pdf_node_label = ""  # To be fetched if editing

        main_layout = QVBoxLayout(self)

        # Selected Text (read-only)
        form_layout = QFormLayout()
        self.selected_text_label = QLineEdit(selected_text)
        self.selected_text_label.setReadOnly(True)
        self.selected_text_label.setStyleSheet("background-color: #f0f0f0;")
        form_layout.addRow("Selected Text:", self.selected_text_label)

        # Tag selection/creation
        self.tag_combo = QComboBox()
        self.tag_combo.setEditable(True)
        self.tag_combo.setPlaceholderText("Select or create new tag...")

        # Populate with existing tags
        self.tag_combo.addItem("", None)  # Add a blank entry
        for tag in self.project_tags:
            self.tag_combo.addItem(tag['name'], tag['id'])

        # Set current tag if editing
        current_tag_name = self.current_data.get('tag_name', '')
        if current_tag_name:
            idx = self.tag_combo.findText(current_tag_name)
            if idx != -1:
                self.tag_combo.setCurrentIndex(idx)
            else:
                self.tag_combo.setEditText(current_tag_name)

        form_layout.addRow("Select tag or create new:", self.tag_combo)

        # Add '#' prefix checkbox
        self.add_prefix_check = QCheckBox("Add '#' prefix")
        self.add_prefix_check.setChecked(True)
        form_layout.addRow("", self.add_prefix_check)

        # --- PDF Node Selection ---
        self.pdf_node_label = QLabel("No PDF Node connected")
        self.pdf_node_label.setStyleSheet("font-style: italic; color: #666;")

        # Button layout for Add/Remove
        pdf_btn_layout = QHBoxLayout()

        self.btn_add_pdf_node = QPushButton("Add PDF Node")
        self.btn_add_pdf_node.clicked.connect(self._open_pdf_link_dialog)

        self.btn_remove_pdf_node = QPushButton("Remove")
        self.btn_remove_pdf_node.clicked.connect(self._remove_pdf_node)
        self.btn_remove_pdf_node.setVisible(False)  # Hidden by default
        self.btn_remove_pdf_node.setStyleSheet("color: red;")

        pdf_btn_layout.addWidget(self.btn_add_pdf_node)
        pdf_btn_layout.addWidget(self.btn_remove_pdf_node)
        pdf_btn_layout.addStretch()

        if not PdfLinkDialog or not self.db:
            self.btn_add_pdf_node.setEnabled(False)
            self.btn_add_pdf_node.setToolTip("DB Connection or Dialog missing")

        form_layout.addRow("Connected Node:", self.pdf_node_label)
        form_layout.addRow("", pdf_btn_layout)
        # --------------------------

        main_layout.addLayout(form_layout)

        # Standard OK/Cancel buttons
        self.button_box = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        self.button_box.accepted.connect(self.accept)
        self.button_box.rejected.connect(self.reject)
        main_layout.addWidget(self.button_box)

        self.tag_combo.currentTextChanged.connect(self._update_prefix_state)
        self._update_prefix_state(self.tag_combo.currentText())

        # Initialize PDF Label if editing
        if self.selected_pdf_node_id and self.db:
            node = self.db.get_pdf_node_details(self.selected_pdf_node_id)
            if node:
                self.selected_pdf_node_id = node['id']
                self._update_pdf_label(node['label'], node['page_number'])
            else:
                self.selected_pdf_node_id = None  # Clear invalid ID

    def _update_prefix_state(self, text):
        """Disables the '#' prefix checkbox if the tag already has one."""
        if text.startswith("#"):
            self.add_prefix_check.setChecked(False)
            self.add_prefix_check.setEnabled(False)
        else:
            self.add_prefix_check.setEnabled(True)

    def _open_pdf_link_dialog(self):
        """Opens the dialog to select a PDF node."""
        if not PdfLinkDialog or not self.db: return

        # We can attempt to get the current project ID from the parent if available,
        # but usually the link dialog handles navigation.
        # We pass None for project_id so it shows all or lets user navigate.
        dialog = PdfLinkDialog(self.db, parent=self)

        if dialog.exec() == QDialog.DialogCode.Accepted:
            node_id = dialog.selected_node_id
            # node_label comes formatted from the dialog selection
            node_data = self.db.get_pdf_node_details(node_id)
            if node_data:
                self.selected_pdf_node_id = node_id
                self._update_pdf_label(node_data['label'], node_data['page_number'])

    def _update_pdf_label(self, label, page_num):
        """Updates the UI label for the selected node."""
        self.pdf_node_label.setText(f"{label} (Pg {page_num + 1})")
        self.pdf_node_label.setStyleSheet("font-weight: bold; color: #2563EB;")
        self.btn_add_pdf_node.setText("Change PDF Node")
        self.btn_remove_pdf_node.setVisible(True)

    def _remove_pdf_node(self):
        """Removes the currently selected PDF node."""
        self.selected_pdf_node_id = None
        self.pdf_node_label.setText("No PDF Node connected")
        self.pdf_node_label.setStyleSheet("font-style: italic; color: #666;")
        self.btn_add_pdf_node.setText("Add PDF Node")
        self.btn_remove_pdf_node.setVisible(False)

    def get_tag_text(self):
        """Gets the final tag text, adding prefix if needed."""
        text = self.tag_combo.currentText().strip()
        if self.add_prefix_check.isChecked() and not text.startswith("#"):
            return f"#{text}"
        return text

    def get_pdf_node_id(self):
        """Returns the ID of the selected PDF node (or None)."""
        return self.selected_pdf_node_id
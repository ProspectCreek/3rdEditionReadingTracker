# dialogs/connect_tags_dialog.py
import sys
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QListWidget, QListWidgetItem,
    QDialogButtonBox, QWidget, QHBoxLayout, QPushButton, QLabel
)
from PySide6.QtCore import Qt


class ConnectTagsDialog(QDialog):
    """
    A dialog that shows a list of tags with checkboxes
    to link them to an item.
    """
    def __init__(self, all_project_tags, selected_tag_names, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Connect Synthesis Tags")
        self.setMinimumWidth(300)

        main_layout = QVBoxLayout(self)
        main_layout.addWidget(QLabel("Select tags to connect:"))

        self.tag_list = QListWidget()
        selected_set = set(selected_tag_names)

        for tag in all_project_tags:
            item = QListWidgetItem(tag['name'])
            item.setData(Qt.ItemDataRole.UserRole, tag['id'])
            # Set checkbox state
            if tag['name'] in selected_set:
                item.setCheckState(Qt.CheckState.Checked)
            else:
                item.setCheckState(Qt.CheckState.Unchecked)
            self.tag_list.addItem(item)

        main_layout.addWidget(self.tag_list)

        # Standard OK/Cancel buttons
        self.button_box = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        self.button_box.accepted.connect(self.accept)
        self.button_box.rejected.connect(self.reject)
        main_layout.addWidget(self.button_box)

    def get_selected_tag_names(self):
        """Returns a list of names of the checked tags."""
        selected_names = []
        for i in range(self.tag_list.count()):
            item = self.tag_list.item(i)
            if item.checkState() == Qt.CheckState.Checked:
                selected_names.append(item.text())
        return selected_names
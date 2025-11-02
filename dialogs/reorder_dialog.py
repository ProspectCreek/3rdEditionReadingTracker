from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QLabel, QListWidget,
    QDialogButtonBox, QPushButton, QHBoxLayout,
    QAbstractItemView, QListWidgetItem
)
from PySide6.QtCore import Qt


class ReorderDialog(QDialog):
    """
    PySide6 port of the ReorderDialog.
    Allows reordering items using a ListWidget with drag-and-drop
    and move up/down buttons.
    """

    def __init__(self, items_to_reorder, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Reorder Items")

        # This will store the final list of DB IDs
        self.ordered_db_ids = None

        main_layout = QVBoxLayout(self)
        main_layout.addWidget(QLabel("Click and drag items to reorder:"))

        self.list_widget = QListWidget()
        # Enable drag-and-drop for reordering
        self.list_widget.setDragDropMode(QAbstractItemView.DragDropMode.InternalMove)
        self.list_widget.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.list_widget.setFixedWidth(350)
        self.list_widget.setFixedHeight(250)

        for item_name, db_id in items_to_reorder:
            list_item = QListWidgetItem(item_name)
            list_item.setData(Qt.ItemDataRole.UserRole, db_id)  # Store db_id
            self.list_widget.addItem(list_item)

        main_layout.addWidget(self.list_widget)

        # Move Up/Down Buttons
        button_layout = QHBoxLayout()
        btn_up = QPushButton("Move Up")
        btn_down = QPushButton("Move Down")

        btn_up.clicked.connect(self.move_up)
        btn_down.clicked.connect(self.move_down)

        button_layout.addStretch()
        button_layout.addWidget(btn_up)
        button_layout.addWidget(btn_down)
        main_layout.addLayout(button_layout)

        # Standard OK/Cancel buttons
        self.button_box = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        self.button_box.accepted.connect(self.accept)
        self.button_box.rejected.connect(self.reject)

        main_layout.addWidget(self.button_box)

        if self.list_widget.count() > 0:
            self.list_widget.setCurrentRow(0)

    def move_up(self):
        current_row = self.list_widget.currentRow()
        if current_row > 0:
            item = self.list_widget.takeItem(current_row)
            self.list_widget.insertItem(current_row - 1, item)
            self.list_widget.setCurrentItem(item)

    def move_down(self):
        current_row = self.list_widget.currentRow()
        if current_row < self.list_widget.count() - 1:
            item = self.list_widget.takeItem(current_row)
            self.list_widget.insertItem(current_row + 1, item)
            self.list_widget.setCurrentItem(item)

    def accept(self):
        """
        Called when OK is clicked.
        Builds the list of ordered IDs and saves it.
        """
        self.ordered_db_ids = []
        for i in range(self.list_widget.count()):
            item = self.list_widget.item(i)
            db_id = item.data(Qt.ItemDataRole.UserRole)
            self.ordered_db_ids.append(db_id)

        super().accept()

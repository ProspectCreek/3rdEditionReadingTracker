# qda_row_dialog.py
import json
from PySide6.QtWidgets import (
    QDialog, QScrollArea, QWidget, QVBoxLayout, QLabel,
    QPlainTextEdit, QComboBox, QCheckBox, QPushButton, QHBoxLayout
)


class RowDetailDialog(QDialog):
    """
    Dialog to view/edit a single QDA row in a form-style layout.
    """
    def __init__(self, parent, db, row_record, columns):
        super().__init__(parent)
        self.db = db
        self.row_id = row_record["id"]
        self.columns = columns
        self.setWindowTitle("Edit Entry Details")
        self.resize(500, 600)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll_content = QWidget()
        self.data_widgets = {}

        form_layout = QVBoxLayout(scroll_content)
        form_layout.setSpacing(10)

        try:
            data = json.loads(row_record["data_json"] or "{}")
        except Exception:
            data = {}

        for col in self.columns:
            col_id = str(col["id"])
            col_name = col["name"]
            col_type = col["col_type"]
            value = data.get(col_id, "")

            field_container = QWidget()
            field_layout = QVBoxLayout(field_container)
            field_layout.setContentsMargins(0, 0, 0, 0)
            field_layout.setSpacing(2)

            label = QLabel(col_name + ":")
            label.setStyleSheet("font-weight: bold; color: #555;")
            field_layout.addWidget(label)

            if col_type == "text":
                widget = QPlainTextEdit()
                widget.setPlainText(str(value))
                widget.setMaximumHeight(60)
                field_layout.addWidget(widget)

            elif col_type == "dropdown":
                widget = QComboBox()
                opts_str = col["options_json"] or "[]"
                try:
                    options = json.loads(opts_str)
                except Exception:
                    options = []
                widget.addItems(options)
                widget.setEditable(True)
                widget.setCurrentText(str(value))
                field_layout.addWidget(widget)

            elif col_type == "checkbox":
                widget = QCheckBox()
                widget.setChecked(str(value) == "True")
                field_layout.addWidget(widget)

            else:
                widget = QPlainTextEdit()
                widget.setPlainText(str(value))
                widget.setMaximumHeight(60)
                field_layout.addWidget(widget)

            self.data_widgets[col_id] = widget
            form_layout.addWidget(field_container)

        form_layout.addStretch()
        scroll.setWidget(scroll_content)

        main_layout = QVBoxLayout(self)
        main_layout.addWidget(scroll)

        btn_layout = QHBoxLayout()
        btn_layout.addStretch()
        btn_save = QPushButton("Save")
        btn_cancel = QPushButton("Cancel")
        btn_layout.addWidget(btn_save)
        btn_layout.addWidget(btn_cancel)
        main_layout.addLayout(btn_layout)

        btn_save.clicked.connect(self._save_and_close)
        btn_cancel.clicked.connect(self.reject)

    def _save_and_close(self):
        data = {}
        for col in self.columns:
            col_id = str(col["id"])
            col_type = col["col_type"]
            widget = self.data_widgets.get(col_id)
            if widget is None:
                continue

            if col_type == "text":
                data[col_id] = widget.toPlainText()
            elif col_type == "dropdown":
                data[col_id] = widget.currentText()
            elif col_type == "checkbox":
                data[col_id] = "True" if widget.isChecked() else "False"
            else:
                if hasattr(widget, "toPlainText"):
                    data[col_id] = widget.toPlainText()
                elif hasattr(widget, "text"):
                    data[col_id] = widget.text()
                else:
                    data[col_id] = ""

        print(f"[DEBUG][Dialog] Saving row_id={self.row_id}, data={data}")
        self.db.update_row_data(self.row_id, data)
        self.accept()

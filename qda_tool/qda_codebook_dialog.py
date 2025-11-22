from PySide6.QtWidgets import (
    QDialog,
    QVBoxLayout,
    QFormLayout,
    QPlainTextEdit,
    QComboBox,
    QHBoxLayout,
    QPushButton,
)


class CodeDetailsDialog(QDialog):
    """
    Dialog to edit "Adler-grade" codebook details for a single column:
    - Definition
    - Inclusion rules
    - Exclusion rules
    - Examples
    - Optional parent code (for hierarchical codes)
    """

    def __init__(self, parent, db, col_id, col_name, all_columns):
        super().__init__(parent)
        self.db = db
        self.col_id = col_id
        self.all_columns = all_columns

        self.setWindowTitle(f"Code Details – {col_name}")
        self.resize(520, 520)

        main_layout = QVBoxLayout(self)

        # --- Form fields ---
        form = QFormLayout()
        form.setSpacing(8)

        self.edit_definition = QPlainTextEdit()
        self.edit_definition.setPlaceholderText(
            "What does this code mean? (1–3 sentences)."
        )

        self.edit_inclusion = QPlainTextEdit()
        self.edit_inclusion.setPlaceholderText(
            "Use this code WHEN… (bullet-style rules are fine)."
        )

        self.edit_exclusion = QPlainTextEdit()
        self.edit_exclusion.setPlaceholderText(
            "Do NOT use this code WHEN… (clarify boundaries)."
        )

        self.edit_examples = QPlainTextEdit()
        self.edit_examples.setPlaceholderText(
            "Short examples / vignettes that are good instances of this code."
        )

        # Parent code selector (for hierarchy)
        self.parent_combo = QComboBox()
        self.parent_combo.addItem("None", userData=None)
        for col in self.all_columns:
            # A column cannot be its own parent
            if col["id"] != self.col_id:
                self.parent_combo.addItem(col["name"], userData=col["id"])

        form.addRow("Definition:", self.edit_definition)
        form.addRow("Include when:", self.edit_inclusion)
        form.addRow("Exclude when:", self.edit_exclusion)
        form.addRow("Examples:", self.edit_examples)
        form.addRow("Parent code:", self.parent_combo)

        main_layout.addLayout(form)

        # --- Buttons ---
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()
        btn_save = QPushButton("Save")
        btn_cancel = QPushButton("Cancel")
        btn_layout.addWidget(btn_save)
        btn_layout.addWidget(btn_cancel)
        main_layout.addLayout(btn_layout)

        btn_save.clicked.connect(self._save_and_close)
        btn_cancel.clicked.connect(self.reject)

        # --- Load existing metadata, if any ---
        meta = self.db.get_codebook_meta(self.col_id)
        if meta:
            self.edit_definition.setPlainText((meta.get("definition") or "").strip())
            self.edit_inclusion.setPlainText((meta.get("inclusion") or "").strip())
            self.edit_exclusion.setPlainText((meta.get("exclusion") or "").strip())
            self.edit_examples.setPlainText((meta.get("examples") or "").strip())

            parent_id = meta.get("parent_id")
            if parent_id is not None:
                idx = self.parent_combo.findData(parent_id)
                if idx != -1:
                    self.parent_combo.setCurrentIndex(idx)

    # ---------------------------------------------------------
    # Save handler
    # ---------------------------------------------------------
    def _save_and_close(self):
        definition = self.edit_definition.toPlainText().strip()
        inclusion = self.edit_inclusion.toPlainText().strip()
        exclusion = self.edit_exclusion.toPlainText().strip()
        examples = self.edit_examples.toPlainText().strip()
        parent_id = self.parent_combo.currentData()

        print(f"[DEBUG][CodeDetails] save col_id={self.col_id}, parent={parent_id}")

        # No color argument anymore; DB handles definition/inclusion/exclusion/examples/parent_id
        self.db.update_codebook_meta(
            self.col_id,
            definition,
            inclusion,
            exclusion,
            examples,
            parent_id,
        )

        self.accept()

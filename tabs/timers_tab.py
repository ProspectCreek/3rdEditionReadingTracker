# tabs/timers_tab.py
import sys
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QSpinBox,
    QFrame, QSplitter, QApplication, QCheckBox, QMessageBox
)
from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QFont


class SingleTimerWidget(QWidget):
    """A widget for a single timer (Focus or Break)."""

    def __init__(self, title, default_minutes):
        super().__init__()
        self.default_minutes = default_minutes
        self.total_seconds = default_minutes * 60
        self.remaining_seconds = self.total_seconds
        self.is_running = False
        self.title_text = title  # Store title for popup

        self.timer = QTimer(self)
        self.timer.timeout.connect(self._update_timer)

        main_layout = QVBoxLayout(self)
        main_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        main_layout.setSpacing(10)  # Add some spacing between elements

        # --- Title ---
        title_label = QLabel(self.title_text)
        # Use CSS for consistent large styling
        title_label.setStyleSheet("font-size: 24px; font-weight: bold; color: #333;")
        title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        main_layout.addWidget(title_label)

        main_layout.addStretch(1)

        # --- Remaining Time Display ---
        # We stack "Remaining:" and the digits vertically for better layout

        # Label "Remaining:"
        lbl_remaining = QLabel("Time Remaining")
        lbl_remaining.setStyleSheet("font-size: 16px; color: #666; font-weight: bold;")
        lbl_remaining.setAlignment(Qt.AlignmentFlag.AlignCenter)
        main_layout.addWidget(lbl_remaining)

        # The Digits (HUGE)
        self.time_label = QLabel(self._format_time(self.remaining_seconds))
        # Use a massive font size and a monospaced-ish look if possible, or standard sans
        self.time_label.setStyleSheet("""
            font-size: 100px; 
            font-weight: bold; 
            color: #2563EB; 
            font-family: 'Segoe UI', sans-serif;
        """)
        self.time_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        main_layout.addWidget(self.time_label)

        # --- Set Time Controls ---
        set_layout = QHBoxLayout()
        set_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        # Style the set controls a bit to match
        set_label = QLabel("Set Duration (mm:ss):")
        set_label.setStyleSheet("font-weight: bold;")
        set_layout.addWidget(set_label)

        self.minutes_spinbox = QSpinBox()
        self.minutes_spinbox.setRange(0, 180)
        self.minutes_spinbox.setValue(default_minutes)
        self.minutes_spinbox.setFixedWidth(60)
        self.minutes_spinbox.setFixedHeight(30)
        self.minutes_spinbox.setStyleSheet("font-size: 14px;")

        self.seconds_spinbox = QSpinBox()
        self.seconds_spinbox.setRange(0, 59)
        self.seconds_spinbox.setValue(0)
        self.seconds_spinbox.setFixedWidth(60)
        self.seconds_spinbox.setFixedHeight(30)
        self.seconds_spinbox.setStyleSheet("font-size: 14px;")

        self.btn_set = QPushButton("Set")
        self.btn_set.setFixedHeight(30)

        set_layout.addWidget(self.minutes_spinbox)
        set_layout.addWidget(QLabel(":"))
        set_layout.addWidget(self.seconds_spinbox)
        set_layout.addWidget(self.btn_set)
        main_layout.addLayout(set_layout)

        # --- Action Buttons ---
        controls_layout = QHBoxLayout()
        controls_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        # Make buttons slightly larger/nicer
        btn_style = "padding: 8px 16px; font-size: 14px;"

        self.btn_start = QPushButton("Start")
        self.btn_start.setStyleSheet(btn_style)

        self.btn_pause = QPushButton("Pause")
        self.btn_pause.setStyleSheet(btn_style)

        self.btn_reset = QPushButton("Reset")
        self.btn_reset.setStyleSheet(btn_style)

        controls_layout.addWidget(self.btn_start)
        controls_layout.addWidget(self.btn_pause)
        controls_layout.addWidget(self.btn_reset)

        # --- Alarm Checkbox ---
        self.checkbox_alarm = QCheckBox("Audible Alarm")
        self.checkbox_alarm.setChecked(True)
        self.checkbox_alarm.setStyleSheet("font-size: 14px; margin-left: 10px;")
        controls_layout.addWidget(self.checkbox_alarm)

        main_layout.addLayout(controls_layout)

        main_layout.addStretch(1)

        # --- Connections ---
        self.btn_set.clicked.connect(self._set_time)
        self.btn_start.clicked.connect(self._start_timer)
        self.btn_pause.clicked.connect(self._pause_timer)
        self.btn_reset.clicked.connect(self._reset_timer)

        self._update_button_states()

    def _format_time(self, seconds):
        mins = seconds // 60
        secs = seconds % 60
        return f"{mins:02}:{secs:02}"

    def _set_time(self):
        if self.is_running:
            return
        self.total_seconds = (self.minutes_spinbox.value() * 60) + self.seconds_spinbox.value()
        self.remaining_seconds = self.total_seconds
        self.time_label.setText(self._format_time(self.remaining_seconds))

    def _start_timer(self):
        if not self.is_running:
            self.is_running = True
            self.timer.start(1000)  # Tick every 1 second
            self._update_button_states()

    def _pause_timer(self):
        if self.is_running:
            self.is_running = False
            self.timer.stop()
            self._update_button_states()

    def _reset_timer(self):
        self.is_running = False
        self.timer.stop()
        self.remaining_seconds = self.total_seconds
        self.time_label.setText(self._format_time(self.remaining_seconds))
        self._update_button_states()

    def _update_timer(self):
        if self.remaining_seconds > 0:
            self.remaining_seconds -= 1
            self.time_label.setText(self._format_time(self.remaining_seconds))
        else:
            self.is_running = False
            self.timer.stop()
            self._update_button_states()

            # --- Alarm logic ---
            if self.checkbox_alarm.isChecked():
                QApplication.beep()

                msg_box = QMessageBox(self)
                msg_box.setWindowTitle("Timer Finished")
                msg_box.setText(f"{self.title_text} Complete!")
                msg_box.setIcon(QMessageBox.Icon.Information)
                msg_box.setStandardButtons(QMessageBox.StandardButton.Ok)
                msg_box.exec()

    def _update_button_states(self):
        self.btn_start.setEnabled(not self.is_running and self.remaining_seconds > 0)
        self.btn_pause.setEnabled(self.is_running)
        self.btn_reset.setEnabled(not self.is_running)
        self.btn_set.setEnabled(not self.is_running)
        self.minutes_spinbox.setEnabled(not self.is_running)
        self.seconds_spinbox.setEnabled(not self.is_running)
        self.checkbox_alarm.setEnabled(not self.is_running)


class TimersTab(QWidget):
    """
    Main tab widget holding the Focus and Break timers side-by-side.
    """

    def __init__(self, parent=None):
        super().__init__(parent)

        main_layout = QHBoxLayout(self)
        splitter = QSplitter(Qt.Orientation.Horizontal)
        main_layout.addWidget(splitter)

        focus_frame = QFrame()
        focus_frame.setFrameShape(QFrame.Shape.StyledPanel)
        focus_layout = QVBoxLayout(focus_frame)
        self.focus_timer = SingleTimerWidget("Focus Timer", 30)
        focus_layout.addWidget(self.focus_timer)

        break_frame = QFrame()
        break_frame.setFrameShape(QFrame.Shape.StyledPanel)
        break_layout = QVBoxLayout(break_frame)
        self.break_timer = SingleTimerWidget("Break Timer", 5)
        break_layout.addWidget(self.break_timer)

        splitter.addWidget(focus_frame)
        splitter.addWidget(break_frame)

        # Set initial 50/50 split
        self.splitter = splitter
        self.splitter.splitterMoved.connect(self._save_split)

    def showEvent(self, event):
        """Set splitter to 50/50 on first show."""
        super().showEvent(event)
        if not hasattr(self, "_initial_split_set"):
            self._initial_split_set = True
            # We set sizes to large equal numbers to force a 50/50 split
            self.splitter.setSizes([self.width() // 2, self.width() // 2])

    def _save_split(self, pos, index):
        """(Optional) Save splitter state if needed later."""
        pass
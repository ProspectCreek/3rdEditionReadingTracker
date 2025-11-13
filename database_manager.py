import sqlite3
import shutil
import os
import json

# Import all our new helpers and mixins
from database_helpers.helpers import DbHelpers
from database_helpers.schema import SchemaSetup
from database_helpers.items_mixin import ItemsMixin
from database_helpers.readings_mixin import ReadingsMixin
from database_helpers.rubric_mixin import RubricMixin
from database_helpers.outline_mixin import OutlineMixin
from database_helpers.attachments_mixin import AttachmentsMixin
from database_helpers.mindmap_mixin import MindmapMixin
from database_helpers.driving_questions_mixin import DrivingQuestionsMixin
from database_helpers.synthesis_mixin import SynthesisMixin
from database_helpers.graph_mixin import GraphMixin
from database_helpers.terminology_mixin import TerminologyMixin
from database_helpers.propositions_mixin import PropositionsMixin
from database_helpers.todo_mixin import TodoMixin
from database_helpers.utility_mixin import UtilityMixin


class DatabaseManager(
    SchemaSetup,
    DbHelpers,
    ItemsMixin,
    ReadingsMixin,
    RubricMixin,
    OutlineMixin,
    AttachmentsMixin,
    MindmapMixin,
    DrivingQuestionsMixin,
    SynthesisMixin,
    GraphMixin,
    TerminologyMixin,
    PropositionsMixin,
    TodoMixin,
    UtilityMixin
):
    def __init__(self, db_file="reading_tracker.db"):
        """Initialize and connect to the SQLite database."""
        self.conn = sqlite3.connect(db_file)
        # We still use Row; public getters coerce to dicts where needed.
        self.conn.row_factory = sqlite3.Row
        self.conn.execute("PRAGMA foreign_keys = ON")
        self.cursor = self.conn.cursor()

        # This method is inherited from SchemaSetup
        self.setup_database()

    # The __del__ method is now inherited from UtilityMixin
    # All other methods are inherited from their respective Mixins
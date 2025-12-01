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
from database_helpers.key_terms_mixin import KeyTermsMixin
from database_helpers.theories_mixin import TheoriesMixin
from database_helpers.arguments_mixin import ArgumentsMixin
from database_helpers.utility_mixin import UtilityMixin
from database_helpers.graph_settings_mixin import GraphSettingsMixin
from database_helpers.global_graph_settings_mixin import GlobalGraphSettingsMixin
from database_helpers.settings_mixin import SettingsMixin
from database_helpers.pdf_nodes_mixin import PdfNodesMixin
from database_helpers.research_mixin import ResearchMixin
from database_helpers.annotated_bib_mixin import AnnotatedBibMixin
from database_helpers.evidence_matrix_mixin import EvidenceMatrixMixin

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
    KeyTermsMixin,
    TheoriesMixin,
    ArgumentsMixin,
    GraphSettingsMixin,
    GlobalGraphSettingsMixin,
    SettingsMixin,
    PdfNodesMixin,
    ResearchMixin,
    AnnotatedBibMixin,
    EvidenceMatrixMixin,
    UtilityMixin
):
    def __init__(self, db_file="reading_tracker.db"):
        """Initialize and connect to the SQLite database."""
        self.conn = sqlite3.connect(db_file)
        self.conn.row_factory = sqlite3.Row
        self.conn.execute("PRAGMA foreign_keys = ON")
        self.cursor = self.conn.cursor()

        # This method is inherited from SchemaSetup
        self.setup_database()
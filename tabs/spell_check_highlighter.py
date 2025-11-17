import re
from PySide6.QtCore import Qt
from PySide6.QtGui import QSyntaxHighlighter, QTextCharFormat, QColor


class SpellCheckHighlighter(QSyntaxHighlighter):
    """
    A syntax highlighter that applies a red wavy underline to misspelled words.
    """

    def __init__(self, parent_document, spell_checker_service):
        super().__init__(parent_document)
        self.spell_checker = spell_checker_service
        self.word_regex = self.spell_checker.get_word_regex()

        # Define the format for misspelled words
        self.misspelled_format = QTextCharFormat()
        self.misspelled_format.setUnderlineColor(Qt.GlobalColor.red)
        self.misspelled_format.setUnderlineStyle(QTextCharFormat.UnderlineStyle.SpellCheckUnderline)

    def highlightBlock(self, text):
        """This method is called by Qt to highlight a block of text."""
        if not self.spell_checker:
            return

        # Iterate over all words in the block
        for match in self.word_regex.finditer(text):
            word = match.group(1)

            # Check if the word is misspelled
            if self.spell_checker.is_misspelled(word):
                # Apply the misspelled format
                start_index = match.start(1)
                length = len(word)
                self.setFormat(start_index, length, self.misspelled_format)
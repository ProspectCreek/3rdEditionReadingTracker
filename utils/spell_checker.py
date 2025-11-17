import os
import re
from spellchecker import SpellChecker

# Define the path to the custom dictionary file at the project root
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CUSTOM_DICT_FILE = os.path.join(PROJECT_ROOT, "custom_dictionary.txt")


class GlobalSpellChecker:
    """
    A singleton-like service to manage the spell checker instance
    and the custom dictionary.
    """
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(GlobalSpellChecker, cls).__new__(cls)
            cls._instance.spell = SpellChecker()
            cls._instance.word_regex = re.compile(r"\b([A-Za-z']{2,})\b")
            cls._instance.load_custom_dictionary()
        return cls._instance

    def load_custom_dictionary(self):
        """Loads words from the custom dictionary file into the spellchecker."""
        try:
            if os.path.exists(CUSTOM_DICT_FILE):
                with open(CUSTOM_DICT_FILE, 'r', encoding='utf-8') as f:
                    words = [line.strip() for line in f if line.strip()]
                    self.spell.word_frequency.load_words(words)
                    print(f"SpellChecker: Loaded {len(words)} custom words.")
            else:
                # Create the file if it doesn't exist
                with open(CUSTOM_DICT_FILE, 'w', encoding='utf-8') as f:
                    f.write("# Custom dictionary file for Reading Tracker\n")
                print(f"SpellChecker: Created empty custom dictionary file.")
        except Exception as e:
            print(f"SpellChecker Error: Could not load custom dictionary. {e}")

    def add_to_dictionary(self, word):
        """Adds a word to the dictionary file and the running instance."""
        cleaned_word = word.lower().strip()
        if not cleaned_word or cleaned_word in self.spell:
            return

        try:
            # Add to the running instance
            self.spell.word_frequency.add(cleaned_word)

            # Add to the file
            with open(CUSTOM_DICT_FILE, 'a', encoding='utf-8') as f:
                f.write(f"\n{cleaned_word}")
            print(f"SpellChecker: Added '{cleaned_word}' to dictionary.")
        except Exception as e:
            print(f"SpellChecker Error: Could not add word to dictionary. {e}")

    def is_misspelled(self, word):
        """Checks if a single word is misspelled."""
        # Ignore numbers or words with numbers
        if not word or not word.isalpha():
            return False

        # Check the unknown list
        return word.lower() not in self.spell

    def suggest(self, word):
        """Gets spelling suggestions for a word."""
        if not self.is_misspelled(word):
            return []

        candidates = self.spell.candidates(word)
        if candidates:
            return list(candidates)[:5]  # Return top 5
        return []

    def get_word_regex(self):
        """Returns the regex used to find words."""
        return self.word_regex
"""
Smart features module
"""
from .duplicate_detector import DuplicateDetector
from .reference_extractor import ReferenceExtractor
from .tag_suggester import TagSuggester

__all__ = ['DuplicateDetector', 'ReferenceExtractor', 'TagSuggester']

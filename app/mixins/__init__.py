"""
Mixins package for shared functionality across test modules.

This package provides reusable mixins to eliminate code duplication
and standardize common patterns across different test implementations.
"""

from .connection_test_mixin import ConnectionTestMixin

__all__ = ["ConnectionTestMixin"]

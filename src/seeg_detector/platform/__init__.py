"""Adapters that isolate competition-platform dependencies."""

from .flydata_adapter import FlyDataResources, load_flydata_resources

__all__ = ["FlyDataResources", "load_flydata_resources"]

"""Pipeline OCR residual para boletas chilenas.

Stage1: OCR + persistencia de glosa/campos (sin matching).
Stage2: matching estricto → fallback → RapidFuzz vs CSV maestro.
Solo procesa el residual (~30% no conciliado); nunca reprocesa el 70% matched.
"""

__version__ = "1.0.0"
__all__ = ["__version__"]

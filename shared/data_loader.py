"""
Singleton DataLoader for Parquet Dataset
Carga el parquet una sola vez al startup y lo expone a todos los MCPs
"""

import pandas as pd
import pyarrow.parquet as pq
from pathlib import Path
from typing import Optional
import hashlib
import json


class DataLoader:
    """
    Singleton pattern para cargar y cachear el dataset

    Uso:
    ```python
    loader = DataLoader.get_instance()
    df = loader.df
    result = loader.get_cached(key) or loader.cache_result(key, result)
    ```
    """

    _instance: Optional['DataLoader'] = None

    def __init__(self, parquet_path: str = None):
        if parquet_path is None:
            parquet_path = "Reto_data_20251023_122206.parquet"

        self.parquet_path = Path(parquet_path)
        self.df = None
        self._cache = {}
        self.load_data()

    @classmethod
    def get_instance(cls, parquet_path: str = None) -> 'DataLoader':
        """Obtener instancia singleton"""
        if cls._instance is None:
            cls._instance = cls(parquet_path)
        return cls._instance

    def load_data(self):
        """Cargar parquet en memoria (una sola vez)"""
        if self.df is not None:
            return  # Ya cargado

        try:
            print(f"[DataLoader] Loading {self.parquet_path}...")
            # Usar PyArrow para evitar problemas de encoding
            table = pq.read_table(self.parquet_path)
            self.df = table.to_pandas()
            print(f"[DataLoader] [OK] Dataset loaded: {len(self.df)} rows x {len(self.df.columns)} cols")
            print(f"[DataLoader] Memory: {self.df.memory_usage(deep=True).sum() / 1024**2:.2f} MB")
        except FileNotFoundError:
            raise FileNotFoundError(
                f"Parquet file not found: {self.parquet_path}\n"
                f"Make sure it's in the project root directory"
            )
        except Exception as e:
            raise Exception(f"Error loading parquet: {str(e)}")

    def cache_result(self, key: str, result: dict) -> dict:
        """
        Guardar resultado en caché

        Args:
            key: Identificador único (ej: "propagacion::post_id123")
            result: Resultado a cachear (dict)

        Returns:
            El mismo resultado (para chainable)
        """
        self._cache[key] = result
        return result

    def get_cached(self, key: str) -> Optional[dict]:
        """Obtener resultado cacheado"""
        return self._cache.get(key)

    def clear_cache(self):
        """Limpiar caché completamente"""
        self._cache.clear()

    def generate_cache_key(self, endpoint: str, params: dict) -> str:
        """
        Generar clave de caché basada en endpoint + parámetros

        Args:
            endpoint: Nombre del endpoint (ej: "propagacion")
            params: Parámetros de la query (dict)

        Returns:
            Hash único para los parámetros
        """
        # Crear string determinístico de parámetros
        params_str = json.dumps(params, sort_keys=True)
        params_hash = hashlib.md5(params_str.encode()).hexdigest()[:8]
        return f"{endpoint}::{params_hash}"

    def get_stats(self) -> dict:
        """Obtener estadísticas del dataset"""
        if self.df is None:
            return {}

        return {
            "rows": len(self.df),
            "columns": len(self.df.columns),
            "memory_mb": self.df.memory_usage(deep=True).sum() / 1024**2,
            "cache_entries": len(self._cache),
        }


def get_loader() -> DataLoader:
    """Helper function para obtener la instancia singleton"""
    return DataLoader.get_instance()

"""
Base Source Class

Classe base para todas as fontes de dados com:
- Rate limiting integrado
- Cache de requéstas
- HTTP client com User-Agents rotativos
- Retry automático
"""

import logging
from abc import ABC, abstractmethod
from typing import Optional, Dict, List, Any
from datetime import datetime

from public_finance_data_hub.core.rate_limiter import CombinedRateLimiter
from public_finance_data_hub.core.cache import APICache, get_or_cache
from public_finance_data_hub.core.http_client import HTTPClient

logger = logging.getLogger(__name__)


class BaseSource(ABC):
    """Classe base para fontes de dados"""
    
    def __init__(
        self,
        name: str,
        rate_limiter: CombinedRateLimiter,
        cache: Optional[APICache] = None,
        http_client: Optional[HTTPClient] = None,
    ):
        """
        Args:
            name: Nome da fonte
            rate_limiter: Limitador de taxa de requisições
            cache: Cache para requéstas (opcional)
            http_client: Cliente HTTP customizado (opcional)
        """
        self.name = name
        self.rate_limiter = rate_limiter
        self.cache = cache
        self.http_client = http_client or HTTPClient()
        self.records_ingested = 0
        self.records_failed = 0
    
    @abstractmethod
    def ingest(self) -> int:
        """
        Coleta dados da fonte
        
        Returns:
            int: Número de registros coletados
        """
        pass
    
    def _fetch_with_protection(
        self,
        url: str,
        fetch_func,
        params: Optional[Dict] = None,
        use_cache: bool = True,
    ) -> Any:
        """
        Busca dados com todas as proteções aplicadas
        
        Aplica em ordem:
        1. Cache (se disponível e use_cache=True)
        2. Rate limiting
        3. Retry com backoff
        4. HTTP client com User-Agents rotativos
        
        Args:
            url: URL para requisitar
            fetch_func: Função que faz a requisição
            params: Parâmetros da requisição (para cache)
            use_cache: Se deve usar cache
            
        Returns:
            Dados retornados pela fetch_func
        """
        
        # 1. Tentar cache primeiro
        if use_cache and self.cache:
            cached = self.cache.get(url, params)
            if cached is not None:
                logger.debug(f"[{self.name}] Retornando do cache: {url}")
                return cached
        
        # 2. Executar com rate limit + delay + retry
        def wrapped_fetch():
            return fetch_func()
        
        data = self.rate_limiter.execute(wrapped_fetch)
        
        # 3. Cachear resultado
        if use_cache and self.cache:
            self.cache.set(url, params, data)
        
        return data
    
    def fetch_json(
        self,
        url: str,
        params: Optional[Dict] = None,
        headers: Optional[Dict] = None,
        use_cache: bool = True,
    ) -> Dict:
        """
        Fetch JSON com todas as proteções
        
        Args:
            url: URL para requisitar
            params: Parâmetros GET
            headers: Headers customizados
            use_cache: Se deve cachear
            
        Returns:
            Dict com JSON retornado
        """
        def fetch():
            return self.http_client.get_json(url, params=params, headers=headers)
        
        return self._fetch_with_protection(
            url,
            fetch,
            params=params,
            use_cache=use_cache,
        )
    
    def get_stats(self) -> Dict[str, Any]:
        """Retorna estatísticas da ingestão"""
        return {
            'name': self.name,
            'records_ingested': self.records_ingested,
            'records_failed': self.records_failed,
            'rate_limiter': self.rate_limiter.get_stats(),
            'cache': self.cache.get_stats() if self.cache else None,
        }
    
    def log_stats(self):
        """Loga estatísticas da ingestão"""
        stats = self.get_stats()
        logger.info(
            f"\n[{self.name}] Ingest Statistics:"
            f"\n  Records ingested: {stats['records_ingested']}"
            f"\n  Records failed: {stats['records_failed']}"
            f"\n  Rate limiter: {stats['rate_limiter']['current_rate_per_min']}/{stats['rate_limiter']['max_rate_per_min']} req/min"
        )


class Example_BCB_Source(BaseSource):
    """Exemplo de como usar a classe base"""
    
    def ingest(self) -> int:
        """
        Exemplo de implementação
        """
        from public_finance_data_hub.core.rate_limiter import BCB_LIMITER
        from public_finance_data_hub.core.cache import global_cache
        
        logger.info(f"\nIniciando ingestão de {self.name}...")
        
        try:
            # URL da API
            url = "https://www.bcb.gov.br/api/v1/dados/series/1/dados"
            
            # Fetch com todas as proteções
            data = self.fetch_json(url, use_cache=True)
            
            # Processar dados
            records = len(data.get('value', []))
            self.records_ingested = records
            
            logger.info(f"[✅ {self.name}] Ingerido com sucesso: {records} registros")
            self.log_stats()
            
            return records
        
        except Exception as e:
            logger.error(f"[❌ {self.name}] Erro na ingestão: {e}", exc_info=True)
            self.records_failed += 1
            raise


# Uso prático em suas fontes:
# 
# from public_finance_data_hub.sources.base_source import BaseSource
# from public_finance_data_hub.core.rate_limiter import BCB_LIMITER
# from public_finance_data_hub.core.cache import global_cache
# 
# class BCBSource(BaseSource):
#     def __init__(self):
#         super().__init__(
#             name="BCB",
#             rate_limiter=BCB_LIMITER,
#             cache=global_cache,
#         )
#     
#     def ingest(self) -> int:
#         data = self.fetch_json(
#             url="https://www.bcb.gov.br/api/v1/dados/series/1/dados",
#             use_cache=True
#         )
#         # ... processar data ...
#         return num_records

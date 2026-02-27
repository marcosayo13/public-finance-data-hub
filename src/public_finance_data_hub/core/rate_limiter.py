"""
Rate Limiter Module

Implementa proteção contra rate limiting de APIs com:
- Controle de requisições por minuto
- Backoff exponencial para erros
- Delays aleatórios entre requisições
"""

import time
import logging
from collections import deque
from datetime import datetime, timedelta
from typing import Optional, Callable
import random

logger = logging.getLogger(__name__)


class RequestRateLimiter:
    """Controla taxa de requisições por janela de tempo"""
    
    def __init__(
        self, 
        max_requests_per_minute: int = 100,
        name: str = "APIRateLimiter"
    ):
        """
        Args:
            max_requests_per_minute: Máximo de requisições por minuto
            name: Nome para logging
        """
        self.max_requests = max_requests_per_minute
        self.name = name
        self.requests = deque(maxlen=self.max_requests)
        self.lock = None
    
    def wait_if_needed(self) -> float:
        """
        Aguarda se necessário para não exceder rate limit
        
        Returns:
            float: Tempo aguardado em segundos
        """
        now = time.time()
        
        # Remove requisições antigas (>1 minuto)
        while self.requests and self.requests[0] < now - 60:
            self.requests.popleft()
        
        sleep_time = 0.0
        if len(self.requests) >= self.max_requests:
            sleep_time = 60 - (now - self.requests[0]) + 0.1
            logger.warning(
                f"[{self.name}] Rate limit atingido. "
                f"Aguardando {sleep_time:.1f}s ({len(self.requests)}/{self.max_requests})"
            )
            time.sleep(sleep_time)
        
        self.requests.append(time.time())
        return sleep_time
    
    def get_current_rate(self) -> float:
        """Retorna requisições/minuto atual"""
        now = time.time()
        while self.requests and self.requests[0] < now - 60:
            self.requests.popleft()
        return len(self.requests)


class DelayedRequester:
    """Faz requisições com delays aleatórios entre elas"""
    
    def __init__(
        self,
        min_delay_seconds: float = 1.0,
        max_delay_seconds: float = 3.0,
        name: str = "DelayedRequester"
    ):
        """
        Args:
            min_delay_seconds: Delay mínimo entre requisições
            max_delay_seconds: Delay máximo entre requisições
            name: Nome para logging
        """
        self.min_delay = min_delay_seconds
        self.max_delay = max_delay_seconds
        self.name = name
        self.last_request_time = 0
    
    def get_delay(self) -> float:
        """Retorna delay aleatório dentro do intervalo"""
        return random.uniform(self.min_delay, self.max_delay)
    
    def sleep(self) -> float:
        """Aguarda delay aleatório e retorna tempo aguardado"""
        delay = self.get_delay()
        logger.debug(f"[{self.name}] Aguardando {delay:.2f}s antes da requisição")
        time.sleep(delay)
        self.last_request_time = time.time()
        return delay


class ExponentialBackoffRetry:
    """Implementa retry com backoff exponencial"""
    
    def __init__(
        self,
        max_retries: int = 3,
        base_delay_seconds: float = 1.0,
        max_delay_seconds: float = 60.0,
        name: str = "ExponentialBackoff"
    ):
        """
        Args:
            max_retries: Número máximo de tentativas
            base_delay_seconds: Delay base em segundos
            max_delay_seconds: Delay máximo
            name: Nome para logging
        """
        self.max_retries = max_retries
        self.base_delay = base_delay_seconds
        self.max_delay = max_delay_seconds
        self.name = name
    
    def get_delay(self, attempt: int) -> float:
        """
        Calcula delay para tentativa N
        Fórmula: min(base * 2^attempt + jitter, max)
        """
        # Exponencial com jitter
        delay = self.base_delay * (2 ** attempt)
        # Adiciona aleatoriedade (±10%)
        jitter = random.uniform(0.9, 1.1)
        delay = delay * jitter
        # Limita ao máximo
        delay = min(delay, self.max_delay)
        return delay
    
    def execute_with_retry(
        self,
        func: Callable,
        *args,
        **kwargs
    ):
        """
        Executa função com retry automático
        
        Args:
            func: Função para executar
            *args: Argumentos posicionais
            **kwargs: Argumentos nomeados
            
        Returns:
            Resultado da função
            
        Raises:
            Última exceção se todos os retries falharem
        """
        last_exception = None
        
        for attempt in range(self.max_retries):
            try:
                logger.debug(f"[{self.name}] Tentativa {attempt + 1}/{self.max_retries}")
                return func(*args, **kwargs)
            
            except Exception as e:
                last_exception = e
                
                if attempt == self.max_retries - 1:
                    logger.error(
                        f"[{self.name}] Todas as {self.max_retries} tentativas falharam: {e}"
                    )
                    raise
                
                delay = self.get_delay(attempt)
                logger.warning(
                    f"[{self.name}] Tentativa {attempt + 1} falhou: {e}. "
                    f"Aguardando {delay:.1f}s antes de retry..."
                )
                time.sleep(delay)
        
        raise last_exception


class CombinedRateLimiter:
    """Combina rate limit, delays e retry em um único objeto"""
    
    def __init__(
        self,
        max_requests_per_minute: int = 100,
        min_delay_seconds: float = 1.0,
        max_delay_seconds: float = 3.0,
        max_retries: int = 3,
        name: str = "API"
    ):
        """
        Args:
            max_requests_per_minute: Limite de requisições/minuto
            min_delay_seconds: Delay mínimo entre requisições
            max_delay_seconds: Delay máximo entre requisições
            max_retries: Tentativas máximas em caso de erro
            name: Nome da API para logging
        """
        self.name = name
        self.rate_limiter = RequestRateLimiter(max_requests_per_minute, name)
        self.delayer = DelayedRequester(min_delay_seconds, max_delay_seconds, name)
        self.retry = ExponentialBackoffRetry(max_retries, name=name)
    
    def execute(self, func: Callable, *args, **kwargs):
        """
        Executa função com todas as proteções
        
        Ordem:
        1. Aguarda rate limit
        2. Aguarda delay aleatório
        3. Executa com retry automático
        """
        # 1. Rate limit
        self.rate_limiter.wait_if_needed()
        
        # 2. Delay aleatório
        self.delayer.sleep()
        
        # 3. Execute com retry
        return self.retry.execute_with_retry(func, *args, **kwargs)
    
    def get_stats(self) -> dict:
        """Retorna estatísticas de uso"""
        return {
            'name': self.name,
            'current_rate_per_min': self.rate_limiter.get_current_rate(),
            'max_rate_per_min': self.rate_limiter.max_requests,
            'min_delay_seconds': self.delayer.min_delay,
            'max_delay_seconds': self.delayer.max_delay,
            'max_retries': self.retry.max_retries,
        }


# Instâncias globais para cada fonte de dados
BCB_LIMITER = CombinedRateLimiter(
    max_requests_per_minute=100,
    min_delay_seconds=0.5,
    max_delay_seconds=1.5,
    max_retries=3,
    name="BCB"
)

FRED_LIMITER = CombinedRateLimiter(
    max_requests_per_minute=100,
    min_delay_seconds=0.5,
    max_delay_seconds=1.5,
    max_retries=3,
    name="FRED"
)

ANBIMA_LIMITER = CombinedRateLimiter(
    max_requests_per_minute=50,
    min_delay_seconds=1.0,
    max_delay_seconds=2.0,
    max_retries=3,
    name="ANBIMA"
)

YAHOO_LIMITER = CombinedRateLimiter(
    max_requests_per_minute=30,
    min_delay_seconds=2.0,
    max_delay_seconds=4.0,
    max_retries=5,
    name="YAHOO"
)

B3_LIMITER = CombinedRateLimiter(
    max_requests_per_minute=20,
    min_delay_seconds=3.0,
    max_delay_seconds=5.0,
    max_retries=5,
    name="B3"
)

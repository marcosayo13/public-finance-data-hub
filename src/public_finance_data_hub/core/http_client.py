"""
HTTP Client Module

Cliente HTTP com:
- User-Agents rotativos realistas
- Headers apropriados para cada fonte
- Sessão reutilizável
- Retry automático
"""

import logging
import requests
from typing import Optional, Dict, List
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
import random

logger = logging.getLogger(__name__)


class UserAgentRotator:
    """Rotaciona entre User-Agents realistas"""
    
    USER_AGENTS = [
        # Chrome Windows
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/92.0.4515.159 Safari/537.36',
        
        # Chrome macOS
        'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
        'Mozilla/5.0 (Macintosh; Intel Mac OS X 11_4) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/92.0.4515.159 Safari/537.36',
        
        # Chrome Linux
        'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
        'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/92.0.4515.159 Safari/537.36',
        
        # Firefox
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:89.0) Gecko/20100101 Firefox/89.0',
        'Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:89.0) Gecko/20100101 Firefox/89.0',
        'Mozilla/5.0 (X11; Linux x86_64; rv:89.0) Gecko/20100101 Firefox/89.0',
        
        # Safari
        'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/14.1.1 Safari/605.1.15',
        'Mozilla/5.0 (iPhone; CPU iPhone OS 14_6 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/14.1.1 Mobile/15E148 Safari/604.1',
    ]
    
    @staticmethod
    def get_random() -> str:
        """Retorna User-Agent aleatório"""
        return random.choice(UserAgentRotator.USER_AGENTS)


class HTTPClient:
    """Cliente HTTP com proteções integradas"""
    
    def __init__(
        self,
        timeout: int = 30,
        max_retries: int = 3,
        backoff_factor: float = 0.3,
    ):
        """
        Args:
            timeout: Timeout em segundos
            max_retries: Tentativas máximas
            backoff_factor: Fator de backoff exponencial
        """
        self.timeout = timeout
        self.session = self._create_session(max_retries, backoff_factor)
    
    def _create_session(
        self,
        max_retries: int,
        backoff_factor: float
    ) -> requests.Session:
        """
        Cria sessão com retry automático
        """
        session = requests.Session()
        
        # Configura retry
        retry_strategy = Retry(
            total=max_retries,
            backoff_factor=backoff_factor,
            status_forcelist=[429, 500, 502, 503, 504],
            allowed_methods=["HEAD", "GET", "OPTIONS", "POST"]
        )
        
        # Monta adaptador
        adapter = HTTPAdapter(max_retries=retry_strategy)
        session.mount("http://", adapter)
        session.mount("https://", adapter)
        
        return session
    
    def get(
        self,
        url: str,
        params: Optional[Dict] = None,
        headers: Optional[Dict] = None,
        **kwargs
    ) -> requests.Response:
        """
        GET request com User-Agent aleatório
        """
        if headers is None:
            headers = {}
        
        # Adiciona User-Agent se não fornecido
        if 'User-Agent' not in headers:
            headers['User-Agent'] = UserAgentRotator.get_random()
        
        # Adiciona headers padrão
        headers.setdefault('Accept', 'application/json, text/plain, */*')
        headers.setdefault('Accept-Language', 'pt-BR,pt;q=0.9,en;q=0.8')
        headers.setdefault('Accept-Encoding', 'gzip, deflate, br')
        headers.setdefault('Referer', 'https://www.google.com/')
        
        logger.debug(f"GET {url} com headers: {headers}")
        
        return self.session.get(
            url,
            params=params,
            headers=headers,
            timeout=self.timeout,
            **kwargs
        )
    
    def post(
        self,
        url: str,
        json: Optional[Dict] = None,
        data: Optional[Dict] = None,
        headers: Optional[Dict] = None,
        **kwargs
    ) -> requests.Response:
        """
        POST request com User-Agent aleatório
        """
        if headers is None:
            headers = {}
        
        if 'User-Agent' not in headers:
            headers['User-Agent'] = UserAgentRotator.get_random()
        
        headers.setdefault('Accept', 'application/json')
        headers.setdefault('Accept-Language', 'pt-BR,pt;q=0.9,en;q=0.8')
        
        logger.debug(f"POST {url} com headers: {headers}")
        
        return self.session.post(
            url,
            json=json,
            data=data,
            headers=headers,
            timeout=self.timeout,
            **kwargs
        )
    
    def get_json(
        self,
        url: str,
        params: Optional[Dict] = None,
        headers: Optional[Dict] = None,
        **kwargs
    ) -> Dict:
        """
        GET request que retorna JSON automaticamente
        
        Raises:
            requests.HTTPError: Se status_code >= 400
        """
        response = self.get(url, params=params, headers=headers, **kwargs)
        response.raise_for_status()
        return response.json()
    
    def close(self):
        """Fecha a sessão"""
        self.session.close()
    
    def __enter__(self):
        return self
    
    def __exit__(self, *args):
        self.close()


def create_bcb_client() -> HTTPClient:
    """Cria cliente HTTP para BCB"""
    return HTTPClient(timeout=30, max_retries=3)


def create_fred_client() -> HTTPClient:
    """Cria cliente HTTP para FRED"""
    return HTTPClient(timeout=30, max_retries=3)


def create_anbima_client() -> HTTPClient:
    """Cria cliente HTTP para Anbima"""
    return HTTPClient(timeout=30, max_retries=3)


def create_yahoo_client() -> HTTPClient:
    """Cria cliente HTTP para Yahoo (mais restritivo)"""
    return HTTPClient(timeout=30, max_retries=5)


def create_b3_client() -> HTTPClient:
    """Cria cliente HTTP para B3 (mais restritivo)"""
    return HTTPClient(timeout=30, max_retries=5)


# Instâncias globais
global_client = HTTPClient(timeout=30, max_retries=3)

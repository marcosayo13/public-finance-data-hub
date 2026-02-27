"""
Cache Module

Sistema de cache para reduzir requisições à API com:
- TTL (Time To Live) configurável
- Armazenamento em arquivo JSON
- Verificação de cache antes de requisições
"""

import json
import hashlib
import logging
from pathlib import Path
from datetime import datetime, timedelta
from typing import Optional, Any, Dict

logger = logging.getLogger(__name__)


class APICache:
    """Cache para respostas de APIs com suporte a TTL"""
    
    def __init__(
        self,
        cache_dir: str = './cache',
        default_ttl_hours: int = 24,
        enabled: bool = True
    ):
        """
        Args:
            cache_dir: Diretório para armazenar cache
            default_ttl_hours: TTL padrão em horas
            enabled: Se cache está habilitado
        """
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.default_ttl = timedelta(hours=default_ttl_hours)
        self.enabled = enabled
    
    def _get_cache_key(self, url: str, params: Optional[Dict] = None) -> str:
        """
        Gera chave de cache única baseada em URL + parâmetros
        
        Args:
            url: URL da requisição
            params: Parâmetros da requisição
            
        Returns:
            str: Chave de cache em hex
        """
        params_str = json.dumps(params, sort_keys=True) if params else '{}'
        full_string = f"{url}:{params_str}"
        return hashlib.md5(full_string.encode()).hexdigest()
    
    def _get_cache_file(self, cache_key: str) -> Path:
        """Retorna path do arquivo de cache"""
        return self.cache_dir / f"{cache_key}.json"
    
    def get(self, url: str, params: Optional[Dict] = None) -> Optional[Dict]:
        """
        Recupera dados do cache se válido
        
        Args:
            url: URL da requisição
            params: Parâmetros da requisição
            
        Returns:
            Dict com dados em cache ou None se expirado/inexistente
        """
        if not self.enabled:
            return None
        
        cache_key = self._get_cache_key(url, params)
        cache_file = self._get_cache_file(cache_key)
        
        if not cache_file.exists():
            logger.debug(f"Cache miss: {url}")
            return None
        
        try:
            with open(cache_file, 'r', encoding='utf-8') as f:
                cache_data = json.load(f)
            
            # Verificar se cache expirou
            created_at = datetime.fromisoformat(cache_data['_created_at'])
            if datetime.now() - created_at > self.default_ttl:
                logger.debug(f"Cache expirado: {url}")
                cache_file.unlink()  # Remover arquivo expirado
                return None
            
            logger.debug(f"Cache hit: {url}")
            return cache_data['data']
        
        except Exception as e:
            logger.warning(f"Erro ao ler cache {cache_file}: {e}")
            return None
    
    def set(self, url: str, params: Optional[Dict], data: Dict) -> bool:
        """
        Armazena dados em cache
        
        Args:
            url: URL da requisição
            params: Parâmetros da requisição
            data: Dados para cachear
            
        Returns:
            bool: True se salvo com sucesso
        """
        if not self.enabled:
            return False
        
        cache_key = self._get_cache_key(url, params)
        cache_file = self._get_cache_file(cache_key)
        
        try:
            cache_data = {
                '_created_at': datetime.now().isoformat(),
                '_url': url,
                '_params': params,
                'data': data
            }
            
            with open(cache_file, 'w', encoding='utf-8') as f:
                json.dump(cache_data, f, indent=2, ensure_ascii=False)
            
            logger.debug(f"Cache saved: {url}")
            return True
        
        except Exception as e:
            logger.error(f"Erro ao salvar cache {cache_file}: {e}")
            return False
    
    def clear(self, older_than_hours: Optional[int] = None) -> int:
        """
        Limpa cache antigo
        
        Args:
            older_than_hours: Limpar arquivos mais antigos que N horas
                            Se None, limpa todo o cache
            
        Returns:
            int: Número de arquivos deletados
        """
        deleted = 0
        cutoff_time = None
        
        if older_than_hours:
            cutoff_time = datetime.now() - timedelta(hours=older_than_hours)
        
        for cache_file in self.cache_dir.glob('*.json'):
            if cutoff_time:
                file_time = datetime.fromtimestamp(cache_file.stat().st_mtime)
                if file_time > cutoff_time:
                    continue
            
            try:
                cache_file.unlink()
                deleted += 1
                logger.debug(f"Cache deletado: {cache_file}")
            except Exception as e:
                logger.warning(f"Erro ao deletar {cache_file}: {e}")
        
        logger.info(f"Total de arquivos de cache deletados: {deleted}")
        return deleted
    
    def get_stats(self) -> Dict[str, Any]:
        """Retorna estatísticas do cache"""
        cache_files = list(self.cache_dir.glob('*.json'))
        total_size = sum(f.stat().st_size for f in cache_files)
        
        return {
            'total_files': len(cache_files),
            'total_size_mb': total_size / (1024 * 1024),
            'cache_dir': str(self.cache_dir),
            'enabled': self.enabled,
            'default_ttl_hours': self.default_ttl.total_seconds() / 3600,
        }


# Instância global de cache
global_cache = APICache(
    cache_dir='./cache',
    default_ttl_hours=24,
    enabled=True
)


def get_or_cache(url: str, fetch_func, params: Optional[Dict] = None) -> Dict:
    """
    Utilitário: tenta obter do cache, senoão busca e cacheia
    
    Args:
        url: URL para cachear
        fetch_func: Função que retorna dados se não estão em cache
        params: Parâmetros para cachear
        
    Returns:
        Dict: Dados do cache ou da função
    """
    # Tentar obter do cache
    cached_data = global_cache.get(url, params)
    if cached_data is not None:
        return cached_data
    
    # Se não está em cache, buscar
    data = fetch_func()
    
    # Armazenar em cache
    global_cache.set(url, params, data)
    
    return data

import requests
from bs4 import BeautifulSoup
from rich.console import Console

from ..base_portal import BasePortal

class MemoryDiaria(BasePortal):
    def __init__(self, callback=None, verbose=False):
        super().__init__(callback, verbose)
        self.console = Console()
    
    def buscar_diarias(self, url_base, ano_inicio, ano_fim, credor_nome):
        # Implementação específica para o método de busca "diaria" no portal Memory
        # Esta é uma implementação de exemplo que deve ser adaptada
        
        self.atualizar_progresso(f"Buscando diárias diretamente no portal Memory")
        
        valor_total = 0.0
        dados_empenhos = []
        
        # Lógica específica para buscar diárias no portal Memory
        # ...
        
        return valor_total, dados_empenhos
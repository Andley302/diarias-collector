import requests
from bs4 import BeautifulSoup
from rich.console import Console
import unicodedata
from ..base_portal import BasePortal
from src.core.utils import remover_acentos
class DigitalizaDiaria(BasePortal):
    def __init__(self, callback=None, verbose=False):
        super().__init__(callback, verbose)
        self.console = Console()
    
    
    def buscar_diarias(self, url_base, ano_inicio, ano_fim, credor_nome):
        # Implementação específica para o método de busca "diaria" no portal Digitaliza
        # Esta é uma implementação de exemplo que deve ser adaptada
        
        self.atualizar_progresso(f"Buscando diárias diretamente no portal Digitaliza")
        
        valor_total = 0.0
        dados_empenhos = []
        
        # Lógica específica para buscar diárias no portal Digitaliza
        # ...
        
        return valor_total, dados_empenhos
from abc import ABC, abstractmethod
from src.core.utils import remover_acentos
from rich.console import Console

class BasePortal(ABC):
    def __init__(self, callback=None, verbose=False):
        self.callback = callback
        self.verbose = verbose
        self.console = Console(force_terminal=True)
    
    @abstractmethod
    def buscar_diarias(self, url_base, ano_inicio, ano_fim, credor_nome):
        """
        Método abstrato que deve ser implementado por cada portal
        
        Returns:
            tuple: (valor_total, dados_empenhos)
        """
        pass
    
    def atualizar_progresso(self, mensagem, empenho=None):
        if self.callback:
            self.callback(mensagem, empenho)
        else:
            self.console.print(mensagem, markup=True, highlight=True)
            
    def remover_acentos(self, texto):
        return remover_acentos(texto)

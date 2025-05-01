import json
import re
from rich.console import Console

from src.core.portais.digitaliza.empenho import DigitalizaEmpenho
from src.core.portais.digitaliza.diaria import DigitalizaDiaria
from src.core.portais.memory.diaria import MemoryDiaria
from src.core.utils import resource_path

class DiariasCollector:
    def __init__(self, callback=None, verbose=False):
        self.callback = callback
        self.verbose = verbose
        self.console = Console()
        
        self.portal_implementations = {
            'digitaliza': {
                'diaria': DigitalizaDiaria,
                'empenho': DigitalizaEmpenho
            },
            'memory': {
                'diaria': MemoryDiaria
            }
        }
        
        self.cidades_orgaos = self.carregar_cidades_orgaos()

    def exibir_configuracoes(self):
        conteudo = (
            f"[bold cyan]Logs detalhados:[/bold cyan] [green]{'Sim' if self.verbose else 'Não'}[/green]"
        )
        self.console.print(conteudo)
        
    def atualizar_progresso(self, mensagem, empenho=None, data=None, total_empenhos=None, total_meses=None):
        if self.callback:
            self.callback(mensagem, empenho, data, total_empenhos, total_meses)
        else:
            self.console.print(mensagem, markup=True, highlight=True)


    def carregar_cidades_orgaos(self):
        try:
            json_path = resource_path('resources/cidades.json')
            with open(json_path, 'r', encoding='utf-8') as file:
                return json.load(file)
        except Exception as e:
            self.atualizar_progresso(f"[bold red]❌ Erro ao carregar cidades.json: {e}[/bold red]")
            return {}

    def validar_entrada(self, ano_inicio, ano_fim, credor_nome):
        try:
            ano_inicio = int(ano_inicio)
            ano_fim = int(ano_fim)
        except ValueError:
            return False, "O ano de início e o ano de fim devem ser números."
        
        if ano_inicio <= 0 or ano_fim <= 0:
            return False, "O ano de início e o ano de fim não podem ser negativos ou zero."
        
        if ano_inicio > ano_fim:
            return False, "O ano de início não pode ser maior que o ano de fim."
        
        if credor_nome.isdigit():
            return False, "O nome do credor não pode ser um número."
        
        if not credor_nome.strip():
            return False, "O nome do credor não pode estar vazio."
        
        return True, ""

    def buscar_diarias(self, cidade, orgao, ano_inicio, ano_fim, credor_nome, verbose=False):
        valido, mensagem = self.validar_entrada(ano_inicio, ano_fim, credor_nome)
        if not valido:
            self.atualizar_progresso(f"[bold red]❌ {mensagem}[/bold red]")
            return False, mensagem, [], 0.0
        
        ano_inicio = int(ano_inicio)
        ano_fim = int(ano_fim)
        
        if cidade not in self.cidades_orgaos:
            self.atualizar_progresso(f"[bold red]❌ Cidade '{cidade}' não encontrada.[/bold red]")
            return False, f"Cidade '{cidade}' não encontrada.", [], 0.0
        
        orgaos = self.cidades_orgaos[cidade]
        if orgao not in orgaos:
            self.atualizar_progresso(f"[bold red]❌ Órgão '{orgao}' não encontrado para a cidade '{cidade}'.[/bold red]")
            return False, f"Órgão '{orgao}' não encontrado para a cidade '{cidade}'.", [], 0.0
        
        orgao_config = orgaos[orgao]
        modelo_portal = orgao_config.get('modelo_portal', '').lower()
        metodo_busca = orgao_config.get('metodo_busca', '').lower()
        url_base = orgao_config.get('url_base', '')

        try:
            timeout = int(orgao_config.get('timeout', 7))
            if timeout <= 0:
                timeout = 7
        except (ValueError, TypeError):
            timeout = 7

        
        if not modelo_portal or not metodo_busca or not url_base:
            self.atualizar_progresso(f"[bold red]❌ Configuração incompleta para o órgão '{orgao}'.[/bold red]")
            return False, f"Configuração incompleta para o órgão '{orgao}'.", [], 0.0
        
        if modelo_portal not in self.portal_implementations:
            self.atualizar_progresso(f"[bold red]❌ Modelo de portal '{modelo_portal}' não suportado.[/bold red]")
            return False, f"Modelo de portal '{modelo_portal}' não suportado.", [], 0.0
        
        if metodo_busca not in self.portal_implementations[modelo_portal]:
            self.atualizar_progresso(f"[bold red]❌ Método de busca '{metodo_busca}' não suportado para o portal '{modelo_portal}'.[/bold red]")
            return False, f"Método de busca '{metodo_busca}' não suportado para o portal '{modelo_portal}'.", [], 0.0
        
        portal_class = self.portal_implementations[modelo_portal][metodo_busca]
        portal_scraper = portal_class(callback=self.callback, verbose=verbose)
        
        self.atualizar_progresso(f"[bold blue]🔍 Buscando diárias em {orgao} - {cidade} via {modelo_portal}/{metodo_busca}[/bold blue]")
        
        try:
            valor_total, dados_empenhos = portal_scraper.buscar_diarias(url_base, ano_inicio, ano_fim, credor_nome, timeout)
            
            primeiro_credor = credor_nome
            if dados_empenhos:
                primeiro_credor = dados_empenhos[0]['Credor']
            
            periodo = f"{ano_inicio} a {ano_fim}" if ano_inicio != ano_fim else str(ano_inicio)
            
            if valor_total > 0:
                self.atualizar_progresso(
                f"[bold green]✅ No período de {periodo}, o credor {primeiro_credor} recebeu aproximadamente R$ {valor_total:.2f} em diárias de viagem.[/bold green]"
            )

                return True, "", dados_empenhos, valor_total 
            else:
                mensagem_final = f" Nenhum valor encontrado para o credor '{primeiro_credor}' no período de {periodo}."
                self.atualizar_progresso(f"[bold yellow]⚠️ {mensagem_final}[/bold yellow]")
                return True, mensagem_final, [], 0.0
                
        except Exception as e:
            error_str = str(e)
            
            if "NameResolutionError" in error_str or "getaddrinfo failed" in error_str:
                host = None
                if "host=" in error_str:
                    host_match = re.search(r"host='([^']+)'", error_str)
                    if host_match:
                        host = host_match.group(1)
                
                if host:
                    erro_msg = f"Erro de conexão: Não foi possível encontrar o servidor '{host}'. Verifique sua conexão com a internet ou se o site está disponível."
                else:
                    erro_msg = "Erro de conexão: Não foi possível encontrar o servidor. Verifique sua conexão com a internet ou se o site está disponível."
            
            elif "ConnectTimeoutError" in error_str or "Read timed out" in error_str:
                erro_msg = "Erro de conexão: O servidor demorou muito para responder. Verifique sua conexão com a internet ou tente novamente mais tarde."
            
            elif "ConnectionRefusedError" in error_str or "Connection refused" in error_str:
                erro_msg = "Erro de conexão: O servidor recusou a conexão. O site pode estar temporariamente indisponível."
            
            elif "SSLError" in error_str:
                erro_msg = "Erro de segurança: Não foi possível estabelecer uma conexão segura com o servidor. O site pode estar com problemas de certificado."
            
            elif "ConnectionError" in error_str or "Connection aborted" in error_str:
                erro_msg = "Erro de conexão: Não foi possível conectar ao servidor. Verifique sua conexão com a internet ou tente novamente mais tarde."
            
            elif "HTTPError" in error_str or "status code" in error_str:
                status_match = re.search(r"(\d{3})", error_str)
                if status_match:
                    status_code = status_match.group(1)
                    erro_msg = f"Erro HTTP {status_code}: O servidor retornou um erro. O site pode estar com problemas ou em manutenção."
                else:
                    erro_msg = "Erro HTTP: O servidor retornou um erro. O site pode estar com problemas ou em manutenção."
            
            else:
                erro_msg = f"Erro ao buscar diárias: {str(e)}"
            
            self.atualizar_progresso(f"[bold red]❌ {erro_msg}[/bold red]")
            return False, erro_msg, [], 0.0


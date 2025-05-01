import requests
import json
import urllib.parse
import re
from datetime import datetime, timedelta
from rich.console import Console
from ..base_portal import BasePortal
from src.core.utils import remover_acentos, carregar_ou_criar_cidades

class MemoryApi(BasePortal):
    def __init__(self, callback=None, verbose=False):
        super().__init__(callback, verbose)
        self.console = Console()
        self.total_empenhos = 0
        self.total_meses = 0
        self.nome_completo_credor = None
        self.session = requests.Session()
        self.local_storage = {}  
        
    def establish_session(self, timeout=30):
        """
        Establish a session by visiting the login page first and extracting localStorage data
        """
        login_url = "https://ilai.memory.com.br/#/entidades/login/9C8FYL/1/"
        
        self.atualizar_progresso(
            f"[bold blue]🔑 Estabelecendo sessão com o portal Memory...[/bold blue]",
            None, None, self.total_empenhos, self.total_meses
        )
        
        try:
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.9',
                'Accept-Language': 'pt-BR,pt;q=0.9,en-US;q=0.8,en;q=0.7',
                'Connection': 'keep-alive',
                'Upgrade-Insecure-Requests': '1',
                'Cache-Control': 'max-age=0',
            }
            
            if self.verbose:
                self.atualizar_progresso(
                    f"[cyan][DEBUG] Acessando URL de login: {login_url} [/cyan]",
                    None, None, self.total_empenhos, self.total_meses
                )
            
            response = self.session.get(login_url, headers=headers, timeout=timeout)
            
            if self.verbose:
                self.atualizar_progresso(
                    f"[cyan][DEBUG] Status da resposta do login: {response.status_code}[/cyan]",
                    None, None, self.total_empenhos, self.total_meses
                )
            
            if response.status_code == 200:
                try:
                    local_storage_data = re.search(r'pouch_check_localstorage\s+1(.*?)ouvidoria', response.text, re.DOTALL)
                    
                    if local_storage_data:
                        data_str = local_storage_data.group(1)
                        self.atualizar_progresso(
                            f"[cyan][DEBUG] Dados de localStorage encontrados[/cyan]",
                            None, None, self.total_empenhos, self.total_meses
                        )
                        
                        pairs = re.findall(r'(\w+)\s+(.*?)(?=\w+\s+|$)', data_str)
                        for key, value in pairs:
                            self.local_storage[key] = value
                            
                        if self.verbose:
                            self.atualizar_progresso(
                                f"[cyan][DEBUG] localStorage simulado: {self.local_storage}[/cyan]",
                                None, None, self.total_empenhos, self.total_meses
                            )
                except Exception as e:
                    self.atualizar_progresso(
                        f"[yellow][WARN] Erro ao extrair dados de localStorage: {str(e)}[/yellow]",
                        None, None, self.total_empenhos, self.total_meses
                    )
            
            if self.verbose:
                self.atualizar_progresso(
                    f"[cyan][DEBUG] Headers da resposta: {dict(response.headers)}[/cyan]",
                    None, None, self.total_empenhos, self.total_meses
                )
            
            if response.status_code == 200:
                self.atualizar_progresso(
                    f"[bold green]✅ Sessão estabelecida com sucesso.[/bold green]",
                    None, None, self.total_empenhos, self.total_meses
                )
                
                if self.verbose:
                    self.atualizar_progresso(
                        f"[cyan][DEBUG] Cookies obtidos: {dict(self.session.cookies)}[/cyan]",
                        None, None, self.total_empenhos, self.total_meses
                    )
                
                self.session.cookies.set('codigo_auxiliar', '9C8FYL', domain='ilai.memory.com.br', path='/')
                self.session.cookies.set('codigo_entidade', '1', domain='ilai.memory.com.br', path='/')
                self.session.cookies.set('codigo_ibge', '3148509', domain='ilai.memory.com.br', path='/')
                self.session.cookies.set('exercicio', '2025', domain='ilai.memory.com.br', path='/')
                
                if self.verbose:
                    self.atualizar_progresso(
                        f"[cyan][DEBUG] Cookies setados após configuração pré-definida.[/cyan]",
                        None, None, self.total_empenhos, self.total_meses
                    )
                
                return True
            else:
                self.atualizar_progresso(
                    f"[bold red]❌ Falha ao estabelecer sessão: {response.status_code}[/bold red]",
                    None, None, self.total_empenhos, self.total_meses
                )
                return False
                
        except Exception as e:
            self.atualizar_progresso(
                f"[bold red]❌ Erro ao estabelecer sessão: {str(e)}[/bold red]",
                None, None, self.total_empenhos, self.total_meses
            )
            return False
    
    def obter_nome_completo(self, url_base, credor_nome, ano_inicio, ano_fim, timeout=30):
        """
        Faz uma requisição inicial para obter o nome completo do credor
        """
        self.atualizar_progresso(
            f"[bold blue]🔍 Buscando nome completo para '{credor_nome}'...[/bold blue]",
            None, None, self.total_empenhos, self.total_meses
        )
        
        data_inicial = f"{ano_inicio}-01-01T03:00:00.000Z"
        data_final = f"{ano_fim}-12-31T03:00:00.000Z"
        
        params = {
            "$format": "json",
            "$inlinecount": "allpages",
            "$skip": 0,
            "$top": 1, 
            "dataInicial": f"datetimeoffset'{data_inicial}'",
            "dataFinal": f"datetimeoffset'{data_final}'",
            "nomeServidor": credor_nome
        }
        
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            'Accept': 'application/json, text/javascript, */*; q=0.01',
            'Accept-Language': 'pt-BR,pt;q=0.9,en-US;q=0.8,en;q=0.7',
            'Referer': 'https://ilai.memory.com.br/',
            'X-Requested-With': 'XMLHttpRequest',
            'Connection': 'keep-alive',
            'Pragma': 'no-cache',
            'Cache-Control': 'no-cache',
        }
        
        for key, value in self.local_storage.items():
            headers[f'X-LocalStorage-{key}'] = value
        
        try:
            response = self.session.get(url_base, params=params, headers=headers, timeout=timeout)
            
            if response.status_code == 200:
                data = response.json()
                
                if 'd' in data and 'results' in data['d'] and data['d']['results']:
                    primeiro_item = data['d']['results'][0]
                    nome_completo = primeiro_item.get('nome_servidor', '')
                    
                    if nome_completo:
                        self.atualizar_progresso(
                            f"[bold blue]ℹ️ Usando o nome completo '{nome_completo}' para o restante da busca.[/bold blue]",
                            None, None, self.total_empenhos, self.total_meses
                        )
                        return nome_completo
                    
                self.atualizar_progresso(
                    f"[yellow]⚠️ Não foi possível encontrar o nome completo para '{credor_nome}'[/yellow]",
                    None, None, self.total_empenhos, self.total_meses
                )
                return credor_nome
                
        except Exception as e:
            self.atualizar_progresso(
                f"[yellow]⚠️ Erro ao buscar nome completo: {str(e)}[/yellow]",
                None, None, self.total_empenhos, self.total_meses
            )
            return credor_nome
        
        return credor_nome
        
    def buscar_diarias(self, url_base, ano_inicio, ano_fim, credor_nome, timeout=None):
        """
        Busca diárias usando a API Memory
        
        Args:
            url_base: URL da API
            ano_inicio: Ano inicial da busca
            ano_fim: Ano final da busca
            credor_nome: Nome do credor a ser buscado
            timeout: Timeout para requisições (opcional, usa o valor do cidades.json se disponível)
            
        Returns:
            tuple: (valor_total, dados_empenhos)
        """
        if timeout is None:
            timeout = 30
            
        self.atualizar_progresso(
            "[bold yellow]⚠️ Atenção: os resultados ainda podem estar imprecisos, pois este recurso está em desenvolvimento.[/bold yellow]",
            None, None, self.total_empenhos, self.total_meses
        )
  
        self.atualizar_progresso(
            f"[bold blue]🔍 Buscando diárias via API Memory para {credor_nome} ({ano_inicio}-{ano_fim})[/bold blue]",
            None, None, self.total_empenhos, self.total_meses
        )
        
        if self.verbose:
            self.atualizar_progresso(
                f"[cyan][DEBUG] Usando timeout de {timeout} segundos para requisições[/cyan]",
                None, None, self.total_empenhos, self.total_meses
            )
        
        valor_total = 0.0
        dados_empenhos = []
        
        if not self.establish_session(timeout):
            self.atualizar_progresso(
                f"[bold red]❌ Não foi possível estabelecer sessão com o portal Memory. Abortando busca.[/bold red]",
                None, None, self.total_empenhos, self.total_meses
            )
            return valor_total, dados_empenhos
        
        nome_completo = self.obter_nome_completo(url_base, credor_nome, ano_inicio, ano_fim, timeout)
        
        data_inicial = f"{ano_inicio}-01-01T03:00:00.000Z"
        data_final = f"{ano_fim}-12-31T03:00:00.000Z"
        

        page_size = 2147483647 
        skip = 0
        has_more = True
        all_items = []
        
        with self.console.status("[yellow]Processando diárias, por favor aguarde..."):
            while has_more:
                params = {
                    "$format": "json",
                    "$inlinecount": "allpages",
                    "$skip": skip,
                    "$top": page_size,
                    "dataInicial": f"datetimeoffset'{data_inicial}'",
                    "dataFinal": f"datetimeoffset'{data_final}'",
                    "nomeServidor": nome_completo
                }
                
                try:
                    query_string = "&".join([f"{k}={urllib.parse.quote(str(v))}" for k, v in params.items()])
                    full_url = f"{url_base}?{query_string}"
                    
                    if self.verbose:
                        self.atualizar_progresso(
                            f"[cyan][DEBUG] URL da requisição (página {skip//page_size + 1}): {full_url}[/cyan]",
                            None, None, self.total_empenhos, self.total_meses
                        )
                    
                    headers = {
                        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
                        'Accept': 'application/json, text/javascript, */*; q=0.01',
                        'Accept-Language': 'pt-BR,pt;q=0.9,en-US;q=0.8,en;q=0.7',
                        'Referer': 'https://ilai.memory.com.br/',
                        'X-Requested-With': 'XMLHttpRequest',
                        'Connection': 'keep-alive',
                        'Pragma': 'no-cache',
                        'Cache-Control': 'no-cache',
                    }
                    
                    for key, value in self.local_storage.items():
                        headers[f'X-LocalStorage-{key}'] = value
                    
                    if self.verbose:
                        self.atualizar_progresso(
                            f"[cyan][DEBUG] Cookies antes da requisição à API: {dict(self.session.cookies)}[/cyan]",
                            None, None, self.total_empenhos, self.total_meses
                        )
                    
                    response = self.session.get(url_base, params=params, headers=headers, timeout=timeout)
                    
                    if self.verbose:
                        self.atualizar_progresso(
                            f"[cyan][DEBUG] Status da resposta (página {skip//page_size + 1}): {response.status_code}[/cyan]",
                            None, None, self.total_empenhos, self.total_meses
                        )
                    
                    if response.status_code == 200:
                        try:
                            data = response.json()
                            
                            if 'd' in data and 'results' in data['d']:
                                items = data['d']['results']
                                total_count = int(data['d'].get('__count', '0'))
                                
                                self.total_empenhos = total_count
                                
                                all_items.extend(items)
                                
                                if len(items) < page_size or skip + len(items) >= total_count:
                                    has_more = False
                                    self.atualizar_progresso(
                                        f"[bold green]✅ Todas as páginas processadas. Total de {len(all_items)} itens recuperados.[/bold green]",
                                        None, None, self.total_empenhos, self.total_meses
                                    )
                                else:
                                    skip += page_size
                                    self.atualizar_progresso(
                                        f"[blue]📄 Processando página {skip//page_size + 1}... ({len(all_items)}/{total_count} itens)[/blue]",
                                        None, None, self.total_empenhos, self.total_meses
                                    )
                            else:
                                has_more = False
                                self.atualizar_progresso(
                                    "[bold yellow]⚠️ Formato de resposta da API inesperado.[/bold yellow]",
                                    None, None, self.total_empenhos, self.total_meses
                                )
                        except json.JSONDecodeError as e:
                            has_more = False
                            self.atualizar_progresso(
                                f"[bold red]❌ Erro ao decodificar JSON: {str(e)}[/bold red]",
                                None, None, self.total_empenhos, self.total_meses
                            )
                    else:
                        has_more = False
                        self.atualizar_progresso(
                            f"[bold red]❌ Erro na requisição à API: {response.status_code}[/bold red]",
                            None, None, self.total_empenhos, self.total_meses
                        )
                
                except requests.exceptions.Timeout:
                    has_more = False
                    self.atualizar_progresso(
                        f"[bold red]❌ Tempo limite excedido ao acessar a API.[/bold red]",
                        None, None, self.total_empenhos, self.total_meses
                    )
                except requests.exceptions.ConnectionError:
                    has_more = False
                    self.atualizar_progresso(
                        f"[bold red]❌ Erro de conexão ao acessar a API.[/bold red]",
                        None, None, self.total_empenhos, self.total_meses
                    )
                except Exception as e:
                    has_more = False
                    self.atualizar_progresso(
                        f"[bold red]❌ Erro ao buscar diárias via API: {str(e)}[/bold red]",
                        None, None, self.total_empenhos, self.total_meses
                    )
            
            meses_unicos = set()
            for item in all_items:
                if 'data_empenho' in item and item['data_empenho']:
                    try:
                        data_empenho = datetime.strptime(item['data_empenho'], '%d/%m/%Y')
                        meses_unicos.add(f"{data_empenho.year}-{data_empenho.month}")
                    except (ValueError, TypeError):
                        pass
            
            self.total_meses = len(meses_unicos)
            
            self.atualizar_progresso(
                f"Encontrados {self.total_empenhos} empenhos em {self.total_meses} meses no período {ano_inicio}-{ano_fim}",
                None, None, self.total_empenhos, self.total_meses
            )
            
            for i, item in enumerate(all_items):
                try:
                    nome_servidor = item.get('nome_servidor', '')
                    numero_empenho = item.get('numero_empenho', '')
                    data_empenho = item.get('data_empenho', '')
                    descricao_empenho = item.get('descricao_empenho', '')
                    valor_empenho = item.get('valor_empenho', 0.0)
                    numero_pagamento = item.get('numero_pagamento', '')
                    data_pagamento = item.get('data_pagamento', '')
                    valor_pago = item.get('valor_pago', 0.0)
                    id_empenho = item.get('id_empenho', '')
                    descricao_liquidacao = item.get('descricao_liquidacao', '')
                    unidade_orcamentaria = item.get('unidade_orcamentaria', '')
                    
                    try:
                        valor_float = float(valor_pago)
                    except (ValueError, TypeError):
                        valor_float = 0.0
                    
                    valor_formatado = f"R$ {valor_float:.2f}".replace('.', ',')
                    
                    try:
                        data_obj = datetime.strptime(data_empenho, '%d/%m/%Y')
                        ano = data_obj.year
                        mes = data_obj.month
                    except (ValueError, TypeError):
                        ano = ano_inicio
                        mes = 1
                    
                    self.atualizar_progresso(
                        f"[bold green]✅ Diária de Viagem para {nome_servidor} no empenho N°{numero_empenho} "
                        f"no dia {data_empenho} no valor de {valor_formatado}.[/bold green]",
                        str(numero_empenho), data_empenho, self.total_empenhos, self.total_meses
                    )
                    
                    cidades = carregar_ou_criar_cidades()
                    descricao_sem_acento = remover_acentos(descricao_liquidacao or descricao_empenho or '').lower()
                    cidade_encontrada = None

                    for cidade in cidades:
                        if cidade.lower() in descricao_sem_acento:
                            cidade_encontrada = cidade
                            break

                    descricao_final = descricao_liquidacao or descricao_empenho or ''
                    if cidade_encontrada:
                        descricao_final = f"VIAGEM A {cidade_encontrada}"
                    elif "viagem" in descricao_sem_acento:
                        descricao_final = "VIAGEM A LOCAL NÃO INFORMADO"
                    
                    dados_empenhos.append({
                        'Ano': ano,
                        'Mês': mes,
                        'Número do Empenho': numero_empenho,
                        'Data': data_empenho,
                        'Modalidade': 'Diária',
                        'Credor': nome_servidor,
                        'Ordenador': unidade_orcamentaria,
                        'CPF do Ordenador': '',
                        'Valor Bruto': valor_formatado,
                        'Descrição': descricao_final.upper(),
                        'Detalhes': f"https://pavao.mg.gov.br/"
                    })
                    
                    valor_total += valor_float
                
                except Exception as e:
                    self.atualizar_progresso(
                        f"[bold red]❌ Erro ao processar item {i+1}: {str(e)}[/bold red]",
                        None, None, self.total_empenhos, self.total_meses
                    )
        
        return valor_total, dados_empenhos


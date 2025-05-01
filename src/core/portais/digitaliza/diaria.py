import time
import requests
from bs4 import BeautifulSoup
from urllib.parse import urlparse
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn, TimeElapsedColumn

from ..base_portal import BasePortal
from src.core.utils import carregar_ou_criar_palavras_chave, carregar_ou_criar_cidades, remover_acentos

class DigitalizaDiaria(BasePortal):
    def __init__(self, callback=None, verbose=False):
        super().__init__(callback, verbose)
        self.console = Console()
        self.max_retries = 3
        self.retry_delays = [5, 10, 30]
        self.connection_lost = False
        self.total_empenhos = 0 
        self.total_meses = 0   
    
    def countdown_retry(self, seconds, message):
        """Display a real-time countdown for retry attempts"""
        with Progress(
            SpinnerColumn(),
            TextColumn("[bold yellow]{task.description}"),
            TimeElapsedColumn(),
            console=self.console,
            transient=True
        ) as progress:
            task = progress.add_task(f"{message}", total=seconds)
            for i in range(seconds):
                self.atualizar_progresso(
                    f"[bold yellow]⏱️ {message} ({seconds-i} segundos restantes...)[/bold yellow]"
                )
                time.sleep(1)
                progress.update(task, advance=1)
    
    def buscar_diarias(self, url_base, ano_inicio, ano_fim, credor_nome, timeout=30):
        valor_total = 0.0
        dados_empenhos = []
        
        self.total_empenhos = 0 
        self.total_meses = 0    
        
        connection_issues = {
            'dns_failures': 0,
            'timeouts': 0,
            'connection_errors': 0,
            'last_error_time': 0,
            'last_error_message': None
        }
        
        try:
            diarias = self.pegar_urls_diarias(url_base, self.verbose, timeout)
            
            diarias_filtradas = self.filtrar_diarias_por_ano(diarias, ano_inicio, ano_fim)
            self.total_meses = len(diarias_filtradas) 
            self.atualizar_progresso(
                f"Encontrados {self.total_meses} meses no período {ano_inicio}-{ano_fim}",
                None, None, self.total_empenhos, self.total_meses 
            )
            
            with self.console.status("[yellow]Processando diárias, por favor aguarde..."):
                for i, diaria in enumerate(diarias_filtradas):
                    url = diaria.get('url')
                    try:
                        ano = int(diaria.get('ano'))
                        mes = int(diaria.get('mes'))
                    except (TypeError, ValueError):
                        self.atualizar_progresso(f"[red]⚠️ Dados inválidos na diária {i+1}, pulando...")
                        continue

                    mes_str = f"{mes:02d}"
                    ano_str = str(ano)

                    self.atualizar_progresso(
                        f"🔎 Lendo diárias {i+1} de {len(diarias_filtradas)} ({mes_str}/{ano_str})"
                    )

                    if not url:
                        self.atualizar_progresso(f"[red]⚠️ URL ausente na diária {i+1}, pulando...")
                        continue

                    retry_count = 0
                    while retry_count <= self.max_retries:
                        try:
                            if self.connection_lost:
                                self.atualizar_progresso(
                                    "[bold green]✅ Conexão restabelecida! Continuando processamento...[/bold green]"
                                )
                                self.connection_lost = False
                                
                            valor, dados = self.extrair_diarias(url, ano, mes, credor_nome, timeout)
                            valor_total += valor
                            dados_empenhos.extend(dados)
                            break 
                            
                        except (requests.exceptions.ConnectTimeout, requests.exceptions.ReadTimeout):
                            connection_issues['timeouts'] += 1
                            current_time = time.time()
                            self.connection_lost = True
                            
                            if not self.connection_lost or current_time - connection_issues['last_error_time'] > 10:
                                connection_issues['last_error_time'] = current_time
                                self.atualizar_progresso(
                                    "[bold red]❌ Conexão com o servidor perdida![/bold red]"
                                )
                            
                            if retry_count < self.max_retries:
                                delay = self.retry_delays[retry_count]
                                retry_message = f"Tentativa {retry_count+1}/{self.max_retries+1} de reconexão"
                                self.countdown_retry(delay, retry_message)
                                retry_count += 1
                            else:
                                self.atualizar_progresso(
                                    f"[bold red]❌ Tempo limite excedido após {self.max_retries+1} tentativas. "
                                    f"Pulando esta diária.[/bold red]"
                                )
                                break
                                
                        except requests.exceptions.ConnectionError as e:
                            self.connection_lost = True
                            if "NameResolutionError" in str(e):
                                connection_issues['dns_failures'] += 1
                                error_type = "DNS"
                                error_detail = "Não foi possível resolver o nome do servidor"
                            else:
                                connection_issues['connection_errors'] += 1
                                error_type = "Conexão"
                                error_detail = "Falha na conexão com o servidor"
                                
                            current_time = time.time()
                            
                            if current_time - connection_issues['last_error_time'] > 10:
                                connection_issues['last_error_time'] = current_time
                                self.atualizar_progresso(
                                    f"[bold red]❌ Erro de {error_type}: {error_detail}. Verifique sua conexão com a internet.[/bold red]"
                                )
                            
                            if retry_count < self.max_retries:
                                delay = self.retry_delays[retry_count]
                                retry_message = f"Tentativa {retry_count+1}/{self.max_retries+1} de reconexão"
                                self.countdown_retry(delay, retry_message)
                                retry_count += 1
                            else:
                                self.atualizar_progresso(
                                    f"[bold red]❌ Falha de {error_type} após {self.max_retries+1} tentativas. "
                                    f"Pulando esta diária.[/bold red]"
                                )
                                break
                                
                        except Exception as e:
                            error_msg = str(e)
                            if error_msg != connection_issues['last_error_message']:
                                connection_issues['last_error_message'] = error_msg
                                self.atualizar_progresso(
                                    f"[bold red]❌ Erro ao processar diária: {error_msg}[/bold red]"
                                )
                            break
            
            if connection_issues['dns_failures'] > 0 or connection_issues['timeouts'] > 0 or connection_issues['connection_errors'] > 0:
                self.atualizar_progresso(
                    f"[bold yellow]⚠️ Resumo de problemas de conexão: {connection_issues['dns_failures']} falhas de DNS, "
                    f"{connection_issues['timeouts']} timeouts, {connection_issues['connection_errors']} erros de conexão[/bold yellow]"
                )
                
            return valor_total, dados_empenhos
            
        except Exception as e:
            raise
    
    def pegar_urls_diarias(self, base_url, verbose=False, timeout=7):
        urls_diarias = []
        self.atualizar_progresso(f"Acessando URL principal: {base_url}")
        
        retry_count = 0
        while retry_count <= self.max_retries:
            try:
                response = self.make_request(base_url)

                if verbose:
                    parsed_url = urlparse(base_url)
                    host_info = f"{parsed_url.hostname}:{parsed_url.port or 80 if parsed_url.scheme == 'http' else 443}"
                    self.atualizar_progresso(
                        f"[cyan][VERBOSE][/cyan] Requisição para {host_info} (Timeout {timeout}s) - Status {response.status_code}"
                    )

                soup = BeautifulSoup(response.text, 'html.parser')
                links = soup.find_all('a', class_='btn_table')
                
                if links:
                    for link in links:
                        detalhe_url = link['href']
                        url_parts = detalhe_url.split('/')
                        if len(url_parts) >= 4:
                            try:
                                ano_diaria = int(url_parts[-3])
                                mes_diaria = int(url_parts[-2])
                                urls_diarias.append({
                                    'ano': ano_diaria,
                                    'mes': mes_diaria,
                                    'url': detalhe_url
                                })
                            except ValueError:
                                self.atualizar_progresso(
                                    f"[yellow]⚠️ Ano ou mês inválido encontrado na URL: {detalhe_url}[/yellow]"
                                )
                else:
                    self.atualizar_progresso("[yellow]⚠️ Nenhuma diária encontrada na página principal.[/yellow]")
                
                break
                
            except requests.exceptions.ConnectionError as e:
                if "NameResolutionError" in str(e):
                    error_msg = f"[bold red]❌ Erro de DNS: Não foi possível resolver o nome '{urlparse(base_url).hostname}'[/bold red]"
                else:
                    error_msg = "[bold red]❌ Erro de conexão. Verifique sua internet.[/bold red]"
                
                if retry_count < self.max_retries:
                    delay = self.retry_delays[retry_count]
                    self.atualizar_progresso(
                        f"{error_msg}\n[yellow]⚠️ Nova tentativa em {delay} segundos...[/yellow]"
                    )
                    time.sleep(delay)
                    retry_count += 1
                else:
                    self.atualizar_progresso(
                        f"{error_msg}\n[bold red]❌ Número máximo de tentativas excedido.[/bold red]"
                    )
                    raise
                
            except requests.exceptions.Timeout:
                if retry_count < self.max_retries:
                    delay = self.retry_delays[retry_count]
                    self.atualizar_progresso(
                        f"[bold yellow]⚠️ Nova tentativa em {delay} segundos...[/bold yellow]"
                    )

                    time.sleep(delay)
                    retry_count += 1
                else:
                    self.atualizar_progresso(
                        f"[bold red]❌ Tempo limite excedido após {self.max_retries} tentativas.[/bold red]"
                    )
                    raise
                
            except Exception as e:
                self.atualizar_progresso(f"[bold red]❌ Erro ao acessar a URL principal: {str(e)}[/bold red]")
                raise

        self.total_empenhos = len(urls_diarias) 
        self.atualizar_progresso(
            f"Total de URLs de diárias encontradas: {self.total_empenhos}",
            None, None, self.total_empenhos, self.total_meses  
        )
        return urls_diarias
    
    def filtrar_diarias_por_ano(self, diarias, ano_inicio, ano_fim):
        return [diaria for diaria in diarias if ano_inicio <= diaria['ano'] <= ano_fim]
    
    def extrair_diarias(self, url_diaria, ano, mes, credor_nome, timeout):
        response = requests.get(url_diaria, timeout=timeout)
        
        if response.status_code == 200:
            soup = BeautifulSoup(response.text, 'html.parser')
            rows = soup.find_all('tr')
            
            valor_total = 0.0
            dados_diarias = []
            
            for row in rows[1:]:
                colunas = row.find_all('td')
                
                if len(colunas) >= 5: 
                    try:
                        credor_tabela = colunas[0].get_text().strip()
                        numero_empenho = colunas[1].get_text().strip()
                        data = colunas[2].get_text().strip()
                        valor_bruto = colunas[3].get_text().strip()
                        
                        link_detalhe = colunas[4].find('a')
                        if not link_detalhe:
                            continue
                            
                        link_detalhe_url = link_detalhe['href']
                        
                        credor_nome_normalizado = remover_acentos(credor_nome).lower()
                        credor_tabela_normalizado = remover_acentos(credor_tabela).lower()
                        
                        if credor_nome_normalizado in credor_tabela_normalizado:
                            self.atualizar_progresso(
                                f"[cyan]🔍 Verificando a diária N°{numero_empenho}...[/cyan]",
                                numero_empenho, data, self.total_empenhos, self.total_meses 
                            )
                                                        
                            valor, dados_detalhados = self.extrair_dados_diaria(link_detalhe_url, credor_nome, numero_empenho, data, valor_bruto)
                            
                            if valor > 0:
                                dados_diarias.append({
                                    'Ano': ano,
                                    'Mês': mes,
                                    'Número do Empenho': numero_empenho,
                                    'Data': dados_detalhados['Data'],
                                    'Modalidade': dados_detalhados['Modalidade'],
                                    'Credor': dados_detalhados['Credor'],
                                    'Ordenador': dados_detalhados['Ordenador'],
                                    'CPF do Ordenador': dados_detalhados['CPF do Ordenador'],
                                    'Valor Bruto': dados_detalhados['Valor Bruto'],
                                    'Descrição': dados_detalhados['Descrição'].upper(),
                                    'Detalhes': link_detalhe_url
                                })
                                valor_total += valor
                            
                    except Exception as e:
                        self.atualizar_progresso(f"[yellow]⚠️ Erro ao processar linha da tabela: {str(e)}[/yellow]")
            
            return valor_total, dados_diarias
        return 0.0, []

    def extrair_dados_diaria(self, url_diaria, credor_nome, numero_empenho, data_tabela, valor_bruto_tabela):
        """Extract detailed information from the diaria details page"""
        retry_count = 0
        last_error = None
        
        while retry_count <= self.max_retries:
            try:
                response = requests.get(url_diaria, timeout=15)
                
                if response.status_code == 200:
                    soup = BeautifulSoup(response.text, 'html.parser')
                    
                    credor = None
                    credor_tags = soup.find_all(['input', 'p', 'div', 'span', 'td'], 
                                              id=lambda x: x and ('credor' in x.lower() if x else False))
                    
                    if not credor_tags:
                        credor_tags = soup.find_all(text=lambda t: t and ('credor' in t.lower() or 'beneficiário' in t.lower()))
                    
                    for tag in credor_tags:
                        if hasattr(tag, 'value') and tag.get('value'):
                            credor = tag.get('value').strip()
                            break
                        elif hasattr(tag, 'find_next'):
                            next_elem = tag.find_next()
                            if next_elem and next_elem.text.strip():
                                credor = next_elem.text.strip()
                                break
                    
                    if not credor:
                        credor = credor_nome
                    
                    ordenador = "Não Informado"
                    ordenador_tags = soup.find_all(['input', 'p', 'div', 'span', 'td'], 
                                                 id=lambda x: x and ('ordenador' in x.lower() if x else False))
                    
                    if not ordenador_tags:
                        ordenador_tags = soup.find_all(text=lambda t: t and ('ordenador' in t.lower() or 'autorizado por' in t.lower()))
                    
                    for tag in ordenador_tags:
                        if hasattr(tag, 'value') and tag.get('value'):
                            ordenador = tag.get('value').strip()
                            break
                        elif hasattr(tag, 'find_next'):
                            next_elem = tag.find_next()
                            if next_elem and next_elem.text.strip():
                                ordenador = next_elem.text.strip()
                                break
                    
                    cpf = "Não Informado"
                    cpf_tags = soup.find_all(['input', 'p', 'div', 'span', 'td'], 
                                           id=lambda x: x and ('c_ordenador' in x.lower() if x else False))
                    
                    for tag in cpf_tags:
                        if hasattr(tag, 'value') and tag.get('value'):
                            cpf = tag.get('value').strip()
                            break
                    
                    descricao = None
                    descricao_tags = soup.find_all(['textarea', 'p', 'div', 'span', 'td'], 
                                                 id=lambda x: x and ('descricao' in x.lower() if x else False))
                    
                    if not descricao_tags:
                        descricao_tags = soup.find_all(text=lambda t: t and ('motivo' in t.lower() or 'finalidade' in t.lower() 
                                                                           or 'descrição' in t.lower() or 'destino' in t.lower()))
                    
                    for tag in descricao_tags:
                        if hasattr(tag, 'text') and tag.text.strip():
                            descricao = tag.text.strip()
                            break
                        elif hasattr(tag, 'find_next'):
                            next_elem = tag.find_next()
                            if next_elem and next_elem.text.strip():
                                descricao = next_elem.text.strip()
                                break
                    
                    if not descricao:
                        descricao = "DIÁRIA DE VIAGEM"
                    
                    cidades = carregar_ou_criar_cidades()
                    descricao_sem_acento = remover_acentos(descricao).lower()
                    
                    cidade_encontrada = None
                    for cidade in cidades:
                        if cidade.lower() in descricao_sem_acento:
                            cidade_encontrada = cidade
                            break
                    
                    if cidade_encontrada:
                        descricao = f"VIAGEM A {cidade_encontrada}"
                    else:
                        page_text = soup.get_text().lower()
                        page_text_sem_acento = remover_acentos(page_text)
                        
                        for cidade in cidades:
                            if cidade.lower() in page_text_sem_acento:
                                descricao = f"VIAGEM A {cidade}"
                                break
                        else:
                            descricao = "VIAGEM A LOCAL NÃO INFORMADO"
                    
                    valor_float = 0.0
                    valor_bruto = valor_bruto_tabela
                    valor_tags = soup.find_all(['input', 'p', 'div', 'span', 'td'], 
                                             id=lambda x: x and ('valor' in x.lower() if x else False))
                    
                    for tag in valor_tags:
                        if hasattr(tag, 'value') and tag.get('value'):
                            valor_bruto = tag.get('value').strip()
                            break
                    
                    try:
                        valor_bruto_clean = valor_bruto.replace("R$", "").replace(".", "").replace(",", ".").strip()
                        valor_float = float(valor_bruto_clean)
                    except ValueError:
                        self.atualizar_progresso(f"[yellow]⚠️ Erro ao converter valor: {valor_bruto}[/yellow]")
                    
                    credor_nome_normalizado = remover_acentos(credor_nome).lower()
                    credor_normalizado = remover_acentos(credor).lower()
                    
                    if credor_nome_normalizado in credor_normalizado:
                        self.atualizar_progresso(
                            f"[bold green]✅ Diária de Viagem para {credor} no empenho N°{numero_empenho} "
                            f"no dia {data_tabela} no valor de {valor_bruto}.[/bold green]"
                        )
                        
                        dados = {
                            'Número do Empenho': numero_empenho,
                            'Data': data_tabela,
                            'Modalidade': 'Diária',
                            'Credor': credor,
                            'Ordenador': ordenador,
                            'CPF do Ordenador': cpf,
                            'Valor Bruto': valor_bruto,
                            'Descrição': descricao
                        }
                        return valor_float, dados
                    
                    return 0.0, {}
                    
                elif response.status_code in [429, 503]: 
                    if retry_count < self.max_retries:
                        delay = self.retry_delays[retry_count]
                        self.atualizar_progresso(
                            f"[bold yellow]⚠️ Servidor sobrecarregado (HTTP {response.status_code}). "
                            f"Nova tentativa em {delay} segundos...[/bold yellow]"
                        )
                        time.sleep(delay)
                        retry_count += 1
                        continue
                    else:
                        self.atualizar_progresso(
                            f"[bold red]❌ Erro HTTP {response.status_code} após {self.max_retries} tentativas.[/bold red]"
                        )
                        break
                else:
                    self.atualizar_progresso(
                        f"[bold red]❌ Erro HTTP {response.status_code} ao acessar detalhes da diária.[/bold red]"
                    )
                    break
                    
            except requests.exceptions.ConnectionError as e:
                if "NameResolutionError" in str(e):
                    error_type = "DNS"
                    error_detail = "Não foi possível resolver o nome do servidor"
                else:
                    error_type = "Conexão"
                    error_detail = "Falha na conexão com o servidor"
                
                error_str = str(e)
                if error_str != last_error:
                    last_error = error_str
                    self.atualizar_progresso(
                        f"[bold red]❌ Erro de {error_type}: {error_detail}[/bold red]"
                    )
                
                if retry_count < self.max_retries:
                    delay = self.retry_delays[retry_count]
                    self.atualizar_progresso(
                        f"[bold yellow]⚠️ Tentativa {retry_count+1}/{self.max_retries+1} em {delay} segundos...[/bold yellow]"
                    )
                    time.sleep(delay)
                    retry_count += 1
                    continue
                else:
                    self.atualizar_progresso(
                        f"[bold red]❌ Falha de {error_type} após {self.max_retries+1} tentativas.[/bold red]"
                    )
                    break
                    
            except requests.exceptions.Timeout:
                if retry_count < self.max_retries:
                    delay = self.retry_delays[retry_count]
                    self.atualizar_progresso(
                        f"[bold yellow]⚠️ Timeout ao acessar detalhes da diária. Nova tentativa em {delay} segundos...[/bold yellow]"
                    )
                    time.sleep(delay)
                    retry_count += 1
                    continue
                else:
                    self.atualizar_progresso(
                        f"[bold red]❌ Tempo limite excedido após {self.max_retries+1} tentativas.[/bold red]"
                    )
                    break
                    
            except Exception as e:
                error_str = str(e)
                if error_str != last_error:
                    last_error = error_str
                    self.atualizar_progresso(f"[bold red]❌ Erro ao processar detalhes da diária: {error_str}[/bold red]")
                
                if retry_count < self.max_retries:
                    delay = self.retry_delays[retry_count]
                    self.atualizar_progresso(
                        f"[bold yellow]⚠️ Tentativa {retry_count+1}/{self.max_retries+1} em {delay} segundos...[/bold yellow]"
                    )
                    time.sleep(delay)
                    retry_count += 1
                    continue
                else:
                    break
        
        return 0.0, {}
        
    def make_request(self, url, retry_count=0):
        """Make an HTTP request with retry logic"""
        try:
            response = requests.get(url, timeout=15)
            if response.status_code == 200:
                return response
            elif response.status_code in [429, 503]: 
                if retry_count < self.max_retries:
                    delay = self.retry_delays[retry_count]
                    self.atualizar_progresso(
                        f"[bold yellow]⚠️ Servidor sobrecarregado (HTTP {response.status_code}). "
                        f"Nova tentativa em {delay} segundos...[/bold yellow]"
                    )
                    time.sleep(delay)
                    return self.make_request(url, retry_count + 1)
            
            self.atualizar_progresso(
                f"[bold red]❌ Erro HTTP {response.status_code} ao acessar {url}[/bold red]"
            )
            raise requests.exceptions.RequestException(f"HTTP {response.status_code}")
            
        except requests.exceptions.ConnectionError:
            if retry_count < self.max_retries:
                delay = self.retry_delays[retry_count]
                self.atualizar_progresso(
                    f"[bold yellow]⚠️ Erro de conexão. Nova tentativa em {delay} segundos...[/bold yellow]"
                )
                time.sleep(delay)
                return self.make_request(url, retry_count + 1)
            raise
            
        except requests.exceptions.Timeout:
            if retry_count < self.max_retries:
                delay = self.retry_delays[retry_count]
                self.atualizar_progresso(
                    f"[bold yellow]⚠️ Timeout. Nova tentativa em {delay} segundos...[/bold yellow]"
                )
                time.sleep(delay)
                return self.make_request(url, retry_count + 1)
            self.atualizar_progresso("[bold red]❌ Tempo limite excedido após várias tentativas.[/bold red]")
            raise


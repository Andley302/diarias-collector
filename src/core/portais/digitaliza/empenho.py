import time
import requests
from bs4 import BeautifulSoup
from urllib.parse import urlparse
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn, TimeElapsedColumn

from ..base_portal import BasePortal
from src.core.utils import carregar_ou_criar_palavras_chave, carregar_ou_criar_cidades, remover_acentos

class DigitalizaEmpenho(BasePortal):
    def __init__(self, callback=None, verbose=False):
        super().__init__(callback, verbose)
        self.console = Console()
        self.max_retries = 3
        self.retry_delays = [5, 10, 30]
        self.connection_lost = False
    
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
        
        connection_issues = {
            'dns_failures': 0,
            'timeouts': 0,
            'connection_errors': 0,
            'last_error_time': 0,
            'last_error_message': None
        }
        
        try:
            empenhos = self.pegar_urls_empenhos(url_base, self.verbose, timeout)
            
            empenhos_filtrados = self.filtrar_empenhos_por_ano(empenhos, ano_inicio, ano_fim)
            self.atualizar_progresso(f"Encontrados {len(empenhos_filtrados)} meses no período {ano_inicio}-{ano_fim}")
            
            with self.console.status("[yellow]Processando empenhos, por favor aguarde..."):
                for i, empenho in enumerate(empenhos_filtrados):
                    url = empenho.get('url')
                    try:
                        ano = int(empenho.get('ano'))
                        mes = int(empenho.get('mes'))
                    except (TypeError, ValueError):
                        self.atualizar_progresso(f"[red]⚠️ Dados inválidos no empenho {i+1}, pulando...")
                        continue

                    mes_str = f"{mes:02d}"
                    ano_str = str(ano)

                    self.atualizar_progresso(
                        f"🔎 Lendo empenho {i+1} de {len(empenhos_filtrados)} ({mes_str}/{ano_str})"
                    )

                    if not url:
                        self.atualizar_progresso(f"[red]⚠️ URL ausente no empenho {i+1}, pulando...")
                        continue

                    retry_count = 0
                    while retry_count <= self.max_retries:
                        try:
                            if self.connection_lost:
                                self.atualizar_progresso(
                                    "[bold green]✅ Conexão restabelecida! Continuando processamento...[/bold green]"
                                )
                                self.connection_lost = False
                                
                            valor, dados = self.extrair_empenhos_palavras_chave(url, ano, mes, credor_nome, timeout)
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
                                    f"Pulando este empenho.[/bold red]"
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
                                    f"Pulando este empenho.[/bold red]"
                                )
                                break
                                
                        except Exception as e:
                            error_msg = str(e)
                            if error_msg != connection_issues['last_error_message']:
                                connection_issues['last_error_message'] = error_msg
                                self.atualizar_progresso(
                                    f"[bold red]❌ Erro ao processar empenho: {error_msg}[/bold red]"
                                )
                            break
            
            if connection_issues['dns_failures'] > 0 or connection_issues['timeouts'] > 0 or connection_issues['connection_errors'] > 0:
                self.atualizar_progresso(
                    f"[bold yellow]⚠️ Resumo de problemas de conexão: {connection_issues['dns_failures']} falhas de DNS, "
                    f"{connection_issues['timeouts']} timeouts, {connection_issues['connection_errors']} erros de conexão[/bold yellow]"
                )
                
            return valor_total, dados_empenhos
            
        except Exception as e:
            #self.atualizar_progresso(
            #    f"[bold red]❌ Erro crítico durante a busca: {str(e)}[/bold red]"
            #)
            raise
    
    def pegar_urls_empenhos(self, base_url, verbose=False, timeout=7):
        urls_empenhos = []
        self.atualizar_progresso(f"Acessando URL principal: {base_url}")
        
        retry_count = 0
        while retry_count <= self.max_retries:
            try:
                response = self.make_request(base_url)

                if verbose:
                    parsed_url = urlparse(base_url)
                    host_info = f"{parsed_url.hostname}:{parsed_url.port or 80 if parsed_url.scheme == 'http' else 443}"
                    self.atualizar_progresso(
                        f"[cyan][VERBOSE][/cyan] Requisição para {host_info} (Timeout {timeout}) - Status {response.status_code}"
                    )

                soup = BeautifulSoup(response.text, 'html.parser')
                links = soup.find_all('a', class_='btn_table')
                
                if links:
                    for link in links:
                        detalhe_url = link['href']
                        url_parts = detalhe_url.split('/')
                        if len(url_parts) >= 4:
                            try:
                                ano_empenho = int(url_parts[-3])
                                mes_empenho = url_parts[-2]
                                urls_empenhos.append({
                                    'ano': ano_empenho,
                                    'mes': mes_empenho,
                                    'url': detalhe_url
                                })
                            except ValueError:
                                self.atualizar_progresso(
                                    f"[yellow]⚠️ Ano ou mês inválido encontrado na URL: {detalhe_url}[/yellow]"
                                )
                else:
                    self.atualizar_progresso("[yellow]⚠️ Nenhum empenho encontrado na página principal.[/yellow]")
                
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

        self.atualizar_progresso(f"Total de URLs de empenhos encontradas: {len(urls_empenhos)}")
        return urls_empenhos
    
    def filtrar_empenhos_por_ano(self, empenhos, ano_inicio, ano_fim):
        return [empenho for empenho in empenhos if ano_inicio <= empenho['ano'] <= ano_fim]
    
    def extrair_empenhos_palavras_chave(self, url_empenho, ano, mes, credor_nome, timeout):
        response = requests.get(url_empenho, timeout=timeout)
        
        if response.status_code == 200:
            soup = BeautifulSoup(response.text, 'html.parser')
            rows = soup.find_all('tr')
            
            palavras_chave = carregar_ou_criar_palavras_chave()

            valor_total = 0.0
            dados_empenhos = []
            
            for row in rows:
                colunas = row.find_all('td')
                
                if len(colunas) > 0:
                    descricao = colunas[0].get_text().lower()
                    
                    if any(palavra in descricao for palavra in palavras_chave):
                        link_empenho = colunas[-1].find('a')['href']
                        valor, dados = self.extrair_dados_empenho(link_empenho, credor_nome, timeout)
                        if valor > 0:
                            dados_empenhos.append({
                                'Ano': ano,
                                'Mês': mes,
                                'Número do Empenho': dados['Número do Empenho'],
                                'Data': dados['Data'],
                                'Modalidade': dados['Modalidade'],
                                'Credor': dados['Credor'],
                                'Ordenador': dados['Ordenador'],
                                'CPF do Ordenador': dados['CPF do Ordenador'],
                                'Valor Bruto': dados['Valor Bruto'],
                                'Descrição': dados['Descrição'].upper(),
                                'Detalhes': link_empenho
                            })
                            valor_total += valor
            
            return valor_total, dados_empenhos
        return 0.0, []
    
    def extrair_dados_empenho(self, url_empenho, credor_nome, timeout):
        retry_count = 0
        last_error = None
        
        while retry_count <= self.max_retries:
            try:
                #self.atualizar_progresso(f"[cyan]🔍 Acessando detalhes do empenho...[/cyan]")
            
                response = requests.get(url_empenho, timeout=timeout)
            
                if response.status_code == 200:
                    try:
                        #self.atualizar_progresso(f"[cyan]🔍 Processando dados do empenho...[/cyan]")
                        
                        soup = BeautifulSoup(response.text, 'html.parser')
                        numero_empenho_tag = soup.find('input', {'id': ''})
                        numero_empenho = numero_empenho_tag['value'] if numero_empenho_tag else ''
                        
                        self.atualizar_progresso(f"[cyan]🔍 Verificando o empenho N°{numero_empenho}...[/cyan]", numero_empenho)
                        
                        data_tag = soup.find('input', {'id': 'contratacao'})
                        data = data_tag['value'] if data_tag else ''
                        
                        modalidade_tag = soup.find('input', {'id': 'modalidade'})
                        modalidade = modalidade_tag['value'] if modalidade_tag else ''
                        
                        credor_tag = soup.find('input', {'id': 'credor'})
                        credor = credor_tag['value'] if credor_tag else ''
                        
                        ordenador_tag = soup.find('input', {'id': 'ordenador'})
                        ordenador = ordenador_tag['value'] if ordenador_tag else ''
                        
                        cpf_tag = soup.find('input', {'id': 'c_ordenador'})
                        cpf = cpf_tag['value'] if cpf_tag else ''
                        
                        valor_bruto_tag = soup.find('input', {'id': 'valor'})
                        valor_bruto = valor_bruto_tag['value'] if valor_bruto_tag else ''
                        
                        descricao_tag = soup.find('textarea', {'id': 'descricao'})
                        descricao = descricao_tag.text.strip() if descricao_tag else ''
                        
                        valor_float = 0.0
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
                                f"no dia {data} no valor de {valor_bruto}.[/bold green]"
                            )

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
                                descricao = "VIAGEM A LOCAL NÃO INFORMADO"

                            dados = {
                                'Número do Empenho': numero_empenho,
                                'Data': data,
                                'Modalidade': modalidade,
                                'Credor': credor,
                                'Ordenador': ordenador,
                                'CPF do Ordenador': cpf,
                                'Valor Bruto': valor_bruto,
                                'Descrição': descricao
                            }
                            return valor_float, dados
                        
                        return 0.0, {}
                        
                    except Exception as e:
                        error_str = str(e)
                        if error_str != last_error:
                            last_error = error_str
                            self.atualizar_progresso(f"[bold red]❌ Erro ao processar HTML do empenho: {error_str}[/bold red]")
                        
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
                    
                elif response.status_code in [429, 503]:  # Rate limit or service unavailable
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
                        f"[bold red]❌ Erro HTTP {response.status_code} ao acessar empenho.[/bold red]"
                    )
                    break
                    
            except requests.exceptions.ConnectionError as e:
                if "NameResolutionError" in str(e):
                    error_type = "DNS"
                    error_detail = "Não foi possível resolver o nome do servidor"
                else:
                    error_type = "Conexão"
                    error_detail = "Falha na conexão com o servidor"
                
                # Only show error if it's different from the last one
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
                    error_message = f"Falha de {error_type} após {self.max_retries+1} tentativas."
                    self.atualizar_progresso(f"[bold red]❌ {error_message}[/bold red]")
                    raise ConnectionError(f"Erro crítico de conexão: {error_message}")

            except requests.exceptions.Timeout:
                if retry_count < self.max_retries:
                    delay = self.retry_delays[retry_count]
                    self.atualizar_progresso(
                      f"[bold yellow]⚠️ Timeout ao acessar empenho. Nova tentativa em {delay} segundos...[/bold yellow]"
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
                    self.atualizar_progresso(f"[bold red]❌ Erro ao processar empenho: {error_str}[/bold red]")
                
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


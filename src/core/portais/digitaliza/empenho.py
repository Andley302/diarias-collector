import requests
from bs4 import BeautifulSoup
import unicodedata
from urllib.parse import urlparse
from rich.console import Console
from src.core.utils import remover_acentos

from ..base_portal import BasePortal
from src.core.utils import carregar_ou_criar_palavras_chave, carregar_ou_criar_cidades
class DigitalizaEmpenho(BasePortal):
    def __init__(self, callback=None, verbose=False):
        super().__init__(callback, verbose)
        self.console = Console()
    
    
    def buscar_diarias(self, url_base, ano_inicio, ano_fim, credor_nome):
        valor_total = 0.0
        dados_empenhos = []
        
        empenhos = self.pegar_urls_empenhos(url_base, self.verbose)
        
        empenhos_filtrados = self.filtrar_empenhos_por_ano(empenhos, ano_inicio, ano_fim)
        self.atualizar_progresso(f"Encontrados {len(empenhos_filtrados)} meses no período {ano_inicio}-{ano_fim}")
        
        with self.console.status("[yellow]Processando empenhos, por favor aguarde..."):
            for i, empenho in enumerate(empenhos_filtrados):
                url = empenho.get('url')
                try:
                    ano = int(empenho.get('ano'))
                    mes = int(empenho.get('mes'))
                except (TypeError, ValueError):
                    self.console.print(f"[red]⚠️ Dados inválidos no empenho {i+1}, pulando...")
                    continue

                mes_str = f"{mes:02d}"
                ano_str = str(ano)

                self.atualizar_progresso(
                    f"🔎 Lendo empenho {i+1} de {len(empenhos_filtrados)} ({mes_str}/{ano_str})"
                )

                if not url:
                    self.console.print(f"[red]⚠️ URL ausente no empenho {i+1}, pulando...")
                    continue

                valor, dados = self.extrair_empenhos_palavras_chave(url, ano, mes, credor_nome)
                valor_total += valor
                dados_empenhos.extend(dados)
                
        return valor_total, dados_empenhos
    
    def pegar_urls_empenhos(self, base_url, verbose=False):
        urls_empenhos = []
        self.atualizar_progresso(f"Acessando URL principal: {base_url}")
        
        try:
            response = requests.get(base_url, timeout=30)

            if verbose:
                parsed_url = urlparse(base_url)
                host_info = f"{parsed_url.hostname}:{parsed_url.port or 80 if parsed_url.scheme == 'http' else 443}"

                self.atualizar_progresso(
                        f"[cyan][VERBOSE][/cyan] Requisição para {host_info} - Status {response.status_code}"
                )

            if response.status_code == 200:
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
                                    f"Ano ou mês inválido encontrado na URL: {detalhe_url}"
                                )
                else:
                    self.atualizar_progresso("Nenhum empenho encontrado na página principal.")

        except Exception as e:
            self.atualizar_progresso(f"Erro ao acessar a URL principal: {str(e)}")

        self.atualizar_progresso(f"Total de URLs de empenhos encontradas: {len(urls_empenhos)}")
        return urls_empenhos
    
    def filtrar_empenhos_por_ano(self, empenhos, ano_inicio, ano_fim):
        return [empenho for empenho in empenhos if ano_inicio <= empenho['ano'] <= ano_fim]
    
    def extrair_empenhos_palavras_chave(self, url_empenho, ano, mes, credor_nome):
        response = requests.get(url_empenho, timeout=30)
        
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
                        valor, dados = self.extrair_dados_empenho(link_empenho, credor_nome)
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
    
    def extrair_dados_empenho(self, url_empenho, credor_nome):
        try:
            response = requests.get(url_empenho, timeout=30)
            
            if response.status_code == 200:
                soup = BeautifulSoup(response.text, 'html.parser')
                numero_empenho_tag = soup.find('input', {'id': ''})
                numero_empenho = numero_empenho_tag['value'] if numero_empenho_tag else ''
                
                self.atualizar_progresso(f"Verificando o empenho N°{numero_empenho}...", numero_empenho)
                
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
                    valor_float = float(valor_bruto.replace("R$", "").replace(".", "").replace(",", ".").strip())
                except ValueError:
                    self.atualizar_progresso(f"Erro ao converter valor: {valor_bruto}")
                
                credor_nome_normalizado = remover_acentos(credor_nome).lower()
                credor_normalizado = remover_acentos(credor).lower()

                if credor_nome_normalizado in credor_normalizado:
                    self.atualizar_progresso(
                        f"[green]✅ Diária de Viagem para {credor} no empenho N°{numero_empenho} "
                        f"no dia {data} no valor de {valor_bruto}.[/green]"
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
        except Exception as e:
            self.atualizar_progresso(f"[red]Erro ao processar empenho {url_empenho}: {str(e)}[/red]")
        
        return 0.0, {}
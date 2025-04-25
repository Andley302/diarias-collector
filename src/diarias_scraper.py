import json
import requests
from bs4 import BeautifulSoup
import unicodedata
import os
from datetime import datetime
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, BarColumn, TextColumn

class DiariasCollector:
    def __init__(self, callback=None):
        """Inicializa o scraper de diárias."""
        self.callback = callback
        self.console = Console()
        self.cidades_orgaos = self.carregar_cidades_orgaos()

    def atualizar_progresso(self, mensagem, empenho=None):
        """Atualiza o progresso na interface, se disponível"""
        if self.callback:
            self.callback(mensagem, empenho)
        else:
            self.console.print(mensagem)

    def remover_acentos(self, texto):
        """Remove acentos de um texto."""
        return ''.join(c for c in unicodedata.normalize('NFD', texto) 
                       if unicodedata.category(c) != 'Mn')

    def carregar_cidades_orgaos(self):
        """Carrega as cidades e órgãos do arquivo JSON."""
        try:
            script_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            json_path = os.path.join(script_dir, 'cidades.json')
            with open(json_path, 'r', encoding='utf-8') as file:
                return json.load(file)
        except Exception as e:
            print(f"Erro ao carregar cidades.json: {e}")
            return {}

    def validar_entrada(self, ano_inicio, ano_fim, credor_nome):
        """Valida os parâmetros de entrada."""
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

    def pegar_urls_empenhos(self, base_url):
        """Obtém as URLs dos empenhos a partir da URL base."""
        urls_empenhos = []
        self.atualizar_progresso(f"Acessando URL principal: {base_url}")
        
        try:
            response = requests.get(base_url, timeout=30)
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
                                self.atualizar_progresso(f"Ano ou mês inválido encontrado na URL: {detalhe_url}")
                else:
                    self.atualizar_progresso("Nenhum empenho encontrado na página principal.")
            else:
                self.atualizar_progresso(f"Erro ao acessar a URL principal: {base_url} - Código de status: {response.status_code}")
        except Exception as e:
            self.atualizar_progresso(f"Erro ao acessar a URL principal: {str(e)}")
        
        self.atualizar_progresso(f"Total de URLs de empenhos encontradas: {len(urls_empenhos)}")
        return urls_empenhos

    def extrair_empenhos_palavras_chave(self, url_empenho, ano, mes, credor_nome):
        """Extrai empenhos que contêm palavras-chave relacionadas a diárias."""
        response = requests.get(url_empenho, timeout=30)
        
        if response.status_code == 200:
            soup = BeautifulSoup(response.text, 'html.parser')
            rows = soup.find_all('tr')
            
            palavras_chave = ['diária', 'diaria', 'diárias', 'diarias', 'viagem', 'viagens', 
                             'locomoção', 'locomocao', 'deslocamento']
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
        """Extrai dados detalhados de um empenho específico."""
        try:
            response = requests.get(url_empenho, timeout=30)
            
            if response.status_code == 200:
                soup = BeautifulSoup(response.text, 'html.parser')
                numero_empenho_tag = soup.find('input', {'id': ''})
                numero_empenho = numero_empenho_tag['value'] if numero_empenho_tag else ''
                
                # Atualizar progresso com o número do empenho sendo verificado
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
                
                credor_nome_normalizado = self.remover_acentos(credor_nome).lower()
                credor_normalizado = self.remover_acentos(credor).lower()

                if credor_nome_normalizado in credor_normalizado:
                    self.atualizar_progresso(
                        f"[green]Diária de Viagem para {credor} no empenho N°{numero_empenho} "
                        f"no dia {data} no valor de {valor_bruto}.[/green]"
                    )

                    # Verificar se a descrição contém uma cidade específica
                    cidades = [
                        "CARLOS CHAGAS", "NANUQUE", "ITAOBIM", "GOVERNADOR VALADARES", "TEOFILO OTONI", 
                        "TEIXEIRA DE FREITAS", "ITANHEM", "MEDEIROS NETO", "VITORIA", "AGUAS FORMOSAS", 
                        "IPATINGA", "BELO HORIZONTE", "BRASILIA", "SAO PAULO", "CRISOLITA", 
                        "NOVO ORIENTE DE MINAS", "PAVAO", "FRONTEIRA DOS VALES", "UMBURATIBA", 
                        "UMBURANINHA", "SANTA HELENA DE MINAS", "FELISBURGO", "ALMENARA", "BH"
                    ]
    
                    descricao_sem_acento = self.remover_acentos(descricao)
                    cidade_encontrada = False
    
                    # Verificar se alguma cidade está na descrição
                    for cidade in cidades:
                        if cidade.lower() in descricao_sem_acento:
                            self.atualizar_progresso(f"Cidade identificada na descrição: {cidade}")
                            cidade_encontrada = True
                            break
    
                    # Se nenhuma cidade for encontrada, mudar a descrição
                    if not cidade_encontrada:
                        descricao = "VIAGEM A LUGAR NÃO INFORMADO"
    
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
            self.atualizar_progresso(f"Erro ao processar empenho {url_empenho}: {str(e)}")
        
        return 0.0, {}

    def filtrar_empenhos_por_ano(self, empenhos, ano_inicio, ano_fim):
        """Filtra empenhos pelo intervalo de anos."""
        return [empenho for empenho in empenhos if ano_inicio <= empenho['ano'] <= ano_fim]

    def buscar_diarias(self, cidade, orgao, ano_inicio, ano_fim, credor_nome):
        """Método principal para buscar diárias."""
        # Validar entrada
        valido, mensagem = self.validar_entrada(ano_inicio, ano_fim, credor_nome)
        if not valido:
            self.atualizar_progresso(mensagem)
            return False, mensagem, None, None
        
        ano_inicio = int(ano_inicio)
        ano_fim = int(ano_fim)
        
        # Verificar se a cidade e o órgão existem
        if cidade not in self.cidades_orgaos:
            return False, f"Cidade '{cidade}' não encontrada.", None, None
        
        orgaos = self.cidades_orgaos[cidade]
        if orgao not in orgaos:
            return False, f"Órgão '{orgao}' não encontrado para a cidade '{cidade}'.", None, None
        
        base_url = orgaos[orgao]
        
        # Obter URLs de empenhos
        self.atualizar_progresso(f"Buscando empenhos para {cidade} - {orgao}...")
        empenhos = self.pegar_urls_empenhos(base_url)
        
        # Filtrar empenhos pelo ano
        empenhos_filtrados = self.filtrar_empenhos_por_ano(empenhos, ano_inicio, ano_fim)
        self.atualizar_progresso(f"Encontrados {len(empenhos_filtrados)} meses no período {ano_inicio}-{ano_fim}")
        
        # Processar empenhos
        valor_total = 0.0
        dados_empenhos = []
        

        with self.console.status("[yellow]Processando empenhos, por favor aguarde..."):
            for i, empenho in enumerate(empenhos_filtrados):
                self.atualizar_progresso(f"🔎 Lendo empenho {i+1} de {len(empenhos_filtrados)}")
                valor, dados = self.extrair_empenhos_palavras_chave(empenho['url'], empenho['ano'], empenho['mes'], credor_nome)
                valor_total += valor
                dados_empenhos.extend(dados)

        primeiro_credor = credor_nome
        if dados_empenhos:
            primeiro_credor = dados_empenhos[0]['Credor']
        
        periodo = f"{ano_inicio} a {ano_fim}" if ano_inicio != ano_fim else str(ano_inicio)
        
        if valor_total > 0:
           mensagem_final = f"[green]O credor {primeiro_credor} somou um total de R$ {valor_total:.2f} em diárias no período de {periodo}.[/green]"
           self.atualizar_progresso(mensagem_final)
           return True, "", dados_empenhos, valor_total 
        else:
            mensagem_final = f"Nenhum valor encontrado para o credor '{primeiro_credor}' no período de {periodo}."
            self.atualizar_progresso(mensagem_final)
            return True, mensagem_final, [], 0

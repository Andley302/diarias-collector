import requests
from bs4 import BeautifulSoup
import unicodedata
import re

class DiariasCollector:
    def __init__(self, base_url):
        self.base_url = base_url
        self.palavras_chave = [
            'diária', 'diaria', 'diárias', 'diária',
            'viagem', 'viagens', 'locomoção', 'locomocao',
            'deslocamento'
        ]

    def remover_acentos(self, texto):
        return ''.join(c for c in unicodedata.normalize('NFD', texto)
                      if unicodedata.category(c) != 'Mn')

    def pegar_urls_empenhos(self):
        urls_empenhos = []
        response = requests.get(self.base_url)

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
                            print(f"Ano ou mês inválido encontrado na URL: {detalhe_url}")
            else:
                print("Nenhum empenho encontrado na página principal.")
        else:
            print(f"Erro ao acessar a URL principal: {self.base_url} - Código de status: {response.status_code}")

        return urls_empenhos

    def extrair_dados_empenho(self, url_empenho, credor_nome):
        response = requests.get(url_empenho)
        
        if response.status_code == 200:
            soup = BeautifulSoup(response.text, 'html.parser')
            
            numero_empenho_tag = soup.find('input', {'id': ''})
            numero_empenho = numero_empenho_tag['value'] if numero_empenho_tag else ''
            
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
            
            valor_float = float(valor_bruto.replace("R$", "").replace(".", "").replace(",", ".").strip())
            
            credor_nome_normalizado = self.remover_acentos(credor_nome).lower()
            credor_normalizado = self.remover_acentos(credor).lower()

            if credor_nome_normalizado in credor_normalizado:
                cidades = [
                    "CARLOS CHAGAS", "NANUQUE", "ITAOBIM", "GOVERNADOR VALADARES",
                    "TEOFILO OTONI", "TEIXEIRA DE FREITAS", "ITANHEM",
                    "MEDEIROS NETO", "VITORIA", "AGUAS FORMOSAS", "IPATINGA",
                    "BELO HORIZONTE", "BRASILIA", "SAO PAULO", "CRISOLITA",
                    "NOVO ORIENTE DE MINAS", "PAVAO", "FRONTEIRA DOS VALES",
                    "UMBURATIBA", "UMBURANINHA", "SANTA HELENA DE MINAS",
                    "FELISBURGO", "ALMENARA", "BH",
                ]
                
                descricao_sem_acento = self.remover_acentos(descricao)
                descricao_original = 'OUTRAS VIAGENS.'
                
                for cidade in cidades:
                    if self.remover_acentos(cidade) in descricao_sem_acento.upper():
                        descricao_original = f"VIAGEM A {cidade}."
                        break
                
                dados = {
                    'Número do Empenho': numero_empenho,
                    'Data': data,
                    'Modalidade': modalidade,
                    'Credor': credor,
                    'Ordenador': ordenador,
                    'CPF do Ordenador': cpf,
                    'Valor Bruto': valor_bruto,
                    'Descrição': descricao_original,
                    'Detalhes': url_empenho
                }
                return valor_float, dados
        return 0.0, {}

    def extrair_empenhos_palavras_chave(self, url_empenho, ano, mes, credor_nome, callback=None):
        response = requests.get(url_empenho)
        
        if response.status_code == 200:
            soup = BeautifulSoup(response.text, 'html.parser')
            rows = soup.find_all('tr')
            
            valor_total = 0.0
            dados_empenhos = []

            for row in rows:
                colunas = row.find_all('td')
                
                if len(colunas) > 0:
                    descricao = colunas[0].get_text().lower()
                    
                    if any(palavra in descricao for palavra in self.palavras_chave):
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
                                'Descrição': dados['Descrição'],
                                'Detalhes': dados['Detalhes']
                            })
                            valor_total += valor
                            if callback:
                                callback(dados)

            return valor_total, dados_empenhos
        return 0.0, []

    def buscar_diarias(self, credor_nome, ano_inicio, ano_fim, callback=None):
        urls_empenhos = self.pegar_urls_empenhos()
        empenhos_filtrados = [
            empenho for empenho in urls_empenhos
            if ano_inicio <= empenho['ano'] <= ano_fim
        ]
        
        valor_total = 0.0
        dados_empenhos = []
        
        for idx, empenho in enumerate(empenhos_filtrados, 1):
            if callback:
                callback(idx, len(empenhos_filtrados))
            
            valor, dados = self.extrair_empenhos_palavras_chave(
                empenho['url'],
                empenho['ano'],
                empenho['mes'],
                credor_nome,
                lambda d: callback(idx, len(empenhos_filtrados), d) if callback else None
            )
            valor_total += valor
            dados_empenhos.extend(dados)
        
        return dados_empenhos, valor_total 
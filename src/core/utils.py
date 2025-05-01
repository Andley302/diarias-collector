import json
import os
import unicodedata

def resource_path(relative_path):
    return os.path.join(os.path.abspath("."), relative_path)

def carregar_ou_criar_cidades(log_callback=None):
    json_path = resource_path('resources/cidades_chave.json')
    cidades_padrao = [
        "CARLOS CHAGAS", "NANUQUE", "ITAOBIM", "GOVERNADOR VALADARES", "TEOFILO OTONI", 
        "TEIXEIRA DE FREITAS", "ITANHEM", "MEDEIROS NETO", "VITORIA", "AGUAS FORMOSAS", 
        "IPATINGA", "BELO HORIZONTE", "BRASILIA", "SAO PAULO", "CRISOLITA", 
        "NOVO ORIENTE DE MINAS", "PAVAO", "FRONTEIRA DOS VALES", "UMBURATIBA", 
        "UMBURANINHA", "SANTA HELENA DE MINAS", "FELISBURGO", "ALMENARA", "BH"
    ]

    if not os.path.exists(json_path):
        try:
            os.makedirs(os.path.dirname(json_path), exist_ok=True)
            with open(json_path, 'w', encoding='utf-8') as file:
                json.dump(cidades_padrao, file, ensure_ascii=False, indent=4)
            if log_callback:
                log_callback(f"[INFO] Arquivo cidades.json criado em {json_path}")
        except Exception as e:
            if log_callback:
                log_callback(f"[ERRO] Não foi possível criar cidades.json: {e}")
            return []

    try:
        with open(json_path, 'r', encoding='utf-8') as file:
            return json.load(file)
    except Exception as e:
        if log_callback:
            log_callback(f"[ERRO] Erro ao carregar cidades.json: {e}")
        return []
    
def carregar_ou_criar_palavras_chave(log_callback=None):
    json_path = resource_path('resources/palavras_chave.json')
    palavras_padrao = [
        'diária', 'diaria', 'diárias', 'diarias', 
        'viagem', 'viagens', 'locomoção', 'locomocao', 'deslocamento'
    ]

    if not os.path.exists(json_path):
        try:
            os.makedirs(os.path.dirname(json_path), exist_ok=True)
            with open(json_path, 'w', encoding='utf-8') as file:
                json.dump(palavras_padrao, file, ensure_ascii=False, indent=4)
            if log_callback:
                log_callback(f"[INFO] Arquivo palavras_chave.json criado em {json_path}")
        except Exception as e:
            if log_callback:
                log_callback(f"[ERRO] Não foi possível criar palavras_chave.json: {e}")
            return []

    try:
        with open(json_path, 'r', encoding='utf-8') as file:
            return json.load(file)
    except Exception as e:
        if log_callback:
            log_callback(f"[ERRO] Erro ao carregar palavras_chave.json: {e}")
        return []

def remover_acentos(texto):
    return ''.join(c for c in unicodedata.normalize('NFD', texto) 
                   if unicodedata.category(c) != 'Mn')
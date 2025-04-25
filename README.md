# Diárias Collector 🔍

Um web scraper especializado para organizar informações sobre subsídios de viagem públicas de pessoas nos portais de transparência.

## Sobre o Projeto

Este sistema é um web scraper especializado que organiza informações já públicas de diárias de viagem disponíveis nos portais de transparência. Embora esses dados sejam públicos, as plataformas oficiais nem sempre oferecem ferramentas adequadas para filtrar e organizar as informações por servidor/beneficiário.

### Objetivo
- Facilitar a visualização de diárias por pessoa específica
- Consolidar dados dispersos em relatórios organizados
- Automatizar a coleta de informações públicas

### Considerações Importantes

#### Dados e Precisão
- Todas as informações coletadas são públicas e disponíveis nos portais oficiais
- Os relatórios gerados são compilações automatizadas, podendo conter imprecisões
- Não nos responsabilizamos pela precisão dos dados, que refletem o conteúdo dos portais
- Recomendamos sempre verificar as informações nas fontes oficiais

#### Limitações Técnicas
- O funcionamento depende da estrutura HTML dos portais
- Alterações nos sites podem afetar temporariamente a coleta
- Alguns portais podem implementar limites de requisições
- Possíveis bloqueios temporários de IP por excesso de acessos
- Mudanças nas URLs ou layouts podem requerer atualizações

#### Boas Práticas
- Use intervalos razoáveis entre consultas
- Evite múltiplas requisições simultâneas
- Mantenha o software atualizado
- Verifique a disponibilidade do portal antes das consultas

## Cidades e Portais Suportados

OO sistema atualmente suporta os municípios e órgãos que usam o Portal da Transparência da Digitaliza (https://www.digitaliza.com.br). Veja a lista abaixo:

### Machacalis
- Prefeitura Municipal de Machacalis

### Bertópolis
- Prefeitura Municipal de Bertópolis
- Câmara Municipal de Bertópolis

### Fronteira dos Vales
- Câmara Municipal de Fronteira dos Vales

O arquivo `cidades.json` mantém o mapeamento entre cidades, órgãos e seus respectivos portais de transparência. Esta estrutura permite:

- Organização hierárquica cidade -> órgão -> URL
- Fácil adição de novos portais
- Manutenção simplificada das URLs
- Suporte a múltiplos órgãos por cidade

Para adicionar uma nova cidade ou órgão, basta incluir suas informações no arquivo seguindo o formato:

```json
{
    "Cidade": {
        "Nome do Órgão": "URL do portal de transparência"
    }
}
```

## Requisitos
- Python 3.12
- Dependências listadas em `requirements.txt`

## Instalação

### Linux (Ubuntu/Debian)
```bash
sudo apt update
sudo apt install python3-venv python3-pip
```

```bash
git clone https://github.com/andley302/diarias-collector.git
cd diarias-collector
```

```bash
python3 -m venv venv
source venv/bin/activate
```

```bash
pip install -r requirements.txt
```

### Windows
```bash
git clone https://github.com/andley302/diarias-collector.git
cd diarias-collector
```

```bash
python -m venv venv
venv\Scripts\activate
```

```bash
pip install -r requirements.txt
```

## Uso

### Interface Gráfica
1. Execute o programa:
```bash
python app.py
```

2. Na interface:
- Selecione cidade e órgão
- Digite nome do credor
- Informe período (ano início/fim)
- Clique em "Buscar Diárias"
- Exporte para Excel ou PDF

### Terminal
```bash
python app.py --terminal
```

## Estrutura do Projeto
```
diarias-collector/
├── app.py
├── src/
│   ├── cli/
│   ├── core/
│   ├── ui/
│   └── utils/
├── relatorios/
├── requirements.txt
└── README.md
```

## Funcionalidades
- Interface gráfica e terminal
- Busca por credor e período
- Exportação Excel/PDF
- Múltiplas cidades/órgãos
- Progresso em tempo real
- Organização por credor

## Solução de Problemas

### ModuleNotFoundError: No module named 'PyQt6'
1. Ative o ambiente virtual:
```bash
source venv/bin/activate  # Linux
venv\Scripts\activate     # Windows
```

2. Instale dependências:
```bash
pip install -r requirements.txt
```

3. Ou instale PyQt6:
```bash
pip install PyQt6
```

### Outros Problemas
- Erro ambiente virtual: `sudo apt install python3-venv` (Linux)
- Erro dependências: `pip install --upgrade pip`
- Erro execução: Verifique diretório e ambiente virtual

## Contribuindo
1. Fork do projeto
2. Branch feature (`git checkout -b feature/nova-feature`)
3. Commit (`git commit -m 'Adiciona feature'`)
4. Push (`git push origin feature/nova-feature`)
5. Pull Request

## Licença
MIT License

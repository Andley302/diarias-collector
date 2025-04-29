# Diárias Collector 🔍

<p align="center">
  <img src="screenshots/home.png" alt="Banner Diárias Collector" width="700"/>
</p>

Um web scraper especializado para organizar informações sobre subsídios de viagem públicas de pessoas nos portais de transparência.

## Sobre o Projeto

Este sistema é um web scraper especializado que organiza informações já públicas de diárias de viagem disponíveis nos portais de transparência. Embora esses dados sejam públicos, as plataformas oficiais nem sempre oferecem ferramentas adequadas para filtrar e organizar as informações por servidor/beneficiário.

### Objetivo
- Facilitar a visualização de diárias por pessoa específica
- Consolidar dados dispersos em relatórios organizados
- Automatizar a coleta de informações públicas

## Uso Responsável e Considerações Éticas

Este projeto tem como objetivo facilitar o acesso e a análise dos dados públicos de diárias em portais da transparência, promovendo o escrutínio público e a boa governança.

**É fundamental que os usuários desta ferramenta a utilizem de forma ética e responsável.** Isso inclui:

* **Respeitar os termos de serviço dos portais da transparência.**
* **Evitar sobrecarregar os servidores dos portais com um número excessivo de requisições.** Implementar pausas entre as requisições é altamente recomendado.
* **Utilizar os dados coletados de forma construtiva, para análise agregada e identificação de tendências, e não para fins de difamação, perseguição ou ataque pessoal a indivíduos.**
* **Ter cautela ao divulgar informações específicas de indivíduos, mesmo que sejam dados públicos, e sempre considerar o impacto potencial dessa divulgação.**

**O desenvolvedor deste projeto não se responsabiliza pelo uso indevido da ferramenta por terceiros.** Ao utilizar este software, você concorda em ser o único responsável pela forma como os dados são coletados, interpretados e utilizados.

Lembre-se que a transparência é importante, mas deve ser exercida com responsabilidade e respeito pela privacidade dentro do que é razoável em se tratando de dados públicos.

## 🖼️ Capturas de Tela

### Tela Inicial
<p align="center">
  <img src="screenshots/search.png" alt="Tela Inicial" width="700"/>
</p>

### Progresso de uma Busca
<p align="center">
  <img src="screenshots/progress.png" alt="Progresso da Busca" width="700"/>
</p>

### Resultado de uma Busca
<p align="center">
  <img src="screenshots/progress_ended.png" alt="Resultado da Busca" width="700"/>
</p>

### Arquivo PDF Gerado
<p align="center">
  <img src="screenshots/result.png" alt="Arquivo PDF Gerado" width="700"/>
</p>

## 🖥️ Download e Execução

### 🪟 Windows

Você pode escolher entre baixar o **instalador** ou o **arquivo .zip**:

#### 📦 Instalador (recomendado)
1. Acesse a aba **[Releases](https://github.com/Andley302/diarias-collector/releases)** do repositório.
2. Baixe o arquivo **`DiariasCollector_Windows_Setup_x86_64.exe`** para Windows x64.
3. Execute o instalador e siga as instruções na tela.
4. Após a instalação, abra o **Diárias Collector** pelo Menu Iniciar ou pela Área de Trabalho.

> Durante a instalação, será necessário aceitar os Termos de Uso.

---

#### 🗜️ Arquivo .zip (alternativo)
1. Acesse a aba **[Releases](https://github.com/Andley302/diarias-collector/releases)**.
2. Baixe o arquivo **`DiariasCollector_Windows_x86_64.zip`**.
3. Extraia o conteúdo do `.zip`.
4. Abra a pasta extraída e dê **dois cliques** em `DiariasCollector.exe` para iniciar o programa.

> Atenção: usando a versão `.zip`, você será responsável por manter os arquivos organizados manualmente.

### 🐧 Linux
1. Acesse a aba **[Releases](https://github.com/Andley302/diarias-collector/releases)** do repositório.
2. Baixe o arquivo para `DiariasCollector_Linux_x86_64.zip`.
3. Extraia o conteúdo do `.zip`.
4. Abra a pasta extraída, procure o executável e clique com o botão direito no arquivo `DiariasCollector`, vá em **Propriedades > Permissões** e marque **"Permitir execução como programa"** (se necessário).
5. Dê **dois cliques** no arquivo para executá-lo.

**Observações:**
- No Windows: Execute diretamente após entrar na pasta extraída (se instalado via .zip).
- No Linux: Necessário dar permissão de execução como programa.
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

Os sistema atualmente suporta os municípios e órgãos que usam o Portal da Transparência da Digitaliza (https://www.digitaliza.com.br). Veja a lista de cidades disponíveis no [arquivo de cidades suportadas](resources/cidades.json) .

## Arquivos de Configuração
Em `resources/`, você encontrará arquivos de configuração:
### cidades.json
Mapeia as cidades e seus respectivos órgãos aos portais de transparência:
```json
{
    "Cidade": {
        "Nome do Órgão": "URL do portal de transparência"
    }
}
```

### cidades_chave.json
Lista de cidades-chave para filtrar destinos de viagens:
```json
[
    "BELO HORIZONTE",
    "BRASILIA",
    "SAO PAULO"
    // ... outras cidades
]
```

### palavras_chave.json 
Termos utilizados para identificar empenhos relacionados a diárias:
```json
[
    "diária",
    "diarias",
    "viagem",
    "deslocamento"
    // ... outras palavras-chave
]
```
## Compilação
Compile o código-fonte na sua máquina local para gerar o executável. Fique livre para explorar e modificar o código-fonte para atender às suas necessidades específicas.

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
### Visualização do Terminal
![Terminal](screenshots/terminal.png)

## Estrutura do Projeto
```
diarias-collector/
├── app.py
├── src/
│   ├── cli/
│   ├── core/
│   ├── ui/
│   └── utils/
├── resources
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

Este projeto está licenciado sob a [Licença MIT](LICENSE) - veja o arquivo [LICENSE](LICENSE) para detalhes.

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)


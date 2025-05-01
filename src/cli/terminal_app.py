import os
import sys
from rich import print
from rich.console import Console
from rich.prompt import Prompt, Confirm
from rich.panel import Panel
from src.utils.version import VERSION, GITHUB_URL
from src.core.scraper import DiariasCollector
from src.utils import save_to_excel, save_to_pdf

def escolher_opcao(titulo, opcoes):
    console = Console()
    while True:
        console.print(Panel(f"[bold cyan]{titulo}[/bold cyan]", style="bold yellow"))
        for i, opcao in enumerate(opcoes, 1):
            console.print(f"[bold green]{i}.[/bold green] {opcao}")
        escolha = Prompt.ask("[bold blue]Digite o número correspondente[/bold blue]", default="1")
        try:
            escolha = int(escolha)
            if 1 <= escolha <= len(opcoes):
                return opcoes[escolha - 1]
            else:
                console.print(f"[bold red]Número inválido. Escolha entre 1 e {len(opcoes)}.[/bold red]")
        except ValueError:
            console.print("[bold red]Entrada inválida. Por favor, digite um número.[/bold red]")

def perguntar_ano(titulo):
    console = Console()
    while True:
        entrada = Prompt.ask(f"[bold blue]{titulo}[/bold blue]")
        if entrada.isdigit() and 1900 <= int(entrada) <= 2100:
            return entrada
        console.print(Panel("[bold red]Entrada inválida.[/bold red]\nDigite um ano válido (ex: 2020).", style="red"))

def perguntar_credor():
    console = Console()
    while True:
        credor = Prompt.ask("[bold blue]Nome do Credor[/bold blue]").strip()
        if credor:
            return credor
        console.print(Panel("[bold red]Erro: O nome do credor não pode estar vazio.[/bold red]", style="red"))


def main(verbose=False):
    console = Console()

    titulo = f"[bold cyan]📄 Diárias Collector v{VERSION}[/bold cyan]"
    console.print(Panel(titulo, expand=False, border_style="bright_blue"))

    termos = (
        "[bold yellow]Termos de Uso[/bold yellow]\n"
        "Este programa acessa portais públicos para consultar e processar dados de diárias.\n"
        "Ao utilizá-lo, você concorda em assumir responsabilidade pelo uso, verificar os dados nas fontes oficiais\n"
        "e evitar qualquer uso que possa comprometer a integridade ou imagem de terceiros."
    )

    console.print(Panel(termos, border_style="yellow"))

    if not Confirm.ask("[bold green]Você aceita os termos de uso?[/bold green]"):
        console.print("[red]Operação cancelada pelo usuário.[/red]")
        return

    titulo = f"[bold cyan]📄 Diárias Collector v{VERSION}[/bold cyan]"
    console.print(Panel(titulo, expand=False, border_style="bright_blue"))

    console.print(
        f"\n[blue]Verifique sempre por atualizações em:[/blue] [underline]{GITHUB_URL}[/underline]\n"
    )

    scraper = DiariasCollector(verbose=verbose)
    cidades_orgaos = scraper.cidades_orgaos

    if not cidades_orgaos:
        console.print("[bold red]Erro: Não foi possível carregar as cidades e órgãos.[/bold red]")
        sys.exit(1)

    cidade_selecionada = escolher_opcao("Selecione uma cidade", list(cidades_orgaos.keys()))
    orgao_selecionado = escolher_opcao(f"Selecione um órgão para [bold]{cidade_selecionada}[/bold]", list(cidades_orgaos[cidade_selecionada].keys()))

    console.print(Panel("[bold cyan]Informe os parâmetros da busca[/bold cyan]", style="bold yellow"))

    ano_inicio = perguntar_ano("Ano de início")
    ano_fim = perguntar_ano("Ano de fim")

    console.print("[bold blue]Digite o nome do Credor:[/bold blue]")
    credor_nome = perguntar_credor()


    base_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "relatorios")
    os.makedirs(base_dir, exist_ok=True)

    sucesso, mensagem, dados_empenhos, valor_total = scraper.buscar_diarias(
        cidade_selecionada, orgao_selecionado, ano_inicio, ano_fim, credor_nome, verbose
    )

    if sucesso:
        if not dados_empenhos or len(dados_empenhos) == 0:
            credor_nome_final = credor_nome
        else:
            credor_nome_final = dados_empenhos[0]['Credor']

        excel_path = save_to_excel(
            dados_empenhos,
            credor_nome=credor_nome_final,
            ano_inicio=ano_inicio,
            ano_fim=ano_fim,
            cidade=cidade_selecionada,
            orgao=orgao_selecionado
         )

        pdf_path = save_to_pdf(
            dados_empenhos,
            valor_total,
            credor_nome=credor_nome_final,
            ano_inicio=ano_inicio,
            ano_fim=ano_fim,
            cidade=cidade_selecionada,
            orgao=orgao_selecionado
        )
        console.print(f"\n[bold green]Relatório Excel salvo em:[/bold green] {excel_path}")
        console.print(f"[bold green]Relatório PDF salvo em:[/bold green] {pdf_path}")
        if mensagem:
          console.print(f"\n[italic green]{mensagem}[/italic green]")

    else:
        console.print(Panel(f"[bold red]Erro:[/bold red] {mensagem}", style="red"))

if __name__ == "__main__":
    main()

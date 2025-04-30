import os
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Spacer, Paragraph, PageBreak
from reportlab.lib import colors
from reportlab.lib.units import inch
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_CENTER
from reportlab.lib.colors import HexColor
import re
import platform
import subprocess
from pathlib import Path
import pandas as pd
from src.utils.version import VERSION, GITHUB_URL

def formatar_nome(nome):
    nome_limpo = re.sub(r'[<>:"/\\|?*]', '', nome).strip()
    return ' '.join([parte.capitalize() for parte in nome_limpo.replace('_', ' ').split()])


def obter_pasta_desktop():
    sistema = platform.system()
    
    if sistema == "Linux":
        try:
            result = subprocess.run(['xdg-user-dir', 'DESKTOP'], capture_output=True, text=True)
            desktop_path = result.stdout.strip()
            if desktop_path and os.path.exists(desktop_path):
                return Path(desktop_path)
            else:
                print("Pasta Desktop não encontrada ou vazia. Usando a pasta pessoal.")
                return Path.home()
        except Exception as e:
            print(f"Erro ao obter Desktop pelo xdg-user-dir: {e}")
            return Path.home()
    else:
        return Path.home() / 'Desktop'

def criar_pasta_do_credor(credor_nome, cidade, orgao, ano_inicio, ano_fim, path_destino=None):
    nome_formatado = formatar_nome(credor_nome)
    if path_destino is None:
        pasta_base = obter_pasta_desktop() / 'Relatórios de Diárias' / cidade / orgao / nome_formatado
    else:
        pasta_base = Path(path_destino) / 'Relatórios de Diárias' / cidade / orgao / nome_formatado
    
    if not pasta_base.exists():
        pasta_base.mkdir(parents=True, exist_ok=True)
    return str(pasta_base)


def save_to_pdf(dados_empenhos, valor_total, credor_nome, ano_inicio, ano_fim, cidade, orgao, path_destino=None):
    try:
        pasta_destino = criar_pasta_do_credor(credor_nome, cidade, orgao, ano_inicio, ano_fim, path_destino)
        nome_arquivo = f"DIARIAS_{ano_inicio}-{ano_fim}.pdf"
        pdf_file_path = os.path.join(pasta_destino, nome_arquivo)

        doc = SimpleDocTemplate(
            pdf_file_path,
            pagesize=letter,
            topMargin=30,
            leftMargin=30,
            rightMargin=30,
            bottomMargin=30
        )

        styles = getSampleStyleSheet()
        normal_style = ParagraphStyle(
            'CustomNormal',
            parent=styles['Normal'],
            spaceBefore=6,
            spaceAfter=6,
            fontSize=11
        )

        centered_style = ParagraphStyle(
            'CenteredStyle',
            parent=styles['Normal'],
            alignment=1,
            fontSize=9,
            spaceBefore=3,
            spaceAfter=3
        )

        def header(canvas, doc):
            canvas.saveState()
            y_top = doc.pagesize[1] - 13

            header_text = Paragraph(
                f"<para alignment='center'><font size=8><b>Extraído por Diárias Collector v{VERSION}</b></font></para>",
                styles["Normal"]
            )
            w, h1 = header_text.wrap(doc.width, doc.topMargin)
            header_text.drawOn(canvas, doc.leftMargin, y_top - h1)

            github_text = Paragraph(
                f"<para alignment='center'><font size='7'>Para mais detalhes, acesse o código fonte no <link href='{GITHUB_URL}'>GitHub</link>.</font></para>",
                styles["Normal"]
            )
            w, h2 = github_text.wrap(doc.width, doc.topMargin)
            github_text.drawOn(canvas, doc.leftMargin, y_top - h1 - h2 - 2)

            empty_text = Paragraph(
                f"<para alignment='center'><font size=8><b>‎</b></font></para>",
                styles["Normal"]
            )
            w, h3 = empty_text.wrap(doc.width, doc.topMargin)
            empty_text.drawOn(canvas, doc.leftMargin, y_top - h1 - h2 - h3 - 4)

            canvas.restoreState()


        elements = [
            Spacer(1, 80),
            Paragraph("Diárias de Viagens", styles["Title"]),
            Spacer(1, 24)
        ]

        total_width = doc.width 
        col_widths = [
            0.12 * total_width,  
            0.12 * total_width, 
            0.2  * total_width, 
            0.20 * total_width, 
            0.14 * total_width, 
            0.20 * total_width  
        ]

        primeiro_credor = dados_empenhos[0]['Credor'].title() if dados_empenhos else credor_nome.title()
        valor_formatado = f"R$ {valor_total:,.2f}".replace(',', 'X').replace('.', ',').replace('X', '.')

        elements += [
            Paragraph(f"<b>Nome:</b> {primeiro_credor}", normal_style),
            Paragraph(f"<b>Município:</b> {cidade}", normal_style),
            Paragraph(f"<b>Órgão:</b> {orgao}", normal_style),
            Paragraph(f"<b>Período:</b> {ano_inicio} a {ano_fim}" if ano_inicio != ano_fim else f"<b>Período:</b> {ano_inicio}", normal_style),
            Paragraph(f"<b>Total Gasto no Período:</b> {valor_formatado}", normal_style),
            Spacer(1, 16),
            Paragraph(
                f"As informações a seguir referem-se às diárias de viagens pagas a <b>{primeiro_credor}</b> durante o período especificado, totalizando o valor de <b>{valor_formatado}</b>.",
                normal_style
            ),
            Paragraph(
                "Todos os dados apresentados são públicos e foram obtidos diretamente do Portal da Transparência.",
                normal_style
            ),
            Spacer(1, 20)
        ]

        if dados_empenhos:
            colunas = ['Data', 'Empenho', 'Ordenador', 'Descrição', 'Valor', 'Detalhes']
            data = [colunas]

            for emp in dados_empenhos:
                data.append([
                    emp['Data'],
                    f"N°{emp['Número do Empenho']}",
                    Paragraph(emp['Ordenador'], normal_style),
                    Paragraph(emp['Descrição'], normal_style),
                    Paragraph(emp['Valor Bruto'], normal_style),
                    Paragraph(f'<link href="{emp["Detalhes"]}">Clique Aqui</link>', centered_style)
                ])

            table = Table(data, colWidths=col_widths)
            style = TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.darkblue),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                ('ALIGN', (0, 0), (-1, -1), 'CENTER'), 
                ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'), 
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, 0), 12),
                ('BOTTOMPADDING', (0, 0), (-1, 0), 10),
                ('BACKGROUND', (0, 1), (-1, -1), colors.whitesmoke),
                ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
                ('FONTSIZE', (0, 1), (-1, -1), 9),
            ])

            table.setStyle(style)
            elements.append(table)

        if not dados_empenhos or valor_total == 0:
            centered_style_empty = ParagraphStyle(
                'CenteredStyle',
                parent=normal_style,
                alignment=TA_CENTER  # Alinha o texto horizontalmente ao centro
            )

            mensagem = Paragraph("Nenhuma diária registrada no período informado.", centered_style_empty)

            caixa = Table([[mensagem]], colWidths=doc.width)
            caixa.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, -1), HexColor("#DCE6F1")), 
                ('TEXTCOLOR', (0, 0), (-1, -1), colors.darkblue),
                ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
                ('FONTSIZE', (0, 0), (-1, -1), 11),
                ('BOX', (0, 0), (-1, -1), 1, colors.darkblue),
                ('PADDING', (0, 0), (-1, -1), 14),
            ]))
            elements.append(Spacer(1, 60))
            elements.append(caixa)


        doc.build(elements, onFirstPage=header, onLaterPages=header)
        return pdf_file_path

    except Exception as e:
        print(f"Erro ao salvar o arquivo PDF: {e}")
        return None

def save_to_excel(dados_empenhos, credor_nome="CREDOR", ano_inicio="XXXX", ano_fim="XXXX", cidade="CIDADE", orgao="ÓRGÃO", path_destino=None):
    if not dados_empenhos:
        print("Nenhum dado de empenho para salvar.")
        return None

    try:
        pasta_destino = criar_pasta_do_credor(credor_nome, cidade, orgao, ano_inicio, ano_fim, path_destino)
        nome_arquivo = f"DIARIAS_{ano_inicio}-{ano_fim}.xlsx"
        caminho_arquivo = os.path.join(pasta_destino, nome_arquivo)

        df = pd.DataFrame(dados_empenhos)

        if 'Valor Bruto' not in df.columns:
            print("Coluna 'Valor Bruto' não encontrada.")
            return None

        df['Valor Bruto'] = df['Valor Bruto'].fillna('R$ 0,00')
        df['Valor Bruto'] = df['Valor Bruto'].apply(lambda x: 
            float(str(x).replace('R$', '')
                      .replace('\xa0', '')
                      .replace('.', '')
                      .replace(',', '.')
                      .strip() or 0)
        )

        total = df['Valor Bruto'].sum()
        total_formatado = f"R$ {total:,.2f}".replace(',', 'X').replace('.', ',').replace('X', '.')

        total_row = [''] * len(df.columns)

        if 'Descrição' in df.columns:
            total_row[df.columns.get_loc('Descrição')] = 'TOTAL'
        if 'Valor Bruto' in df.columns:
            total_row[df.columns.get_loc('Valor Bruto')] = total_formatado

        df.loc[len(df)] = total_row

        df.to_excel(caminho_arquivo, index=False)
        return caminho_arquivo

    except Exception as e:
        print(f"Erro ao salvar o arquivo Excel: {e}")
        return None

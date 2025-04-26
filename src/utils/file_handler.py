import os
import pandas as pd
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Spacer, Paragraph
from reportlab.lib import colors
from reportlab.lib.units import inch
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
import re
import platform

def formatar_nome(nome):
    nome_limpo = re.sub(r'[<>:"/\\|?*]', '', nome).strip()
    return ' '.join([parte.capitalize() for parte in nome_limpo.replace('_', ' ').split()])


def criar_pasta_do_credor(credor_nome, cidade, orgao, ano_inicio, ano_fim, path_destino=None):
    nome_formatado = formatar_nome(credor_nome)
    
    sistema = platform.system()
    
    if path_destino is None:
        if sistema == "Linux" or sistema == "Darwin":  
            user_home = os.path.expanduser("~")
            pasta_base = os.path.join(user_home, 'Desktop', 'Relatórios de Diárias', cidade, orgao, nome_formatado)
        elif sistema == "Windows":  
            user_profile = os.environ.get('USERPROFILE', os.path.expanduser("~"))
            pasta_base = os.path.join(user_profile, 'Desktop', 'Relatórios de Diárias', cidade, orgao, nome_formatado)
    else:
        pasta_base = path_destino

    if not os.path.exists(pasta_base):
        os.makedirs(pasta_base, exist_ok=True)
    
    return pasta_base


def save_to_excel(dados_empenhos, credor_nome="CREDOR", ano_inicio="XXXX", ano_fim="XXXX", cidade="CIDADE", orgao="ÓRGÃO", path_destino=None):
    if not dados_empenhos or len(dados_empenhos) == 0:
        print("Nenhum dado de empenho para salvar.")
        return None  

    try:
        pasta_destino = criar_pasta_do_credor(credor_nome, cidade, orgao, ano_inicio, ano_fim, path_destino)
        nome_arquivo = f"DIARIAS_{ano_inicio}-{ano_fim}.xlsx"
        caminho_arquivo = os.path.join(pasta_destino, nome_arquivo)

        df = pd.DataFrame(dados_empenhos)
        df.to_excel(caminho_arquivo, index=False)
        return caminho_arquivo
    except Exception as e:
        print(f"Erro ao salvar o arquivo Excel: {e}")
        return None

def save_to_pdf(dados_empenhos, valor_total, credor_nome, ano_inicio, ano_fim, cidade, orgao, path_destino=None):
    #if not dados_empenhos or len(dados_empenhos) == 0:
    #    print("Nenhum dado de empenho para gerar o PDF.")
    #    return None  

    try:
        pasta_destino = criar_pasta_do_credor(credor_nome, cidade, orgao, ano_inicio, ano_fim, path_destino)
        nome_arquivo = f"DIARIAS_{ano_inicio}-{ano_fim}.pdf"
        pdf_file_path = os.path.join(pasta_destino, nome_arquivo)

        doc = SimpleDocTemplate(pdf_file_path, pagesize=letter)
        elements = []

        styles = getSampleStyleSheet()
        bold_normal_style = ParagraphStyle(name='BoldNormal', fontName='Helvetica-Bold', fontSize=10, leading=12)

        elements.append(Paragraph(f"Diárias de Viagens", styles["Title"]))
        elements.append(Spacer(1, 12))

        if dados_empenhos:
            primeiro_credor = dados_empenhos[0]['Credor']
        else:
            primeiro_credor = credor_nome

        elements.append(Paragraph(f"<b>Nome:</b> {primeiro_credor}", styles["Normal"]))
        elements.append(Paragraph(f"<b>Município:</b> {cidade}", styles["Normal"]))
        elements.append(Paragraph(f"<b>Órgão:</b> {orgao}", styles["Normal"]))

        periodo_pdf = f"{ano_inicio} a {ano_fim}" if ano_inicio != ano_fim else ano_inicio
        elements.append(Paragraph(f"<b>Período:</b> {periodo_pdf}", styles["Normal"]))

        valor_formatado = f"R$ {valor_total:,.2f}".replace(',', 'X').replace('.', ',').replace('X', '.')
        elements.append(Paragraph(f"<b>Total Gasto no Período:</b> {valor_formatado}", styles["Normal"]))
        elements.append(Spacer(1, 12))

        if dados_empenhos:
            elements.append(Paragraph(
                f"As diárias de viagens pagas a {primeiro_credor} no período de {periodo_pdf} somaram {valor_formatado}.",
                bold_normal_style
            ))
        else:
            elements.append(Paragraph("Não há diárias de viagens para este credor neste período.", styles["Normal"]))

        elements.append(Spacer(1, 12))
        elements.append(Paragraph(
            "Todos os dados são PÚBLICOS e estão no portal da transparência. Clique em Detalhes para ver mais.",
            bold_normal_style
        ))
        elements.append(Spacer(1, 12))

        data = [['Data', 'Empenho', 'Ordenador', 'Descrição', 'Valor', 'Detalhes']]
        data.extend([[  
            empenho['Data'],
            f"N° {empenho['Número do Empenho']}",
            Paragraph(empenho['Ordenador'], styles["Normal"]),
            Paragraph(empenho['Descrição'], styles["Normal"]),
            Paragraph(f"{empenho['Valor Bruto']}", styles["Normal"]),
            Paragraph(f'<link href="{empenho["Detalhes"]}">{empenho["Detalhes"]}</link>', styles["Normal"])
        ] for empenho in dados_empenhos])

        col_widths = [1 * inch, 1 * inch, 1.5 * inch, 1 * inch, 1 * inch, 2 * inch]
        table = Table(data, colWidths=col_widths)
        style = TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 12),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
            ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
            ('GRID', (0, 0), (-1, -1), 1, colors.black),
            ('FONTSIZE', (0, 1), (-1, -1), 10),
            ('VALIGN', (0, 0), (-1, -1), 'TOP')
        ])
        table.setStyle(style)
        elements.append(table)

        doc.build(elements)
        return pdf_file_path
    except Exception as e:
        print(f"Erro ao salvar o arquivo PDF: {e}")
        return None

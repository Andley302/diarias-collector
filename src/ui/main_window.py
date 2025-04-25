import os
import sys
from PyQt6.QtWidgets import (QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, 
                             QLabel, QComboBox, QLineEdit, QPushButton, 
                             QTextEdit, QMessageBox, QStackedWidget)
from PyQt6.QtCore import Qt, QThread, pyqtSignal
from PyQt6.QtGui import QFont

from src.diarias_scraper import DiariasCollector
from src.utils import save_to_excel, save_to_pdf
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, BarColumn, TextColumn
from rich.logging import RichHandler
import logging

# Configuração do logger com Rich
console = Console()
logging.basicConfig(
    level=logging.DEBUG, 
    format="%(message)s", 
    handlers=[RichHandler(console=console)]
)

# Função de log
def log_message(message, level=logging.INFO):
    logging.log(level, message)

# Thread para execução do scraper
class ScraperThread(QThread):
    update_signal = pyqtSignal(str, str)
    finished_signal = pyqtSignal(bool, str, list, float)

    def __init__(self, cidade, orgao, ano_inicio, ano_fim, credor_nome):
        super().__init__()
        self.cidade = cidade
        self.orgao = orgao
        self.ano_inicio = ano_inicio
        self.ano_fim = ano_fim
        self.credor_nome = credor_nome

    def run(self):
        def callback(mensagem, empenho=None):
            self.update_signal.emit(mensagem, empenho or "")

        scraper = DiariasCollector(callback)
        sucesso, mensagem, dados_empenhos, valor_total = scraper.buscar_diarias(
            self.cidade, self.orgao, self.ano_inicio, self.ano_fim, self.credor_nome
        )
        self.finished_signal.emit(sucesso, mensagem, dados_empenhos, valor_total)

# Tela de boas-vindas
class WelcomeScreen(QWidget):
    def __init__(self, controller):
        super().__init__()
        self.controller = controller
        self.setup_ui()

    def setup_ui(self):
        layout = QVBoxLayout()

        self.log_text = QTextEdit()
        self.log_text.setReadOnly(True)

        title_label = QLabel("Bem-vindo ao Diárias Scraper")
        title_label.setFont(QFont("", 18, QFont.Weight.Bold))
        title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)

        desc_label = QLabel("Ferramenta para buscar diárias em portais de transparência.")
        desc_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        desc_label.setWordWrap(True)

        instructions = QLabel("Selecione cidade, órgão, período e nome do credor.")
        instructions.setAlignment(Qt.AlignmentFlag.AlignCenter)
        instructions.setWordWrap(True)

        start_button = QPushButton("Iniciar Busca")
        start_button.clicked.connect(self.start_logging)
        start_button.setMinimumHeight(40)
        start_button.clicked.connect(self.controller.switch_to_search_screen)

        layout.addStretch()
        layout.addWidget(title_label)
        layout.addSpacing(20)
        layout.addWidget(desc_label)
        layout.addSpacing(30)
        layout.addWidget(instructions)
        layout.addSpacing(40)
        layout.addWidget(start_button)
        layout.addStretch()

        self.setLayout(layout)

    def start_logging(self):
       log_message("Iniciando a busca...")
       log_message("Erro na busca!", logging.ERROR)


# Tela de busca
class SearchScreen(QWidget):
    def __init__(self, controller):
        super().__init__()
        self.controller = controller
        self.callback = None
        self.scraper = DiariasCollector()
        self.thread = None

        self.setup_ui()  


    def setup_ui(self):
        layout = QVBoxLayout()

        title_label = QLabel("Busca de Diárias")
        title_label.setFont(QFont("", 16, QFont.Weight.Bold))
        title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)

        form_layout = QVBoxLayout()

        cidade_layout = QHBoxLayout()
        cidade_label = QLabel("Cidade:")
        self.cidade_combo = QComboBox()
        self.cidade_combo.addItems(self.scraper.cidades_orgaos.keys())
        self.cidade_combo.currentIndexChanged.connect(self.atualizar_orgaos)
        cidade_layout.addWidget(cidade_label)
        cidade_layout.addWidget(self.cidade_combo)

        orgao_layout = QHBoxLayout()
        orgao_label = QLabel("Órgão:")
        self.orgao_combo = QComboBox()
        orgao_layout.addWidget(orgao_label)
        orgao_layout.addWidget(self.orgao_combo)

        periodo_layout = QHBoxLayout()
        self.ano_inicio_edit = QLineEdit()
        self.ano_fim_edit = QLineEdit()
        periodo_layout.addWidget(QLabel("Ano Início:"))
        periodo_layout.addWidget(self.ano_inicio_edit)
        periodo_layout.addWidget(QLabel("Ano Fim:"))
        periodo_layout.addWidget(self.ano_fim_edit)

        credor_layout = QHBoxLayout()
        self.credor_edit = QLineEdit()
        credor_layout.addWidget(QLabel("Nome do Credor:"))
        credor_layout.addWidget(self.credor_edit)

        buttons_layout = QHBoxLayout()
        self.voltar_button = QPushButton("Voltar")
        self.voltar_button.clicked.connect(self.controller.switch_to_welcome_screen)
        self.buscar_button = QPushButton("Buscar Diárias")
        self.buscar_button.clicked.connect(self.iniciar_busca)
        buttons_layout.addWidget(self.voltar_button)
        buttons_layout.addWidget(self.buscar_button)

        form_layout.addLayout(cidade_layout)
        form_layout.addLayout(orgao_layout)
        form_layout.addLayout(periodo_layout)
        form_layout.addLayout(credor_layout)
        form_layout.addLayout(buttons_layout)

        layout.addWidget(title_label)
        layout.addSpacing(20)
        layout.addLayout(form_layout)

        self.setLayout(layout)
        self.atualizar_orgaos()

    def atualizar_orgaos(self):
        self.orgao_combo.clear()
        cidade = self.cidade_combo.currentText()
        if cidade in self.scraper.cidades_orgaos:
            self.orgao_combo.addItems(self.scraper.cidades_orgaos[cidade].keys())

    def iniciar_busca(self):
        cidade = self.cidade_combo.currentText()
        orgao = self.orgao_combo.currentText()
        ano_inicio = self.ano_inicio_edit.text()
        ano_fim = self.ano_fim_edit.text()
        credor_nome = self.credor_edit.text()

        valido, mensagem = self.scraper.validar_entrada(ano_inicio, ano_fim, credor_nome)
        if not valido:
            QMessageBox.warning(self, "Entrada Inválida", mensagem)
            return

        self.controller.switch_to_progress_screen(cidade, orgao, ano_inicio, ano_fim, credor_nome)

exibir_detalhes_log = False

# Update the LogHandler class
from rich.text import Text
from rich.console import Console

import re
from PyQt6.QtGui import QTextCursor

class LogHandler:
    def __init__(self, text_widget):
        self.text_widget = text_widget
        self.colors = {
            'SUCCESS': '#00FF00',
            'INFO': '#FFFFFF', 
            'WARNING': '#FFA500',
            'ERROR': '#FF0000'
        }

    def write(self, message):
        try:
            if message.strip() and not self._is_http_log(message):
                # Remove Rich markup tags usando regex
                message = self._remove_rich_tags(message)
                
                # Garante quebra de linha
                if not message.endswith('\n'):
                    message += '\n'
                
                # Define a cor baseada no conteúdo
                color = self._get_color(message)
                html_message = f'<span style="color:{color}; white-space:pre-wrap;">{message}</span>'
                
                # Insere HTML no QTextEdit
                cursor = self.text_widget.textCursor()
                cursor.movePosition(QTextCursor.MoveOperation.End)
                cursor.insertHtml(html_message)
                self.text_widget.setTextCursor(cursor)

                # Força scroll para o final
                self.text_widget.verticalScrollBar().setValue(
                    self.text_widget.verticalScrollBar().maximum()
                )

        except Exception as e:
            # fallback para texto plano, sem formatação
            self.text_widget.append(message)

    def _remove_rich_tags(self, message):
        # Remove qualquer tag [tag] ou [/tag]
        return re.sub(r'\[/?[a-zA-Z0-9_=#]+\]', '', message)

    def _get_color(self, message):
        if "Diária de Viagem" in message:
            return self.colors['SUCCESS']
        elif "Erro" in message or "cancelada" in message:
            return self.colors['ERROR']
        elif "Verificando" in message:
            return self.colors['INFO']
        return self.colors['INFO']

    def flush(self):
        pass

    def _is_http_log(self, message):
        http_patterns = [
            "Starting new HTTPS connection",
            "GET /",
            "HTTP/1.1",
            "Connected to",
            "Starting new HTTP connection"
        ]
        return any(pattern in message for pattern in http_patterns)


class ProgressScreen(QWidget):
    def __init__(self, controller, callback=None):
        super().__init__()
        self.controller = controller
        self.callback = callback
        self.thread = None

        self.setup_ui()
        self.setup_logger()

    def setup_ui(self):
        layout = QVBoxLayout()

        title_label = QLabel("Buscando Diárias...")
        title_label.setFont(QFont("", 16, QFont.Weight.Bold))
        title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self.info_label = QLabel()
        self.info_label.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self.empenho_label = QLabel()
        self.empenho_label.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self.log_text = QTextEdit()  # <== AQUI criamos o atributo antes de usar
        self.log_text.setReadOnly(True)

        self.log_text.setFont(QFont("Monospace", 10))
        self.log_text.setStyleSheet("background-color: black; font-family: monospace; font-size: 12px;")

        self.cancelar_button = QPushButton("Cancelar")
        self.cancelar_button.clicked.connect(self.cancelar_busca)

        layout.addWidget(title_label)
        layout.addSpacing(10)
        layout.addWidget(self.info_label)
        layout.addWidget(self.empenho_label)
        layout.addWidget(self.log_text)
        layout.addWidget(self.cancelar_button)

        self.setLayout(layout)

    def setup_logger(self):
        log_handler = LogHandler(self.log_text)
        sys.stdout = log_handler
        sys.stderr = log_handler

        self.logger = logging.getLogger()
        self.logger.setLevel(logging.DEBUG)

        if self.logger.hasHandlers():
            self.logger.handlers.clear()

        stream_handler = logging.StreamHandler(log_handler)
        self.logger.addHandler(stream_handler)

        self.thread = None

    def iniciar_busca(self, cidade, orgao, ano_inicio, ano_fim, credor_nome):
        self.info_label.setText(f"Buscando para {credor_nome} em {cidade} - {orgao}")
        self.log_text.clear()

        self.thread = ScraperThread(cidade, orgao, ano_inicio, ano_fim, credor_nome)
        self.thread.update_signal.connect(self.atualizar_progresso)
        self.thread.finished_signal.connect(self.busca_finalizada)
        self.thread.start()

    def atualizar_progresso(self, mensagem, empenho=None):
        if empenho:
            self.empenho_label.setText(f"Número do empenho: {empenho}\n\n")
    
        # Add message to log
        self.logger.info(mensagem)

    def busca_finalizada(self, sucesso, mensagem, dados_empenhos, valor_total):
     if sucesso:
        try:
            # Create reports directory
            base_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "../../relatorios")
            os.makedirs(base_dir, exist_ok=True)

            # Save Excel report
            excel_path = save_to_excel(
                dados_empenhos, 
                credor_nome=self.thread.credor_nome,
                ano_inicio=self.thread.ano_inicio, 
                ano_fim=self.thread.ano_fim
            )

            # Save PDF report 
            pdf_path = save_to_pdf(
                dados_empenhos,
                valor_total=valor_total,
                credor_nome=self.thread.credor_nome,
                ano_inicio=self.thread.ano_inicio,
                ano_fim=self.thread.ano_fim,
                cidade=self.thread.cidade,
                orgao=self.thread.orgao
            )

            # Log success
            self.logger.info(f"\nRelatório Excel salvo em: {excel_path}")
            self.logger.info(f"Relatório PDF salvo em: {pdf_path}")

        except Exception as e:
            self.logger.error(f"\nErro ao salvar relatórios: {str(e)}")

    def cancelar_busca(self):
        if self.thread and self.thread.isRunning():
            self.thread.terminate()
            self.thread.wait()
            log_message("\nBusca cancelada pelo usuário.", logging.WARNING)
            self.empenho_label.setText("Busca cancelada!")

        self.cancelar_button.setText("Voltar")
        self.cancelar_button.clicked.disconnect()
        self.cancelar_button.clicked.connect(self.controller.switch_to_search_screen)

# Janela principal
class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Diárias Scraper")
        self.setMinimumSize(800, 600)

        self.central_widget = QWidget()
        self.setCentralWidget(self.central_widget)

        main_layout = QVBoxLayout(self.central_widget)
        self.stack = QStackedWidget()

        self.welcome_screen = WelcomeScreen(controller=self)
        self.search_screen = SearchScreen(controller=self)
        self.progress_screen = ProgressScreen(controller=self)

        self.stack.addWidget(self.welcome_screen)
        self.stack.addWidget(self.search_screen)
        self.stack.addWidget(self.progress_screen)

        main_layout.addWidget(self.stack)
        self.stack.setCurrentWidget(self.welcome_screen)

    def switch_to_welcome_screen(self):
        self.stack.setCurrentWidget(self.welcome_screen)

    def switch_to_search_screen(self):
        self.stack.setCurrentWidget(self.search_screen)

    def switch_to_progress_screen(self, cidade, orgao, ano_inicio, ano_fim, credor_nome):
        self.stack.setCurrentWidget(self.progress_screen)
        self.progress_screen.iniciar_busca(cidade, orgao, ano_inicio, ano_fim, credor_nome)

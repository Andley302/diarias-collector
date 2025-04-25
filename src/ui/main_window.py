import os
import sys
from PyQt6.QtWidgets import  (QMainWindow, QWidget, QVBoxLayout, 
                             QLabel, QComboBox, QLineEdit, QPushButton, 
                             QTextEdit, QMessageBox, QStackedWidget, QFormLayout, QApplication, QFileDialog)
from PyQt6.QtCore import Qt, QThread, pyqtSignal, QDate, QUrl
from PyQt6.QtGui import QFont, QIcon, QDesktopServices

from src.diarias_scraper import DiariasCollector
from src.utils import save_to_excel, save_to_pdf
from rich.console import Console
from rich.logging import RichHandler
import logging


console = Console()
logging.basicConfig(
    level=logging.DEBUG, 
    format="%(message)s", 
    handlers=[RichHandler(console=console)]
)

def log_message(message, level=logging.INFO):
    logging.log(level, message)

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

        title_font = QFont("Segoe UI", 18, QFont.Weight.Bold)
        title_font.setStyleStrategy(QFont.StyleStrategy.PreferAntialias)

        title_label = QLabel("Bem-vindo ao Diárias Collector")
        title_label.setFont(title_font)
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


        # Estilizando o botão
        start_button.setStyleSheet("""
            QPushButton {
                background-color: #4CAF50; /* Cor de fundo verde */
                color: white; /* Cor do texto branco */
                border: none; /* Sem borda */
                padding: 10px 20px; /* Espaçamento interno */
                text-align: center; /* Texto centralizado */
                text-decoration: none; /* Sem sublinhado */
                font-size: 16px;
                margin: 4px 2px;
                border-radius: 5px; /* Bordas arredondadas */
            }

            QPushButton:hover {
                background-color: #45a049; /* Cor de fundo verde mais escura ao passar o mouse */
            }

            QPushButton:pressed {
                background-color: #367c39; /* Cor de fundo verde ainda mais escura ao pressionar */
            }
        """)

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
        wrapper_layout = QVBoxLayout()
        wrapper_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        layout = QVBoxLayout()
        layout.setAlignment(Qt.AlignmentFlag.AlignTop)

        # Título
        title_label = QLabel("Busca de Diárias")
        title_font = QFont("Segoe UI", 18, QFont.Weight.Bold)
        title_font.setStyleStrategy(QFont.StyleStrategy.PreferAntialias)
        title_label.setFont(title_font)
        title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)

        # Descrição
        description_label = QLabel("Preencha os dados abaixo para buscar informações sobre diárias.")
        description_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        description_label.setStyleSheet("color: gray; font-size: 12px;")

        # Formulário
        form_layout = QFormLayout()
        form_layout.setLabelAlignment(Qt.AlignmentFlag.AlignRight)
        form_layout.setFormAlignment(Qt.AlignmentFlag.AlignTop)

        # Cidade e órgão
        self.cidade_combo = QComboBox()
        self.cidade_combo.addItems(self.scraper.cidades_orgaos.keys())
        self.cidade_combo.currentIndexChanged.connect(self.atualizar_orgaos)

        self.orgao_combo = QComboBox()

        form_layout.addRow("Cidade:", self.cidade_combo)
        form_layout.addRow("Órgão:", self.orgao_combo)

        self.ano_inicio_combo = QComboBox()
        self.ano_fim_combo = QComboBox()

        ano_atual = QDate.currentDate().year()
        for ano in range(2010, 2026):
            self.ano_inicio_combo.addItem(str(ano))
            self.ano_fim_combo.addItem(str(ano))

        # Define o ano atual como selecionado
        index_atual = self.ano_inicio_combo.findText(str(ano_atual))
        if index_atual != -1:
            self.ano_inicio_combo.setCurrentIndex(index_atual)
            self.ano_fim_combo.setCurrentIndex(index_atual)

        form_layout.addRow("Ano Início:", self.ano_inicio_combo)
        form_layout.addRow("Ano Fim:", self.ano_fim_combo)

        # Nome do credor
        self.credor_edit = QLineEdit()
        form_layout.addRow("Nome:", self.credor_edit)

        buttons_layout = QVBoxLayout()
        self.sair_button = QPushButton("Sair")
        self.sair_button.setStyleSheet("background-color: red; color: white;")

        self.sair_button.clicked.connect(self.controller.confirmar_saida)
        self.buscar_button = QPushButton("Buscar Diárias")
        self.buscar_button.setStyleSheet("background-color: green; color: white;")
        self.buscar_button.clicked.connect(self.iniciar_busca)

        buttons_layout.addWidget(self.buscar_button)
        buttons_layout.addWidget(self.sair_button)

        layout.addWidget(title_label)
        layout.addWidget(description_label)
        layout.addSpacing(20)
        layout.addLayout(form_layout)
        layout.addSpacing(10)
        layout.addLayout(buttons_layout)

        wrapper_layout.addLayout(layout)
        self.setLayout(wrapper_layout)

        self.atualizar_orgaos()


    def atualizar_orgaos(self):
        self.orgao_combo.clear()
        cidade = self.cidade_combo.currentText()
        if cidade in self.scraper.cidades_orgaos:
            self.orgao_combo.addItems(self.scraper.cidades_orgaos[cidade].keys())

    def iniciar_busca(self):
            if not self.scraper.cidades_orgaos:
                QMessageBox.critical(
                   self,
                    "Erro ao carregar dados",
                    "Não foi possível carregar a lista de cidades e órgãos. Verifique o arquivo JSON.")
                return


            cidade = self.cidade_combo.currentText().strip()
            orgao = self.orgao_combo.currentText().strip()
            ano_inicio = self.ano_inicio_combo.currentText().strip()
            ano_fim = self.ano_fim_combo.currentText().strip()
            credor = self.credor_edit.text().strip()

            # Verificações
            if not cidade:
                QMessageBox.warning(self, "Campo obrigatório", "Selecione uma cidade.")
                return
            if not orgao:
                QMessageBox.warning(self, "Campo obrigatório", "Selecione um órgão.")
                return
            if not ano_inicio or not ano_fim:
                QMessageBox.warning(self, "Campo obrigatório", "Selecione o ano de início e fim.")
                return
            if int(ano_fim) < int(ano_inicio):
                QMessageBox.warning(self, "Ano inválido", "O ano final não pode ser anterior ao ano inicial.")
                return
            if not credor:
                QMessageBox.warning(self, "Campo obrigatório", "Digite o nome do credor.")
                return
    

            valido, mensagem = self.scraper.validar_entrada(ano_inicio, ano_fim, credor)
            if not valido:
                 QMessageBox.warning(self, "Entrada Inválida", mensagem)
                 return

            self.controller.switch_to_progress_screen(cidade, orgao, ano_inicio, ano_fim, credor)

#Logs Detalhados
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

        title_label = QLabel("Busca de Diárias")
        title_label.setFont( QFont("Segoe UI", 18, QFont.Weight.Bold))
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
        self.info_label.setText(f"Buscando diárias de {credor_nome} em {cidade} - {orgao}")
        self.log_text.clear()

        self.empenho_label.setText(
            f"<br><b><font color='green'>Iniciando Busca...</font></b><br>"
        )

        self.thread = ScraperThread(cidade, orgao, ano_inicio, ano_fim, credor_nome)
        self.thread.update_signal.connect(self.atualizar_progresso)
        self.thread.finished_signal.connect(self.busca_finalizada)
        self.thread.start()

    def atualizar_progresso(self, mensagem, empenho=None):
        if empenho:
            self.empenho_label.setText(
               f"<br>Número do empenho: {empenho}<br><br>"
               f"<b><font color='orange'>Esse processo pode demorar. Aguarde!</font></b><br>"
           )

        self.logger.info(mensagem)

    def busca_finalizada(self, sucesso, mensagem, dados_empenhos, valor_total):
     if sucesso:
        try:

            # Caminho para o Desktop
            user_profile = os.environ.get('USERPROFILE', os.path.expanduser("~"))
            desktop_path = os.path.join(user_profile, 'Desktop')

            # Exibir a janela de diálogo para escolher o diretório
            pasta_usuario = QFileDialog.getExistingDirectory(
                None,  # Passa None para não especificar uma janela pai
                "Escolha o diretório para salvar os relatórios",  # Título da janela
                desktop_path,  # Caminho inicial sendo o Desktop
                QFileDialog.Option.ShowDirsOnly  # Opção para mostrar apenas diretórios
            )

            # Se o usuário não escolher um diretório, usar o Desktop como padrão
            if not pasta_usuario:
                pasta_usuario = desktop_path

            # Criar o diretório base caso não exista
            os.makedirs(pasta_usuario, exist_ok=True)

            # Salvar o relatório Excel
            excel_path = save_to_excel(
                dados_empenhos, 
                credor_nome=self.thread.credor_nome,
                ano_inicio=self.thread.ano_inicio, 
                ano_fim=self.thread.ano_fim,
                cidade=self.thread.cidade,
                path_destino=pasta_usuario  # Usando o diretório escolhido
            )

            # Salvar o relatório PDF
            pdf_path = save_to_pdf(
                dados_empenhos,
                valor_total=valor_total,
                credor_nome=self.thread.credor_nome,
                ano_inicio=self.thread.ano_inicio,
                ano_fim=self.thread.ano_fim,
                cidade=self.thread.cidade,
                orgao=self.thread.orgao,
                path_destino=pasta_usuario  # Usando o diretório escolhido
            )

            self.cancelar_button.setText("Voltar")
            self.cancelar_button.clicked.disconnect()
            self.cancelar_button.clicked.connect(self.controller.switch_to_search_screen)

            self.empenho_label.setText(
            f"<br><b><font color='green'>Arquivos salvos com sucesso!</font></b><br>"
            f"<a href='{pdf_path}'>Clique aqui para abrir o PDF</a><br>"
            )
        
            self.empenho_label.setOpenExternalLinks(False)  # Desliga a abertura automática
            self.empenho_label.linkActivated.connect(self.controller.abrir_pdf_no_navegador)  # Conecta seu slot

            # Log de sucesso
            if excel_path:  # Verifica se excel_path não é None, vazio ou falso
                self.logger.info(f"\nRelatório Excel salvo em: {excel_path}")
            self.logger.info(f"Relatório PDF salvo em: {pdf_path}")

            # Exibir mensagem de sucesso
            QMessageBox.information(None, "Sucesso", f"Relatórios salvos em:\n{pasta_usuario}")

        except Exception as e:
            self.logger.error(f"\nErro ao salvar relatórios: {str(e)}")
            QMessageBox.critical(None, "Erro", f"Erro ao salvar relatórios: {str(e)}")
        
            self.cancelar_button.setText("Voltar")
            self.cancelar_button.clicked.disconnect()
            self.cancelar_button.clicked.connect(self.controller.switch_to_search_screen)

    def cancelar_busca(self):
        if self.thread and self.thread.isRunning():
            self.thread.terminate()
            self.thread.wait()
            log_message("Busca cancelada pelo usuário.", logging.WARNING)
            self.empenho_label.setText(
               f"<br><b><font color='red'>Busca cancelada!</font></b><br>"
            )

        self.cancelar_button.setText("Voltar")
        self.cancelar_button.clicked.disconnect()
        self.cancelar_button.clicked.connect(self.controller.switch_to_search_screen)

# Janela principal
class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Diárias Collector")
        self.setMinimumSize(800, 600)
        icone = QIcon("resources/icon.ico")
        self.setWindowIcon(icone)

        self.setWindowFlags(
        Qt.WindowType.Window |
        Qt.WindowType.WindowCloseButtonHint | Qt.WindowType.WindowMinimizeButtonHint)
        self.setFixedSize(self.size()) 

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
    
    def exit_app(self):
      QApplication.quit()

    def confirmar_saida(self):
        reply = QMessageBox.question(
            self,
            "Confirmação",
            "Deseja realmente sair?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        if reply == QMessageBox.StandardButton.Yes:
            QApplication.quit()  

    def abrir_pdf_no_navegador(self, link):
      # Garante que é um caminho absoluto e corretamente codificado
      caminho_absoluto = os.path.abspath(link)
    
      if os.path.exists(caminho_absoluto):
          # Cria uma URL no formato file:///C:/... com encoding correto
          url = QUrl.fromLocalFile(caminho_absoluto)
          print(f"Abrindo PDF no navegador: {url.toString()}")
          QDesktopServices.openUrl(url)
      else:
          print(f"Arquivo não encontrado: {caminho_absoluto}")

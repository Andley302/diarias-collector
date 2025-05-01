import os
import sys
from PyQt6.QtWidgets import  (QMainWindow, QWidget, QVBoxLayout, 
                             QLabel, QComboBox, QLineEdit, QPushButton, 
                             QTextEdit, QMessageBox, QStackedWidget, QFormLayout, QApplication, QFileDialog, QCheckBox, QDialog, QMenuBar, QMenu, QTextBrowser)
from PyQt6.QtCore import Qt, QThread, pyqtSignal, QDate, QUrl, QSettings
from PyQt6.QtGui import QFont, QIcon, QDesktopServices, QAction, QTextCursor

from src.core.scraper import DiariasCollector
from src.utils import save_to_excel, save_to_pdf
from src.utils.version import VERSION
from src.utils.updater import UpdateChecker
from src.utils import obter_pasta_desktop
from rich.console import Console
from rich.logging import RichHandler
import logging
import re

console = Console()
nivel_log =  logging.INFO

for handler in logging.root.handlers[:]:
    logging.root.removeHandler(handler)

logging.basicConfig(
    level=nivel_log,
    format="%(message)s",
    handlers=[RichHandler(console=console, level=nivel_log)]
)

def log_message(message, level=logging.INFO):
    logging.log(level, message)

class ScraperThread(QThread):
    update_signal = pyqtSignal(str, str, str, int, int) 
    finished_signal = pyqtSignal(bool, str, list, float)

    def __init__(self, cidade, orgao, ano_inicio, ano_fim, credor_nome, verbose=False):
        super().__init__()
        self.cidade = cidade
        self.orgao = orgao
        self.ano_inicio = ano_inicio
        self.ano_fim = ano_fim
        self.credor_nome = credor_nome
        self.verbose = verbose

    def run(self):
            def callback(mensagem, empenho=None, data=None, total_empenhos=None, total_meses=None):            
                self.update_signal.emit(mensagem, empenho or "", data or "", 
                                       total_empenhos or 0, total_meses or 0)

            scraper = DiariasCollector(
                callback=callback,
                verbose=self.verbose,
            )

            try:
                sucesso, mensagem, dados_empenhos, valor_total = scraper.buscar_diarias(
                    self.cidade, self.orgao, self.ano_inicio, self.ano_fim, self.credor_nome, self.verbose)
                self.finished_signal.emit(sucesso, mensagem, dados_empenhos, valor_total)
            except Exception as e:
                erro_mensagem = f"Ocorreu um erro durante a busca: {e}"
                print(erro_mensagem) 
                self.finished_signal.emit(False, erro_mensagem, {}, 0.0)


class WelcomeScreen(QWidget):
    def __init__(self, controller):
        super().__init__()
        self.controller = controller
        self.setup_ui()

    def setup_ui(self):
        layout = QVBoxLayout()

        #self.log_text = QTextEdit()
        #self.log_text.setReadOnly(True)

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

        self.terms_checkbox = QCheckBox("Li e aceito os termos de uso")
        self.terms_checkbox.setChecked(True)

        terms_link = QLabel("<a href='#'>Ver termos de uso</a>")
        terms_link.setAlignment(Qt.AlignmentFlag.AlignCenter)
        terms_link.setOpenExternalLinks(False)
        terms_link.linkActivated.connect(self.controller.show_terms_dialog)


        start_button = QPushButton("Iniciar Busca")
        start_button.setMinimumHeight(40)
        start_button.clicked.connect(self.validate_and_start)
        start_button.setStyleSheet(""" 
            QPushButton {
                background-color: #4CAF50;
                color: white;
                border: none;
                padding: 10px 20px;
                text-align: center;
                font-size: 16px;
                margin: 4px 2px;
                border-radius: 5px;
            }
            QPushButton:hover {
                background-color: #45a049;
            }
            QPushButton:pressed {
                background-color: #367c39;
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
        layout.addSpacing(10)
        layout.addWidget(self.terms_checkbox)
        layout.addWidget(terms_link)
        layout.addSpacing(30)
        #layout.addWidget(self.log_text)
        layout.addStretch()

        self.setLayout(layout)

    def start_logging(self):
       log_message("Iniciando a busca...")
       log_message("Erro na busca!", logging.ERROR)

    
    def validate_and_start(self):
        if self.terms_checkbox.isChecked():
            self.start_logging()
            self.controller.switch_to_search_screen()
        else:
            QMessageBox.warning(self, "Aviso", "Você precisa aceitar os termos de uso para continuar.")


class SearchScreen(QWidget):
    def __init__(self, controller, verbose=False):
        super().__init__()
        self.controller = controller
        self.verbose = verbose
        self.callback = None
        self.scraper = DiariasCollector(callback=self.callback, verbose=self.verbose)
        self.thread = None
        self.setup_ui()


    def setup_ui(self):
        wrapper_layout = QVBoxLayout()
        wrapper_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        layout = QVBoxLayout()
        layout.setAlignment(Qt.AlignmentFlag.AlignTop)

        title_label = QLabel("Busca de Diárias")
        title_font = QFont("Segoe UI", 18, QFont.Weight.Bold)
        title_font.setStyleStrategy(QFont.StyleStrategy.PreferAntialias)
        title_label.setFont(title_font)
        title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)

        description_label = QLabel("Preencha os dados abaixo para buscar informações sobre diárias.")
        description_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        description_label.setStyleSheet("color: gray; font-size: 12px;")

        form_layout = QFormLayout()
        form_layout.setLabelAlignment(Qt.AlignmentFlag.AlignRight)
        form_layout.setFormAlignment(Qt.AlignmentFlag.AlignTop)

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

        index_atual = self.ano_inicio_combo.findText(str(ano_atual))
        if index_atual != -1:
            self.ano_inicio_combo.setCurrentIndex(index_atual)
            self.ano_fim_combo.setCurrentIndex(index_atual)

        form_layout.addRow("Ano Início:", self.ano_inicio_combo)
        form_layout.addRow("Ano Fim:", self.ano_fim_combo)

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

            
        self.controller.switch_to_progress_screen(cidade, orgao, ano_inicio, ano_fim, credor, self.verbose)
        
class LogHandler:
    def __init__(self, text_widget):
        self.text_widget = text_widget
        self.colors = {
            'SUCCESS': '#00FF00',
            'INFO': '#FFFFFF',
            'WARNING': '#FFA500',
            'ERROR': '#FF0000',
            'green': '#00FF00',
            'red': '#FF0000',
            'yellow': '#FFA500',
            'blue': '#0000FF',
            'cyan': '#00FFFF',
            'bold red': '#FF0000',
            'bold green': '#00FF00',
            'bold yellow': '#FFA500',
            'bold blue': '#0000FF',
            'bold cyan': '#00FFFF'
        }

    def write(self, message):
        try:
            if message.strip():
                if self._is_http_log(message):
                    return
                
                color = self._extract_rich_color(message)
                if not color:
                    color = self._get_color(message)
                    
                message = self._remove_rich_tags(message).strip() 
                
                if not message.endswith('\n'):
                    message += '\n'
                    
                html_message = f'<span style="color:{color}; white-space:pre-wrap;">{message}</span>'
                
                cursor = self.text_widget.textCursor()
                cursor.movePosition(QTextCursor.MoveOperation.End)
                cursor.insertHtml(html_message)
                self.text_widget.setTextCursor(cursor)
                
                self.text_widget.verticalScrollBar().setValue(
                    self.text_widget.verticalScrollBar().maximum()
                )
        except Exception as e:
            self.text_widget.append(f"[ERRO NO LOG] {message}")


    def _extract_rich_color(self, message):
        for color_key in self.colors.keys():
            if f'[{color_key}]' in message:
                return self.colors[color_key]
        return None

    def _remove_rich_tags(self, message):
        #message = re.sub(r'[✅❌⚠️🔍]', '', message)
        message = re.sub(r'\[/?(?:bold\s+)?[a-zA-Z0-9_=#]+\]', '', message)
        return message

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
            "Starting new HTTP connection",
            "Retrying",
            "Read timed out"
        ]
        return any(pattern in message for pattern in http_patterns)


class ProgressScreen(QWidget):
    def __init__(self, controller, verbose=False, settings={}):
        super().__init__()
        self.controller = controller
        self.callback = None
        self.settings = settings

        self.verbose = verbose
        
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

        self.log_text = QTextEdit()  
        self.log_text.setReadOnly(True)

        self.log_text.setFont(QFont("Monospace", 10))
        self.log_text.setStyleSheet("background-color: black; font-family: monospace; font-size: 12px;")

        self.cancelar_button = QPushButton("Cancelar")
        self.cancelar_button.setStyleSheet("background-color: red; color: white;")
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

    def iniciar_busca(self, cidade, orgao, ano_inicio, ano_fim, credor_nome, verbose):
        self.verbose = verbose
        
        self.info_label.setText(f"Buscando diárias de {credor_nome} em {cidade} - {orgao}")
        self.log_text.clear()

        self.empenho_label.setText(
            f"<br><b><font color='blue'>Iniciando Busca...</font></b><br>"
        )

        verbose = self.settings.value("verbose", False, type=bool)

        try:            
            self.thread = ScraperThread(
                cidade,
                orgao,
                ano_inicio,
                ano_fim,
                credor_nome,
                verbose
            )
        except AttributeError as e:
            self.log_text.append(f"<b><font color='red'>Erro ao iniciar busca:</font></b> {e}")
            return

        self.thread.update_signal.connect(self.atualizar_progresso)
        self.thread.finished_signal.connect(self.busca_finalizada)
        self.thread.start()


    def atualizar_progresso(self, mensagem, empenho=None, data=None, total_empenhos=None, total_meses=None):

        if empenho:
            color = 'orange'  
            time_estimate = 'vários minutos' 
            
            if total_meses is not None:
                if total_meses < 3:
                    color = 'green'
                    time_estimate = 'alguns minutos'
                elif total_meses < 6:
                    color = 'orange'
                    time_estimate = 'vários minutos'
                else:
                    color = 'orange'
                    time_estimate = 'vários minutos a horas'
            
            empenho_info = f"<br><b>Empenho N°{empenho}</b>"
            if data:
                empenho_info += f"<br><b>Data: {data}</b>"
            
            total_info = ""
            if total_empenhos > 0 or total_meses > 0:
                partes = []
                if total_empenhos > 0:
                    partes.append(f"{total_empenhos} URLs")
                if total_meses > 0:
                    partes.append(f"{total_meses} meses")
                total_info = " | ".join(partes)
                        
                wait_message = (
                    f"<br><b><font color='{color}'>Esse processo pode demorar {time_estimate}, a depender da<br>"
                    f"quantidade de anos selecionados e das diárias no portal. Aguarde!</font></b>"
                )

                if total_info:
                    wait_message += f"<br><br><small><i>Processando {total_info}</i></small><br>"

            
            self.empenho_label.setText(f"{empenho_info}<br>{wait_message}")

        self.logger.info(mensagem)

    def busca_finalizada(self, sucesso, mensagem, dados_empenhos, valor_total):
        if not sucesso:
            QMessageBox.critical(
                None,
                "Erro na Busca",
                f"A busca foi interrompida devido a um erro:\n\n{mensagem}\n\n"
                "Tente novamente mais tarde."
            )
            self.cancelar_button.setText("Voltar")
            self.cancelar_button.setStyleSheet("background-color: blue; color: white;")
            self.cancelar_button.clicked.disconnect()
            self.cancelar_button.clicked.connect(self.controller.switch_to_search_screen)
            return
        
        if valor_total == 0 and mensagem:
            self.empenho_label.setText(
                f"<br><b><font color='orange'>Busca concluída</font></b><br>"
                f"<font color='orange'>{mensagem}</font><br>"
            )
            self.cancelar_button.setText("Voltar")
            self.cancelar_button.setStyleSheet("background-color: blue; color: white;")
            self.cancelar_button.clicked.disconnect()
            self.cancelar_button.clicked.connect(self.controller.switch_to_search_screen)
            
            QMessageBox.information(
                None,
                "Busca Concluída",
                f"{mensagem}\n\nNenhum relatório foi gerado."
            )
            return
            
        try:
            desktop_path = obter_pasta_desktop()
            
            if not dados_empenhos or len(dados_empenhos) == 0:
                credor_nome_final = self.thread.credor_nome
            else:
                credor_nome_final = dados_empenhos[0]['Credor']
                
            pasta_usuario = QFileDialog.getExistingDirectory(
                None,  
                "Escolha o diretório para salvar os relatórios",  
                str(desktop_path), 
                QFileDialog.Option.ShowDirsOnly  
            )

            if not pasta_usuario:
                pasta_usuario = os.path.abspath(str(desktop_path))

            os.makedirs(pasta_usuario, exist_ok=True)

            excel_path = save_to_excel(
                dados_empenhos, 
                credor_nome=credor_nome_final,
                ano_inicio=self.thread.ano_inicio, 
                ano_fim=self.thread.ano_fim,
                cidade=self.thread.cidade,
                orgao=self.thread.orgao,
                path_destino=pasta_usuario  
            )

            pdf_path = save_to_pdf(
                dados_empenhos,
                valor_total=valor_total,
                credor_nome=credor_nome_final,
                ano_inicio=self.thread.ano_inicio,
                ano_fim=self.thread.ano_fim,
                cidade=self.thread.cidade,
                orgao=self.thread.orgao,
                path_destino=pasta_usuario  
            )

            self.cancelar_button.setText("Voltar")
            self.cancelar_button.setStyleSheet("background-color: blue; color: white;")
            self.cancelar_button.clicked.disconnect()
            self.cancelar_button.clicked.connect(self.controller.switch_to_search_screen)

            self.empenho_label.setText(
            f"<br><b><font color='green'>Arquivos salvos com sucesso!</font></b><br>"
            f"<a href='{pdf_path}'>Clique aqui para abrir o PDF</a><br>"
            )
        
            self.empenho_label.setOpenExternalLinks(False)  
            self.empenho_label.linkActivated.connect(self.controller.abrir_pdf_no_navegador)  

            if excel_path: 
                self.logger.info(f"\n\n[blue]📊 Relatório Excel salvo em: {excel_path}[/blue]")
            if pdf_path:
                self.logger.info(f"[blue]📄 Relatório PDF salvo em: {pdf_path}[/blue]")
            if excel_path and pdf_path:
                self.logger.info(f"[bold green]\n\n✅ Sucesso![/bold green]")

            QMessageBox.information(None, "Sucesso", f"Relatórios salvos em:\n{pasta_usuario}")

        except Exception as e:
            self.logger.error(f"\nErro ao salvar relatórios: {str(e)}")
            QMessageBox.critical(None, "Erro", f"Erro ao salvar relatórios: {str(e)}")
        
            self.cancelar_button.setText("Voltar")
            self.cancelar_button.setStyleSheet("background-color: blue; color: white;")
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
        self.cancelar_button.setStyleSheet("background-color: blue; color: white;")
        self.cancelar_button.clicked.disconnect()
        self.cancelar_button.clicked.connect(self.controller.switch_to_search_screen)

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
        self.settings = QSettings("Diárias Collector", "DiariasCollectorApp")

        self.verbose = self.settings.value("verbose", False, type=bool)

        self.setup_menu()

        main_layout = QVBoxLayout(self.central_widget)
        self.stack = QStackedWidget()

        self.welcome_screen = WelcomeScreen(controller=self)
        self.search_screen = SearchScreen(controller=self, verbose=self.verbose,)

        self.progress_screen = ProgressScreen(controller=self, verbose=self.verbose, settings=self.settings)

        self.stack.addWidget(self.welcome_screen)
        self.stack.addWidget(self.search_screen)
        self.stack.addWidget(self.progress_screen)

        main_layout.addWidget(self.stack)
        self.stack.setCurrentWidget(self.welcome_screen)
        
        self.check_for_updates(False, True)

    def switch_to_welcome_screen(self):
        self.stack.setCurrentWidget(self.welcome_screen)

    def switch_to_search_screen(self):
        self.stack.setCurrentWidget(self.search_screen)

    def switch_to_progress_screen(self, cidade, orgao, ano_inicio, ano_fim, credor_nome, verbose):
        self.stack.setCurrentWidget(self.progress_screen)

        self.progress_screen.cancelar_button.setText("Cancelar")
        self.progress_screen.cancelar_button.setStyleSheet("background-color: red; color: white;")

        try:
            self.progress_screen.cancelar_button.clicked.disconnect()
        except TypeError:
            pass

        try:
            self.progress_screen.cancelar_button.clicked.connect(self.progress_screen.cancelar_busca)
        except Exception as e:
            print(f"Erro ao conectar o evento do botão cancelar: {str(e)}")
            QMessageBox.critical(self, "Erro", f"Ocorreu um erro ao configurar o botão cancelar: {str(e)}")
            return 

        try:
            self.progress_screen.iniciar_busca(cidade, orgao, ano_inicio, ano_fim, credor_nome, verbose)
        except Exception as e:
            print(f"Erro ao iniciar a busca na tela de progresso: {str(e)}")
            QMessageBox.critical(self, "Erro", f"Ocorreu um erro ao iniciar a busca: {str(e)}")

        
    def exit_app(self):
      QApplication.quit()

    def closeEvent(self, event):
            reply = QMessageBox.question(
                self,
                "Confirmação",
                "Deseja realmente sair?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
            )
            if reply == QMessageBox.StandardButton.Yes:
                event.accept() 
            else:
                event.ignore() 

    def confirmar_saida(self):
        QApplication.quit() 

    def abrir_pdf_no_navegador(self, link):
      caminho_absoluto = os.path.abspath(link)
    
      if os.path.exists(caminho_absoluto):
          url = QUrl.fromLocalFile(caminho_absoluto)
          print(f"🌎 Abrindo PDF no navegador: {url.toString()}")

          QDesktopServices.openUrl(url)
      else:
          print(f"Arquivo não encontrado: {caminho_absoluto}")

    def check_for_updates(self, show_up_to_date_message=False, force_exit_on_update=False):
        """
        Check for updates and show notification if a new version is available.
        
        Args:
            show_up_to_date_message (bool): Whether to show a message when software is up to date.
                                        Set to True for manual checks, False for automatic checks.
            force_exit_on_update (bool): Whether to force exit the application after user confirms update.
        """
        try:
            updater = UpdateChecker()
            update_available, latest_version, release_url = updater.check_for_updates()
            
            if update_available:
                reply = QMessageBox.question(
                    self,
                    "Atualização Disponível",
                    f"Uma nova versão ({latest_version}) está disponível!\n\n"
                    f"Você está usando a versão {VERSION}.\n\n"
                    "Deseja visitar a página de download?",
                    QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
                )
                
                if reply == QMessageBox.StandardButton.Yes:
                    QDesktopServices.openUrl(QUrl(release_url))
                    if force_exit_on_update:
                        print("Fechando aplicativo para atualização...")
                        self.closeEvent = lambda event: event.accept()
                        import os
                        os._exit(0)  
            elif show_up_to_date_message:
                QMessageBox.information(
                    self,
                    "Software Atualizado",
                    f"Você já está usando a versão mais recente ({VERSION})."
                )
        except Exception as e:
            print(f"Erro ao verificar atualizações: {e}")



    def setup_menu(self):
        menubar = self.menuBar()

        config_menu = menubar.addMenu("Configurações")

        self.logs_action = QAction("Logs detalhados", self, checkable=True)
        self.logs_action.setChecked(self.verbose)
        self.logs_action.triggered.connect(self.toggle_verbose)
        
        config_menu.addAction(self.logs_action)

        config_menu.setStyleSheet("""
            QMenu {
            }

            QMenu::item:selected {
                background-color: #2196F3; 
                color: white;
            }

            QMenu::item:checked {
                background-color: #4CAF50; 
                color: white;
            }
        """)
    
        how_it_works_menu = menubar.addMenu("Informações")

        how_it_works_action = QAction("Como Funciona?", self)
        how_it_works_action.triggered.connect(self.show_how_it_works_dialog)
        how_it_works_menu.addAction(how_it_works_action)

        legal_notice_action = QAction("Aviso Legal", self)
        legal_notice_action.triggered.connect(self.show_legal_notice_dialog)
        how_it_works_menu.addAction(legal_notice_action)

        help_menu = menubar.addMenu("Sobre")
    
        terms_action = QAction("Ver Termos de Uso", self)
        terms_action.triggered.connect(self.show_terms_dialog)
        help_menu.addAction(terms_action)
    
        licenses_action = QAction("Licenças de Software", self)
        licenses_action.triggered.connect(self.show_licenses_dialog)
        help_menu.addAction(licenses_action)
    
        github_action = QAction("Abrir GitHub", self)
        github_action.triggered.connect(self.open_github)
        help_menu.addAction(github_action)

        version_action = QAction("Versão", self)
        version_action.triggered.connect(self.show_version)
        help_menu.addAction(version_action)
        
        update_action = QAction("Verificar Atualizações", self)
        update_action.triggered.connect(lambda: self.check_for_updates(True, True))
        help_menu.addAction(update_action)
    
    def toggle_verbose(self):
        self.verbose = self.logs_action.isChecked()
        self.settings.setValue("verbose", self.verbose)  
        print(f"[DEBUG] Logs detalhados: {self.verbose}")
    

    def show_licenses_dialog(self):
        dialog = QDialog(self)
        dialog.setWindowTitle("Licenças de Software")
        dialog.setMinimumSize(500, 400)
    
        layout = QVBoxLayout()
        text = QTextBrowser()
    
        licenses_text = """LICENÇAS DE SOFTWARE

        Este projeto utiliza os seguintes pacotes open source:

        PyQt6 (GPL v3)
        - Interface gráfica
        - https://www.qt.io/licensing

        Requests (Apache 2.0)
        - Requisições HTTP
        - https://requests.readthedocs.io/

        BeautifulSoup4 (MIT)
        - Parser HTML
        - https://www.crummy.com/software/BeautifulSoup/

        Pandas (BSD 3-Clause)
        - Manipulação de dados
        - https://pandas.pydata.org/

        XlsxWriter (BSD)
        - Exportação Excel
        - https://xlsxwriter.readthedocs.io/

        ReportLab (BSD)
        - Geração de PDFs
        - https://www.reportlab.com/

        Agradecemos aos desenvolvedores de todas estas ferramentas que tornaram este projeto possível."""

        text.setPlainText(licenses_text)
        layout.addWidget(text)
    
        close_button = QPushButton("Fechar")
        close_button.clicked.connect(dialog.accept)
        layout.addWidget(close_button, alignment=Qt.AlignmentFlag.AlignRight)
    
        dialog.setLayout(layout)
        dialog.exec()

    def show_how_it_works_dialog(self):
        dialog = QDialog(self)
        dialog.setWindowTitle("Como Funciona o Diárias Collector?")
        dialog.setMinimumSize(600, 500)
    
        layout = QVBoxLayout()
        layout.setSpacing(20)
        layout.setContentsMargins(20, 20, 20, 20)
    
        title = QLabel("Como Funciona o Diárias Collector?")
        title.setStyleSheet("""
            QLabel {
               font-size: 18px;
               font-weight: bold;
             }
        """)
        
        how_it_works_text = """Este programa ajuda você a encontrar e organizar informações de diárias pagas por orgãos públicos de forma automática.

        Veja como ele funciona:

        1. Você escolhe a cidade, o órgão público, os anos de início e fim, e o nome da pessoa (credor) que recebeu as diárias. É importante digitar o nome completo, pois nomes parciais podem causar erros ou confusão.
        2. O programa acessa o portal da transparência da cidade e busca todas as diárias dentro do período escolhido.
        3. Ele analisa cada diária e verifica se há palavras como "viagem", "locomoção", entre outras relacionadas.
        4. Se encontrar essas palavras e o nome for igual ao que você informou, ele guarda os dados dessa diária.
        5. Enquanto faz isso, o programa mostra na tela o que está sendo processado, passo a passo.
        6. Quando terminar, ele mostra o valor total encontrado.
        7. Você pode salvar esses dados em arquivos PDF ou Excel. O programa informa onde esses arquivos foram salvos.
        8. Depois, você pode abrir o PDF e ver todas as informações reunidas.

        Resumindo: o programa automatiza a busca. Em vez de você ter que verificar diária por diária no site, ele faz isso por você — de forma rápida e organizada.


        🟡 Atenção:

        - Os resultados dependem da forma como os dados são exibidos nos sites. Às vezes, o portal pode mudar ou ter falhas que atrapalham a leitura.
        - Se o nome estiver incompleto, abreviado ou diferente do que está registrado no portal, o programa pode não encontrar todas as diárias corretamente.
        - Ele pode deixar passar alguma informação, principalmente se a descrição estiver fora do padrão esperado.


        ✅ Sobre a legalidade:

        Este programa usa apenas informações públicas, coletadas diretamente dos portais oficiais de transparência. Ele não acessa dados sigilosos nem faz nenhuma alteração — apenas consulta e organiza o que já está disponível para qualquer cidadão.

        O programa é gratuito, de código aberto, e você pode ver como ele foi feito no GitHub."""

        layout.addWidget(title, alignment=Qt.AlignmentFlag.AlignCenter)
    
        text = QTextBrowser()
        text.setStyleSheet("""
                QTextBrowser {
                    border: 1px solid #DEE2E6;
                    border-radius: 5px;
                    padding: 15px;
                    font-size: 14px;
                    line-height: 1.6;
        }
        """)
        text.setPlainText(how_it_works_text)
        layout.addWidget(text)
    
        close_button = QPushButton("Fechar")
        close_button.clicked.connect(dialog.accept)
        layout.addWidget(close_button, alignment=Qt.AlignmentFlag.AlignRight)
    
        dialog.setLayout(layout)
        dialog.exec()

    def show_legal_notice_dialog(self):
        texto = (
            "Este programa acessa dados públicos disponíveis nos portais oficiais de "
            "transparência de orgãos públicos. Ele não acessa dados privados ou sigilosos, "
            "e não realiza alterações em nenhuma informação.\n\n"
            "Os dados exibidos são coletados automaticamente e podem conter falhas se os "
            "portais estiverem fora do ar, se houver mudanças na estrutura do site ou se o "
            "nome do credor estiver incompleto.\n\n"
            "É importante verificar manualmente as informações em caso de dúvidas.\n\n"
            "Este programa é gratuito, de código aberto, e existe para facilitar o acesso "
            "a informações públicas por qualquer cidadão."
        )

        QMessageBox.information(self, "Aviso Legal", texto)

    def show_version(self):
       QMessageBox.information(self, "Versão", f"Diárias Collector v{VERSION}")

    def open_github(self):
        QDesktopServices.openUrl(QUrl("https://github.com/Andley302/diarias-collector"))

    def show_terms_dialog(self):
        dialog = QDialog(self)
        dialog.setWindowTitle("Termos de Uso")
        dialog.setMinimumSize(500, 400)

        layout = QVBoxLayout()
        text = QTextBrowser()
        text.setPlainText("""TERMOS DE USO - DIÁRIAS COLLECTOR

        1. NATUREZA DO SOFTWARE

        Este é um software livre e de código aberto (open source) sob licença MIT, desenvolvido para automatizar a coleta de informações públicas sobre diárias e viagens disponíveis em portais de transparência.

        2. DADOS E PRECISÃO

        • Todos os dados coletados são de natureza pública
        • O sistema usa palavras-chave como "diárias", "viagens" etc para busca
        • Tente usar o nome completo do credor para melhorar a precisão. Nomes parciais ou abreviaturas podem gerar resultados imprecisos.
        • Podem ocorrer falhas na coleta devido a:
          - Mudanças nos padrões HTML dos portais
          - Implementação de captchas ou rate limits
          - Proteções contra automação
          - Alterações nas estruturas das páginas

        3. RESPONSABILIDADE DO USUÁRIO

        • Verificar a URL de cada empenho nos relatórios gerados
        • Conferir a precisão dos dados nas fontes oficiais
        • Assumir responsabilidade pelo uso dos dados coletados
        • Responder por eventuais problemas jurídicos decorrentes do uso

        4. LIMITAÇÕES TÉCNICAS
        
        • O sistema pode apresentar instabilidades devido a:
          - Proteções implementadas nos portais
          - Limites de requisições
          - Mudanças nas estruturas dos sites
          - Bloqueios de IP

        5. RESTRIÇÕES DE USO

        • Proibida a comercialização do software
        • Permitido:
          - Adicionar novas cidades
          - Implementar suporte a novos portais
          - Desenvolver novas funcionalidades
          - Contribuir com o código fonte

        6. BOAS PRÁTICAS

        • Use como ferramenta de automação
        • Verifique sempre os dados coletados
        • Respeite os limites dos portais
        • Mantenha intervalos entre consultas

        7. ISENÇÃO DE RESPONSABILIDADE

        O desenvolvedor não se responsabiliza por:
        • Precisão dos dados coletados
        • Uso indevido da ferramenta
        • Problemas legais decorrentes
        • Indisponibilidade dos portais                                       

        Ao usar este software, você concorda com todos os termos acima.""")  
       
        layout.addWidget(text)

        close_button = QPushButton("Fechar")
        close_button.clicked.connect(dialog.accept)
        layout.addWidget(close_button, alignment=Qt.AlignmentFlag.AlignRight)

        dialog.setLayout(layout)
        dialog.exec()

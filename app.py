import sys
import os


def main():

    if len(sys.argv) > 1 and sys.argv[1] == "--terminal":
        from src.cli.terminal_app import main as terminal_main
        terminal_main()
        return

    try:
        from PyQt6.QtWidgets import QApplication, QMessageBox
        from src.ui.main_window import MainWindow
    except ImportError as e:
        print("\033[93m[AVISO]\033[0m Interface gráfica indisponível. Instale PyQt6 para usar o modo gráfico.")
        print("Erro:", e)
        print("\nVocê pode usar o modo terminal com: python app.py --terminal")
        sys.exit(1)

    try:
        # Executar GUI
        app = QApplication(sys.argv)
        window = MainWindow()
        window.show()
        sys.exit(app.exec())
    except Exception as e:
        if "xcb" in str(e).lower():
            error_message = (
                "O plugin 'xcb' do Qt falhou ao iniciar.\n\n"
                "Provavelmente seu sistema não tem as bibliotecas necessárias.\n\n"
                "Tente instalar com:\n"
                "  sudo apt install libxcb-cursor0 libxcb-xinerama0 libxcb-icccm4 "
                "libxcb-image0 libxcb-keysyms1 libxcb-render-util0\n\n"
                "Alternativamente, você pode usar o modo terminal com: python app.py --terminal"
            )

            # Exibir aviso no terminal
            print("\033[93m[AVISO]\033[0m " + error_message)

            # Tentar exibir em janela gráfica
            try:
                msg = QMessageBox()
                msg.setIcon(QMessageBox.Icon.Warning)
                msg.setText("Erro ao carregar a interface gráfica")
                msg.setInformativeText("O plugin 'xcb' do Qt falhou ao iniciar.\n\n"
                                       "Seu sistema pode não ter as bibliotecas necessárias.")
                msg.setDetailedText(error_message)
                msg.setWindowTitle("Erro Qt")
                msg.exec()
            except:
                pass

            sys.exit(1)
        else:
            print(f"\033[91m[ERRO]\033[0m {str(e)}")
            print("\nVocê pode usar o modo terminal com: python app.py --terminal")
            import traceback
            traceback.print_exc()
            raise


if __name__ == "__main__":
    main()

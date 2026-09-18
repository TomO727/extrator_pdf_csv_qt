#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Extrator de campos de PDF para CSV - versão com tema Zili (PySide6/Qt)
========================================================================

Mesma funcionalidade da versão Tkinter (extrator_pdf_csv.py), mas com
interface em PySide6, para poder aplicar o tema escuro da empresa
(tema_zili.qss), o ícone da janela (assets/logo_zili.ico) e a logo
ZiliCred no topo da tela (assets/logo_zili.png).

A lógica de extração (regex, leitura do PDF, normalização de valor) é a
mesma e vem do arquivo extrator_core.py - qualquer ajuste feito lá vale
também para a versão Tkinter.

Dependências
------------
- Python 3.8+
- pdfplumber  ->  pip install pdfplumber
- PySide6     ->  pip install PySide6

Estrutura de pastas esperada (mantenha os arquivos juntos)
------------------------------------------------------------
    extrator_pdf_csv_qt.py
    extrator_core.py
    tema_zili.qss
    assets/
        logo_zili.png
        logo_zili.ico

Como usar
---------
1. Instale as dependências:  pip install pdfplumber PySide6
2. Rode:  python extrator_pdf_csv_qt.py
3. O fluxo na tela é o mesmo da versão Tkinter: selecionar PDF(s) ou
   pasta, opcionalmente ver o texto extraído do primeiro PDF, ajustar os
   padrões de Data/Prestador/Valor se necessário, extrair e salvar o CSV.
"""

import os
import re
import sys
import csv
import traceback
from datetime import datetime

from PySide6.QtCore import Qt, QThread, Signal, QObject
from PySide6.QtGui import QIcon, QPixmap
from PySide6.QtWidgets import (
    QApplication,
    QMainWindow,
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QGroupBox,
    QPushButton,
    QLabel,
    QLineEdit,
    QListWidget,
    QTableWidget,
    QTableWidgetItem,
    QTextEdit,
    QPlainTextEdit,
    QProgressBar,
    QFileDialog,
    QMessageBox,
    QDialog,
    QHeaderView,
    QAbstractItemView,
)

from extrator_core import (
    PADRAO_PADRAO,
    pdfplumber,
    extrair_texto_pdf,
    processar_pdf,
)

def _pasta_base():
    """
    Descobre a pasta onde estão o tema_zili.qss e a pasta assets/.

    Em execução normal (python extrator_pdf_csv_qt.py) é a pasta do próprio
    arquivo .py. Já em um executável gerado pelo PyInstaller (--onefile ou
    --onedir), o arquivo .py não existe mais como tal: os dados empacotados
    com --add-data ficam em sys._MEIPASS (onefile, pasta temporária) ou ao
    lado do executável (onedir). getattr(sys, "frozen", False) é a forma
    padrão de detectar que o código está rodando "congelado" pelo PyInstaller.
    """
    if getattr(sys, "frozen", False):
        return getattr(sys, "_MEIPASS", os.path.dirname(sys.executable))
    return os.path.dirname(os.path.abspath(__file__))


PASTA_BASE = _pasta_base()
CAMINHO_QSS = os.path.join(PASTA_BASE, "tema_zili.qss")
CAMINHO_ICONE = os.path.join(PASTA_BASE, "assets", "logo_zili.ico")
CAMINHO_LOGO = os.path.join(PASTA_BASE, "assets", "logo_zili.png")


# ----------------------------------------------------------------------
# Worker: roda a extração em uma thread separada para não travar a tela
# ----------------------------------------------------------------------
class ExtratorWorker(QObject):
    progresso = Signal(int, int)          # (atual, total)
    linha_pronta = Signal(dict)           # um resultado por PDF processado
    mensagem = Signal(str)                # linha de log
    concluido = Signal()

    def __init__(self, arquivos, padroes):
        super().__init__()
        self.arquivos = arquivos
        self.padroes = padroes

    def rodar(self):
        total = len(self.arquivos)
        for i, caminho in enumerate(self.arquivos, start=1):
            registro = processar_pdf(caminho, self.padroes)
            nome_arquivo = registro["arquivo"]

            if registro.get("erro"):
                self.mensagem.emit(f"[{nome_arquivo}] ERRO ao processar: {registro['erro']}")
            for aviso in registro.get("avisos", []):
                self.mensagem.emit(f"[{nome_arquivo}] AVISO: {aviso}")

            self.linha_pronta.emit(registro)
            self.progresso.emit(i, total)

        self.mensagem.emit(f"Extração concluída: {total} arquivo(s) processado(s).")
        self.concluido.emit()


class JanelaTextoExtraido(QDialog):
    def __init__(self, parent, titulo, texto):
        super().__init__(parent)
        self.setWindowTitle(titulo)
        self.resize(700, 500)
        layout = QVBoxLayout(self)
        caixa = QPlainTextEdit(self)
        caixa.setReadOnly(True)
        caixa.setPlainText(texto)
        layout.addWidget(caixa)


class JanelaPrincipal(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Extrator de PDF para CSV - Zili")
        self.resize(1020, 720)
        if os.path.isfile(CAMINHO_ICONE):
            self.setWindowIcon(QIcon(CAMINHO_ICONE))

        self.arquivos_pdf = []
        self.resultados = []
        self._thread = None
        self._worker = None

        self._montar_interface()
        self._verificar_dependencias()

    # ------------------------------------------------------------------
    def _montar_interface(self):
        central = QWidget()
        self.setCentralWidget(central)
        layout_principal = QVBoxLayout(central)
        layout_principal.setSpacing(10)

        # --- Cabeçalho com logo ---
        cabecalho = QHBoxLayout()
        if os.path.isfile(CAMINHO_LOGO):
            logo_label = QLabel()
            pixmap = QPixmap(CAMINHO_LOGO).scaledToHeight(56, Qt.SmoothTransformation)
            logo_label.setPixmap(pixmap)
            cabecalho.addWidget(logo_label)
        titulo_label = QLabel("Extrator de PDF para CSV")
        titulo_label.setStyleSheet("font-size: 20px; font-weight: bold;")
        cabecalho.addWidget(titulo_label)
        cabecalho.addStretch(1)
        layout_principal.addLayout(cabecalho)

        # --- 1. Arquivos PDF ---
        grupo_arquivos = QGroupBox("1. Arquivos PDF")
        v1 = QVBoxLayout(grupo_arquivos)
        linha_botoes = QHBoxLayout()
        btn_selecionar = QPushButton("Selecionar PDF(s)...")
        btn_selecionar.clicked.connect(self.selecionar_pdfs)
        btn_pasta = QPushButton("Selecionar pasta...")
        btn_pasta.clicked.connect(self.selecionar_pasta)
        btn_limpar = QPushButton("Limpar seleção")
        btn_limpar.clicked.connect(self.limpar_selecao)
        btn_ver_texto = QPushButton("Ver texto extraído do 1º PDF")
        btn_ver_texto.clicked.connect(self.ver_texto_extraido)
        for b in (btn_selecionar, btn_pasta, btn_limpar, btn_ver_texto):
            linha_botoes.addWidget(b)
        linha_botoes.addStretch(1)
        v1.addLayout(linha_botoes)

        self.lista_arquivos = QListWidget()
        self.lista_arquivos.setMaximumHeight(110)
        v1.addWidget(self.lista_arquivos)
        layout_principal.addWidget(grupo_arquivos)

        # --- 2. Padrões de busca ---
        grupo_padroes = QGroupBox("2. Padrões de busca de cada campo (ajuste conforme o texto do seu PDF)")
        v2 = QVBoxLayout(grupo_padroes)

        self.campo_data = QLineEdit(PADRAO_PADRAO["data"])
        self.campo_prestador = QLineEdit(PADRAO_PADRAO["prestador"])
        self.campo_valor = QLineEdit(PADRAO_PADRAO["valor"])

        v2.addLayout(self._linha_padrao("Data:", self.campo_data))
        v2.addLayout(self._linha_padrao("Prestador:", self.campo_prestador))
        v2.addLayout(self._linha_padrao("Valor:", self.campo_valor))

        linha_restaurar = QHBoxLayout()
        linha_restaurar.addStretch(1)
        btn_restaurar = QPushButton("Restaurar padrões originais")
        btn_restaurar.clicked.connect(self.restaurar_padroes)
        linha_restaurar.addWidget(btn_restaurar)
        v2.addLayout(linha_restaurar)

        layout_principal.addWidget(grupo_padroes)

        # --- 3. Ações ---
        linha_acoes = QHBoxLayout()
        self.btn_extrair = QPushButton("Extrair dados de todos os PDFs")
        self.btn_extrair.setObjectName("primary")
        self.btn_extrair.clicked.connect(self.iniciar_extracao)
        self.btn_salvar = QPushButton("Salvar como CSV...")
        self.btn_salvar.setEnabled(False)
        self.btn_salvar.clicked.connect(self.salvar_csv)
        self.barra_progresso = QProgressBar()
        linha_acoes.addWidget(self.btn_extrair)
        linha_acoes.addWidget(self.btn_salvar)
        linha_acoes.addWidget(self.barra_progresso, stretch=1)
        layout_principal.addLayout(linha_acoes)

        # --- 4. Resultados ---
        grupo_resultado = QGroupBox("3. Resultado")
        v4 = QVBoxLayout(grupo_resultado)
        self.tabela = QTableWidget(0, 5)
        self.tabela.setHorizontalHeaderLabels(
            ["Arquivo", "Data", "Prestador", "Valor (texto)", "Valor (número)"]
        )
        self.tabela.horizontalHeader().setSectionResizeMode(2, QHeaderView.Stretch)
        self.tabela.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.tabela.setSelectionBehavior(QAbstractItemView.SelectRows)
        v4.addWidget(self.tabela)
        layout_principal.addWidget(grupo_resultado, stretch=2)

        # --- 5. Log ---
        grupo_log = QGroupBox("Status / avisos")
        v5 = QVBoxLayout(grupo_log)
        self.caixa_log = QTextEdit()
        self.caixa_log.setReadOnly(True)
        self.caixa_log.setMaximumHeight(120)
        v5.addWidget(self.caixa_log)
        layout_principal.addWidget(grupo_log, stretch=1)

    def _linha_padrao(self, rotulo, campo):
        linha = QHBoxLayout()
        label = QLabel(rotulo)
        label.setFixedWidth(80)
        linha.addWidget(label)
        linha.addWidget(campo)
        return linha

    # ------------------------------------------------------------------
    def log(self, mensagem):
        hora = datetime.now().strftime("%H:%M:%S")
        self.caixa_log.append(f"[{hora}] {mensagem}")

    def _verificar_dependencias(self):
        if pdfplumber is None:
            self.log("ATENÇÃO: biblioteca 'pdfplumber' não encontrada. Instale com: pip install pdfplumber")
            QMessageBox.warning(
                self, "Dependência ausente",
                "A biblioteca 'pdfplumber' não está instalada.\n\n"
                "Feche este programa e instale com:\n\npip install pdfplumber",
            )

    # ------------------------------------------------------------------
    # Seleção de arquivos
    # ------------------------------------------------------------------
    def selecionar_pdfs(self):
        caminhos, _ = QFileDialog.getOpenFileNames(
            self, "Selecione um ou mais PDFs", "", "Arquivos PDF (*.pdf);;Todos os arquivos (*)"
        )
        if caminhos:
            self._adicionar_arquivos(caminhos)

    def selecionar_pasta(self):
        pasta = QFileDialog.getExistingDirectory(self, "Selecione a pasta com os PDFs")
        if pasta:
            encontrados = [
                os.path.join(pasta, f) for f in sorted(os.listdir(pasta))
                if f.lower().endswith(".pdf")
            ]
            if not encontrados:
                QMessageBox.information(self, "Nenhum PDF encontrado", "Não há arquivos .pdf nessa pasta.")
                return
            self._adicionar_arquivos(encontrados)

    def _adicionar_arquivos(self, caminhos):
        novos = 0
        for c in caminhos:
            if c not in self.arquivos_pdf:
                self.arquivos_pdf.append(c)
                self.lista_arquivos.addItem(os.path.basename(c))
                novos += 1
        self.log(f"{novos} arquivo(s) adicionado(s). Total: {len(self.arquivos_pdf)}.")

    def limpar_selecao(self):
        self.arquivos_pdf.clear()
        self.lista_arquivos.clear()
        self.log("Seleção de arquivos limpa.")

    def restaurar_padroes(self):
        self.campo_data.setText(PADRAO_PADRAO["data"])
        self.campo_prestador.setText(PADRAO_PADRAO["prestador"])
        self.campo_valor.setText(PADRAO_PADRAO["valor"])
        self.log("Padrões restaurados para os valores originais.")

    def ver_texto_extraido(self):
        if not self.arquivos_pdf:
            QMessageBox.information(self, "Nenhum arquivo", "Selecione ao menos um PDF primeiro.")
            return
        if pdfplumber is None:
            QMessageBox.critical(self, "Dependência ausente", "Instale 'pdfplumber' primeiro.")
            return
        caminho = self.arquivos_pdf[0]
        try:
            texto = extrair_texto_pdf(caminho)
        except Exception as e:
            QMessageBox.critical(self, "Erro ao ler PDF", str(e))
            return
        if not texto.strip():
            texto = ("(Nenhum texto foi extraído. O PDF pode ser uma imagem escaneada, "
                      "que exigiria OCR para ser lido.)")
        janela = JanelaTextoExtraido(self, f"Texto extraído - {os.path.basename(caminho)}", texto)
        janela.exec()

    # ------------------------------------------------------------------
    # Extração
    # ------------------------------------------------------------------
    def iniciar_extracao(self):
        if not self.arquivos_pdf:
            QMessageBox.information(self, "Nenhum arquivo", "Selecione ao menos um PDF primeiro.")
            return
        if pdfplumber is None:
            QMessageBox.critical(self, "Dependência ausente", "Instale 'pdfplumber' primeiro.")
            return

        padroes = {
            "data": self.campo_data.text(),
            "prestador": self.campo_prestador.text(),
            "valor": self.campo_valor.text(),
        }
        for nome, padrao in padroes.items():
            try:
                re.compile(padrao)
            except re.error as e:
                QMessageBox.critical(self, "Padrão inválido", f"O padrão de '{nome}' é inválido:\n{e}")
                return

        self.tabela.setRowCount(0)
        self.resultados = []
        self.btn_salvar.setEnabled(False)
        self.btn_extrair.setEnabled(False)
        self.barra_progresso.setMaximum(len(self.arquivos_pdf))
        self.barra_progresso.setValue(0)

        self._thread = QThread()
        self._worker = ExtratorWorker(list(self.arquivos_pdf), padroes)
        self._worker.moveToThread(self._thread)

        self._thread.started.connect(self._worker.rodar)
        self._worker.progresso.connect(self._atualizar_progresso)
        self._worker.linha_pronta.connect(self._inserir_linha_tabela)
        self._worker.mensagem.connect(self.log)
        self._worker.concluido.connect(self._finalizar_extracao)
        self._worker.concluido.connect(self._thread.quit)
        self._worker.concluido.connect(self._worker.deleteLater)
        self._thread.finished.connect(self._thread.deleteLater)

        self._thread.start()

    def _atualizar_progresso(self, atual, total):
        self.barra_progresso.setValue(atual)

    def _inserir_linha_tabela(self, registro):
        self.resultados.append(registro)
        linha = self.tabela.rowCount()
        self.tabela.insertRow(linha)
        valores = [
            registro["arquivo"], registro["data"], registro["prestador"],
            registro["valor"], registro["valor_num"],
        ]
        for col, valor in enumerate(valores):
            self.tabela.setItem(linha, col, QTableWidgetItem(str(valor)))

    def _finalizar_extracao(self):
        self.btn_extrair.setEnabled(True)
        if self.resultados:
            self.btn_salvar.setEnabled(True)

    # ------------------------------------------------------------------
    # Exportação CSV
    # ------------------------------------------------------------------
    def salvar_csv(self):
        if not self.resultados:
            QMessageBox.information(self, "Nada para salvar", "Execute a extração primeiro.")
            return

        caminho_csv, _ = QFileDialog.getSaveFileName(
            self, "Salvar CSV como...", "dados_extraidos.csv", "Arquivo CSV (*.csv)"
        )
        if not caminho_csv:
            return
        if not caminho_csv.lower().endswith(".csv"):
            caminho_csv += ".csv"

        colunas = ["arquivo", "data", "prestador", "valor", "valor_num"]
        cabecalho = ["Arquivo", "Data", "Prestador", "Valor", "Valor_numerico"]
        try:
            with open(caminho_csv, "w", newline="", encoding="utf-8-sig") as f:
                escritor = csv.writer(f, delimiter=";")
                escritor.writerow(cabecalho)
                for registro in self.resultados:
                    escritor.writerow([registro.get(c, "") for c in colunas])
        except Exception as e:
            QMessageBox.critical(self, "Erro ao salvar", str(e))
            self.log(f"ERRO ao salvar CSV: {e}")
            return

        self.log(f"CSV salvo em: {caminho_csv}")
        QMessageBox.information(self, "Concluído", f"Arquivo CSV salvo em:\n{caminho_csv}")


def carregar_tema(app):
    if os.path.isfile(CAMINHO_QSS):
        with open(CAMINHO_QSS, encoding="utf-8") as f:
            app.setStyleSheet(f.read())


def main():
    app = QApplication(sys.argv)
    carregar_tema(app)
    if os.path.isfile(CAMINHO_ICONE):
        app.setWindowIcon(QIcon(CAMINHO_ICONE))
    janela = JanelaPrincipal()
    janela.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()

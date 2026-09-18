# extrator_pdf_csv_qt
Extrator de campos de PDF para CSV - versão com tema Zili (PySide6/Qt)

Programa com interface gráfica que lê PDFs de texto selecionável (não
escaneados), extrai três campos - **Data**, **Prestador** e **Valor** - e
grava o resultado em um arquivo CSV.

Os padrões de busca padrão foram ajustados e testados contra o texto real
de uma **NFS-e (Nota Fiscal de Serviço Eletrônica) da Prefeitura de São
Paulo**. Se o seu PDF tiver um layout diferente, os padrões ficam
editáveis na própria tela do programa, sem precisar mexer no código.

Existem duas versões do programa, com a mesma lógica de extração por
baixo:

| Arquivo                    | Interface | Quando usar |
|----------------------------|-----------|-------------|
| `extrator_pdf_csv_qt.py`   | PySide6 (Qt) | Versão recomendada - usa o tema escuro da Zili, ícone e logo. |
| `extrator_pdf_csv.py`      | Tkinter | Alternativa mais simples, sem precisar instalar Qt (não usa o tema). |


## Estrutura de arquivos

```
extrator_pdf_csv_qt.py   - programa principal (versão com tema Zili)
extrator_pdf_csv.py      - versão alternativa em Tkinter
extrator_core.py         - lógica de extração compartilhada pelas duas versões
tema_zili.qss            - tema visual (Qt Style Sheet) aplicado na versão Qt
requirements.txt         - dependências Python
compiler.txt             - passo a passo para gerar um .exe (PyInstaller)
assets/
    logo_xxxx.ico         - ícone da janela/executável
    logo_xxxx.png         - logo exibida no topo da tela
```

Mantenha todos esses arquivos juntos, na mesma pasta - o programa procura
o tema, o ícone e a logo relativos à sua própria localização.


## Instalação

Com Python 3.10 ou mais novo instalado:

```
pip install -r requirements.txt
```

Isso instala `pdfplumber` (leitura de PDF) e `PySide6` (interface gráfica
da versão Qt). A versão Tkinter usa só o `pdfplumber` - o Tkinter em si já
vem com o Python no Windows/Mac; no Linux, se faltar, instale com
`sudo apt-get install python3-tk`.


## Como usar

1. Rode `python extrator_pdf_csv_qt.py` (ou `extrator_pdf_csv.py` para a
   versão Tkinter).
2. Clique em **"Selecionar PDF(s)..."** ou **"Selecionar pasta..."** para
   escolher os arquivos a processar.
3. (Opcional) Clique em **"Ver texto extraído do 1º PDF"** para ver o
   texto bruto do documento - isso ajuda a conferir o rótulo exato usado
   no seu PDF, caso precise ajustar algum padrão.
4. Ajuste os padrões de **Data**, **Prestador** e **Valor**, se o seu PDF
   usar rótulos diferentes dos padrões (veja a seção abaixo).
5. Clique em **"Extrair dados de todos os PDFs"**.
6. Confira o resultado na tabela e clique em **"Salvar como CSV..."**.

O CSV é gravado com separador `;` e codificação UTF-8 com BOM, para abrir
corretamente no Excel em português (acentos certos, sem precisar
configurar nada na importação).


## Sobre os padrões de busca (regex)

Cada campo usa uma expressão regular para encontrar o valor no texto do
PDF. Os padrões padrão (ajustados para a NFS-e de São Paulo) são:

- **Data**: encontra a primeira data (`dd/mm/aaaa`) que aparece logo após
  a palavra "Data" no texto (cobre tanto `Data: 15/03/2026` quanto
  `Data e Hora de Emissão` seguida da data em outra linha).
- **Prestador**: procura a seção `PRESTADOR DE SERVIÇOS` do documento e
  pega o `Nome/Razão Social` de dentro dela (evita pegar por engano o
  nome do Tomador do serviço, que aparece mais adiante no mesmo PDF).
- **Valor**: encontra o número logo após `VALOR TOTAL DO SERVIÇO`, com ou
  sem `:`, `=` ou `R$` entre o rótulo e o número.

Se o seu PDF não seguir esse layout (por exemplo, um recibo simples sem
o cabeçalho "PRESTADOR DE SERVIÇOS"), ajuste os padrões na tela do
programa. O botão **"Restaurar padrões originais"** volta para os valores
acima a qualquer momento.


## Limitações conhecidas

- O programa **não faz OCR**: se o PDF for uma imagem escaneada (sem
  texto selecionável/copiável), o texto extraído vem vazio e nenhum
  campo é encontrado.
- Os padrões padrão foram calibrados para o layout da NFS-e de São
  Paulo. Outros layouts de documento podem exigir ajuste manual dos
  padrões na tela.


## Gerar um executável (.exe)

Veja o arquivo `compiler.txt` para o passo a passo completo de
compilação com PyInstaller (Windows e macOS), incluindo os comandos
exatos e os erros mais comuns.


## Licenciamento

A versão Qt usa **PySide6** (não PyQt5), que tem licença LGPL - pode ser
usada e distribuída em software comercial fechado sem custo de licença.
Se a empresa já usa PyQt5 em outros sistemas e tem a licença resolvida,
é possível adaptar o import de `PySide6` para `PyQt5` (a API é quase
idêntica), mas isso não foi testado neste projeto.


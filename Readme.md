# Dashboard de Análise de Qualidade da Água - Sisagua (Python/Flask)

## Descrição

Este projeto consiste em um dashboard web interativo desenvolvido para visualizar e analisar dados de qualidade da água, utilizando como exemplo dados do Sistema de Informação de Vigilância da Qualidade da Água para Consumo Humano (Sisagua). O dashboard permite explorar diversas métricas, identificar tendências, verificar conformidade com padrões de potabilidade e visualizar a distribuição geográfica das coletas.

O backend é construído com Flask (Python) e utiliza Pandas e Geopandas para manipulação e análise dos dados. O frontend é renderizado com HTML, CSS (Bootstrap) e JavaScript, utilizando Plotly.js para a geração de gráficos interativos e Folium para a criação de mapas.

#Nome do Projeto e Integrantes do Grupo
#Integrantes:
- Bianca Santos
- Fernando Melo
- Igor Santos
- Raquel Moura
- Vinicius Santos

## Funcionalidades Implementadas

O dashboard oferece as seguintes visualizações e análises:

1.  **Visão Geral:**
    *   Cards com estatísticas resumidas: total de amostras, percentual de conformidade geral, percentual de não conformidade e número de bairros analisados.
    *   Gráfico de barras mostrando a distribuição do total de amostras coletadas por mês.
    *   Gráfico de barras exibindo o percentual de conformidade para os principais parâmetros (E. coli, Coliformes Totais, Turbidez, Cloro Residual Livre, Fluoreto).

2.  **Ranking por Bairro:**
    *   Gráfico de barras horizontais mostrando o número total de análises realizadas em cada bairro.
    *   Gráfico de barras horizontais classificando os bairros pelo percentual de conformidade geral das amostras.

3.  **Conformidade Detalhada:**
    *   Gráfico de barras (repetido da Visão Geral) com a conformidade por parâmetro.
    *   Gráfico de barras horizontais mostrando os pontos de coleta com os menores índices de conformidade.

4.  **Distribuição Temporal e Geográfica:**
    *   Gráfico de barras (repetido da Visão Geral) com a distribuição de amostras por mês.
    *   Gráfico de barras horizontais (repetido do Ranking) com a distribuição de amostras por bairro.

5.  **Tendências Temporais:**
    *   Gráfico de linhas mostrando a evolução do percentual de conformidade geral e por parâmetro ao longo dos meses.
    *   **Série Temporal Detalhada:** Gráfico de linhas mostrando a evolução do *valor médio* mensal para parâmetros numéricos específicos (Turbidez e Cloro Residual Livre).

6.  **Análise Microbiológica:**
    *   Gráfico de barras mostrando o percentual mensal de amostras com *presença* de indicadores microbiológicos (E. coli e Coliformes Totais).
    *   Gráfico de barras horizontais empilhadas mostrando o percentual de amostras com *presença* de indicadores microbiológicos por bairro.

7.  **Mapa Interativo:**
    *   Mapa geográfico (utilizando Folium) exibindo a localização das coletas.
    *   Marcadores coloridos indicando se a amostra está dentro (verde) ou fora (vermelho) do padrão de conformidade.
    *   Pop-ups com detalhes da amostra ao clicar em um marcador.
    *   Camada opcional com os limites geográficos dos bairros (requer arquivo GeoJSON).
    *   Legenda explicativa dos marcadores e critérios de conformidade.

8.  **Filtros Interativos:**
    *   Permite filtrar os dados exibidos em todos os gráficos e no mapa por Ano, Mês, Bairro e Parâmetro.

# Tecnologias Utilizadas

*   **Backend:**
    *   Python 3
    *   Flask (Microframework web)
    *   Pandas (Manipulação e análise de dados)
    *   GeoPandas (Manipulação de dados geoespaciais - para o GeoJSON)
    *   Folium (Criação de mapas interativos)
*   **Frontend:**
    *   HTML5
    *   CSS3 (com Bootstrap 5 para estilização e responsividade)
    *   JavaScript
    *   Plotly.js (Biblioteca para gráficos interativos)
*   **Formato dos Dados:**
    *   CSV (`dados_sisagua_limpos.csv`) para os dados das amostras.
    *   GeoJSON (`Delimitação_dos_Bairros_-_Dec._32.791_2020.geojson`) para os limites dos bairros.

## Configuração do Ambiente

1.  **Pré-requisitos:**
    *   Python 3.x instalado.
    *   `pip` (gerenciador de pacotes do Python) instalado.

2.  **Clonar o Repositório (após criá-lo no GitHub):**
    ```bash
    git clone https://github.com/SEU_USUARIO/NOME_DO_REPOSITORIO.git
    cd NOME_DO_REPOSITORIO
    ```

3.  **Criar um Ambiente Virtual (Recomendado):**
    ```bash
    python -m venv venv
    # No Windows
    .\venv\Scripts\activate
    # No macOS/Linux
    source venv/bin/activate
    ```

4.  **Instalar as Dependências:**
    Certifique-se de que o arquivo `requirements.txt` está na raiz do projeto.
    ```bash
    pip install -r requirements.txt
    ```
    *Observação:* A instalação do `geopandas` pode ter dependências adicionais dependendo do seu sistema operacional (como `fiona`, `pyproj`, `shapely`, `gdal`). Consulte a [documentação oficial do Geopandas](https://geopandas.org/en/stable/getting_started/install.html) para instruções específicas do seu sistema, caso encontre problemas.

## Estrutura de Arquivos Essenciais

```
QualiÁgua
│
├── app.py                     # Arquivo principal da aplicação Flask (backend)
├── dados_sisagua_limpos.csv   # Arquivo CSV com os dados das amostras
├── Delimitação_dos_Bairros_-_Dec._32.791_2020.geojson # Arquivo GeoJSON com limites dos bairros
├── requirements.txt           # Lista de dependências Python
├── README.md                  # Este arquivo
│
├── static/                    # Pasta para arquivos estáticos (mapa gerado)
│   └── mapa_coletas.html      # Mapa gerado pelo Folium (criado na execução)
│
├── templates/                 # Pasta para templates HTML
│   └── index_vertical_final.html # Template principal do dashboard
│
└── venv/                      # Pasta do ambiente virtual (se criado)
```

## Executando a Aplicação

1.  Certifique-se de que seu ambiente virtual está ativado (se você criou um).
2.  Navegue até o diretório raiz do projeto no terminal.
3.  Execute o script Flask:
    ```bash
    python app.py
    ```
4.  Abra seu navegador web e acesse o endereço fornecido (geralmente `http://127.0.0.1:5000/` ou `http://0.0.0.0:5000/`).

O dashboard interativo será carregado, exibindo as análises e o mapa com base nos dados fornecidos.


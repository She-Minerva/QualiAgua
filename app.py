import os
import sqlite3
import pandas as pd
import json
import folium
import geopandas as gpd  # Added for GeoJSON
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime
from flask import Flask, render_template, jsonify, request, send_from_directory

app = Flask(__name__)

# Configurações
DB_PATH = 'dados_sisagua.db'
CSV_PATH = 'dados_sisagua_limpos.csv'
GEOJSON_PATH = 'Delimitação_dos_Bairros_-_Dec._32.791_2020.geojson' # Adicionado: caminho para o GeoJSON
STATIC_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'static')
os.makedirs(STATIC_DIR, exist_ok=True)
# Ensure the templates folder exists for template copying
if not os.path.exists(os.path.join(os.path.dirname(os.path.abspath(__file__)), 'templates')):
    os.makedirs(os.path.join(os.path.dirname(os.path.abspath(__file__)), 'templates'))


# Valores de referência da Portaria GM/MS Nº 888/2021
VALORES_REFERENCIA = {
    'Escherichia coli': {'tipo': 'ausencia', 'valor': 'AUSENTE'},
    'Coliformes totais': {'tipo': 'ausencia', 'valor': 'AUSENTE'},
    'Turbidez (uT)': {'tipo': 'maximo', 'valor': 5.0},
    'Cloro residual livre (mg/L)': {'tipo': 'intervalo', 'min': 0.2, 'max': 5.0},
    'Fluoreto (mg/L)': {'tipo': 'maximo', 'valor': 1.5}
}

# Função para carregar dados
def carregar_dados(filtros=None):
    try:
        df = pd.read_csv(CSV_PATH)
        
        # Apply filters if provided
        if filtros:
            if filtros.get('ano') and filtros['ano'] != 'todos':
                if 'ano' in df.columns:
                    df['ano'] = pd.to_numeric(df['ano'], errors='coerce')
                    df.dropna(subset=['ano'], inplace=True)
                    df = df[df['ano'] == int(filtros['ano'])]
            if filtros.get('mes') and filtros['mes'] != 'todos':
                if 'mes' in df.columns:
                    df['mes'] = pd.to_numeric(df['mes'], errors='coerce')
                    df.dropna(subset=['mes'], inplace=True)
                    df = df[df['mes'] == int(filtros['mes'])]
            if filtros.get('bairro') and filtros['bairro'] != 'todos':
                if 'bairro' in df.columns:
                    df = df[df['bairro'] == filtros['bairro']]
            if filtros.get('parametro') and filtros['parametro'] != 'todos':
                if 'parametro' in df.columns:
                    df = df[df['parametro'] == filtros['parametro']]
        
        # Expected columns for map and other functions. Add if not existing.
        expected_cols = ['latitude', 'longitude', 'bairro', 'parametro', 'resultado', 'resultado_numerico',
                         'ponto_de_coleta', 'data_da_coleta', 'unidade_de_medida', 'id']
        for col in expected_cols:
            if col not in df.columns:
                if col == 'resultado_numerico': # For numeric result, it can be float
                    df[col] = pd.NA
                else:
                    df[col] = None # Or pd.NA for consistency

        # Convert geolocation columns to numeric, handling errors
        if 'latitude' in df.columns:
            df['latitude'] = pd.to_numeric(df['latitude'], errors='coerce')
        if 'longitude' in df.columns:
            df['longitude'] = pd.to_numeric(df['longitude'], errors='coerce')

        return df
    except FileNotFoundError:
        print(f"Error: CSV file '{CSV_PATH}' not found.")
        return pd.DataFrame(columns=['latitude', 'longitude', 'bairro', 'parametro', 'resultado', 'resultado_numerico', 'ponto_de_coleta', 'data_da_coleta', 'unidade_de_medida', 'id', 'ano', 'mes'])
    except Exception as e:
        print(f"Error loading data: {e}")
        return pd.DataFrame(columns=['latitude', 'longitude', 'bairro', 'parametro', 'resultado', 'resultado_numerico', 'ponto_de_coleta', 'data_da_coleta', 'unidade_de_medida', 'id', 'ano', 'mes'])

# Função para verificar conformidade (Modificada para aceitar a linha inteira)
def verificar_conformidade(row):
    # Use .get() to avoid KeyError if 'parametro' doesn't exist in the row
    parametro = row.get('parametro')
    try:
        if pd.isna(parametro) or parametro not in VALORES_REFERENCIA:
            return False 
        
        ref = VALORES_REFERENCIA[parametro]
        
        if ref['tipo'] == 'ausencia':
            resultado_str = str(row.get('resultado')).strip().upper() if pd.notna(row.get('resultado')) else ''
            return resultado_str == ref['valor'] 
        elif ref['tipo'] in ['maximo', 'intervalo']:
            # Use .get() for 'resultado_numerico'
            resultado_num_val = row.get('resultado_numerico')
            if pd.isna(resultado_num_val): # If NaN, try to convert 'resultado'
                if pd.notna(row.get('resultado')):
                    try:
                        resultado_num_val = float(str(row.get('resultado')).replace(',', '.'))
                    except (ValueError, TypeError):
                        return False # Conversion of 'resultado' failed
                else:
                    return False # 'resultado_numerico' is NaN and 'resultado' is also NaN/None
            
            try:
                valor = float(resultado_num_val)
                if ref['tipo'] == 'maximo':
                    return valor <= ref['valor']
                elif ref['tipo'] == 'intervalo':
                    return ref['min'] <= valor <= ref['max']
            except (ValueError, TypeError): # Failed to convert the already obtained value
                return False
        return False 
    except Exception as e:
        row_identifier = row.name if hasattr(row, 'name') else 'unknown (no index)'
        print(f"Error checking compliance for parameter '{parametro}' on row {row_identifier}: {e}")
        return False

# Função para calcular estatísticas
def calcular_estatisticas(df):
    try:
        stats = {}
        df_copy = df.copy() 
        
        stats['total_amostras'] = len(df_copy)
        stats['bairros_unicos'] = df_copy['bairro'].nunique() if 'bairro' in df_copy.columns else 0
        
        if not df_copy.empty:
            df_copy["conforme"] = df_copy.apply(verificar_conformidade, axis=1)
            stats['conformidade_geral'] = df_copy['conforme'].mean() * 100 if not df_copy['conforme'].empty else 0
            stats['nao_conformidade_geral'] = 100 - stats['conformidade_geral']
        else:
            stats['conformidade_geral'] = 0
            stats['nao_conformidade_geral'] = 100

        # Parameters for which statistics are explicitly calculated and named.
        # Add 'Fluoreto (mg/L)' if you want statistics for it too.
        parametros_para_stats = ['Escherichia coli', 'Coliformes totais', 'Turbidez (uT)', 'Cloro residual livre (mg/L)', 'Fluoreto (mg/L)']
        
        for param in parametros_para_stats:
            # Generate the key based on the parameter name (e.g., conformidade_escherichia_coli)
            param_key_stats = f"conformidade_{param.lower().replace(' ', '_').replace('(', '').replace(')', '').replace('/', '_')}"
            if 'parametro' in df_copy.columns and not df_copy.empty:
                df_param = df_copy[df_copy['parametro'] == param]
                # Reuses the 'conforme' column already calculated in df_copy
                if not df_param.empty:
                    conformidade = df_param['conforme'].mean() * 100
                    stats[param_key_stats] = conformidade
                else:
                    stats[param_key_stats] = 0 # No samples for this parameter
            else:
                stats[param_key_stats] = 0 # 'parametro' column doesn't exist or df is empty
        
        # Simplify names for template compatibility
        stats['conformidade_ecoli'] = stats.get('conformidade_escherichia_coli', 0)
        stats['conformidade_coliformes'] = stats.get('conformidade_coliformes_totais', 0)
        stats['conformidade_turbidez'] = stats.get('conformidade_turbidez_ut', 0)
        stats['conformidade_cloro'] = stats.get('conformidade_cloro_residual_livre_mg_l', 0)
        stats['conformidade_fluoreto'] = stats.get('conformidade_fluoreto_mg_l', 0) # Added
        
        return stats
    except Exception as e:
        print(f"Error calculating statistics: {e}")
        return {
            'total_amostras': 0, 'bairros_unicos': 0, 'conformidade_geral': 0,
            'nao_conformidade_geral': 0, 'conformidade_ecoli': 0,
            'conformidade_coliformes': 0, 'conformidade_turbidez': 0,
            'conformidade_cloro': 0, 'conformidade_fluoreto': 0
        }

# Função para obter dados de bairros
def obter_dados_bairros(df):
    try:
        bairros_data = []
        if df.empty or 'bairro' not in df.columns:
            return bairros_data
            
        df_copy = df.copy()
        
        for bairro_nome in df_copy['bairro'].unique():
            df_bairro = df_copy[df_copy['bairro'] == bairro_nome].copy() 
            total_analises = len(df_bairro)
            
            if not df_bairro.empty:
                df_bairro['conforme'] = df_bairro.apply(verificar_conformidade, axis=1)
                percentual_conforme = df_bairro['conforme'].mean() * 100 if not df_bairro['conforme'].empty else 0
            else:
                percentual_conforme = 0
            
            dados_bairro = {
                'bairro': bairro_nome,
                'total_analises': total_analises,
                'percentual_conforme': percentual_conforme
            }
            
            parametros_para_bairros = ['Escherichia coli', 'Coliformes totais', 'Turbidez (uT)', 'Cloro residual livre (mg/L)', 'Fluoreto (mg/L)']
            for param in parametros_para_bairros:
                param_key_bairro = param.lower().replace(' ', '_').replace('(', '').replace(')', '').replace('/', '_')
                if 'parametro' in df_bairro.columns:
                    df_param_bairro = df_bairro[df_bairro['parametro'] == param]
                    if not df_param_bairro.empty:
                        # Reuses the 'conforme' column already calculated for df_bairro
                        percentual = df_param_bairro['conforme'].mean() * 100
                        dados_bairro[f'percentual_{param_key_bairro}'] = percentual
                    else:
                        dados_bairro[f'percentual_{param_key_bairro}'] = None 
                else:
                    dados_bairro[f'percentual_{param_key_bairro}'] = None

            dados_bairro['percentual_ecoli'] = dados_bairro.get('percentual_escherichia_coli', None)
            dados_bairro['percentual_coliformes'] = dados_bairro.get('percentual_coliformes_totais', None)
            dados_bairro['percentual_turbidez'] = dados_bairro.get('percentual_turbidez_ut', None)
            dados_bairro['percentual_cloro'] = dados_bairro.get('percentual_cloro_residual_livre_mg_l', None)
            dados_bairro['percentual_fluoreto'] = dados_bairro.get('percentual_fluoreto_mg_l', None)
            
            bairros_data.append(dados_bairro)
        
        return bairros_data
    except Exception as e:
        print(f"Error getting neighborhood data: {e}")
        return []

# Função para obter distribuição por mês
def obter_distribuicao_mes(df):
    try:
        meses_data = []
        if df.empty or 'mes' not in df.columns:
            return meses_data

        df_copy = df.copy()
        df_copy['mes'] = pd.to_numeric(df_copy['mes'], errors='coerce')
        df_copy.dropna(subset=['mes'], inplace=True)

        nomes_meses = ['Janeiro', 'Fevereiro', 'Março', 'Abril', 'Maio', 'Junho', 
                       'Julho', 'Agosto', 'Setembro', 'Outubro', 'Novembro', 'Dezembro']
        
        for mes_num in range(1, 13):
            df_mes_atual = df_copy[df_copy['mes'] == mes_num].copy() 
            total_amostras = len(df_mes_atual)
            
            if total_amostras > 0:
                df_mes_atual['conforme'] = df_mes_atual.apply(verificar_conformidade, axis=1)
                percentual_conforme = df_mes_atual['conforme'].mean() * 100 if not df_mes_atual['conforme'].empty else 0
                
                dados_mes = {
                    'mes': mes_num,
                    'nome_mes': nomes_meses[mes_num-1],
                    'total_amostras': total_amostras,
                    'percentual_conforme': percentual_conforme
                }
                
                parametros_para_mes = ['Escherichia coli', 'Coliformes totais', 'Turbidez (uT)', 'Cloro residual livre (mg/L)', 'Fluoreto (mg/L)']
                for param in parametros_para_mes:
                    param_key_mes = param.lower().replace(' ', '_').replace('(', '').replace(')', '').replace('/', '_')
                    if 'parametro' in df_mes_atual.columns:
                        df_param_mes = df_mes_atual[df_mes_atual['parametro'] == param]
                        if not df_param_mes.empty:
                            percentual = df_param_mes['conforme'].mean() * 100 # Reuses 'conforme' from df_mes_atual
                            dados_mes[f'percentual_{param_key_mes}'] = percentual
                        else:
                            dados_mes[f'percentual_{param_key_mes}'] = None
                    else:
                        dados_mes[f'percentual_{param_key_mes}'] = None
                
                dados_mes['percentual_ecoli'] = dados_mes.get('percentual_escherichia_coli', None)
                dados_mes['percentual_coliformes'] = dados_mes.get('percentual_coliformes_totais', None)
                dados_mes['percentual_turbidez'] = dados_mes.get('percentual_turbidez_ut', None)
                dados_mes['percentual_cloro'] = dados_mes.get('percentual_cloro_residual_livre_mg_l', None)
                dados_mes['percentual_fluoreto'] = dados_mes.get('percentual_fluoreto_mg_l', None) # Added
                
                meses_data.append(dados_mes)
        
        return meses_data
    except Exception as e:
        print(f"Error getting monthly distribution: {e}")
        return []

# Função para obter distribuição por ponto de coleta
def obter_distribuicao_ponto_coleta(df):
    try:
        pontos_data = []
        if df.empty or 'ponto_de_coleta' not in df.columns:
            return pontos_data
            
        df_copy = df.copy()
        
        for ponto_coleta_nome in df_copy['ponto_de_coleta'].unique():
            df_ponto = df_copy[df_copy['ponto_de_coleta'] == ponto_coleta_nome].copy() 
            total_analises = len(df_ponto)
            
            if total_analises > 0:
                df_ponto['conforme'] = df_ponto.apply(verificar_conformidade, axis=1)
                percentual_conforme = df_ponto['conforme'].mean() * 100 if not df_ponto['conforme'].empty else 0
                
                dados_ponto = {
                    'ponto_de_coleta': ponto_coleta_nome,
                    'total_analises': total_analises,
                    'percentual_conforme': percentual_conforme
                }
                pontos_data.append(dados_ponto)
        
        return pontos_data
    except Exception as e:
        print(f"Error getting distribution by collection point: {e}")
        return []

# Função para criar mapa de coletas (MODIFIED for GeoJSON and individual markers)
def criar_mapa_coletas(df):
    try:
        mapa = folium.Map(location=[-12.9714, -38.5014], zoom_start=12, tiles='CartoDB positron')
        geojson_loaded = False

        # --- Neighborhood Layer (GeoJSON) ---
        geojson_full_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), GEOJSON_PATH)
        try:
            if os.path.exists(geojson_full_path):
                gdf = gpd.read_file(geojson_full_path)
                # Normalize the neighborhood name in GeoJSON to match CSV, if necessary
                if 'nome_bairr' in gdf.columns: # Adjust the neighborhood column name in your GeoJSON
                    gdf['nome_bairr_norm'] = gdf['nome_bairr'].astype(str).str.upper().str.strip()
                    tooltip_field = 'nome_bairr_norm'
                elif 'NM_BAIRRO' in gdf.columns: # Another common name
                    gdf['nome_bairr_norm'] = gdf['NM_BAIRRO'].astype(str).str.upper().str.strip()
                    tooltip_field = 'nome_bairr_norm'
                else: # If a known name column is not found, try to use the first geometric column
                    tooltip_field = gdf.columns[0]
                    print(f"Warning: Neighborhood name column not identified in GeoJSON. Using '{tooltip_field}' for tooltip.")

                folium.GeoJson(
                    gdf,
                    name="Limites dos Bairros", # Layer name
                    style_function=lambda x: {
                        'fillColor': 'transparent', # No fill to see markers
                        'color': 'black',           # Border color of neighborhoods
                        'weight': 0.7,              # Border thickness
                        'fillOpacity': 0.1          # Fill opacity (low so it doesn't cover)
                    },
                    tooltip=folium.GeoJsonTooltip(fields=[tooltip_field], aliases=['Bairro:'])
                ).add_to(mapa)
                geojson_loaded = True
            else:
                print(f"GeoJSON file not found: {geojson_full_path}")
        except Exception as e:
            print(f"Error loading or processing GeoJSON '{geojson_full_path}': {e}")

        # --- Sample Markers (CircleMarker) ---
        # Ensure latitude and longitude columns are numeric and remove NaNs for plotting
        df_mapa_valida = df.copy()
        if 'latitude' in df_mapa_valida.columns and 'longitude' in df_mapa_valida.columns:
            df_mapa_valida['latitude'] = pd.to_numeric(df_mapa_valida['latitude'], errors='coerce')
            df_mapa_valida['longitude'] = pd.to_numeric(df_mapa_valida['longitude'], errors='coerce')
            df_mapa_valida.dropna(subset=['latitude', 'longitude'], inplace=True)
        else:
            print("Warning: 'latitude' or 'longitude' columns not found in DataFrame for the map.")
            df_mapa_valida = pd.DataFrame() # Empty DataFrame if no coordinates

        if df_mapa_valida.empty:
            print("No valid coordinates samples to plot on the map.")
        else:
            for idx, row in df_mapa_valida.iterrows():
                try:
                    # verificar_conformidade is the original function
                    conforme_status = verificar_conformidade(row) # Call here for each sample
                    cor = 'green' if conforme_status else 'red'
                    situacao_texto = 'Dentro do padrão' if conforme_status else 'Fora do padrão'

                    # Use .get() for safe access to row fields for the popup
                    popup_text = (
                        f"<strong>Bairro:</strong> {row.get('bairro', 'N/A')}<br>"
                        f"<strong>Ponto de Coleta:</strong> {row.get('ponto_de_coleta', 'N/A')}<br>"
                        f"<strong>Data da coleta:</strong> {row.get('data_da_coleta', 'N/A')}<br>"
                        f"<strong>Parâmetro:</strong> {row.get('parametro', 'N/A')}<br>"
                        f"<strong>Resultado:</strong> {row.get('resultado', 'N/A')} "
                        f"{row.get('unidade_de_medida', '')}<br>"
                        f"<strong>Situação:</strong> {situacao_texto}<br>"
                        f"<small>ID Amostra: {row.get('id', idx)}</small>" # Use idx if 'id' doesn't exist
                    )
                    folium.CircleMarker(
                        location=[row['latitude'], row['longitude']],
                        radius=5, # Circle size
                        color=cor,
                        fill=True,
                        fill_color=cor,
                        fill_opacity=0.7,
                        popup=folium.Popup(popup_text, max_width=350) # Increase max_width if needed
                    ).add_to(mapa)
                except Exception as e:
                    row_identifier = row.name if hasattr(row, 'name') else f"index {idx}"
                    print(f"Error adding sample marker at {row_identifier}: {e}. Lat={row.get('latitude')}, Lon={row.get('longitude')}")
                    continue
        
        # --- Custom Legend ---
        # Values are taken from VALORES_REFERENCIA defined at the beginning of the script
        cloro_ref_map = VALORES_REFERENCIA['Cloro residual livre (mg/L)']
        turbidez_ref_map = VALORES_REFERENCIA['Turbidez (uT)']
        ecoli_ref_map = VALORES_REFERENCIA['Escherichia coli']
        coliformes_ref_map = VALORES_REFERENCIA['Coliformes totais']
        fluoreto_ref_map = VALORES_REFERENCIA['Fluoreto (mg/L)']

        bairros_legenda_item = ""
        if geojson_loaded: # Only add neighborhood legend item if GeoJSON was loaded
            bairros_legenda_item = "<div style='margin-bottom: 5px;'><i style='background:transparent; border: 1px solid black; width:12px; height:12px; display:inline-block; margin-right:5px;'></i> Limite Bairros</div>"

        legenda_html = f'''
          <div style="
              position: fixed; bottom: 20px; left: 20px; z-index: 1000;
              background-color: white; border: 2px solid grey; border-radius: 8px;
              padding: 10px; font-size: 12px; line-height: 1.5; max-width: 280px;">
              <h4 style='margin-top:0; margin-bottom: 5px; text-align: center;'>Legenda</h4>
              <div style='margin-bottom: 5px;'><i style='background:green; width:12px; height:12px; border-radius:50%; display:inline-block; margin-right:5px;'></i> Amostra Dentro do Padrão</div>
              <div style='margin-bottom: 5px;'><i style='background:red; width:12px; height:12px; border-radius:50%; display:inline-block; margin-right:5px;'></i> Amostra Fora do Padrão</div>
              {bairros_legenda_item}
              <hr style='margin: 5px 0;'>
              <div style='font-size: 10px; text-align: center;'><strong>Critérios (Portaria GM/MS 888/2021):</strong></div>
              <ul style='padding-left: 15px; margin-bottom: 0; font-size: 10px;'>
                  <li>Cloro: {cloro_ref_map['min']} - {cloro_ref_map['max']} mg/L</li>
                  <li>Turbidez: ≤ {turbidez_ref_map['valor']} uT</li>
                  <li>E. coli: {ecoli_ref_map['valor']}</li>
                  <li>Coliformes T.: {coliformes_ref_map['valor']}</li>
                  <li>Fluoreto: ≤ {fluoreto_ref_map['valor']} mg/L</li>
              </ul>
          </div>
          '''
        mapa.get_root().html.add_child(folium.Element(legenda_html))

        # Add layer control if there is the neighborhood layer
        if geojson_loaded:
            folium.LayerControl().add_to(mapa)

        mapa_path = os.path.join(STATIC_DIR, 'mapa_coletas.html')
        mapa.save(mapa_path)
        return True
    except Exception as e:
        print(f"Fatal error creating collection map: {e}")
        # Saving an error map can help with frontend diagnostics
        try:
            mapa_erro_fallback = folium.Map(location=[-12.9714, -38.5014], zoom_start=12)
            folium.Marker([-12.9714, -38.5014], popup=f"Critical error generating map: {e}").add_to(mapa_erro_fallback)
            mapa_erro_fallback.save(os.path.join(STATIC_DIR, 'mapa_coletas.html'))
        except:
            pass # Fail to save even the error map
        return False

# Rota principal
@app.route('/')
def index():
    try:
        df = carregar_dados()
        stats = calcular_estatisticas(df)
        
        bairros_lista = []
        if 'bairro' in df.columns and not df['bairro'].empty:
             bairros_lista = sorted(df['bairro'].dropna().unique())
        
        create_map_success = criar_mapa_coletas(df)
        if not create_map_success:
            print("Warning: Map generation failed. Dashboard might not display map correctly.")
        
        ultima_atualizacao = datetime.now().strftime("%d/%m/%Y %H:%M")
        
        return render_template('index.html', stats=stats, bairros=bairros_lista, ultima_atualizacao=ultima_atualizacao)
    except Exception as e:
        print(f"Error in main route: {e}")
        return render_template('index.html', stats={}, bairros=[], ultima_atualizacao="Erro ao carregar dados", error_message=str(e))

# Rota para arquivos estáticos
@app.route('/static/<path:path>')
def serve_static(path):
    return send_from_directory(STATIC_DIR, path)

# API para obter dados de bairros
@app.route('/api/bairros')
def api_bairros():
    try:
        filtros_req = request.args.to_dict()
        df = carregar_dados(filtros_req) # Pass filters to carregar_dados
        bairros = obter_dados_bairros(df)
        return jsonify(bairros)
    except Exception as e:
        print(f"Error in neighborhoods API: {e}")
        return jsonify([])

# API para obter distribuição por mês
@app.route('/api/distribuicao_mes')
def api_distribuicao_mes():
    try:
        filtros_req = request.args.to_dict()
        df = carregar_dados(filtros_req) # Pass filters
        meses = obter_distribuicao_mes(df)
        return jsonify(meses)
    except Exception as e:
        print(f"Error in monthly distribution API: {e}")
        return jsonify([])

# API para obter distribuição por ponto de coleta
@app.route('/api/distribuicao_ponto_coleta')
def api_distribuicao_ponto_coleta():
    try:
        filtros_req = request.args.to_dict()
        df = carregar_dados(filtros_req) # Pass filters
        pontos = obter_distribuicao_ponto_coleta(df)
        return jsonify(pontos)
    except Exception as e:
        print(f"Error in collection point distribution API: {e}")
        return jsonify([])

# API para filtrar dados
@app.route('/api/filtrar_dados', methods=['POST'])
def api_filtrar_dados():
    try:
        filtros = request.json
        df = carregar_dados(filtros)
        stats = calcular_estatisticas(df)
        map_created = criar_mapa_coletas(df) # Recreate map with filtered data
        
        response_data = stats.copy()
        response_data['map_status'] = 'success' if map_created else 'error'
        response_data['map_path'] = '/static/mapa_coletas.html' # Path to the generated map HTML
        return jsonify(response_data)
    except Exception as e:
        print(f"Error in data filtering API: {e}")
        return jsonify({'error': str(e), 'map_status': 'error'})

# Rota para atualizar dados
@app.route('/atualizar_dados', methods=['POST'])
def atualizar_dados():
    try:
        # Logic to update CSV_PATH here
        ultima_atualizacao = datetime.now().strftime("%d/%m/%Y %H:%M")
        return jsonify({
            'status': 'success',
            'message': 'Dados atualizados com sucesso (simulação)',
            'ultima_atualizacao': ultima_atualizacao
        })
    except Exception as e:
        print(f"Error updating data: {e}")
        return jsonify({'status': 'error', 'message': str(e)})

if __name__ == '__main__':
    # The original template copy logic is maintained.
    # Ensure the 'templates' folder exists or is created.
    templates_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'templates')
    os.makedirs(templates_dir, exist_ok=True)

    template_dst = os.path.join(templates_dir, 'index.html')
    if not os.path.exists(template_dst):
        try:
            import shutil
            # Tries to copy from 'index_vertical_final.html' if it exists in the templates folder or in the root
            src_paths_to_try = [
                os.path.join(templates_dir, 'index_vertical_final.html'),
                os.path.join(os.path.dirname(os.path.abspath(__file__)), 'index_vertical_final.html')
            ]
            template_src_found = None
            for src_path in src_paths_to_try:
                if os.path.exists(src_path):
                    template_src_found = src_path
                    break
            
            if template_src_found:
                shutil.copy(template_src_found, template_dst)
                print(f"Template index.html copied from {template_src_found}")
            else:
                print(f"Template file 'index_vertical_final.html' not found. Create an 'index.html' in the '{templates_dir}' folder.")
                # You can add the creation of a basic index.html here as a fallback if desired.
        except Exception as e:
            print(f"Error copying template: {e}")
    else:
        print("Template index.html already exists.")

    app.run(host='0.0.0.0', port=5001, debug=True)
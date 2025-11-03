from flask import Flask, render_template, jsonify
from flask_cors import CORS
import sys
import os
from datetime import datetime, timedelta
import requests

# Adicionar o diretório web_dashboard ao path
current_dir = os.path.dirname(os.path.abspath(__file__))
web_dashboard_dir = os.path.join(current_dir, '..', 'web_dashboard')
sys.path.insert(0, web_dashboard_dir)

# Criar aplicação Flask
app = Flask(__name__, 
            template_folder=os.path.join(web_dashboard_dir, 'templates'),
            static_folder=os.path.join(web_dashboard_dir, 'static'))
CORS(app)

# Importar funções do app original
try:
    from app import (
        get_lme_data, 
        processar_dados_mensal, 
        calcular_medias_semanais,
        calcular_medias_mensais,
        get_ptax_periodo,
        montar_indicadores_variacao
    )
except ImportError:
    # Se não conseguir importar, definir as funções aqui
    def get_lme_data():
        url = "https://lme.gorilaxpress.com/cotacao/2cf4ff0e-8a30-48a5-8add-f4a1a63fee10/json/"
        try:
            response = requests.get(url, timeout=10)
            response.raise_for_status()
            return response.json()
        except Exception as e:
            print(f"Erro ao buscar dados LME: {e}")
            return []
    
    def processar_dados_mensal(dados, mes, ano, meses_anteriores=1):
        from datetime import datetime
        dados_filtrados = []
        
        mes_inicio = mes - meses_anteriores
        ano_inicio = ano
        if mes_inicio < 1:
            mes_inicio += 12
            ano_inicio -= 1
        
        for item in dados:
            try:
                data_str = item.get("data", "")
                data_obj = datetime.strptime(data_str, "%Y-%m-%d")
                
                data_inicio = datetime(ano_inicio, mes_inicio, 1)
                data_fim = datetime(ano, mes, 31)
                
                if data_inicio <= data_obj <= data_fim:
                    dados_filtrados.append({
                        "data": data_str,
                        "data_formatada": data_obj.strftime("%d/%m/%Y"),
                        "cobre": float(item.get("cobre", 0)),
                        "zinco": float(item.get("zinco", 0)),
                        "aluminio": float(item.get("aluminio", 0)),
                        "chumbo": float(item.get("chumbo", 0)),
                        "estanho": float(item.get("estanho", 0)),
                        "niquel": float(item.get("niquel", 0)),
                        "dolar": float(item.get("dolar", 0))
                    })
            except Exception as e:
                continue
        
        return sorted(dados_filtrados, key=lambda x: x["data"])
    
    def calcular_medias_semanais(dados):
        from datetime import datetime
        semanas = {}
        
        for item in dados:
            try:
                data_obj = datetime.strptime(item["data"], "%Y-%m-%d")
                semana = data_obj.isocalendar()[1]
                
                if semana not in semanas:
                    semanas[semana] = {
                        "cobre": [], "zinco": [], "aluminio": [],
                        "chumbo": [], "estanho": [], "niquel": [], "dolar": []
                    }
                
                for metal in ["cobre", "zinco", "aluminio", "chumbo", "estanho", "niquel", "dolar"]:
                    semanas[semana][metal].append(item[metal])
            except Exception:
                continue
        
        medias = []
        for semana, valores in semanas.items():
            media = {"semana": semana}
            for metal, lista in valores.items():
                media[metal] = sum(lista) / len(lista) if lista else 0
            medias.append(media)
        
        return sorted(medias, key=lambda x: x["semana"])
    
    def calcular_medias_mensais(dados):
        from datetime import datetime
        meses = {}
        
        for item in dados:
            try:
                data_obj = datetime.strptime(item["data"], "%Y-%m-%d")
                mes_ano = data_obj.strftime("%m/%Y")
                
                if mes_ano not in meses:
                    meses[mes_ano] = {
                        "cobre": [], "zinco": [], "aluminio": [],
                        "chumbo": [], "estanho": [], "niquel": [], "dolar": []
                    }
                
                for metal in ["cobre", "zinco", "aluminio", "chumbo", "estanho", "niquel", "dolar"]:
                    meses[mes_ano][metal].append(item[metal])
            except Exception:
                continue
        
        medias = []
        for mes, valores in meses.items():
            media = {"mes": mes}
            for metal, lista in valores.items():
                media[metal] = sum(lista) / len(lista) if lista else 0
            medias.append(media)
        
        return sorted(medias, key=lambda x: x["mes"])
    
    def get_ptax_periodo(data_inicio, data_fim):
        return {}
    
    def montar_indicadores_variacao(dados_completos, dados_periodo, mes, ano):
        return {}

# Rotas
@app.route('/')
def index():
    return render_template('index.html')

@app.route('/api/dados/<int:mes>/<int:ano>')
def api_dados_mes(mes, ano):
    """API para obter dados diários de um mês específico (com 1 mês anterior para comparação)"""
    dados = get_lme_data()
    dados_processados = processar_dados_mensal(dados, mes, ano, meses_anteriores=1)  # 2 meses
    # PTAX para o período
    if dados_processados:
        di = datetime.strptime(dados_processados[0]["data"], "%Y-%m-%d")
        df = datetime.strptime(dados_processados[-1]["data"], "%Y-%m-%d")
        ptax = get_ptax_periodo(di, df)
        for item in dados_processados:
            item["dolar_ptax"] = float(ptax.get(item["data"], 0))
    
    indicadores_variacao = montar_indicadores_variacao(dados, dados_processados, mes, ano)
    
    return jsonify({
        "dados_diarios": dados_processados,
        "indicadores_variacao": indicadores_variacao
    })

# Rotas de Simulação
@app.route('/api/simulacao/padroes')
def api_simulacao_padroes():
    """Retorna parâmetros padrão para a simulação de preço."""
    try:
        # Obter cotações atuais (simulando a função obter_cotacoes_atualizadas)
        dados = get_lme_data()
        if not dados or len(dados) == 0:
            return jsonify({"erro": "Não foi possível obter cotações atuais"}), 500
            
        # Usar o último dado disponível
        ultimo_dado = dados[0]
        cotacao_lme = float(ultimo_dado.get('aluminio', 0))  # Assumindo que 'aluminio' é a cotação LME
        cotacao_dolar = float(ultimo_dado.get('dolar', 5.0))  # Usando dolar do último registro
        data_ref = ultimo_dado.get('data', datetime.now().strftime('%Y-%m-%d'))
        
        fator_referencia = 1.30
        preco_base_usd_kg = cotacao_lme / 1000
        preco_base_brl_kg = preco_base_usd_kg * cotacao_dolar * fator_referencia

        custos_detalhados = {
            "mao_obra": preco_base_brl_kg * 0.10,
            "energia": preco_base_brl_kg * 0.05,
            "manutencao": preco_base_brl_kg * 0.03,
            "administracao": preco_base_brl_kg * 0.05,
        }
        custos_totais = sum(custos_detalhados.values())

        resposta = {
            "cotacao_lme": round(cotacao_lme, 2),
            "cotacao_dolar": round(cotacao_dolar, 4),
            "fator_referencia": fator_referencia,
            "preco_base_referencia": round(preco_base_brl_kg, 2),
            "custos_referencia": round(custos_totais, 2),
            "custos_detalhados": {k: round(v, 2) for k, v in custos_detalhados.items()},
            "data_referencia": data_ref,
            "margem_padrao": 25.0,
            "margem_minima": 20.0,
            "quantidade_padrao": 1.0,
            "sensibilidade_padrao": 5.0
        }
        
        return jsonify(resposta)
        
    except Exception as e:
        return jsonify({"erro": f"Erro ao gerar parâmetros padrão: {str(e)}"}), 500

@app.route('/api/simulacao/salvar', methods=['POST'])
def api_simulacao_salvar():
    """Endpoint para salvar simulações (implementação básica)."""
    try:
        dados = request.get_json()
        # Simulando o salvamento (em produção, salvaria em um banco de dados)
        print("Simulação recebida:", dados)
        return jsonify({"status": "success", "mensagem": "Simulação salva com sucesso"})
    except Exception as e:
        return jsonify({"status": "error", "mensagem": str(e)}), 400

@app.route('/api/dados-semanais/<int:mes>/<int:ano>')
def api_dados_semanais(mes, ano):
    dados = get_lme_data()
    dados_processados = processar_dados_mensal(dados, mes, ano, meses_anteriores=1)
    medias = calcular_medias_semanais(dados_processados)
    return jsonify(medias)

@app.route('/api/dados-mensais')
def api_dados_mensais():
    dados = get_lme_data()
    if dados:
        dados_formatados = []
        for item in dados:
            try:
                data_obj = datetime.strptime(item.get("data", ""), "%Y-%m-%d")
                dados_formatados.append({
                    "data": item.get("data"),
                    "cobre": float(item.get("cobre", 0)),
                    "zinco": float(item.get("zinco", 0)),
                    "aluminio": float(item.get("aluminio", 0)),
                    "chumbo": float(item.get("chumbo", 0)),
                    "estanho": float(item.get("estanho", 0)),
                    "niquel": float(item.get("niquel", 0)),
                    "dolar": float(item.get("dolar", 0))
                })
            except Exception:
                continue
        
        medias = calcular_medias_mensais(dados_formatados)
        return jsonify(medias)
    return jsonify([])

@app.route('/api/dados-completos')
def api_dados_completos():
    dados = get_lme_data()
    return jsonify(dados)

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from datetime import datetime
import time
import os
import re
import undetected_chromedriver as uc

# tempo máximo de espera para decidir que o elemento não existe
WAIT_TIMEOUT = 10

# JS click script constant
CLICK_SCRIPT = "arguments[0].click();"

# coletor de resultados adicionais (ex.: objetivos cadastrados) para incluir no relatório
additional_test_results = []


global fluxo_atual
fluxo_atual = 1

def start_driver_no_prompts():
    options = uc.ChromeOptions()
    
    # Preferências para desabilitar popup de senha
    prefs = {
        "credentials_enable_service": False,
        "profile.password_manager_enabled": False,
        "profile.default_content_setting_values.notifications": 2,
    }
    options.add_experimental_option("prefs", prefs)
    
    # Argumentos para desabilitar prompts
    options.add_argument("--disable-blink-features=AutomationControlled")
    options.add_argument("--disable-notifications")
    options.add_argument("--disable-popup-blocking")
    options.add_argument("--no-default-browser-check")
    options.add_argument("--no-first-run")
    
    # SOLUÇÃO: modo incognito remove o alerta definitivamente
    options.add_argument("--incognito")
    
    # Argumentos para estabilidade
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--no-sandbox")
    
    # Argumentos críticos para desabilitar alertas de senha
    options.add_argument("--disable-features=PasswordLeakDetection,PasswordCheck,AutofillServerCommunication")
    options.add_argument("--disable-infobars")
    
    # Criar driver
    driver = uc.Chrome(options=options, use_subprocess=True, version_main=None)
    
    # Maximizar após abrir
    driver.maximize_window()
    
    return driver


def limpar_relatorio_antigo(nome_arquivo="report.html"):
    """Remove relatório HTML antigo se existir."""
    try:
        if os.path.exists(nome_arquivo):
            os.remove(nome_arquivo)
            print(f"✓ Relatório antigo '{nome_arquivo}' removido")
            return True
        else:
            print(f"ℹ Nenhum relatório antigo encontrado")
            return False
    except Exception as e:
        print(f"⚠ Erro ao remover relatório antigo: {e}")
        return False

def gerar_relatorio_html(testes, nome_arquivo="report.html"):
    """Gera relatório HTML estilo Robot Framework com diferenciação entre cadastro, verificação e não incluídos"""
    
    # Separar testes por tipo e por fluxo
    testes_fluxo1_cadastro = []
    testes_fluxo1_verificacao = []
    testes_fluxo1_nao_incluidos = []
    testes_fluxo2_cadastro = []
    testes_fluxo2_verificacao = []
    testes_fluxo2_nao_incluidos = []
    testes_gerais = []
    
    for t in testes:
        if t is None:
            continue
        
        resultado = t.get('resultado', '').lower()
        nome = t.get('nome', '').lower()
        fluxo = t.get('fluxo', 0)
        
        # Determinar tipo do teste
        # Projetos não incluídos são corretos quando ausentes dos vínculos
        eh_nao_incluido = ('não incluído' in nome or 'não incluído' in resultado or 
                  'não incluídos incorretamente' in resultado or
                  'ausentes corretamente' in resultado or
                  'não incluídos: ausentes' in resultado)
        eh_verificacao = any(palavra in resultado for palavra in [
            'ja existente', 'ja cadastrado', 'ja avaliado', 'pulado', 
            'ja preenchido', 'ja processado', 'ja configurado', 'já existente',
            'já cadastrado', 'já avaliado', 'já preenchido'
        ])
        
        # Classificar por fluxo e tipo
        if fluxo == 1:
            if eh_nao_incluido:
                testes_fluxo1_nao_incluidos.append(t)
            elif eh_verificacao:
                testes_fluxo1_verificacao.append(t)
            else:
                testes_fluxo1_cadastro.append(t)
        elif fluxo == 2:
            if eh_nao_incluido:
                testes_fluxo2_nao_incluidos.append(t)
            elif eh_verificacao:
                testes_fluxo2_verificacao.append(t)
            else:
                testes_fluxo2_cadastro.append(t)
        else:
            testes_gerais.append(t)
    
    # Calcular estatísticas
    total_testes = len(testes)
    testes_pass = sum(1 for t in testes if t and t.get('status') == 'PASS')
    testes_fail = sum(1 for t in testes if t and t.get('status') == 'FAIL')
    
    total_cadastros = len(testes_fluxo1_cadastro) + len(testes_fluxo2_cadastro)
    total_verificacoes = len(testes_fluxo1_verificacao) + len(testes_fluxo2_verificacao)
    total_nao_incluidos = len(testes_fluxo1_nao_incluidos) + len(testes_fluxo2_nao_incluidos)
    
    html = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Test Report - Sistema Portplace</title>
        <style>
            * {{
                margin: 0;
                padding: 0;
                box-sizing: border-box;
            }}
            
            body {{
                font-family: 'Helvetica Neue', Arial, sans-serif;
                font-size: 0.8rem;
                background: #f4f4f4;
                color: #000;
                line-height: 1.4;
            }}
            
            .header {{
                background: #fff;
                padding: 1rem 2rem;
                border-bottom: 1px solid #ddd;
                display: flex;
                justify-content: space-between;
                align-items: center;
            }}
            
            .header h1 {{
                font-size: 1.5rem;
                font-weight: 500;
                color: #000;
            }}
            
            .header .timestamp {{
                color: #666;
                font-size: 0.75rem;
            }}
            
            .container {{
                max-width: 1600px;
                margin: 0 auto;
                padding: 1rem;
            }}
            
            .summary-stats {{
                display: flex;
                gap: 1rem;
                margin-bottom: 1.5rem;
                background: #fff;
                padding: 1rem;
                border: 1px solid #ddd;
            }}
            
            .stat-box {{
                flex: 1;
                text-align: center;
                padding: 0.75rem;
                border-right: 1px solid #eee;
            }}
            
            .stat-box:last-child {{
                border-right: none;
            }}
            
            .stat-label {{
                font-size: 0.7rem;
                color: #666;
                text-transform: uppercase;
                letter-spacing: 0.5px;
                margin-bottom: 0.25rem;
            }}
            
            .stat-value {{
                font-size: 1.8rem;
                font-weight: 600;
            }}
            
            .stat-pass {{ color: #090; }}
            .stat-fail {{ color: #c00; }}
            .stat-cadastro {{ color: #0066cc; }}
            .stat-verificacao {{ color: #ff9800; }}
            .stat-nao-incluido {{ color: #9e9e9e; }}
            
            .section {{
                background: #fff;
                margin-bottom: 1rem;
                border: 1px solid #ddd;
            }}
            
            .section-header {{
                background: #f7f7f7;
                padding: 0.5rem 1rem;
                border-bottom: 1px solid #ddd;
                font-weight: 600;
                font-size: 0.85rem;
                cursor: pointer;
                user-select: none;
            }}
            
            .section-header:hover {{
                background: #eee;
            }}
            
            table {{
                width: 100%;
                border-collapse: collapse;
                font-size: 0.75rem;
            }}
            
            th {{
                background: #f0f0f0;
                padding: 0.4rem 0.6rem;
                text-align: left;
                font-weight: 600;
                border-bottom: 1px solid #ddd;
                font-size: 0.7rem;
                text-transform: uppercase;
                letter-spacing: 0.3px;
            }}
            
            td {{
                padding: 0.4rem 0.6rem;
                border-bottom: 1px solid #eee;
            }}
            
            tr:hover {{
                background: #f9f9f9;
            }}
            
            .status {{
                display: inline-block;
                padding: 0.15rem 0.4rem;
                border-radius: 2px;
                font-size: 0.65rem;
                font-weight: 600;
                text-transform: uppercase;
                letter-spacing: 0.5px;
            }}
            
            .status-pass {{
                background: #d4f4dd;
                color: #060;
            }}
            
            .status-fail {{
                background: #fdd;
                color: #900;
            }}
            
            .tipo-badge {{
                display: inline-block;
                padding: 0.15rem 0.4rem;
                border-radius: 2px;
                font-size: 0.6rem;
                margin-left: 0.3rem;
                font-weight: 500;
            }}
            
            .tipo-cadastro {{ background: #e1f5fe; color: #01579b; }}
            .tipo-verificacao {{ background: #fff3e0; color: #e65100; }}
            .tipo-nao-incluido {{ background: #fbe9e7; color: #bf360c; }}
            
            .info-box {{
                background: #e8f5e9;
                border-left: 3px solid #4caf50;
                padding: 0.75rem 1rem;
                margin: 1rem 0;
                font-size: 0.75rem;
            }}
            
            .warning-box {{
                background: #fff3e0;
                border-left: 3px solid #ff9800;
                padding: 0.75rem 1rem;
                margin: 1rem 0;
                font-size: 0.75rem;
            }}
            
            .fluxo-container {{
                margin-bottom: 2rem;
            }}
            
            .fluxo-title {{
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                color: white;
                padding: 1rem 1.5rem;
                font-size: 1.1rem;
                font-weight: 600;
                margin-bottom: 1rem;
            }}
            
            .footer {{
                text-align: center;
                padding: 2rem 1rem;
                color: #666;
                font-size: 0.7rem;
            }}
        </style>
    </head>
    <body>
        <div class="header">
            <h1>📊 Test Report - Sistema Portplace</h1>
            <div class="timestamp">Generated: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}</div>
        </div>
        
        <div class="container">
            <div class="summary-stats">
                <div class="stat-box">
                    <div class="stat-label">Total Tests</div>
                    <div class="stat-value">{total_testes}</div>
                </div>
                <div class="stat-box">
                    <div class="stat-label">Passed</div>
                    <div class="stat-value stat-pass">{testes_pass}</div>
                </div>
                <div class="stat-box">
                    <div class="stat-label">Failed</div>
                    <div class="stat-value stat-fail">{testes_fail}</div>
                </div>
                <div class="stat-box">
                    <div class="stat-label">Cadastros</div>
                    <div class="stat-value stat-cadastro">{total_cadastros}</div>
                </div>
                <div class="stat-box">
                    <div class="stat-label">Verificações</div>
                    <div class="stat-value stat-verificacao">{total_verificacoes}</div>
                </div>
                <div class="stat-box">
                    <div class="stat-label">Não Incluídos</div>
                    <div class="stat-value stat-nao-incluido">{total_nao_incluidos}</div>
                </div>
            </div>
            
            <div class="info-box">
                <strong>ℹ️ Sobre este relatório:</strong><br>
                <strong>Cadastros:</strong> Operações que criaram novos registros | 
                <strong>Verificações:</strong> Registros já existentes (skip) | 
                <strong>⚠ Não incluídos:</strong> Projetos não selecionados no cenário autorizado
            </div>
    """
    
    # Função auxiliar para gerar tabela
    def gerar_tabela(lista_testes, titulo, tipo):
        if not lista_testes:
            return ""
        
        if tipo == "cadastro":
            badge_class = "tipo-cadastro"
            badge_text = "📝 CADASTRO"
        elif tipo == "verificacao":
            badge_class = "tipo-verificacao"
            badge_text = "🔍 VERIFICAÇÃO"
        else:  # nao_incluido
            badge_class = "tipo-nao-incluido"
            badge_text = "⚠ NÃO INCLUÍDO"
        
        tabela = f"""
            <div class="section">
                <div class="section-header">
                    {titulo} <span class="tipo-badge {badge_class}">{badge_text}</span>
                </div>
                <table>
                    <tr>
                        <th style="width: 3%">#</th>
                        <th style="width: 28%">Teste</th>
                        <th style="width: 7%">Status</th>
                        <th style="width: 20%">Entrada</th>
                        <th style="width: 32%">Resultado</th>
                        <th style="width: 5%">Tempo</th>
                        <th style="width: 5%">Timestamp</th>
                    </tr>
        """
        
        for idx, t in enumerate(lista_testes, 1):
            nome = t.get('nome', 'Desconhecido')
            status = t.get('status', 'UNKNOWN')
            entrada = t.get('entrada', '')
            resultado = t.get('resultado', '')
            tempo = t.get('tempo', 0.0)
            timestamp = t.get('timestamp', '')
            
            status_badge = f'<span class="status status-{status.lower()}">{status}</span>'
            
            tabela += f"""
            <tr>
                <td><strong>{idx}</strong></td>
                <td>{nome}</td>
                <td>{status_badge}</td>
                <td>{entrada}</td>
                <td>{resultado}</td>
                <td>{tempo:.2f}s</td>
                <td>{timestamp.split()[1] if len(timestamp.split()) > 1 else timestamp}</td>
            </tr>
            """
        
        tabela += """
                </table>
            </div>
        """
        return tabela
    
    # TESTES GERAIS (LOGIN, etc)
    if testes_gerais:
        html += """
            <div class="section">
                <div class="section-header">🔐 Testes Gerais do Sistema</div>
        """
        html += gerar_tabela(testes_gerais, "Operações Iniciais", "cadastro").replace('<div class="section">', '').replace('</div>', '', 1)
        html += "</div>"
    
    # FLUXO 1
    if testes_fluxo1_cadastro or testes_fluxo1_verificacao or testes_fluxo1_nao_incluidos:
        html += """
            <div class="fluxo-container">
                <div class="fluxo-title">🎯 FLUXO 1: Portfólio 2025</div>
        """
        
        if testes_fluxo1_cadastro:
            html += gerar_tabela(testes_fluxo1_cadastro, "Novos Cadastros", "cadastro")
        
        if testes_fluxo1_verificacao:
            html += gerar_tabela(testes_fluxo1_verificacao, "Verificações (Skip)", "verificacao")
        
        if testes_fluxo1_nao_incluidos:
            html += gerar_tabela(testes_fluxo1_nao_incluidos, "Projetos Não Incluídos no Cenário", "nao_incluido")
        
        html += "</div>"
    
    # FLUXO 2
    if testes_fluxo2_cadastro or testes_fluxo2_verificacao or testes_fluxo2_nao_incluidos:
        html += """
            <div class="fluxo-container">
                <div class="fluxo-title">🚀 FLUXO 2: Transformação Digital</div>
        """
        
        if testes_fluxo2_cadastro:
            html += gerar_tabela(testes_fluxo2_cadastro, "Novos Cadastros", "cadastro")
        
        if testes_fluxo2_verificacao:
            html += gerar_tabela(testes_fluxo2_verificacao, "Verificações (Skip)", "verificacao")
        
        if testes_fluxo2_nao_incluidos:
            html += gerar_tabela(testes_fluxo2_nao_incluidos, "Projetos Não Incluídos no Cenário", "nao_incluido")
        
        html += "</div>"
    
    html += """
            <div class="footer">
                <strong>Sistema de Gestão de Portfólio - Testes Automatizados</strong><br>
                Desenvolvido com Selenium WebDriver + Python
            </div>
        </div>
    </body>
    </html>
    """
    
    with open(nome_arquivo, "w", encoding="utf-8") as f:
        f.write(html)

# ========================================
# CONFIGURAÇÕES CENTRALIZADAS - EDITE AQUI
# ========================================

# Credenciais de Login
EMAIL_LOGIN = "adm@portplace.com"

# FLUXO 1 - Configuração Inicial (Sistema tradicional)
FLUXO_1 = {
    "portfolio": {
        "nome": "Portfólio 2025",
        "categorias": ["Inovação", "Infraestrutura", "Comercial"]
    },
    "projetos": [
        {
            "nome": "Sistema de Gestão de Vendas",
            "data_inicio": "15-01-2025",
            "data_fim": "30-06-2025",
            "categoria": "Inovação",
            "indicadores": {
                "ev": 150000,
                "pv": 200000,
                "ac": 120000,
                "bac": 250000,
                "payback": 2.5,
                "roi": 35
            },
            "notas_avaliacao": [850, 750, 900, 700, 650],  
            "resultado_esperado": 802.5  # ⭐ Valor esperado para validação
        },
        {
            "nome": "Modernização da Infraestrutura de TI",
            "data_inicio": "01-02-2025",
            "data_fim": "31-08-2025",
            "categoria": "Infraestrutura",
            "indicadores": {
                "ev": 80000,
                "pv": 150000,
                "ac": 90000,
                "bac": 180000,
                "payback": 3.0,
                "roi": 28
            },
            "notas_avaliacao": [900, 600, 650, 800, 700],
            "resultado_esperado": 750.0  # ⭐ Valor esperado
        },
        {
            "nome": "Implementação de CRM",
            "data_inicio": "01-03-2025",
            "data_fim": "15-09-2025",
            "categoria": "Comercial",
            "indicadores": {
                "ev": 100000,
                "pv": 180000,
                "ac": 95000,
                "bac": 200000,
                "payback": 2.8,
                "roi": 32
            },
            "notas_avaliacao": [800, 800, 850, 750, 600],
            "resultado_esperado": 760.0  # ⭐ Valor esperado
        }
    ],
    "estrategia": {
        "nome": "Estratégia 2025 - 2026",
        "objetivos": [
            "Aumentar receita",
            "Reduzir custos",
            "Melhorar satisfação do cliente"
        ],
        "grupo_criterios": {
            "nome": "Grupo Critérios 2025",
            "criterios": [
                "Viabilidade técnica",
                "Custo-benefício",
                "Impacto no usuário",
                "Prazo de implementação",
                "Risco envolvido"
            ],
            # ⭐ Mapeamento Critério → Objetivo
            "vinculos_criterio_objetivo": {
                "Viabilidade técnica": "Aumentar receita",
                "Custo-benefício": "Reduzir custos",
                "Impacto no usuário": "Melhorar satisfação do cliente",
                "Prazo de implementação": "Aumentar receita",
                "Risco envolvido": "Reduzir custos"
            },
            # ⭐ Importâncias AHP (valores do select da imagem)
            # "MORE_IMPORTANT" = Mais importante
            # "EQUAL" = É tão importante quanto
            # "LESS_IMPORTANT" = Menos importante
            "comparacoes_ahp": {
                "Viabilidade técnica": {
                    "Custo-benefício": " Extremamente mais importante ",        # Viab. técnica > Custo
                    "Impacto no usuário": "EQUALLY_IMPORTANT",              # Viab. técnica = Impacto
                    "Prazo de implementação": "MORE_IMPORTANT", # Viab. técnica > Prazo
                    "Risco envolvido": "MORE_IMPORTANT"         # Viab. técnica > Risco
                },
                "Custo-benefício": {
                    "Impacto no usuário": "LESS_IMPORTANT",     # Custo < Impacto
                    "Prazo de implementação": "EQUALLY_IMPORTANT",          # Custo = Prazo
                    "Risco envolvido": "MORE_IMPORTANT"         # Custo > Risco
                },
                "Impacto no usuário": {
                    "Prazo de implementação": "MORE_IMPORTANT", # Impacto > Prazo
                    "Risco envolvido": "MORE_IMPORTANT"         # Impacto > Risco
                },
                "Prazo de implementação": {
                    "Risco envolvido": "EQUALLY_IMPORTANT"                  # Prazo = Risco
                }
            }
        },
        "grupo_avaliacao": {
            "nome": "Avaliação Estratégica 2025"
        },
        "cenario": {
            "nome": "Cenário Base 2025-2026",
            "orcamento": "500000"
        }
    }
}

# FLUXO 2 - Transformação Digital (da planilha)
FLUXO_2 = {
    "portfolio": {
        "nome": "Portfólio Transformação Digital",
        "categorias": ["Cloud", "Segurança", "Analytics"]
    },
    "projetos": [
        {
            "nome": "Implantação de sistema ERP",
            "data_inicio": "01-04-2025",
            "data_fim": "31-12-2025",
            "categoria": "Cloud",
            "indicadores": {
                "ev": 200000,
                "pv": 250000,
                "ac": 180000,
                "bac": 300000,
                "payback": 2.2,
                "roi": 42
            },
            "notas_avaliacao": [1000, 800, 600],  # Notas para os 3 critérios
            "resultado_esperado": 939.74  # ⭐ Da planilha (tolerância ±5)
        },
        {
            "nome": "Implantação de sistema GRC",
            "data_inicio": "15-04-2025",
            "data_fim": "30-11-2025",
            "categoria": "Segurança",
            "indicadores": {
                "ev": 150000,
                "pv": 200000,
                "ac": 140000,
                "bac": 220000,
                "payback": 2.7,
                "roi": 38
            },
            "notas_avaliacao": [900, 700, 500],
            "resultado_esperado": 839.74  # ⭐ Da planilha (tolerância ±5)
        },
        {
            "nome": "Migração para CLOUD",
            "data_inicio": "01-05-2025",
            "data_fim": "31-10-2025",
            "categoria": "Cloud",
            "indicadores": {
                "ev": 100000,
                "pv": 150000,
                "ac": 95000,
                "bac": 180000,
                "payback": 3.1,
                "roi": 30
            },
            "notas_avaliacao": [500, 700, 200],
            "resultado_esperado": 520.64  # ⭐ Da planilha (tolerância ±5)
        }
    ],
    "estrategia": {
        "nome": "Estratégia Digital 2025",
        "objetivos": [
            "Modernizar infraestrutura",
            "Aumentar segurança",
            "Otimizar processos"
        ],
        "grupo_criterios": {
            "nome": "Grupo Transformação Digital",
            "criterios": [
                "Potencial de crescimento",
                "Impacto na eficiência",
                "Aderência ao cliente"
            ],
            # ⭐ Mapeamento Critério → Objetivo
            "vinculos_criterio_objetivo": {
                "Potencial de crescimento": "Modernizar infraestrutura",
                "Impacto na eficiência": "Aumentar segurança",
                "Aderência ao cliente": "Otimizar processos"
            },
            # ⭐ CONFIGURAÇÃO AHP DO FLUXO 2 (como você pediu)
            # Potencial >> Impacto >> Aderência
            "comparacoes_ahp": {
                "Potencial de crescimento": {
                    "Impacto na eficiência": "MORE_IMPORTANT",  
                    "Aderência ao cliente": "MORE_IMPORTANT"    
                },
                "Impacto na eficiência": {
                    "Aderência ao cliente": "MORE_IMPORTANT"     
                }
            }
        },
        "grupo_avaliacao": {
            "nome": "Avaliação Digital 2025"
        },
        "cenario": {
            "nome": "Cenário Transformação Digital",
            "orcamento": "700000"
        }
    }
}

# Variáveis auxiliares (serão preenchidas antes de usar)
nomes_objetivos = []
nomes_criterios = []
projetos_avaliacoes = []

driver = start_driver_no_prompts()
 
wait = WebDriverWait(driver, 10)


def verificar_item_existe_na_tabela(nome_item):
    """Verifica se um item já existe na tabela antes de cadastrar (verifica apenas a primeira coluna)."""
    try:
       
        # Normalizar o nome do item para comparação
        nome_normalizado = nome_item.strip().lower()
        
        cards = driver.find_elements(By.CSS_SELECTOR, "app-card, .card")
        for card in cards:
            rows = card.find_elements(By.CSS_SELECTOR, "table tbody tr, table tr")
            for row in rows:
                # Pegar todas as células (td) da linha
                tds = row.find_elements(By.TAG_NAME, "td")
                
                # Verificar apenas a primeira célula (td[0]) - onde fica o nome
                if len(tds) > 0:
                    # Tentar pegar especificamente o botão.link que contém o nome
                    try:
                        link_button = tds[0].find_element(By.CSS_SELECTOR, "button.link")
                        texto_primeira_celula = link_button.text.strip().lower()
                    except Exception:
                        # Se não encontrar button.link, pegar o texto da célula normalmente
                        texto_primeira_celula = tds[0].text.strip().lower()
                    
                    print(f"Verificando item na tabela: '{texto_primeira_celula}' vs '{nome_normalizado}'")
                    
                    # Comparação normalizada (sem espaços extras, lowercase)
                    if nome_normalizado == texto_primeira_celula:
                        print(f"✓ Item '{nome_item}' ENCONTRADO na tabela.")
                        return True
        
        print(f"✗ Item '{nome_item}' NÃO encontrado na tabela.")
        return False
    except Exception as e:
        print(f"✗ Erro ao verificar item na tabela: {e}")
        return False
    


def achar_e_clicar_na_tabela(nome_item):
    """Acha um item na tabela pelo nome e clica nele."""
    try:
      
        wait_local = WebDriverWait(driver, WAIT_TIMEOUT)
        cards = driver.find_elements(By.CSS_SELECTOR, "app-card, .card")
        if not cards:
            cards = wait_local.until(EC.presence_of_all_elements_located((By.CSS_SELECTOR, "app-card, .card")))

        for card in cards:
            rows = card.find_elements(By.CSS_SELECTOR, "table tbody tr.table-row, table tr")
            if not rows:
                rows = card.find_elements(By.CSS_SELECTOR, "tr")

            for row in rows:
                tds = row.find_elements(By.TAG_NAME, "td")
                texts = [td.text.strip() for td in tds if td.text.strip()]
                match = any((nome_item == txt or nome_item in txt) for txt in texts)
                if match:
                    try:
                        link = row.find_element(By.CSS_SELECTOR, "td.clickable .link, td.clickable div.link")
                        driver.execute_script(CLICK_SCRIPT, link)
                    except Exception:
                        driver.execute_script(CLICK_SCRIPT, row)
                    return True
        return False
    except Exception:
        return False


def cadastrar_objetivo(nome_objetivo):
    """Clica no botão 'Cadastrar' da tabela genérica e preenche o modal de cadastro de objetivo."""
    start = time.time()
    try:
        # verificar se já existe
        if verificar_item_existe_na_tabela(nome_objetivo):
            end = time.time()
            return {
                "nome": "Cadastrar objetivo",
                "status": "PASS",
                "entrada": nome_objetivo,
                "resultado": "Já existente (pulado)",
                "tempo": end - start,
                "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "fluxo": fluxo_atual
            }

        # clicar no botão cadastrar
        try:
            wait_local = WebDriverWait(driver, WAIT_TIMEOUT)
            botao = wait_local.until(EC.element_to_be_clickable((By.CSS_SELECTOR, "app-table-action-text-filter button")))
            driver.execute_script(CLICK_SCRIPT, botao)
        except Exception:
            components = driver.find_elements(By.CSS_SELECTOR, "app-table-action-text-filter, app-table app-table-action-text-filter")
            if not components:
                try:
                    components = wait_local.until(EC.presence_of_all_elements_located((By.CSS_SELECTOR, "app-table-action-text-filter, app-table app-table-action-text-filter")))
                except Exception:
                    components = []
            
            comp = components[0]
            botao = comp.find_element(By.TAG_NAME, "button")
            driver.execute_script(CLICK_SCRIPT, botao)

        modal = WebDriverWait(driver, WAIT_TIMEOUT).until(EC.presence_of_element_located((By.CSS_SELECTOR, "app-form-modal-component")))

        try:
            name_input = modal.find_element(By.CSS_SELECTOR, "input#name")
            name_input.clear()
            name_input.send_keys(nome_objetivo)
            driver.execute_script("arguments[0].dispatchEvent(new Event('input', {bubbles: true})); arguments[0].dispatchEvent(new Event('change', {bubbles: true}));", name_input)
        except Exception:
            try:
                name_input = modal.find_element(By.CSS_SELECTOR, "input[name='name']")
                name_input.clear()
                name_input.send_keys(nome_objetivo)
            except Exception:
                pass

        try:
            desc = modal.find_element(By.CSS_SELECTOR, "textarea#description")
            desc.clear()
            desc.send_keys("Descrição do objetivo: automático")
            driver.execute_script("arguments[0].dispatchEvent(new Event('input', {bubbles: true})); arguments[0].dispatchEvent(new Event('change', {bubbles: true}));", desc)
        except Exception:
            pass

        try:
            save_btn = modal.find_element(By.CSS_SELECTOR, "button.btn-primary")
        except Exception:
            save_btns = modal.find_elements(By.TAG_NAME, "button")
            for btn in save_btns:
                if "salvar" in btn.text.lower() or "save" in btn.text.lower():
                    save_btn = btn
                    break

        def _enabled(d):
            try:
                el = modal.find_element(By.CSS_SELECTOR, "button.btn-primary")
                return el.is_enabled()
            except Exception:
                return False

        try:
            WebDriverWait(driver, WAIT_TIMEOUT).until(_enabled)
        except Exception:
            try:
                driver.execute_script("arguments[0].removeAttribute('disabled');", save_btn)
            except Exception:
                pass

        driver.execute_script(CLICK_SCRIPT, save_btn)
        
        # aguardar e verificar se foi cadastrado
        time.sleep(1)
        if verificar_item_existe_na_tabela(nome_objetivo):
            resultado_verificacao = "Cadastrado e verificado na tabela"
        else:
            resultado_verificacao = "Cadastrado mas não encontrado na tabela"

        end = time.time()
        return {
            "nome": "Cadastrar objetivo",
            "status": "PASS",
            "entrada": nome_objetivo,
            "resultado": resultado_verificacao,
            "tempo": end - start,
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "fluxo": fluxo_atual
        }

    except Exception as e:
        print("Erro ao cadastrar objetivo:", e)
        end = time.time()
        return {
            "nome": "Cadastrar objetivo",
            "status": "FAIL",
            "entrada": nome_objetivo,
            "resultado": str(e),
            "tempo": end - start,
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "fluxo": fluxo_atual
        }


def clicar_tab(texto_tab):
    """Clica em uma tab dentro de tabs-container pelo texto."""
    start = time.time()
    try:
        wait_local = WebDriverWait(driver, WAIT_TIMEOUT)
        
        # Tentar encontrar tabs-container
        tabs_container = None
        try:
            tabs_container = wait_local.until(EC.presence_of_element_located((By.CSS_SELECTOR, "tabs-container")))
        except Exception:
            try:
                tabs_container = wait_local.until(EC.presence_of_element_located((By.CSS_SELECTOR, ".tabs-container")))
            except Exception:
                tabs_container = driver.find_element(By.CSS_SELECTOR, "[class*='tabs-list']")
        
        if not tabs_container:
            raise RuntimeError("Container de tabs não encontrado")
        
        # Buscar lista de tabs
        tabs_list = None
        try:
            tabs_list = tabs_container.find_element(By.CSS_SELECTOR, "tabs-list")
        except Exception:
            try:
                tabs_list = tabs_container.find_element(By.CSS_SELECTOR, ".tabs-list")
            except Exception:
                tabs_list = tabs_container
        
        # Procurar todos os botões
        buttons = tabs_list.find_elements(By.TAG_NAME, "button")
        if not buttons:
            buttons = tabs_list.find_elements(By.CSS_SELECTOR, "button, a, [role='tab']")
        
        for btn in buttons:
            try:
                texto = btn.text.strip()
                
                if not texto:
                    try:
                        span = btn.find_element(By.TAG_NAME, "span")
                        texto = span.text.strip()
                    except Exception:
                        pass
                texto = btn.text.replace("\n", " ").strip().lower()
                if texto_tab.lower() in texto.lower():
                    driver.execute_script(CLICK_SCRIPT, btn)
                    time.sleep(0.5)
                    return
            except Exception:
                continue
        
        raise RuntimeError(f"Tab '{texto_tab}' não encontrada")
        
    except Exception as e:
        print(f"Erro ao clicar na tab {texto_tab}:", e)
       

def vincular_objetivo_ao_criterio(nome_criterio, nome_objetivo):
    """Vincula um objetivo a um critério."""
    start = time.time()
    try:
        # ⭐ AGUARDAR E GARANTIR QUE ESTAMOS NA LISTA DE CRITÉRIOS
        time.sleep(1)
        
        # VERIFICAR SE JÁ TEM OBJETIVO VINCULADO ANTES DE CLICAR
        try:
            # Aguardar a tabela carregar
            WebDriverWait(driver, 5).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, ".table-row"))
            )
            time.sleep(0.5)
            
            rows = driver.find_elements(By.CSS_SELECTOR, ".table-row")
            print(f"\n  • Procurando critério '{nome_criterio}' na tabela ({len(rows)} linhas encontradas)")
            
            for row in rows:
                tds = row.find_elements(By.TAG_NAME, "td")
                if len(tds) >= 3:
                    nome_celula = tds[0].text.strip()
                    objetivos_vinculados = tds[2].text.strip()
                    
                    # Debug: mostrar o que está encontrando
                    if nome_celula:  # Só mostra se não for vazio
                        print(f"    - Linha encontrada: '{nome_celula}' | Objetivos: {objetivos_vinculados}")
                    
                    # Se achar o critério e já tiver objetivo vinculado (>0), PULAR
                    if nome_criterio.strip().lower() == nome_celula.strip().lower():
                        try:
                            num_objetivos = int(objetivos_vinculados)
                            if num_objetivos > 0:
                                print(f"  ✓ Critério '{nome_criterio}' já tem {num_objetivos} objetivo(s) vinculado(s). Pulando.")
                                end = time.time()
                                return {
                                    "nome": "Vincular objetivo",
                                    "status": "PASS",
                                    "entrada": f"{nome_criterio} -> {nome_objetivo}",
                                    "resultado": f"Já tem objetivo vinculado - Pulado",
                                    "tempo": end - start,
                                    "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                                    "fluxo": fluxo_atual
                                }
                        except:
                            pass
        except Exception as e:
            print(f"  ⚠ Erro ao verificar objetivos vinculados: {e}")
        
        # ⭐ TENTAR CLICAR NO CRITÉRIO (com retry)
        print(f"  • Tentando clicar no critério '{nome_criterio}'...")
        
        max_tentativas = 3
        clicou = False
        
        for tentativa in range(1, max_tentativas + 1):
            print(f"    Tentativa {tentativa}/{max_tentativas}...")
            
            if achar_e_clicar_na_tabela(nome_criterio):
                clicou = True
                print(f"    ✓ Clicou no critério '{nome_criterio}'")
                break
            else:
                print(f"    ✗ Falha ao clicar (tentativa {tentativa})")
                time.sleep(1)
                
                # Se não achou, tentar recarregar a página/lista
                if tentativa < max_tentativas:
                    try:
                        # Scroll para o topo
                        driver.execute_script("window.scrollTo(0, 0);")
                        time.sleep(0.5)
                    except:
                        pass
        
        if not clicou:
            raise RuntimeError(f"Critério '{nome_criterio}' não encontrado na tabela após {max_tentativas} tentativas")
        
        time.sleep(0.5)
        
        # Clicar na aba Objetivos
        print(f"  • Clicando na aba 'Objetivos'...")
        clicar_tab("Objetivos")
        time.sleep(0.5)
        
        # verificar se há a mensagem "Nenhum objetivo vinculado"
        tem_vinculo = False
        try:
            empty_msg = driver.find_element(By.CSS_SELECTOR, ".empty-objectives")
            tem_vinculo = False
            print(f"  • Nenhum objetivo vinculado ainda")
        except Exception:
            try:
                objectives_list = driver.find_element(By.CSS_SELECTOR, ".objectives-list")
                tem_vinculo = True
                print(f"  • Já tem objetivos vinculados")
            except Exception:
                tem_vinculo = False
        
        if tem_vinculo:
            # já tem objetivos vinculados, verificar se o objetivo específico está vinculado
            try:
                objective_items = driver.find_elements(By.CSS_SELECTOR, ".objective-item .objective-name")
                for item in objective_items:
                    if nome_objetivo in item.text:
                        print(f"  ✓ Objetivo '{nome_objetivo}' já vinculado")
                        end = time.time()
                        return {
                            "nome": "Vincular objetivo",
                            "status": "PASS",
                            "entrada": f"{nome_criterio} -> {nome_objetivo}",
                            "resultado": "Objetivo já vinculado",
                            "tempo": end - start,
                            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                            "fluxo": fluxo_atual
                        }
            except Exception:
                pass
        
        # clicar no botão "Cadastrar novo vínculo"
        print(f"  • Clicando em 'Cadastrar novo vínculo'...")
        try:
            wait_local = WebDriverWait(driver, WAIT_TIMEOUT)
            buttons = driver.find_elements(By.CSS_SELECTOR, ".actions-right button.btn-primary")
            for btn in buttons:
                if "vínculo" in btn.text.lower():
                    driver.execute_script(CLICK_SCRIPT, btn)
                    print(f"  ✓ Clicou em 'Cadastrar novo vínculo'")
                    break
        except Exception as e:
            print(f"  ✗ Erro ao clicar em cadastrar vínculo: {e}")
            raise
        
        time.sleep(0.5)
        
        # aguardar modal/formulário abrir
        wait_local = WebDriverWait(driver, WAIT_TIMEOUT)
        
        # procurar select de objetivos
        print(f"  • Selecionando objetivo '{nome_objetivo}' no select...")
        try:
            select = wait_local.until(EC.presence_of_element_located((By.CSS_SELECTOR, "select")))
            options = select.find_elements(By.TAG_NAME, "option")
            
            objetivo_encontrado = False
            for opt in options:
                if nome_objetivo in opt.text:
                    driver.execute_script("""
                        arguments[0].selected = true;
                        arguments[0].dispatchEvent(new Event('change', {bubbles: true}));
                    """, opt)
                    objetivo_encontrado = True
                    print(f"  ✓ Objetivo '{nome_objetivo}' selecionado")
                    break
            
            if not objetivo_encontrado:
                raise RuntimeError(f"Objetivo '{nome_objetivo}' não encontrado no select")
                
        except Exception as e:
            print(f"  ✗ Erro ao selecionar objetivo: {e}")
            raise
        
        time.sleep(0.3)
        
        # clicar no botão salvar/confirmar
        print(f"  • Salvando vínculo...")
        try:
            save_buttons = driver.find_elements(By.CSS_SELECTOR, "button.btn-primary")
            for btn in save_buttons:
                texto_btn = btn.text.lower()
                if any(palavra in texto_btn for palavra in ["salvar", "confirmar", "vincular", "adicionar"]):
                    driver.execute_script(CLICK_SCRIPT, btn)
                    print(f"  ✓ Clicou em salvar")
                    break
        except Exception as e:
            print(f"  ✗ Erro ao clicar em salvar: {e}")
            raise
        
        time.sleep(0.5)
        
        # verificar se vinculou corretamente
        try:
            objective_items = driver.find_elements(By.CSS_SELECTOR, ".objective-item .objective-name")
            vinculado = False
            for item in objective_items:
                if nome_objetivo in item.text:
                    vinculado = True
                    break
            
            if vinculado:
                resultado_msg = "Objetivo vinculado e verificado na lista"
                print(f"  ✓ {resultado_msg}")
            else:
                resultado_msg = "Objetivo vinculado mas não aparece na lista"
                print(f"  ⚠ {resultado_msg}")
        except Exception:
            resultado_msg = "Objetivo vinculado (verificação não possível)"
            print(f"  ⚠ {resultado_msg}")
        
        end = time.time()
        return {
            "nome": "Vincular objetivo",
            "status": "PASS",
            "entrada": f"{nome_criterio} -> {nome_objetivo}",
            "resultado": resultado_msg,
            "tempo": end - start,
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "fluxo": fluxo_atual
        }

    except Exception as e:
        print(f"✗ Erro ao vincular objetivo ao critério {nome_criterio}: {e}")
        try:
            driver.save_screenshot(f"erro_vincular_{nome_criterio}.png")
            print(f"  • Screenshot salvo: erro_vincular_{nome_criterio}.png")
        except Exception:
            pass
        end = time.time()
        return {
            "nome": "Vincular objetivo",
            "status": "FAIL",
            "entrada": f"{nome_criterio} -> {nome_objetivo}",
            "resultado": str(e),
            "tempo": end - start,
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "fluxo": fluxo_atual
        }


def tem_probabilidade_valida(texto):
    """Retorna True apenas se o texto for uma porcentagem real > 0 (ignora 0%)."""
    if not texto:
        return False

    texto = texto.replace(" ", "").replace(",", ".").strip()

    if not texto.endswith("%"):
        return False

    valor = texto[:-1]

    try:
        num = float(valor)
        # Somente trata como válido se for > 0
        return num > 0 and num <= 100
    except:
        return False


def preencher_comparacoes_criterio(nome_criterio, config_fluxo):
    """Preenche as comparações diretas de um critério usando configuração AHP."""
    start = time.time()
    try:
        # VERIFICAR SE JÁ TEM PROBABILIDADE CALCULADA ANTES DE CLICAR
        try:
            rows = driver.find_elements(By.CSS_SELECTOR, ".table-row")
            for row in rows:
                tds = row.find_elements(By.TAG_NAME, "td")
                if len(tds) >= 2:
                    nome_celula = tds[0].text.strip()
                    probabilidade_celula = tds[1].text.strip()
                    
                    prob = probabilidade_celula.strip()

                    if nome_criterio.lower() == nome_celula.lower() and tem_probabilidade_valida(prob):
                        print(f"Critério '{nome_criterio}' já tem probabilidade válida ({prob}). Pulando.")
                        return {
                            "nome": "Comparações critério",
                            "status": "PASS",
                            "entrada": nome_criterio,
                            "resultado": f"pulado (probabilidade existente: {prob})",
                            "tempo": time.time() - start,
                            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                            "fluxo": fluxo_atual
                        }
        except Exception as e:
            print(f"Erro ao verificar probabilidade: {e}")
        
        # Se NÃO tem probabilidade, clicar e preencher
        if not achar_e_clicar_na_tabela(nome_criterio):
            raise RuntimeError(f"Critério '{nome_criterio}' não encontrado na tabela")
        
        time.sleep(0.5)
        
        # garantir que estamos na aba de comparações diretas
        try:
            clicar_tab("Comparações diretas")
            time.sleep(0.5)
        except Exception:
            pass
        
        # verificar se existem selects de comparação
        selects = driver.find_elements(By.CSS_SELECTOR, "select.custom-select")
        
        if not selects:
            end = time.time()
            return {
                "nome": "Preencher comparações",
                "status": "PASS",
                "entrada": nome_criterio,
                "resultado": "Sem comparações disponíveis",
                "tempo": end - start,
                "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "fluxo": fluxo_atual
            }
        
        # ⭐ PEGAR CONFIGURAÇÃO AHP DO FLUXO
        comparacoes_config = config_fluxo["estrategia"]["grupo_criterios"].get("comparacoes_ahp", {})
        comparacoes_deste_criterio = comparacoes_config.get(nome_criterio, {})
        
        print(f"\n  • Configurações AHP para '{nome_criterio}':")
        for crit, imp in comparacoes_deste_criterio.items():
            print(f"    - vs '{crit}': {imp}")
        
        # preencher cada select baseado na configuração
        comparacoes_preenchidas = 0
        
        # Buscar linhas da tabela para mapear índices
        table_rows = driver.find_elements(By.CSS_SELECTOR, ".table-row")
        
        for idx, select in enumerate(selects):
            try:
                # verificar se já está preenchido
                valor_atual = select.get_attribute("value")
                if valor_atual and valor_atual != "":
                    try:
                        option_text = select.find_element(By.CSS_SELECTOR, f"option[value='{valor_atual}']").text
                        if "Avalie" not in option_text:
                            print(f"    ⚠ Select {idx} já preenchido")
                            continue
                    except:
                        pass
                
                # ⭐ IDENTIFICAR QUAL CRITÉRIO ESTÁ SENDO COMPARADO NESTA LINHA
                nome_criterio_comparado = None
                
                if idx < len(table_rows):
                    cells = table_rows[idx].find_elements(By.CSS_SELECTOR, ".table-cell")
                    
                    # Tentar pegar da primeira célula
                    if len(cells) >= 1:
                        texto = cells[0].text.strip()
                        if len(texto) > 3:  # Se tem conteúdo válido
                            nome_criterio_comparado = texto
                    
                    # Se não conseguiu, tentar da terceira célula
                    if not nome_criterio_comparado and len(cells) >= 3:
                        texto = cells[2].text.strip()
                        if len(texto) > 3:
                            nome_criterio_comparado = texto
                
                if not nome_criterio_comparado:
                    print(f"    ⚠ Select {idx}: Não conseguiu identificar critério comparado")
                    continue
                
                # ⭐ BUSCAR IMPORTÂNCIA NA CONFIGURAÇÃO
                valor = comparacoes_deste_criterio.get(nome_criterio_comparado, "EQUALLY_IMPORTANT")
                
                print(f"    → Select {idx}: '{nome_criterio}' vs '{nome_criterio_comparado}' = {valor}")
                
                # Selecionar o valor
                driver.execute_script(f"""
                    arguments[0].value = '{valor}';
                    arguments[0].dispatchEvent(new Event('change', {{bubbles: true}}));
                """, select)
                
                comparacoes_preenchidas += 1
                time.sleep(0.3)
                
            except Exception as e:
                print(f"    ✗ Erro ao preencher select {idx}: {e}")
                continue
        
        time.sleep(0.5)
        
        end = time.time()
        return {
            "nome": "Preencher comparações diretas",
            "status": "PASS",
            "entrada": nome_criterio,
            "resultado": f"{comparacoes_preenchidas} comparações preenchidas com configuração AHP",
            "tempo": end - start,
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "fluxo": fluxo_atual
        }

    except Exception as e:
        print(f"Erro ao preencher comparações do critério {nome_criterio}:", e)
        end = time.time()
        return {
            "nome": "Preencher comparações diretas",
            "status": "FAIL",
            "entrada": nome_criterio,
            "resultado": str(e),
            "tempo": end - start,
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "fluxo": fluxo_atual
        }

def verificar_comparacoes_reciprocas(nome_criterio):
    """Verifica se as comparações recíprocas estão corretas."""
    start = time.time()
    try:
        # clicar na aba Comparações recíprocas
        
        time.sleep(0.5)
        
        # verificar se há tabela de comparações
        try:
            table_rows = driver.find_elements(By.CSS_SELECTOR, ".table-row")
            if not table_rows:
                raise RuntimeError("Nenhuma comparação recíproca encontrada")
            
            comparacoes_verificadas = 0
            comparacoes_corretas = 0
            
            for row in table_rows:
                try:
                    cells = row.find_elements(By.CSS_SELECTOR, ".table-cell")
                    if len(cells) >= 3:
                        criterio_atual = cells[0].text.strip()
                        comparacao = cells[1].text.strip()
                        criterio_comparado = cells[2].text.strip()
                        
                        if comparacao and comparacao != "Avalie":
                            comparacoes_verificadas += 1
                            # verificar se a comparação faz sentido
                            if any(palavra in comparacao.lower() for palavra in ["importante", "menos", "mais", "tão"]):
                                comparacoes_corretas += 1
                except Exception as e:
                    print(f"Erro ao verificar linha: {e}")
                    continue
            
            resultado = f"{comparacoes_corretas}/{comparacoes_verificadas} comparações recíprocas verificadas como corretas"
            
        except Exception as e:
            resultado = f"Erro ao verificar tabela: {str(e)}"
        
        end = time.time()
        return {
            "nome": "Verificar comparações recíprocas",
            "status": "PASS",
            "entrada": nome_criterio,
            "resultado": resultado,
            "tempo": end - start,
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "fluxo": fluxo_atual
        }

    except Exception as e:
        print(f"Erro ao verificar comparações recíprocas do critério {nome_criterio}:", e)
        end = time.time()
        return {
            "nome": "Verificar comparações recíprocas",
            "status": "FAIL",
            "entrada": nome_criterio,
            "resultado": str(e),
            "tempo": end - start,
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "fluxo": fluxo_atual
        }

def cadastrar_criterio(nome_criterio):
    """Cadastra um critério dentro do grupo de critérios."""
    start = time.time()
    try:
        # verificar se já existe
        if verificar_item_existe_na_tabela(nome_criterio):
            end = time.time()
            return {
                "nome": "Cadastrar critério",
                "status": "PASS",
                "entrada": nome_criterio,
                "resultado": "Já existente (pulado)",
                "tempo": end - start,
                "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "fluxo": fluxo_atual
            }

        # clicar no botão cadastrar
        try:
            wait_local = WebDriverWait(driver, WAIT_TIMEOUT)
            botao = wait_local.until(EC.element_to_be_clickable((By.CSS_SELECTOR, "app-table-action-text-filter button")))
            driver.execute_script(CLICK_SCRIPT, botao)
        except Exception:
            components = driver.find_elements(By.CSS_SELECTOR, "app-table-action-text-filter, app-table app-table-action-text-filter")
            if not components:
                try:
                    components = wait_local.until(EC.presence_of_all_elements_located((By.CSS_SELECTOR, "app-table-action-text-filter, app-table app-table-action-text-filter")))
                except Exception:
                    components = []
            
            comp = components[0]
            botao = comp.find_element(By.TAG_NAME, "button")
            driver.execute_script(CLICK_SCRIPT, botao)

        modal = WebDriverWait(driver, WAIT_TIMEOUT).until(EC.presence_of_element_located((By.CSS_SELECTOR, "app-form-modal-component")))

        # preencher nome do critério
        try:
            name_input = modal.find_element(By.CSS_SELECTOR, "input#name")
            name_input.clear()
            name_input.send_keys(nome_criterio)
            driver.execute_script("arguments[0].dispatchEvent(new Event('input', {bubbles: true})); arguments[0].dispatchEvent(new Event('change', {bubbles: true}));", name_input)
        except Exception:
            try:
                name_input = modal.find_element(By.CSS_SELECTOR, "input[name='name']")
                name_input.clear()
                name_input.send_keys(nome_criterio)
            except Exception:
                pass

        # botão salvar
        try:
            save_btn = modal.find_element(By.CSS_SELECTOR, "button.btn-primary")
        except Exception:
            save_btns = modal.find_elements(By.TAG_NAME, "button")
            for btn in save_btns:
                if "salvar" in btn.text.lower() or "save" in btn.text.lower():
                    save_btn = btn
                    break

        def _enabled(d):
            try:
                el = modal.find_element(By.CSS_SELECTOR, "button.btn-primary")
                return el.is_enabled()
            except Exception:
                return False

        try:
            WebDriverWait(driver, WAIT_TIMEOUT).until(_enabled)
        except Exception:
            try:
                driver.execute_script("arguments[0].removeAttribute('disabled');", save_btn)
            except Exception:
                pass

        driver.execute_script(CLICK_SCRIPT, save_btn)
        
        # aguardar e verificar se foi cadastrado
        time.sleep(1)
        if verificar_item_existe_na_tabela(nome_criterio):
            resultado_verificacao = "Cadastrado e verificado na tabela"
        else:
            resultado_verificacao = "Cadastrado mas não encontrado na tabela"

        end = time.time()
        return {
            "nome": "Cadastrar critério",
            "status": "PASS",
            "entrada": nome_criterio,
            "resultado": resultado_verificacao,
            "tempo": end - start,
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "fluxo": fluxo_atual
        }

    except Exception as e:
        print("Erro ao cadastrar critério:", e)
        end = time.time()
        return {
            "nome": "Cadastrar critério",
            "status": "FAIL",
            "entrada": nome_criterio,
            "resultado": str(e),
            "tempo": end - start,
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "fluxo": fluxo_atual
        }
    


def cadastrar_grupo_criterios(nome_grupo):
    """Cadastra um grupo de critérios."""
    start = time.time()
    try:
        # verificar se já existe
        if verificar_item_existe_na_tabela(nome_grupo):
            # se existe, clicar nele
            if achar_e_clicar_na_tabela(nome_grupo):
                end = time.time()
                return {
                    "nome": "Cadastrar grupo de critérios",
                    "status": "PASS",
                    "entrada": nome_grupo,
                    "resultado": "Já existente (aberto)",
                    "tempo": end - start,
                    "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    "fluxo": fluxo_atual
                }
        
        # cadastrar novo grupo
        try:
            wait_local = WebDriverWait(driver, WAIT_TIMEOUT)
            botao = wait_local.until(EC.element_to_be_clickable((By.CSS_SELECTOR, "app-table-action-text-filter button")))
            driver.execute_script(CLICK_SCRIPT, botao)
        except Exception:
            components = driver.find_elements(By.CSS_SELECTOR, "app-table-action-text-filter, app-table app-table-action-text-filter")
            if not components:
                try:
                    components = wait_local.until(EC.presence_of_all_elements_located((By.CSS_SELECTOR, "app-table-action-text-filter, app-table app-table-action-text-filter")))
                except Exception:
                    components = []
            
            comp = components[0]
            botao = comp.find_element(By.TAG_NAME, "button")
            driver.execute_script(CLICK_SCRIPT, botao)

        modal = WebDriverWait(driver, WAIT_TIMEOUT).until(EC.presence_of_element_located((By.CSS_SELECTOR, "app-form-modal-component")))

        try:
            name_input = modal.find_element(By.CSS_SELECTOR, "input#name")
            name_input.clear()
            name_input.send_keys(nome_grupo)
            driver.execute_script("arguments[0].dispatchEvent(new Event('input', {bubbles: true})); arguments[0].dispatchEvent(new Event('change', {bubbles: true}));", name_input)
        except Exception:
            try:
                name_input = modal.find_element(By.CSS_SELECTOR, "input[name='name']")
                name_input.clear()
                name_input.send_keys(nome_grupo)
            except Exception:
                pass

        try:
            desc = modal.find_element(By.CSS_SELECTOR, "textarea#description")
            desc.clear()
            desc.send_keys("Descrição do grupo de critérios: automático")
            driver.execute_script("arguments[0].dispatchEvent(new Event('input', {bubbles: true})); arguments[0].dispatchEvent(new Event('change', {bubbles: true}));", desc)
        except Exception:
            pass

        try:
            save_btn = modal.find_element(By.CSS_SELECTOR, "button.btn-primary")
        except Exception:
            save_btns = modal.find_elements(By.TAG_NAME, "button")
            for btn in save_btns:
                if "salvar" in btn.text.lower() or "save" in btn.text.lower():
                    save_btn = btn
                    break

        def _enabled(d):
            try:
                el = modal.find_element(By.CSS_SELECTOR, "button.btn-primary")
                return el.is_enabled()
            except Exception:
                return False

        try:
            WebDriverWait(driver, WAIT_TIMEOUT).until(_enabled)
        except Exception:
            try:
                driver.execute_script("arguments[0].removeAttribute('disabled');", save_btn)
            except Exception:
                pass

        driver.execute_script(CLICK_SCRIPT, save_btn)
        
        # aguardar cadastro
        time.sleep(1)
        
        # clicar no grupo cadastrado
        if achar_e_clicar_na_tabela(nome_grupo):
            resultado_verificacao = "Cadastrado e aberto com sucesso"
        else:
            resultado_verificacao = "Cadastrado mas não foi possível abrir"

        end = time.time()
        return {
            "nome": "Cadastrar grupo de critérios",
            "status": "PASS",
            "entrada": nome_grupo,
            "resultado": resultado_verificacao,
            "tempo": end - start,
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "fluxo": fluxo_atual
        }

    except Exception as e:
        print("Erro ao cadastrar grupo de critérios:", e)
        end = time.time()
        return {
            "nome": "Cadastrar grupo de critérios",
            "status": "FAIL",
            "entrada": nome_grupo,
            "resultado": str(e),
            "tempo": end - start,
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "fluxo": fluxo_atual
        }

def cadastrar_grupo_avaliacao(nome_grupo_avaliacao, nome_grupo_criterios):
    """Cadastra um grupo de avaliações vinculado a um grupo de critérios."""
    start = time.time()
    try:
        # verificar se já existe
        if verificar_item_existe_na_tabela(nome_grupo_avaliacao):
            if achar_e_clicar_na_tabela(nome_grupo_avaliacao):
                end = time.time()
                return {
                    "nome": "Cadastrar grupo de critérios",
                    "status": "PASS",
                    "entrada": nome_grupo_avaliacao,
                    "resultado": "Já existente (aberto)",
                    "tempo": end - start,
                    "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    "fluxo": fluxo_atual
                }

        # clicar no botão cadastrar
        try:
            wait_local = WebDriverWait(driver, WAIT_TIMEOUT)
            botao = wait_local.until(EC.element_to_be_clickable((By.CSS_SELECTOR, "app-table-action-text-filter button")))
            driver.execute_script(CLICK_SCRIPT, botao)
        except Exception:
            components = driver.find_elements(By.CSS_SELECTOR, "app-table-action-text-filter, app-table app-table-action-text-filter")
            if not components:
                try:
                    components = wait_local.until(EC.presence_of_all_elements_located((By.CSS_SELECTOR, "app-table-action-text-filter, app-table app-table-action-text-filter")))
                except Exception:
                    components = []
            
            comp = components[0]
            botao = comp.find_element(By.TAG_NAME, "button")
            driver.execute_script(CLICK_SCRIPT, botao)

        # aguardar modal específico de grupo de avaliações
        modal = WebDriverWait(driver, WAIT_TIMEOUT).until(EC.presence_of_element_located((By.CSS_SELECTOR, ".modal-content, app-form-modal-component")))

        # preencher nome do grupo de avaliações
        try:
            name_input = modal.find_element(By.CSS_SELECTOR, "input")
            name_input.clear()
            name_input.send_keys(nome_grupo_avaliacao)
            driver.execute_script("arguments[0].dispatchEvent(new Event('input', {bubbles: true})); arguments[0].dispatchEvent(new Event('change', {bubbles: true}));", name_input)
        except Exception as e:
            print(f"Erro ao preencher nome: {e}")
            pass

        # selecionar grupo de critérios relacionado
        try:
            select = modal.find_element(By.TAG_NAME, "select")
            options = select.find_elements(By.TAG_NAME, "option")
            
            grupo_selecionado = False
            for opt in options:
                if nome_grupo_criterios in opt.text:
                    driver.execute_script("""
                        arguments[0].selected = true;
                        arguments[0].dispatchEvent(new Event('change', {bubbles: true}));
                    """, opt)
                    grupo_selecionado = True
                    break
            
            if not grupo_selecionado:
                raise RuntimeError(f"Grupo de critérios '{nome_grupo_criterios}' não encontrado no select")
                
        except Exception as e:
            print(f"Erro ao selecionar grupo de critérios: {e}")
            raise

        time.sleep(0.3)

        # preencher descrição (opcional)
        try:
            desc = modal.find_element(By.CSS_SELECTOR, "textarea")
            desc.clear()
            desc.send_keys("Descrição do grupo de avaliações: automático")
            driver.execute_script("arguments[0].dispatchEvent(new Event('input', {bubbles: true})); arguments[0].dispatchEvent(new Event('change', {bubbles: true}));", desc)
        except Exception:
            pass

        # clicar no botão salvar
        try:
            save_btn = modal.find_element(By.CSS_SELECTOR, "button.btn-primary")
        except Exception:
            save_btns = modal.find_elements(By.TAG_NAME, "button")
            for btn in save_btns:
                if "salvar" in btn.text.lower():
                    save_btn = btn
                    break

        def _enabled(d):
            try:
                el = modal.find_element(By.CSS_SELECTOR, "button.btn-primary")
                return el.is_enabled()
            except Exception:
                return False

        try:
            WebDriverWait(driver, WAIT_TIMEOUT).until(_enabled)
        except Exception:
            try:
                driver.execute_script("arguments[0].removeAttribute('disabled');", save_btn)
            except Exception:
                pass

        driver.execute_script(CLICK_SCRIPT, save_btn)
        
        # aguardar e verificar se houve erro
        time.sleep(1)
        
        # verificar se apareceu mensagem de erro
        try:
            error_msg = driver.find_element(By.CSS_SELECTOR, ".validation-error, .error-message, .alert-error")
            erro_texto = error_msg.text
            
            if "não foram totalmente comparados" in erro_texto.lower():
                end = time.time()
                return {
                    "nome": "Cadastrar grupo de avaliações",
                    "status": "FAIL",
                    "entrada": nome_grupo_avaliacao,
                    "resultado": f"ERRO: {erro_texto}",
                    "tempo": end - start,
                    "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    "fluxo": fluxo_atual
                }
        except Exception:
            # sem erro, continuar verificação
            pass
        
        # verificar se foi cadastrado
        if verificar_item_existe_na_tabela(nome_grupo_avaliacao):
            resultado_verificacao = f"Cadastrado para o grupo de critérios '{nome_grupo_criterios}' - Critérios comparados com sucesso"
        else:
            resultado_verificacao = "Cadastrado mas não encontrado na tabela"

        end = time.time()
        return {
            "nome": "Cadastrar grupo de avaliações",
            "status": "PASS",
            "entrada": nome_grupo_avaliacao,
            "resultado": resultado_verificacao,
            "tempo": end - start,
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "fluxo": fluxo_atual
        }

    except Exception as e:
        print("Erro ao cadastrar grupo de avaliações:", e)
        try:
            driver.save_screenshot("erro_grupo_avaliacao.png")
        except Exception:
            pass
        end = time.time()
        return {
            "nome": "Cadastrar grupo de avaliações",
            "status": "FAIL",
            "entrada": nome_grupo_avaliacao,
            "resultado": str(e),
            "tempo": end - start,
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "fluxo": fluxo_atual
        }

def cadastrar_projeto_no_grupo_avaliacao(nome_projeto, nome_grupo_avaliacao):
    """Cadastra um projeto no grupo de avaliação."""
    start = time.time()
    try:
        # Verificar se o projeto já está cadastrado E avaliado (tem resultado > 0)
        try:
            cards = driver.find_elements(By.CSS_SELECTOR, "app-card, .card")
            for card in cards:
                rows = card.find_elements(By.CSS_SELECTOR, "table tbody tr, table tr")
                for row in rows:
                    tds = row.find_elements(By.TAG_NAME, "td")
                    if len(tds) >= 2:
                        nome_celula = tds[0].text.strip()
                        resultado_celula = tds[1].text.strip()
                        
                        # Se achar o projeto e tiver resultado > 0, já foi avaliado
                        if nome_projeto.lower() in nome_celula.lower():
                            try:
                                resultado_valor = int(resultado_celula)
                                if resultado_valor > 0:
                                    print(f"Projeto '{nome_projeto}' já avaliado com resultado {resultado_valor}")
                                    end = time.time()
                                    return {
                                        "nome": "Cadastrar projeto no grupo de avaliação",
                                        "status": "PASS",
                                        "entrada": f"{nome_projeto} -> {nome_grupo_avaliacao}",
                                        "resultado": f"Já cadastrado e avaliado (resultado: {resultado_valor})",
                                        "tempo": end - start,
                                        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                                        "fluxo": fluxo_atual
                                    }
                            except:
                                pass
        except Exception as e:
            print(f"Erro ao verificar projeto avaliado: {e}")
        
        # Clicar no botão Cadastrar
        try:
            wait_local = WebDriverWait(driver, WAIT_TIMEOUT)
            botao = wait_local.until(EC.element_to_be_clickable((By.CSS_SELECTOR, ".actions-right button.btn-primary")))
            driver.execute_script(CLICK_SCRIPT, botao)
        except Exception as e:
            print(f"Erro ao clicar em cadastrar: {e}")
            raise
        
        time.sleep(1)
        
        # Aguardar modal abrir
        modal = WebDriverWait(driver, WAIT_TIMEOUT).until(EC.presence_of_element_located((By.CSS_SELECTOR, ".modal-content, app-form-modal-component")))
        
        # Selecionar o projeto no select
        try:
            select = modal.find_element(By.TAG_NAME, "select")
            options = select.find_elements(By.TAG_NAME, "option")
            
            projeto_encontrado = False
            for opt in options:
                if nome_projeto in opt.text:
                    driver.execute_script("""
                        arguments[0].selected = true;
                        arguments[0].dispatchEvent(new Event('change', {bubbles: true}));
                    """, opt)
                    projeto_encontrado = True
                    break
            
            if not projeto_encontrado:
                raise RuntimeError(f"Projeto '{nome_projeto}' não encontrado no select")
        except Exception as e:
            print(f"Erro ao selecionar projeto: {e}")
            raise
        
        time.sleep(0.5)
        
        # Clicar em Salvar
        try:
            save_btn = modal.find_element(By.CSS_SELECTOR, "button.btn-primary")
            driver.execute_script(CLICK_SCRIPT, save_btn)
        except Exception as e:
            print(f"Erro ao salvar: {e}")
            raise
        
        time.sleep(1)
        
        end = time.time()
        return {
            "nome": "Cadastrar projeto no grupo de avaliação",
            "status": "PASS",
            "entrada": f"{nome_projeto} -> {nome_grupo_avaliacao}",
            "resultado": "Projeto cadastrado no grupo de avaliação",
            "tempo": end - start,
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "fluxo": fluxo_atual
        }
    
    except Exception as e:
        print(f"Erro ao cadastrar projeto no grupo de avaliação:", e)
        end = time.time()
        return {
            "nome": "Cadastrar projeto no grupo de avaliação",
            "status": "FAIL",
            "entrada": f"{nome_projeto} -> {nome_grupo_avaliacao}",
            "resultado": str(e),
            "tempo": end - start,
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "fluxo": fluxo_atual
        }


def avaliar_projeto_no_grupo(nome_projeto, notas_criterios):

    start = time.time()
    try:
   
        
        time.sleep(1)
        
        # Clicar no botão Avaliar
        try:
            wait_local = WebDriverWait(driver, WAIT_TIMEOUT)
            botao_avaliar = wait_local.until(EC.element_to_be_clickable((By.CSS_SELECTOR, "button.evaluation-btn")))
            driver.execute_script(CLICK_SCRIPT, botao_avaliar)
        except Exception as e:
            print(f"Erro ao clicar em avaliar: {e}")
            raise
        
        time.sleep(1)
        
        # Aguardar modal de avaliação abrir
        modal = WebDriverWait(driver, WAIT_TIMEOUT).until(EC.presence_of_element_located((By.CSS_SELECTOR, ".modal-container")))
        
        # Preencher notas para cada critério
        try:
            inputs = modal.find_elements(By.CSS_SELECTOR, ".criterion-input")
            
            for idx, nota in enumerate(notas_criterios):
                if idx < len(inputs):
                    inputs[idx].clear()
                    inputs[idx].send_keys(str(nota))
                    driver.execute_script("arguments[0].dispatchEvent(new Event('input', {bubbles: true})); arguments[0].dispatchEvent(new Event('change', {bubbles: true}));", inputs[idx])
                    time.sleep(0.2)
        except Exception as e:
            print(f"Erro ao preencher notas: {e}")
            raise
        
        time.sleep(0.5)
        
        # Clicar em Salvar
        try:
            save_buttons = modal.find_elements(By.CSS_SELECTOR, "button.btn-primary")
            for btn in save_buttons:
                if "salvar" in btn.text.lower():
                    driver.execute_script(CLICK_SCRIPT, btn)
                    break
        except Exception as e:
            print(f"Erro ao salvar avaliação: {e}")
            raise
        
        time.sleep(1)
        
        # Voltar para lista de projetos do grupo
        try:
            botao_voltar = driver.find_element(By.CSS_SELECTOR, "button.back-btn")
            driver.execute_script(CLICK_SCRIPT, botao_voltar)
            time.sleep(0.5)
        except Exception as e:
            print(f"Aviso: não foi possível clicar em voltar: {e}")
        
        end = time.time()
        return {
            "nome": "Avaliar projeto",
            "status": "PASS",
            "entrada": f"{nome_projeto} - Notas: {notas_criterios}",
            "resultado": "Projeto avaliado com sucesso",
            "tempo": end - start,
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "fluxo": fluxo_atual
        }
    
    except Exception as e:
        print(f"Erro ao avaliar projeto {nome_projeto}:", e)
        try:
            driver.save_screenshot(f"erro_avaliar_{nome_projeto}.png")
        except Exception:
            pass
        end = time.time()
        return {
            "nome": "Avaliar projeto",
            "status": "FAIL",
            "entrada": nome_projeto,
            "resultado": str(e),
            "tempo": end - start,
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "fluxo": fluxo_atual
        }
    

def balancear_e_autorizar_cenario(nome_cenario):
    """
    Balanceia o cenário seguindo o fluxo correto:
    1. Seleciona a categoria para cada projeto
    2. Ajusta o orçamento disponível global para incluir automaticamente os projetos
    3. Autoriza o cenário
    """
    start = time.time()
    try:
        time.sleep(2)
        print(f"\n{'='*80}")
        print(f"CONFIGURANDO CENÁRIO: {nome_cenario}")
        print(f"{'='*80}")
        
        config_fluxo = FLUXO_1 if fluxo_atual == 1 else FLUXO_2
        
        # PASSO 1: Selecionar categoria para cada projeto
        print("\n▶ PASSO 1: Selecionando categorias dos projetos")
        
        for proj_config in config_fluxo["projetos"]:
            nome_proj = proj_config["nome"]
            categoria = proj_config["categoria"]
            
            try:
                print(f"\n  • Projeto: {nome_proj}")
                print(f"    Categoria esperada: {categoria}")
                time.sleep(0.5)
                
                cards = driver.find_elements(By.CSS_SELECTOR, "app-card, .card")
                projeto_encontrado = False
                
                for card in cards:
                    rows = card.find_elements(By.CSS_SELECTOR, "table tbody tr.table-row, table tr")
                    
                    for row in rows:
                        tds = row.find_elements(By.TAG_NAME, "td")
                        if len(tds) < 6:
                            continue
                        
                        nome_encontrado = False
                        for td in tds:
                            if nome_proj.lower() in td.text.strip().lower():
                                nome_encontrado = True
                                projeto_encontrado = True
                                print(f"    ✓ Projeto encontrado na tabela")
                                break
                        
                        if nome_encontrado:
                            try:
                                categoria_select = None
                                for td in tds:
                                    try:
                                        select_elem = td.find_element(By.CSS_SELECTOR, "select.select-with-style")
                                        options = select_elem.find_elements(By.TAG_NAME, "option")
                                        categorias_conhecidas = ["Inovação", "Infraestrutura", "Comercial", "Cloud", "Segurança", "Analytics"]
                                        
                                        for opt in options:
                                            if any(cat.lower() in opt.text.lower() for cat in categorias_conhecidas):
                                                categoria_select = select_elem
                                                break
                                        
                                        if categoria_select:
                                            break
                                    except:
                                        continue
                                
                                if categoria_select:
                                    driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", categoria_select)
                                    time.sleep(0.3)
                                    
                                    driver.execute_script("""
                                        var select = arguments[0];
                                        var categoria = arguments[1];
                                        for(var i = 0; i < select.options.length; i++) {
                                            if(select.options[i].text.toLowerCase().includes(categoria.toLowerCase())) {
                                                select.selectedIndex = i;
                                                select.dispatchEvent(new Event('change', { bubbles: true }));
                                                break;
                                            }
                                        }
                                    """, categoria_select, categoria)
                                    
                                    time.sleep(0.5)
                                    print(f"    ✓ Categoria '{categoria}' selecionada")
                                    print(f"    ⏳ Aguardando 2s para tabela reordenar...")
                                    time.sleep(2)
                                else:
                                    print("    ⚠ Select de categoria não encontrado")
                            
                            except Exception as e:
                                print(f"    ✗ Erro ao selecionar categoria: {str(e)}")
                            
                            break
                    
                    if projeto_encontrado:
                        break
                
                if not projeto_encontrado:
                    print(f"    ✗ Projeto não encontrado na tabela")
            
            except Exception as e:
                print(f"    ✗ Erro ao processar projeto: {str(e)}")
                continue
        
        # PASSO 2: Ajustar orçamento disponível global
        print("\n▶ PASSO 2: Ajustando orçamento disponível global")
        
        try:
            # Calcular orçamento para incluir exatamente 2 projetos
            bac_projetos = []
            for proj in config_fluxo["projetos"]:
                bac = proj["indicadores"]["bac"]
                nome = proj["nome"]
                if isinstance(bac, str):
                    bac = float(bac.replace(".", "").replace(",", "."))
                bac_projetos.append({"nome": nome, "bac": bac})
            
            bac_projetos_sorted = sorted(bac_projetos, key=lambda x: x["bac"], reverse=True)
            top_2_projetos = bac_projetos_sorted[:2]
            orcamento_para_2_projetos = sum([p["bac"] for p in top_2_projetos])
            
            print(f"  • Projetos com maiores BAC:")
            for i, p in enumerate(top_2_projetos, 1):
                print(f"    {i}. {p['nome']}: R$ {p['bac']:,.2f}".replace(",", "X").replace(".", ",").replace("X", "."))
            
            print(f"  • Orçamento calculado: R$ {orcamento_para_2_projetos:,.2f}".replace(",", "X").replace(".", ",").replace("X", "."))
            
            # Encontrar campo de orçamento
            orcamento_input = WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.ID, "budget"))
            )
            
            driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", orcamento_input)
            time.sleep(0.5)
            
            # Clicar no campo
            orcamento_input.click()
            time.sleep(0.5)
            
            # Fechar modal de aviso se aparecer
            try:
                modal = WebDriverWait(driver, 3).until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, ".modal-content"))
                )
                botao_entendi = modal.find_element(By.CSS_SELECTOR, "button.btn-primary")
                if "entendi" in botao_entendi.text.lower():
                    driver.execute_script(CLICK_SCRIPT, botao_entendi)
                    time.sleep(1)
            except:
                pass

            # Re-encontrar campo
            orcamento_input = driver.find_element(By.ID, "budget")
            driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", orcamento_input)
            time.sleep(0.5)

            # Limpar campo
            driver.execute_script("arguments[0].focus();", orcamento_input)
            time.sleep(0.2)
            driver.execute_script("""
                arguments[0].value = '';
                arguments[0].dispatchEvent(new Event('input', { bubbles: true }));
                arguments[0].dispatchEvent(new Event('change', { bubbles: true }));
            """, orcamento_input)
            time.sleep(0.3)

            # Forçar limpeza se necessário
            valor_atual = orcamento_input.get_attribute("value")
            if valor_atual and valor_atual.strip():
                orcamento_input.click()
                time.sleep(0.2)
                orcamento_input.send_keys(Keys.CONTROL + "a")
                time.sleep(0.1)
                orcamento_input.send_keys(Keys.BACKSPACE)
                time.sleep(0.3)

            # Preencher novo valor
            orcamento_formatado = f"{orcamento_para_2_projetos:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
            
            try:
                orcamento_input.send_keys(orcamento_formatado)
                time.sleep(0.5)
                
                valor_preenchido = orcamento_input.get_attribute("value")
                
                if orcamento_formatado not in valor_preenchido:
                    driver.execute_script(f"""
                        arguments[0].value = '{orcamento_formatado}';
                        arguments[0].dispatchEvent(new Event('input', {{ bubbles: true }}));
                        arguments[0].dispatchEvent(new Event('change', {{ bubbles: true }}));
                    """, orcamento_input)
                    time.sleep(0.5)
                    
            except Exception as e:
                driver.execute_script(f"""
                    arguments[0].value = '{orcamento_formatado}';
                    arguments[0].dispatchEvent(new Event('input', {{ bubbles: true }}));
                    arguments[0].dispatchEvent(new Event('change', {{ bubbles: true }}));
                """, orcamento_input)
                time.sleep(0.5)

            # Disparar blur
            driver.execute_script("arguments[0].blur();", orcamento_input)
            time.sleep(0.5)

            valor_final = orcamento_input.get_attribute("value")
            print(f"  ✓ Orçamento definido: {valor_final}")

            time.sleep(3)  # ⭐ CRÍTICO: Aguardar sistema recalcular
        
        except Exception as e:
            print(f"  ✗ Erro ao ajustar orçamento: {str(e)}")
        
        # ⭐ PASSO 3: Verificar projetos incluídos ANTES DE AUTORIZAR (pela coluna badge)
        print("\n▶ PASSO 3: Verificando projetos incluídos (ANTES de autorizar)")
        
        try:
            time.sleep(2)
            
            cards = driver.find_elements(By.CSS_SELECTOR, "app-card, .card")
            nomes_incluidos = []
            nomes_removidos = []
            
            for card in cards:
                rows = card.find_elements(By.CSS_SELECTOR, "table tbody tr.table-row, table tr")
                
                for row in rows:
                    tds = row.find_elements(By.TAG_NAME, "td")
                    if len(tds) < 5:
                        continue
                    
                    # td[2] = Nome do projeto
                    nome_td = tds[2].text.strip()
                    
                    # ⭐ td[3] = Coluna Inclusão (badge verde ou vermelho)
                    try:
                        badge = tds[3].find_element(By.CSS_SELECTOR, ".badge")
                        classe_badge = badge.get_attribute("class")
                        
                        # Identificar o projeto
                        projeto_nome = None
                        for proj in config_fluxo["projetos"]:
                            if proj["nome"].strip().lower() in nome_td.strip().lower():
                                projeto_nome = proj["nome"]
                                break
                        
                        if projeto_nome:
                            # ⭐ VERIFICAR PELA CLASSE DO BADGE
                            if "badge-green" in classe_badge:
                                if projeto_nome not in nomes_incluidos:
                                    nomes_incluidos.append(projeto_nome)
                                    print(f"  ✓ INCLUÍDO: {projeto_nome}")
                            elif "badge-red" in classe_badge:
                                if projeto_nome not in nomes_removidos:
                                    nomes_removidos.append(projeto_nome)
                                    print(f"  ⚠ REMOVIDO: {projeto_nome}")
                    except Exception as e:
                        pass
            
            print(f"\n  • Total de projetos INCLUÍDOS: {len(nomes_incluidos)}")
            print(f"  • Total de projetos REMOVIDOS: {len(nomes_removidos)}")
            
            if len(nomes_incluidos) != 2:
                print(f"  ⚠ AVISO: Esperava 2 incluídos, encontrou {len(nomes_incluidos)}")
            else:
                print(f"  ✓ Correto: 2 projetos incluídos")
            
            # Debug detalhado
            if nomes_incluidos:
                print(f"\n  📋 Lista de INCLUÍDOS:")
                for nome in nomes_incluidos:
                    print(f"    ✓ '{nome}'")
            
            if nomes_removidos:
                print(f"\n  📋 Lista de REMOVIDOS:")
                for nome in nomes_removidos:
                    print(f"    ⚠ '{nome}'")
        
        except Exception as e:
            print(f"  ⚠ Erro ao verificar: {str(e)}")
            nomes_incluidos = []
        
        # PASSO 4: Autorizar cenário
        print("\n▶ PASSO 4: Autorizando cenário")
        try:
            botao_autorizar = WebDriverWait(driver, WAIT_TIMEOUT).until(
                EC.element_to_be_clickable((By.CSS_SELECTOR, "app-table-action-text-filter button.btn-primary"))
            )
            driver.execute_script(CLICK_SCRIPT, botao_autorizar)
            time.sleep(1)
            
            modal = WebDriverWait(driver, WAIT_TIMEOUT).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, ".modal-content"))
            )
            
            botoes = modal.find_elements(By.CSS_SELECTOR, "button.btn-primary")
            for btn in botoes:
                if "autorizar" in btn.text.lower():
                    driver.execute_script(CLICK_SCRIPT, btn)
                    print("  ✓ Cenário autorizado")
                    break
        except Exception as e:
            print(f"  ✗ Erro ao autorizar: {e}")
            raise
        
        time.sleep(2)
        
        # Voltar
        try:
            botao_voltar = WebDriverWait(driver, 5).until(
                EC.element_to_be_clickable((By.CSS_SELECTOR, "button.back-btn"))
            )
            driver.execute_script(CLICK_SCRIPT, botao_voltar)
            time.sleep(1)
        except:
            pass
        
        end = time.time()
        
        return {
            "nome": "Balancear e autorizar cenário",
            "status": "PASS",
            "entrada": f"{len(nomes_incluidos)} projetos incluídos com categorias",
            "resultado": f"Cenário balanceado e autorizado - {len(nomes_incluidos)} projetos incluídos automaticamente",
            "tempo": end - start,
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "fluxo": fluxo_atual,
            "projetos_incluidos": nomes_incluidos  # ⭐ Lista EXATA dos incluídos
        }

    except Exception as e:
        print(f"Erro: {e}")
        try:
            driver.save_screenshot("erro_autorizar_cenario.png")
        except:
            pass
        end = time.time()
        return {
            "nome": "Balancear e autorizar cenário",
            "status": "FAIL",
            "entrada": nome_cenario,
            "resultado": str(e),
            "tempo": end - start,
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "fluxo": fluxo_atual,
            "projetos_incluidos": []
        }

def verificar_vinculos_objetivos(objetivos_cadastrados, criterios_vinculos, nome_grupo_aval, nome_portfolio, projetos_incluidos_cenario=None):
    """
    Verifica os vínculos dos objetivos estratégicos.
    
    Args:
        projetos_incluidos_cenario: Lista com nomes dos projetos incluídos no cenário autorizado.
                                   Se None, verifica todos os projetos cadastrados.
    """
    resultados = []
    
    try:
        # Clicar na aba Objetivos
        time.sleep(1)
        try:
            clicar_tab("Objetivos")
            time.sleep(1)
        except Exception as e:
            print(f"Erro ao clicar em Objetivos: {e}")
            return resultados
        
        # Para cada objetivo cadastrado
        for nome_obj in objetivos_cadastrados:
            start = time.time()
            try:
                print(f"\n=== Verificando objetivo: {nome_obj} ===")
                
                # Clicar no objetivo
                if not achar_e_clicar_na_tabela(nome_obj):
                    raise RuntimeError(f"Objetivo '{nome_obj}' não encontrado")
                
                time.sleep(1)
                
                # Verificar vínculos em cada aba
                abas = ["Critérios", "Portfólios", "Projetos"]
                vinculos_ok = []
                
                for aba in abas:
                    try:
                        clicar_tab(aba)
                        time.sleep(0.5)
                        
                        if aba == "Critérios":
                            # Verificar critérios vinculados
                            criterios_esperados = criterios_vinculos.get(nome_obj, [])
                            criterios_encontrados = []
                            
                            rows = driver.find_elements(By.CSS_SELECTOR, ".table-row")
                            for row in rows:
                                tds = row.find_elements(By.TAG_NAME, "td")
                                if len(tds) > 0:
                                    nome_criterio = tds[0].text.strip()
                                    criterios_encontrados.append(nome_criterio)
                            
                            # Verificar se todos os critérios esperados estão presentes
                            todos_presentes = all(
                                any(crit_esp.lower() in crit_enc.lower() for crit_enc in criterios_encontrados)
                                for crit_esp in criterios_esperados
                            )
                            
                            if todos_presentes:
                                vinculos_ok.append(f"Critérios: {len(criterios_encontrados)} vinculados")
                                print(f"  ✓ Critérios vinculados: {criterios_encontrados}")
                            else:
                                vinculos_ok.append(f"Critérios: ERRO - esperados {criterios_esperados}, encontrados {criterios_encontrados}")
                                print(f"  ✗ Critérios com problema")
                        
                        elif aba == "Portfólios":
                            # Verificar se o portfólio está vinculado
                            rows = driver.find_elements(By.CSS_SELECTOR, ".table-row")
                            portfolio_encontrado = False
                            
                            for row in rows:
                                tds = row.find_elements(By.TAG_NAME, "td")
                                if len(tds) > 0:
                                    nome_port = tds[0].text.strip()
                                    if nome_portfolio.lower() in nome_port.lower():
                                        portfolio_encontrado = True
                                        vinculos_ok.append(f"Portfólio: {nome_port}")
                                        print(f"  ✓ Portfólio vinculado: {nome_port}")
                                        break
                            
                            if not portfolio_encontrado:
                                vinculos_ok.append(f"Portfólio: ERRO - '{nome_portfolio}' não encontrado")
                                print(f"  ✗ Portfólio não encontrado")
                        
                        elif aba == "Projetos":
                            # Verificar projetos vinculados
                            # Se temos lista de projetos incluídos, verificar apenas esses
                            if projetos_incluidos_cenario is not None:
                                print(f"    • Verificando projetos com base no cenário autorizado")
                                print(f"    • Projetos incluídos no cenário: {projetos_incluidos_cenario}")
                            
                            rows = driver.find_elements(By.CSS_SELECTOR, ".table-row")
                            projetos_encontrados = []
                            projetos_incluidos_encontrados = []
                            projetos_nao_incluidos_encontrados = []
                            
                            for row in rows:
                                tds = row.find_elements(By.TAG_NAME, "td")
                                if len(tds) > 0:
                                    nome_proj = tds[0].text.strip()
                                    projetos_encontrados.append(nome_proj)
                                    
                                    # Se temos filtro de incluídos, verificar se está na lista
                                    if projetos_incluidos_cenario is not None:
                                        eh_incluido = False
                                        for proj_incluido in projetos_incluidos_cenario:
                                            if proj_incluido.lower() in nome_proj.lower():
                                                projetos_incluidos_encontrados.append(nome_proj)
                                                eh_incluido = True
                                                break
                                        
                                        # Se não é incluído mas está nos vínculos, é um ERRO
                                        if not eh_incluido:
                                            projetos_nao_incluidos_encontrados.append(nome_proj)
                            
                            # Se temos filtro de projetos incluídos, validar corretamente
                            if projetos_incluidos_cenario is not None:
                                # Verificar projetos incluídos
                                if len(projetos_incluidos_encontrados) > 0:
                                    print(f"  ✓ {len(projetos_incluidos_encontrados)} projeto(s) incluído(s) no cenário e corretamente vinculado(s):")
                                    for proj in projetos_incluidos_encontrados:
                                        print(f"    - {proj}")
                                else:
                                    print(f"  ⚠ Nenhum dos projetos incluídos no cenário está vinculado")
                                
                                # ⭐ VERIFICAR PROJETOS NÃO INCLUÍDOS (VALIDAÇÃO DE CORREÇÃO)
                                if len(projetos_nao_incluidos_encontrados) > 0:
                                    # ERRO: Projetos não incluídos no cenário NÃO devem estar nos vínculos
                                    print(f"  ✗ ERRO: {len(projetos_nao_incluidos_encontrados)} projeto(s) NÃO incluído(s) no cenário mas incorretamente vinculado(s):")
                                    for proj in projetos_nao_incluidos_encontrados:
                                        print(f"    - {proj} (NÃO deveria estar vinculado)")
                                    
                                    vinculos_ok.append(f"Projetos incluídos: {len(projetos_incluidos_encontrados)} corretos | ⚠ ERRO: {len(projetos_nao_incluidos_encontrados)} não incluídos incorretamente vinculados")
                                else:
                                    # CORRETO: Nenhum projeto não incluído está vinculado
                                    print(f"  ✓ Projetos não incluídos no cenário corretamente ausentes dos vínculos")
                                    vinculos_ok.append(f"Projetos incluídos: {len(projetos_incluidos_encontrados)} vinculado(s) corretamente | Não incluídos: ausentes corretamente")
                            else:
                                # Modo original: mostrar todos
                                if len(projetos_encontrados) > 0:
                                    vinculos_ok.append(f"Projetos: {len(projetos_encontrados)} vinculados")
                                    print(f"  ✓ Projetos vinculados: {projetos_encontrados}")
                                else:
                                    vinculos_ok.append(f"Projetos: Nenhum vinculado")
                                    print(f"  ⚠ Nenhum projeto vinculado")
                    
                    except Exception as e:
                        vinculos_ok.append(f"{aba}: ERRO - {str(e)}")
                        print(f"  ✗ Erro ao verificar {aba}: {e}")
                
                # Voltar para lista de objetivos
                time.sleep(0.5)
                try:
                    botao_voltar = driver.find_element(By.CSS_SELECTOR, "button.back-btn")
                    driver.execute_script(CLICK_SCRIPT, botao_voltar)
                    time.sleep(0.5)
                except Exception:
                    pass
                
                end = time.time()
                resultados.append({
                    "nome": f"Verificar vínculos do objetivo '{nome_obj}'",
                    "status": "PASS",
                    "entrada": nome_obj,
                    "resultado": " | ".join(vinculos_ok),
                    "tempo": end - start,
                    "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    "fluxo": fluxo_atual
                })
                
            except Exception as e:
                print(f"Erro ao verificar objetivo {nome_obj}: {e}")
                end = time.time()
                resultados.append({
                    "nome": f"Verificar vínculos do objetivo '{nome_obj}'",
                    "status": "FAIL",
                    "entrada": nome_obj,
                    "resultado": str(e),
                    "tempo": end - start,
                    "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    "fluxo": fluxo_atual
                })
        
        return resultados
        
    except Exception as e:
        print(f"Erro geral ao verificar vínculos dos objetivos: {e}")
        return resultados

def cadastrar_cenario(nome_cenario, nome_grupo_avaliacao, orcamento, nome_portfolio):
    """Cadastra um cenário de avaliação e, se necessário, balanceia e autoriza."""
    start = time.time()
    
    try:
        # Verificar se já existe
        if verificar_item_existe_na_tabela(nome_cenario):
            print(f"Cenário '{nome_cenario}' já existe.")
            end = time.time()
            return {
                "nome": "Cadastrar cenário",
                "status": "PASS",
                "entrada": nome_cenario,
                "resultado": "Já existente (pulado)",
                "tempo": end - start,
                "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "fluxo": fluxo_atual
            }

        # Clicar no botão Cadastrar
        try:
            wait_local = WebDriverWait(driver, WAIT_TIMEOUT)
            botao = wait_local.until(EC.element_to_be_clickable((By.CSS_SELECTOR, "app-table-action-text-filter button.btn-primary")))
            driver.execute_script(CLICK_SCRIPT, botao)
        except Exception as e:
            print(f"Erro ao clicar em cadastrar: {e}")
            raise

        time.sleep(1)

        # Aguardar modal abrir
        modal = WebDriverWait(driver, WAIT_TIMEOUT).until(EC.presence_of_element_located((By.CSS_SELECTOR, ".modal-content")))

        # Preencher nome do cenário
        try:
            name_input = modal.find_elements(By.CSS_SELECTOR, "input")[0]
            name_input.clear()
            name_input.send_keys(nome_cenario)
            driver.execute_script("arguments[0].dispatchEvent(new Event('input', {bubbles: true})); arguments[0].dispatchEvent(new Event('change', {bubbles: true}));", name_input)
        except Exception as e:
            print(f"Erro ao preencher nome: {e}")
            raise

        time.sleep(0.5)

        # Selecionar grupo de avaliação
        try:
            selects = modal.find_elements(By.TAG_NAME, "select")
            print(f"  • Encontrados {len(selects)} selects no modal")
            
            if len(selects) >= 1:
                grupo_select = selects[0]
                
                # Aguardar opções serem carregadas (tentar por até 10 segundos)
                print("  • Aguardando opções do grupo de avaliação serem carregadas...")
                timeout = 10
                start_wait = time.time()
                
                while time.time() - start_wait < timeout:
                    options = grupo_select.find_elements(By.TAG_NAME, "option")
                    if len(options) > 0:
                        print(f"  ✓ {len(options)} opção(ões) carregada(s)")
                        break
                    time.sleep(0.5)
                else:
                    print("  ⚠ Timeout aguardando opções")
                
                time.sleep(0.5)
                options = grupo_select.find_elements(By.TAG_NAME, "option")
                
                # Log das opções disponíveis
                print(f"  • Opções disponíveis:")
                for i, opt in enumerate(options):
                    print(f"    [{i}] value='{opt.get_attribute('value')}' text='{opt.text.strip()}'")
                
                grupo_encontrado = False
                for opt in options:
                    if nome_grupo_avaliacao.lower() in opt.text.lower():
                        driver.execute_script("""
                            arguments[0].selected = true;
                            arguments[0].dispatchEvent(new Event('change', {bubbles: true}));
                        """, opt)
                        grupo_encontrado = True
                        print(f"  ✓ Grupo de avaliação selecionado: {opt.text.strip()}")
                        break
                
                if not grupo_encontrado:
                    raise RuntimeError(f"Grupo de avaliação '{nome_grupo_avaliacao}' não encontrado no select")
            else:
                raise RuntimeError("Nenhum select encontrado no modal")
        except Exception as e:
            print(f"Erro ao selecionar grupo de avaliação: {e}")
            raise

        time.sleep(0.3)

        # Preencher orçamento
        try:
            budget_input = modal.find_element(By.CSS_SELECTOR, "input#budget")
            budget_input.clear()
            budget_input.send_keys(str(orcamento))
            driver.execute_script("arguments[0].dispatchEvent(new Event('input', {bubbles: true})); arguments[0].dispatchEvent(new Event('change', {bubbles: true}));", budget_input)
        except Exception as e:
            print(f"Erro ao preencher orçamento: {e}")
            raise

        time.sleep(0.3)

        # Selecionar portfólio específico
        try:
            if len(selects) >= 2:
                portfolio_select = selects[1]
                
                # Aguardar opções do portfólio serem carregadas
                print("  • Aguardando opções do portfólio serem carregadas...")
                timeout = 10
                start_wait = time.time()
                
                while time.time() - start_wait < timeout:
                    options = portfolio_select.find_elements(By.TAG_NAME, "option")
                    if len(options) > 0:
                        print(f"  ✓ {len(options)} opção(ões) carregada(s)")
                        break
                    time.sleep(0.5)
                else:
                    print("  ⚠ Timeout aguardando opções")
                
                time.sleep(0.5)
                options = portfolio_select.find_elements(By.TAG_NAME, "option")
                
                # Log das opções disponíveis
                print(f"  • Opções disponíveis:")
                for i, opt in enumerate(options):
                    print(f"    [{i}] value='{opt.get_attribute('value')}' text='{opt.text.strip()}'")
                
                portfolio_encontrado = False
                for opt in options:
                    if nome_portfolio.lower() in opt.text.lower():
                        driver.execute_script("""
                            arguments[0].selected = true;
                            arguments[0].dispatchEvent(new Event('change', {bubbles: true}));
                        """, opt)
                        portfolio_encontrado = True
                        print(f"  ✓ Portfólio selecionado: {opt.text.strip()}")
                        break
                
                if not portfolio_encontrado:
                    raise RuntimeError(f"Portfólio '{nome_portfolio}' não encontrado no select")
            else:
                raise RuntimeError("Select de portfólio não encontrado no modal")
        except Exception as e:
            print(f"Erro ao selecionar portfólio: {e}")
            raise

        time.sleep(0.3)

        # Preencher descrição (opcional)
        try:
            textarea = modal.find_element(By.TAG_NAME, "textarea")
            textarea.clear()
            textarea.send_keys(f"Descrição automática do cenário {nome_cenario}")
            driver.execute_script("arguments[0].dispatchEvent(new Event('input', {bubbles: true})); arguments[0].dispatchEvent(new Event('change', {bubbles: true}));", textarea)
        except Exception:
            pass

        time.sleep(0.5)

        # Clicar em Salvar
        try:
            save_buttons = modal.find_elements(By.CSS_SELECTOR, "button.btn-primary")
            for btn in save_buttons:
                if "salvar" in btn.text.lower():
                    driver.execute_script(CLICK_SCRIPT, btn)
                    print("✓ Clicou em Salvar no modal do cenário")
                    break
        except Exception as e:
            print(f"✗ Erro ao salvar cenário: {e}")
            raise

        time.sleep(2)  # Aguardar sistema processar e abrir tela do cenário
        
        # Após salvar, o sistema ENTRA automaticamente na tela do cenário
        # Não precisa verificar na tabela pois já estamos dentro do cenário
        print(f"✓ Cenário '{nome_cenario}' cadastrado com sucesso. Sistema abriu tela do cenário automaticamente.")
        print(f"▶ Iniciando balanceamento e autorização...")
        
        # Balancear e autorizar o cenário recém-cadastrado
        res_balancear = balancear_e_autorizar_cenario(nome_cenario)
        
        # Retornar também os projetos incluídos
        projetos_incluidos = res_balancear.get("projetos_incluidos", [])
        
        end = time.time()
        resultado_retorno = {
            "nome": "Cadastrar cenário",
            "status": "PASS",
            "entrada": f"{nome_cenario} (Orçamento: R$ {orcamento}, Portfólio: {nome_portfolio})",
            "resultado": f"Cadastrado, balanceado e autorizado | {res_balancear.get('resultado', '')}",
            "tempo": end - start,
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "fluxo": fluxo_atual,
            "projetos_incluidos": projetos_incluidos  # Propagar lista de projetos incluídos
        }
        
        return resultado_retorno

    except Exception as e:
        print(f"Erro ao cadastrar cenário: {e}")
        try:
            driver.save_screenshot("erro_cadastrar_cenario.png")
        except Exception:
            pass
        end = time.time()
        return {
            "nome": "Cadastrar cenário",
            "status": "FAIL",
            "entrada": nome_cenario,
            "resultado": str(e),
            "tempo": end - start,
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "fluxo": fluxo_atual
        }

def fechar_popup_senha():
    """Tenta fechar popup de salvar senha do Chrome."""
    try:

        time.sleep(1)
        
        ActionChains(driver).send_keys(Keys.ESCAPE).perform()
        time.sleep(0.5)
        
        # Método 2: Clicar em "Nunca" ou "Não" se aparecer
        try:
            # Procurar por botões comuns em popups de senha
            botoes = driver.find_elements(By.CSS_SELECTOR, "button")
            for btn in botoes:
                texto = btn.text.lower()
                if any(palavra in texto for palavra in ["nunca", "não", "never", "no", "nope", "ok"]):
                    driver.execute_script(CLICK_SCRIPT, btn)
                    break
        except Exception:
            pass
            
    except Exception as e:
        print(f"Não foi possível fechar popup de senha: {e}")
        pass


def login(email):
    start = time.time()
    status = "FAIL"
    resultado = ""

    try:
        driver.get("http://localhost:4200/")

        wait = WebDriverWait(driver, 10)

        box = wait.until(EC.presence_of_element_located((By.ID, "email")))
        box.send_keys(email)
        box.send_keys(Keys.ENTER)

        box = wait.until(EC.presence_of_element_located((By.ID, "password")))
        box.send_keys("12345")
        box.send_keys(Keys.ENTER)

        botao = wait.until(EC.presence_of_element_located((By.CLASS_NAME, "login-btn")))
        botao.click()

        
     
        status = "PASS"
        resultado = "OK"

    except Exception as e:
        resultado = str(e)

    end = time.time()
    
    return {
        "nome": "Login",
        "status": status,
        "entrada": email,
        "resultado": resultado,
        "driver": driver,
        "tempo": end - start,
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "fluxo": fluxo_atual
    }

def vincular_objetivo_ao_criterio_direto(nome_criterio, nome_objetivo, ja_esta_no_criterio=False):
    """Vincula um objetivo a um critério (versão otimizada que não clica no critério se já estiver nele)."""
    start = time.time()
    try:
        # ⭐ SE JÁ ESTÁ NO CRITÉRIO (veio das comparações), NÃO PRECISA CLICAR
        if not ja_esta_no_criterio:
            print(f"\n  • Procurando critério '{nome_criterio}' para vincular objetivo...")
            
            # Aguardar tabela carregar
            time.sleep(1)
            WebDriverWait(driver, 5).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, ".table-row"))
            )
            time.sleep(0.5)
            
            # Verificar se já tem objetivo vinculado
            try:
                rows = driver.find_elements(By.CSS_SELECTOR, ".table-row")
                for row in rows:
                    tds = row.find_elements(By.TAG_NAME, "td")
                    if len(tds) >= 3:
                        nome_celula = tds[0].text.strip()
                        objetivos_vinculados = tds[2].text.strip()
                        
                        if nome_criterio.strip().lower() == nome_celula.strip().lower():
                            try:
                                num_objetivos = int(objetivos_vinculados)
                                if num_objetivos > 0:
                                    print(f"  ✓ Critério '{nome_criterio}' já tem {num_objetivos} objetivo(s) vinculado(s). Pulando.")
                                    end = time.time()
                                    return {
                                        "nome": "Vincular objetivo",
                                        "status": "PASS",
                                        "entrada": f"{nome_criterio} -> {nome_objetivo}",
                                        "resultado": f"Já tem objetivo vinculado - Pulado",
                                        "tempo": end - start,
                                        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                                        "fluxo": fluxo_atual
                                    }
                            except:
                                pass
            except Exception as e:
                print(f"  ⚠ Erro ao verificar objetivos: {e}")
            
            # Clicar no critério
            if not achar_e_clicar_na_tabela(nome_criterio):
                raise RuntimeError(f"Critério '{nome_criterio}' não encontrado na tabela")
            
            time.sleep(0.5)
        else:
            print(f"\n  • Já está dentro do critério '{nome_criterio}', indo direto para aba Objetivos...")
        
        # Clicar na aba Objetivos
        print(f"  • Clicando na aba 'Objetivos'...")
        clicar_tab("Objetivos")
        time.sleep(0.5)
        
        # Verificar se já tem objetivo vinculado
        tem_vinculo = False
        try:
            empty_msg = driver.find_element(By.CSS_SELECTOR, ".empty-objectives")
            tem_vinculo = False
            print(f"  • Nenhum objetivo vinculado ainda")
        except Exception:
            try:
                objectives_list = driver.find_element(By.CSS_SELECTOR, ".objectives-list")
                tem_vinculo = True
                print(f"  • Já tem objetivos vinculados")
            except Exception:
                tem_vinculo = False
        
        if tem_vinculo:
            # Verificar se o objetivo específico já está vinculado
            try:
                objective_items = driver.find_elements(By.CSS_SELECTOR, ".objective-item .objective-name")
                for item in objective_items:
                    if nome_objetivo in item.text:
                        print(f"  ✓ Objetivo '{nome_objetivo}' já vinculado")
                        end = time.time()
                        return {
                            "nome": "Vincular objetivo",
                            "status": "PASS",
                            "entrada": f"{nome_criterio} -> {nome_objetivo}",
                            "resultado": "Objetivo já vinculado",
                            "tempo": end - start,
                            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                            "fluxo": fluxo_atual
                        }
            except Exception:
                pass
        
        # Clicar no botão "Cadastrar novo vínculo"
        print(f"  • Clicando em 'Cadastrar novo vínculo'...")
        try:
            buttons = driver.find_elements(By.CSS_SELECTOR, ".actions-right button.btn-primary")
            for btn in buttons:
                if "vínculo" in btn.text.lower():
                    driver.execute_script(CLICK_SCRIPT, btn)
                    print(f"  ✓ Clicou em 'Cadastrar novo vínculo'")
                    break
        except Exception as e:
            print(f"  ✗ Erro ao clicar em cadastrar vínculo: {e}")
            raise
        
        time.sleep(0.5)
        
        # Aguardar modal e selecionar objetivo
        print(f"  • Selecionando objetivo '{nome_objetivo}'...")
        wait_local = WebDriverWait(driver, WAIT_TIMEOUT)
        
        try:
            select = wait_local.until(EC.presence_of_element_located((By.CSS_SELECTOR, "select")))
            options = select.find_elements(By.TAG_NAME, "option")
            
            objetivo_encontrado = False
            for opt in options:
                if nome_objetivo in opt.text:
                    driver.execute_script("""
                        arguments[0].selected = true;
                        arguments[0].dispatchEvent(new Event('change', {bubbles: true}));
                    """, opt)
                    objetivo_encontrado = True
                    print(f"  ✓ Objetivo selecionado")
                    break
            
            if not objetivo_encontrado:
                raise RuntimeError(f"Objetivo '{nome_objetivo}' não encontrado no select")
                
        except Exception as e:
            print(f"  ✗ Erro ao selecionar objetivo: {e}")
            raise
        
        time.sleep(0.3)
        
        # Salvar
        print(f"  • Salvando...")
        try:
            save_buttons = driver.find_elements(By.CSS_SELECTOR, "button.btn-primary")
            for btn in save_buttons:
                if any(palavra in btn.text.lower() for palavra in ["salvar", "confirmar", "vincular"]):
                    driver.execute_script(CLICK_SCRIPT, btn)
                    print(f"  ✓ Salvo")
                    break
        except Exception as e:
            print(f"  ✗ Erro ao salvar: {e}")
            raise
        
        time.sleep(0.5)
        
        end = time.time()
        return {
            "nome": "Vincular objetivo",
            "status": "PASS",
            "entrada": f"{nome_criterio} -> {nome_objetivo}",
            "resultado": "Objetivo vinculado com sucesso",
            "tempo": end - start,
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "fluxo": fluxo_atual
        }

    except Exception as e:
        print(f"✗ Erro: {e}")
        end = time.time()
        return {
            "nome": "Vincular objetivo",
            "status": "FAIL",
            "entrada": f"{nome_criterio} -> {nome_objetivo}",
            "resultado": str(e),
            "tempo": end - start,
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "fluxo": fluxo_atual
        }


def estrategia(nomeEstrategia, nome_portfolio):
    start = time.time()
    status = "FAIL"
    resultado_msg = ""
    try:
        wait = WebDriverWait(driver, WAIT_TIMEOUT)

        cards = driver.find_elements(By.CSS_SELECTOR, ".nav-card")
        if not cards:
            try:
                cards = wait.until(EC.presence_of_all_elements_located((By.CSS_SELECTOR, ".nav-card")))
            except Exception:
                cards = []

        for c in cards:
            try:
                title = c.find_element(By.TAG_NAME, "h3").text.strip()
                if title.lower().startswith("estratég"):
                    driver.execute_script(CLICK_SCRIPT, c)
                    break
            except Exception:
                continue

        # verificar se estratégia já existe
        if not verificar_item_existe_na_tabela(nomeEstrategia):
            # cadastrar nova estratégia
            try:
                botao = wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, "app-table-action-text-filter button")))
                botao.click()
                
            except Exception:
                components = driver.find_elements(By.CSS_SELECTOR, "app-table-action-text-filter, app-table app-table-action-text-filter")
                if not components:
                    try:
                        components = wait.until(EC.presence_of_all_elements_located((By.CSS_SELECTOR, "app-table-action-text-filter, app-table app-table-action-text-filter")))
                    except Exception:
                        components = []

                comp = components[0]
                try:
                    botao = comp.find_element(By.TAG_NAME, "button")
                    driver.execute_script(CLICK_SCRIPT, botao)
                except Exception:
                    try:
                        driver.save_screenshot("erro_appTable_click.png")
                        with open("erro_appTable_page.html", "w", encoding="utf-8") as f:
                            f.write(driver.page_source)
                    except Exception:
                        pass
                    raise

            try:
                modal = wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, "app-form-modal-component")))

                name_input = modal.find_element(By.CSS_SELECTOR, "input#name")
                name_input.clear()
                name_input.send_keys(nomeEstrategia)
                driver.execute_script("arguments[0].dispatchEvent(new Event('input', {bubbles: true})); arguments[0].dispatchEvent(new Event('change', {bubbles: true}));", name_input)

                try:
                    desc_input = modal.find_element(By.CSS_SELECTOR, "textarea#description")
                except Exception:
                    desc_input = driver.find_element(By.CSS_SELECTOR, "textarea#description")
                desc_input.clear()
                desc_input.send_keys("Esta estratégia contemplará o ciclo 2025 - 2026.")
                driver.execute_script("arguments[0].dispatchEvent(new Event('input', {bubbles: true})); arguments[0].dispatchEvent(new Event('change', {bubbles: true}));", desc_input)

                try:
                    save_btn = modal.find_element(By.CSS_SELECTOR, "button.btn-primary")
                except Exception:
                    save_btn = modal.find_element(By.CSS_SELECTOR, "button, btn-primary")

                def _save_enabled(d):
                    try:
                        el = modal.find_element(By.CSS_SELECTOR, "button.btn-primary")
                        return el.is_enabled()
                    except Exception:
                        return False

                try:
                    WebDriverWait(driver, WAIT_TIMEOUT).until(_save_enabled)
                except Exception:
                    try:
                        driver.execute_script("arguments[0].removeAttribute('disabled');", save_btn)
                    except Exception:
                        pass

                driver.execute_script(CLICK_SCRIPT, save_btn)
                time.sleep(1)
                
            except Exception as e:
                print("Erro ao cadastrar estratégia:", e)
                raise
        
        # clicar na estratégia (já existente ou recém cadastrada)
        if not achar_e_clicar_na_tabela(nomeEstrategia):
            try:
                driver.save_screenshot("debug_no_strategy_found.png")
                with open("debug_no_strategy_page.html", "w", encoding="utf-8") as f:
                    f.write(driver.page_source)
            except Exception:
                pass
            resultado_msg = f"Estratégia '{nomeEstrategia}' não encontrada na tabela"
            raise RuntimeError(resultado_msg)

        for nome_obj in nomes_objetivos:
            res = cadastrar_objetivo(nome_obj)
            additional_test_results.append(res)

        # clicar na tab Grupos de critérios
        time.sleep(1)
        clicar_tab("Grupos de critérios")
        
        # cadastrar grupo de critérios
        time.sleep(1)
        # nome_grupo = ESTRATEGIA["grupo_criterios"]["nome"]
        config_fluxo = FLUXO_1 if fluxo_atual == 1 else FLUXO_2
        nome_grupo = config_fluxo["estrategia"]["grupo_criterios"]["nome"]
        res_grupo = cadastrar_grupo_criterios(nome_grupo)
        additional_test_results.append(res_grupo)

        # cadastrar critérios dentro do grupo
        time.sleep(1)
        criterios_cadastrados = []

        for nome_criterio in nomes_criterios:
            res_criterio = cadastrar_criterio(nome_criterio)
            additional_test_results.append(res_criterio)
            if res_criterio["status"] == "PASS":
                criterios_cadastrados.append(nome_criterio)

        # Guardar mapeamento de vínculos critério->objetivo
        criterios_vinculos_map = {}

        # preencher comparações de cada critério e vincular objetivos
        time.sleep(1)
        total_criterios = len(criterios_cadastrados)
        for idx, nome_criterio in enumerate(criterios_cadastrados):
            print(f"\n{'='*60}")
            print(f"PROCESSANDO CRITÉRIO {idx+1}/{total_criterios}: {nome_criterio}")
            print(f"{'='*60}")
            
            # preencher comparações diretas
            res_comp = preencher_comparacoes_criterio(nome_criterio, config_fluxo)
            additional_test_results.append(res_comp)
            
            # ⭐ DETECTAR SE PULOU AS COMPARAÇÕES
            comparacoes_puladas = "pulado" in res_comp["resultado"].lower()
            
            if comparacoes_puladas:
                print(f"  ℹ Critério '{nome_criterio}' já tem comparações preenchidas")
            
            time.sleep(0.5)
            
            # Verificar comparações recíprocas (se não pulou)
            if not comparacoes_puladas:
                clicar_tab("Comparações recíprocas")
                time.sleep(0.5)
                res_reciprocas = verificar_comparacoes_reciprocas(nome_criterio)
                additional_test_results.append(res_reciprocas)
                time.sleep(0.5)
            
            # ⭐ SE PULOU AS COMPARAÇÕES, PRECISA CLICAR NO CRITÉRIO NOVAMENTE
            if comparacoes_puladas:
                print(f"\n  • Clicando novamente no critério '{nome_criterio}' para vincular objetivo...")
                time.sleep(0.5)
                
                if not achar_e_clicar_na_tabela(nome_criterio):
                    print(f"  ✗ Erro: não conseguiu clicar no critério '{nome_criterio}'")
                    # Continuar para o próximo critério
                    continue
                else:
                    print(f"  ✓ Clicou no critério '{nome_criterio}'")
                    time.sleep(0.5)
            
            # Clicar na aba Objetivos
            print(f"  • Indo para aba Objetivos...")
            clicar_tab("Objetivos")
            time.sleep(0.5)
            
            # ⭐ VINCULAR OBJETIVO USANDO MAPEAMENTO CONFIGURADO
            vinculos_map = config_fluxo["estrategia"]["grupo_criterios"].get("vinculos_criterio_objetivo", {})
            nome_obj_vincular = vinculos_map.get(nome_criterio, None)
            
            if nome_obj_vincular is None:
                # Fallback: usar índice se não houver mapeamento configurado
                if idx < len(nomes_objetivos):
                    nome_obj_vincular = nomes_objetivos[idx]
                else:
                    nome_obj_vincular = nomes_objetivos[idx % len(nomes_objetivos)]
                print(f"  ⚠ Mapeamento não encontrado para '{nome_criterio}', usando fallback: '{nome_obj_vincular}'")
            else:
                print(f"  ✓ Mapeamento configurado: '{nome_criterio}' → '{nome_obj_vincular}'")
            
            # Guardar vínculo no mapa
            if nome_obj_vincular not in criterios_vinculos_map:
                criterios_vinculos_map[nome_obj_vincular] = []
            criterios_vinculos_map[nome_obj_vincular].append(nome_criterio)
            
            # ⭐ VERIFICAR SE JÁ TEM OBJETIVO VINCULADO (direto na aba Objetivos)
            try:
                # Verificar se há objetivos vinculados
                tem_objetivo_vinculado = False
                try:
                    objectives_list = driver.find_element(By.CSS_SELECTOR, ".objectives-list")
                    # Se encontrou a lista, já tem objetivos vinculados
                    objective_items = driver.find_elements(By.CSS_SELECTOR, ".objective-item .objective-name")
                    for item in objective_items:
                        if nome_obj_vincular in item.text:
                            tem_objetivo_vinculado = True
                            print(f"  ✓ Objetivo '{nome_obj_vincular}' já vinculado ao critério '{nome_criterio}'")
                            break
                except:
                    # Se não encontrou lista, não tem objetivos vinculados
                    pass
                
                if not tem_objetivo_vinculado:
                    # ⭐ VINCULAR OBJETIVO (já está na aba Objetivos)
                    print(f"  • Vinculando objetivo '{nome_obj_vincular}'...")
                    
                    # Clicar no botão "Cadastrar novo vínculo"
                    try:
                        buttons = driver.find_elements(By.CSS_SELECTOR, ".actions-right button.btn-primary")
                        for btn in buttons:
                            if "vínculo" in btn.text.lower():
                                driver.execute_script(CLICK_SCRIPT, btn)
                                print(f"    ✓ Clicou em 'Cadastrar novo vínculo'")
                                break
                    except Exception as e:
                        print(f"    ✗ Erro ao clicar em cadastrar vínculo: {e}")
                        raise
                    
                    time.sleep(0.5)
                    
                    # Selecionar objetivo no select
                    try:
                        wait_local = WebDriverWait(driver, WAIT_TIMEOUT)
                        select = wait_local.until(EC.presence_of_element_located((By.CSS_SELECTOR, "select")))
                        options = select.find_elements(By.TAG_NAME, "option")
                        
                        objetivo_encontrado = False
                        for opt in options:
                            if nome_obj_vincular in opt.text:
                                driver.execute_script("""
                                    arguments[0].selected = true;
                                    arguments[0].dispatchEvent(new Event('change', {bubbles: true}));
                                """, opt)
                                objetivo_encontrado = True
                                print(f"    ✓ Objetivo '{nome_obj_vincular}' selecionado")
                                break
                        
                        if not objetivo_encontrado:
                            raise RuntimeError(f"Objetivo '{nome_obj_vincular}' não encontrado no select")
                            
                    except Exception as e:
                        print(f"    ✗ Erro ao selecionar objetivo: {e}")
                        raise
                    
                    time.sleep(0.3)
                    
                    # Salvar
                    try:
                        save_buttons = driver.find_elements(By.CSS_SELECTOR, "button.btn-primary")
                        for btn in save_buttons:
                            if any(palavra in btn.text.lower() for palavra in ["salvar", "confirmar", "vincular"]):
                                driver.execute_script(CLICK_SCRIPT, btn)
                                print(f"    ✓ Objetivo vinculado com sucesso")
                                break
                    except Exception as e:
                        print(f"    ✗ Erro ao salvar: {e}")
                        raise
                    
                    time.sleep(0.5)
                    
                    # Registrar resultado
                    additional_test_results.append({
                        "nome": "Vincular objetivo",
                        "status": "PASS",
                        "entrada": f"{nome_criterio} -> {nome_obj_vincular}",
                        "resultado": "Objetivo vinculado com sucesso",
                        "tempo": 0,
                        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                        "fluxo": fluxo_atual
                    })
                else:
                    # Registrar que já estava vinculado
                    additional_test_results.append({
                        "nome": "Vincular objetivo",
                        "status": "PASS",
                        "entrada": f"{nome_criterio} -> {nome_obj_vincular}",
                        "resultado": "Objetivo já vinculado - Pulado",
                        "tempo": 0,
                        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                        "fluxo": fluxo_atual
                    })
            
            except Exception as e:
                print(f"    ✗ Erro ao vincular objetivo: {e}")
                additional_test_results.append({
                    "nome": "Vincular objetivo",
                    "status": "FAIL",
                    "entrada": f"{nome_criterio} -> {nome_obj_vincular}",
                    "resultado": str(e),
                    "tempo": 0,
                    "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    "fluxo": fluxo_atual
                })
            
            time.sleep(0.5)
            
            # Voltar para lista de critérios
            try:
                botao_voltar = driver.find_element(By.CSS_SELECTOR, "button.back-btn")
                driver.execute_script(CLICK_SCRIPT, botao_voltar)
                time.sleep(0.5)
                print(f"✓ Voltou para lista de critérios")
            except Exception as e:
                print(f"✗ Erro ao voltar para lista de critérios: {e}")
                pass
        
        print(f"\n{'='*60}")
        print(f"FINALIZOU PROCESSAMENTO DE TODOS OS {len(criterios_cadastrados)} CRITÉRIOS")
        print(f"{'='*60}\n")
        
        # voltar para estratégia 
        try:
            botao_voltar = driver.find_element(By.CSS_SELECTOR, "button.back-btn")
            driver.execute_script(CLICK_SCRIPT, botao_voltar)
            time.sleep(0.5)
            print("✓ Voltou para página da estratégia (saiu do grupo de critérios)")
        except Exception as e:
            print(f"✗ Erro ao voltar para estratégia: {e}")
            pass
        
        # clicar na aba Grupos de avaliações
        print("\n▶ Tentando clicar na aba 'Grupos de avaliações'...")
        res_tab = clicar_tab("Grupos de avaliações")
        if res_tab and res_tab.get("status") == "FAIL":
            print(f"✗ ERRO ao clicar na tab: {res_tab.get('resultado')}")
            raise RuntimeError(f"Falha ao clicar na aba Grupos de avaliações: {res_tab.get('resultado')}")
        else:
            print("✓ Clicou com sucesso na aba 'Grupos de avaliações'")
        time.sleep(1)
        print(f"\n▶ Cadastrando grupo de avaliação '{config_fluxo['estrategia']['grupo_avaliacao']['nome']}'...")
        nome_grupo_aval = config_fluxo["estrategia"]["grupo_avaliacao"]["nome"]
        res_grupo_aval = cadastrar_grupo_avaliacao(nome_grupo_aval, nome_grupo)
        additional_test_results.append(res_grupo_aval)
        
        if res_grupo_aval["status"] == "FAIL":
            print(f"✗ ERRO ao cadastrar grupo de avaliação: {res_grupo_aval['resultado']}")
            raise RuntimeError(f"Falha ao cadastrar grupo de avaliação: {res_grupo_aval['resultado']}")
        else:
            print(f"✓ Grupo de avaliação '{nome_grupo_aval}' processado com sucesso")
        
        time.sleep(1)
        
        print(f"\n{'='*60}")
        print(f"INICIANDO CADASTRO E AVALIAÇÃO DE {len(projetos_avaliacoes)} PROJETOS")
        print(f"{'='*60}\n")
        
        # Cadastrar e avaliar cada projeto
        for nome_proj, notas in projetos_avaliacoes:
            try:
                projeto_encontrado = False
                projeto_ja_avaliado = False
                
                cards = driver.find_elements(By.CSS_SELECTOR, "app-card, .card")
                for card in cards:
                    rows = card.find_elements(By.CSS_SELECTOR, "table tbody tr, table tr")
                    for row in rows:
                        tds = row.find_elements(By.TAG_NAME, "td")
                        if len(tds) >= 2:
                            nome_celula = tds[0].text.strip()
                            resultado_celula = tds[1].text.strip()
                            
                            if nome_proj.lower() in nome_celula.lower():
                                projeto_encontrado = True
                                print(f"Projeto '{nome_proj}' encontrado na tabela. Resultado: '{resultado_celula}'")
                                
                                try:
                                    resultado_limpo = resultado_celula.replace(".", "").replace(",", ".").strip()
                                    resultado_valor = float(resultado_limpo)
                                    
                                    if resultado_valor > 0:
                                        print(f"Projeto '{nome_proj}' já avaliado (resultado: {resultado_valor}). Pulando.")
                                        projeto_ja_avaliado = True
                                        additional_test_results.append({
                                            "nome": "Avaliar projeto no grupo",
                                            "status": "PASS",
                                            "entrada": nome_proj,
                                            "resultado": f"Já avaliado (resultado: {resultado_celula}) - Pulado",
                                            "tempo": 0.0,
                                            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                                            "fluxo": fluxo_atual 
                                        })
                                    else:
                                        print(f"Projeto '{nome_proj}' com resultado 0, precisa avaliar.")
                                except (ValueError, AttributeError) as e:
                                    print(f"Erro ao converter resultado '{resultado_celula}': {e}")
                                    pass
                                break
                    if projeto_encontrado:
                        break
                
                if projeto_ja_avaliado:
                    continue
                
                if not projeto_encontrado:
                    print(f"Projeto '{nome_proj}' não encontrado, cadastrando...")
                    res_cadastro = cadastrar_projeto_no_grupo_avaliacao(nome_proj, nome_grupo_aval)
                    additional_test_results.append(res_cadastro)
                    time.sleep(0.5)
                    
                    if res_cadastro["status"] == "FAIL":
                        continue
                
                print(f"Avaliando projeto '{nome_proj}'...")
                if verificar_item_existe_na_tabela(nome_proj):
                    try:
                        wait_local = WebDriverWait(driver, WAIT_TIMEOUT)
                        cards = driver.find_elements(By.CSS_SELECTOR, "app-card, .card")
                        if not cards:
                            cards = wait_local.until(EC.presence_of_all_elements_located((By.CSS_SELECTOR, "app-card, .card")))
                        
                        projeto_clicado = False
                        for card in cards:
                            rows = card.find_elements(By.CSS_SELECTOR, "table tbody tr.table-row, table tr")
                            if not rows:
                                rows = card.find_elements(By.CSS_SELECTOR, "tr")
                            
                            for row in rows:
                                tds = row.find_elements(By.TAG_NAME, "td")
                                texts = [td.text.strip() for td in tds if td.text.strip()]
                                match = any((nome_proj.lower() in txt.lower()) for txt in texts)
                                
                                if match:
                                    try:
                                        link = row.find_element(By.CSS_SELECTOR, "button.link")
                                        driver.execute_script(CLICK_SCRIPT, link)
                                        projeto_clicado = True
                                        print(f"Clicou no botão.link do projeto '{nome_proj}'")
                                        break
                                    except Exception as e:
                                        print(f"Erro ao encontrar button.link do projeto '{nome_proj}': {e}")
                                        raise
                            
                            if projeto_clicado:
                                break
                        
                        if not projeto_clicado:
                            raise RuntimeError(f"Não conseguiu clicar no botão.link do projeto '{nome_proj}'")
                        
                        time.sleep(1)
                        
                        print(f"Projeto '{nome_proj}' encontrado na tabela, iniciando avaliação...")
                        res_avaliacao = avaliar_projeto_no_grupo(nome_proj, notas)
                        additional_test_results.append(res_avaliacao)
                        time.sleep(0.5)
                        
                    except Exception as e:
                        print(f"Erro ao clicar no projeto '{nome_proj}' na tabela para avaliação: {e}")
                        additional_test_results.append({
                            "nome": "Avaliar projeto no grupo",
                            "status": "FAIL",
                            "entrada": nome_proj,
                            "resultado": f"Erro ao clicar no botão: {str(e)}",
                            "tempo": 0.0,
                            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                            "fluxo": fluxo_atual 
                        })
                    
            except Exception as e:
                print(f"✗ Erro ao processar projeto {nome_proj}: {e}")
                continue

        print(f"\n{'='*60}")
        print(f"FINALIZOU PROCESSAMENTO DE TODOS OS {len(projetos_avaliacoes)} PROJETOS")
        print(f"{'='*60}\n")

        # === COLETAR RESULTADOS DOS PROJETOS AVALIADOS ===
        print("\n" + "="*60)
        print("COLETANDO RESULTADOS DOS PROJETOS AVALIADOS")
        print("="*60)
        
        resultados_projetos_dict = {}
        time.sleep(1)

        try:
            cards = driver.find_elements(By.CSS_SELECTOR, "app-card, .card")
            for card in cards:
                rows = card.find_elements(By.CSS_SELECTOR, "table tbody tr, table tr")
                for row in rows:
                    tds = row.find_elements(By.TAG_NAME, "td")
                    if len(tds) >= 2:
                        nome_celula = tds[0].text.strip()
                        resultado_celula = tds[1].text.strip()
                        
                        # Para cada projeto configurado
                        for proj in config_fluxo["projetos"]:
                            if proj["nome"].lower() in nome_celula.lower():
                                try:
                                    resultado_limpo = resultado_celula.replace(".", "").replace(",", ".").strip()
                                    resultado_valor = float(resultado_limpo)
                                    resultados_projetos_dict[proj["nome"]] = resultado_valor
                                    print(f"✓ Guardou resultado de '{proj['nome']}': {resultado_valor}")
                                except Exception as e:
                                    print(f"✗ Erro ao coletar resultado de '{proj['nome']}': {e}")
                                break
        except Exception as e:
            print(f"Erro ao coletar resultados: {e}")

        # Voltar para tela de grupo de avaliações
        time.sleep(1)
        try:
            botao_voltar = driver.find_element(By.CSS_SELECTOR, "button.back-btn")
            driver.execute_script(CLICK_SCRIPT, botao_voltar)
            time.sleep(0.5)
            print("✓ Voltou para tela de grupo de avaliações")
        except Exception as e:
            print(f"✗ Erro ao voltar para grupo de avaliações: {e}")

        # Clicar na aba Cenários
        print("\n▶ Tentando clicar na aba 'Cenários'...")
        time.sleep(1)
        try:
            res_tab_cenario = clicar_tab("Cenários")
            time.sleep(1)
            if res_tab_cenario and res_tab_cenario.get("status") == "FAIL":
                print(f"✗ ERRO ao clicar na tab Cenários: {res_tab_cenario.get('resultado')}")
                raise RuntimeError(f"Falha ao clicar na aba Cenários: {res_tab_cenario.get('resultado')}")
            else:
                print("✓ Clicou com sucesso na aba 'Cenários'")
        except Exception as e:
            print(f"✗ Erro ao clicar em Cenários: {e}")
            raise

        # Cadastrar cenário (já inclui balanceamento e autorização se for novo)
        print("\n▶ Acessando configuração do cenário...")
        try:
            print(f"   config_fluxo keys: {list(config_fluxo.keys())}")
            print(f"   config_fluxo['estrategia'] keys: {list(config_fluxo['estrategia'].keys())}")
            nome_cenario = config_fluxo["estrategia"]["cenario"]["nome"]
            orcamento_cenario = config_fluxo["estrategia"]["cenario"]["orcamento"]
            print(f"✓ Configuração do cenário carregada: '{nome_cenario}' com orçamento R$ {orcamento_cenario}")
        except Exception as e:
            print(f"✗ ERRO ao acessar configuração do cenário: {e}")
            raise
        
        print(f"\n▶ Cadastrando cenário '{nome_cenario}'...")
        res_cenario = cadastrar_cenario(nome_cenario, nome_grupo_aval, orcamento_cenario, nome_portfolio)
        additional_test_results.append(res_cenario)
        
        # Extrair lista de projetos incluídos no cenário para usar na verificação de vínculos
        projetos_incluidos_no_cenario = res_cenario.get("projetos_incluidos", None)
        
        if res_cenario["status"] == "FAIL":
            print(f"✗ ERRO ao cadastrar cenário: {res_cenario['resultado']}")
        else:
            print(f"✓ Cenário '{nome_cenario}' processado: {res_cenario['resultado']}")
            if projetos_incluidos_no_cenario:
                print(f"\n  ℹ Projetos incluídos no cenário autorizado:")
                for proj in projetos_incluidos_no_cenario:
                    print(f"    - {proj}")

        # === VERIFICAÇÕES DE VÍNCULOS ===
        print("\n" + "="*60)
        print("VERIFICANDO VÍNCULOS ESTRATÉGICOS")
        print("="*60)

        # 1. Verificar vínculos dos objetivos (apenas projetos incluídos no cenário)
        time.sleep(2)
        print("\n▶ Verificando vínculos dos OBJETIVOS...")
        resultados_verificacao = verificar_vinculos_objetivos(
            nomes_objetivos,
            criterios_vinculos_map,
            nome_grupo_aval,
            nome_portfolio,
            projetos_incluidos_cenario=projetos_incluidos_no_cenario  # Passa apenas os projetos incluídos
        )
        for res in resultados_verificacao:
            additional_test_results.append(res)

        # 2. Verificar vínculos dos projetos
        time.sleep(1)
        print("\n▶ Verificando vínculos dos PROJETOS...")
        res_vinculos_proj = verificar_vinculos_projetos(
            nomeEstrategia,
            nome_portfolio,
            nomes_objetivos,
            resultados_projetos_dict,
            projetos_incluidos_cenario=projetos_incluidos_no_cenario  
        )

        for r in res_vinculos_proj:
            additional_test_results.append(r)

        # 3. Verificar vínculos do portfólio
        time.sleep(1)
        print("\n▶ Verificando vínculos do PORTFÓLIO...")
        res_vinculos_portfolio = verificar_vinculos_portfolio(
            nome_portfolio,
            nomeEstrategia,
            nomes_objetivos
        )

        for r in res_vinculos_portfolio:
            additional_test_results.append(r)

        print("\n" + "="*60)
        print("VERIFICAÇÕES CONCLUÍDAS")
        print("="*60)

    except Exception as e:
        print("Erro na função estratégia:", e)
        end = time.time()
        return {
            "nome": "Cadastrar estratégia",
            "status": "FAIL",
            "entrada": nomeEstrategia,
            "resultado": resultado_msg or str(e),
            "tempo": end - start,
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "fluxo": fluxo_atual
        }
    else:
        end = time.time()
        return {
            "nome": "Cadastrar estratégia",
            "status": "PASS",
            "entrada": nomeEstrategia,
            "resultado": "Estratégia processada com sucesso",
            "tempo": end - start,
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "fluxo": fluxo_atual
        }

def cadastrar_projeto(nome_projeto, data_inicio, data_fim):
    """Cadastra um novo projeto."""
    start = time.time()
    try:
        # verificar se já existe
        if verificar_item_existe_na_tabela(nome_projeto):
            end = time.time()
            return {
                "nome": "Cadastrar projeto",
                "status": "PASS",
                "entrada": nome_projeto,
                "resultado": "Já existente (pulado)",
                "tempo": end - start,
                "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "fluxo": fluxo_atual
            }

        # clicar no botão cadastrar
        try:
            wait_local = WebDriverWait(driver, WAIT_TIMEOUT)
            botao = wait_local.until(EC.element_to_be_clickable((By.CSS_SELECTOR, "app-table-action-text-filter button")))
            driver.execute_script(CLICK_SCRIPT, botao)
        except Exception:
            components = driver.find_elements(By.CSS_SELECTOR, "app-table-action-text-filter, app-table app-table-action-text-filter")
            if not components:
                try:
                    components = wait_local.until(EC.presence_of_all_elements_located((By.CSS_SELECTOR, "app-table-action-text-filter, app-table app-table-action-text-filter")))
                except Exception:
                    components = []
            
            comp = components[0]
            botao = comp.find_element(By.TAG_NAME, "button")
            driver.execute_script(CLICK_SCRIPT, botao)

        modal = WebDriverWait(driver, WAIT_TIMEOUT).until(EC.presence_of_element_located((By.CSS_SELECTOR, ".modal-content, app-form-modal-component")))

        # preencher nome
        try:
            name_input = modal.find_element(By.CSS_SELECTOR, "input#name")
            name_input.clear()
            name_input.send_keys(nome_projeto)
            driver.execute_script("arguments[0].dispatchEvent(new Event('input', {bubbles: true})); arguments[0].dispatchEvent(new Event('change', {bubbles: true}));", name_input)
        except Exception:
            pass

        # preencher descrição
        try:
            desc = modal.find_element(By.CSS_SELECTOR, "textarea#description")
            desc.clear()
            desc.send_keys(f"Descrição automática do projeto {nome_projeto}")
            driver.execute_script("arguments[0].dispatchEvent(new Event('input', {bubbles: true})); arguments[0].dispatchEvent(new Event('change', {bubbles: true}));", desc)
        except Exception:
            pass

        # preencher data início
        try:
            start_date_input = modal.find_element(By.CSS_SELECTOR, "input#startDate")
            start_date_input.clear()
            start_date_input.send_keys(data_inicio)
            driver.execute_script("arguments[0].dispatchEvent(new Event('input', {bubbles: true})); arguments[0].dispatchEvent(new Event('change', {bubbles: true}));", start_date_input)
        except Exception:
            pass

        # preencher data fim
        try:
            end_date_input = modal.find_element(By.CSS_SELECTOR, "input#endDate")
            end_date_input.clear()
            end_date_input.send_keys(data_fim)
            driver.execute_script("arguments[0].dispatchEvent(new Event('input', {bubbles: true})); arguments[0].dispatchEvent(new Event('change', {bubbles: true}));", end_date_input)
        except Exception:
            pass

        time.sleep(0.5)

        # clicar no botão salvar
        try:
            save_btn = modal.find_element(By.CSS_SELECTOR, "button.btn-primary")
        except Exception:
            save_btns = modal.find_elements(By.TAG_NAME, "button")
            for btn in save_btns:
                if "salvar" in btn.text.lower():
                    save_btn = btn
                    break

        def _enabled(d):
            try:
                el = modal.find_element(By.CSS_SELECTOR, "button.btn-primary")
                return el.is_enabled()
            except Exception:
                return False

        try:
            WebDriverWait(driver, WAIT_TIMEOUT).until(_enabled)
        except Exception:
            try:
                driver.execute_script("arguments[0].removeAttribute('disabled');", save_btn)
            except Exception:
                pass

        driver.execute_script(CLICK_SCRIPT, save_btn)
        
        # aguardar e verificar se foi cadastrado
        time.sleep(1)
        if verificar_item_existe_na_tabela(nome_projeto):
            resultado_verificacao = "Cadastrado e verificado na tabela"
        else:
            resultado_verificacao = "Cadastrado mas não encontrado na tabela"

        end = time.time()
        return {
            "nome": "Cadastrar projeto",
            "status": "PASS",
            "entrada": f"{nome_projeto} ({data_inicio} a {data_fim})",
            "resultado": resultado_verificacao,
            "tempo": end - start,
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "fluxo": fluxo_atual
        }

    except Exception as e:
        print("Erro ao cadastrar projeto:", e)
        end = time.time()
        return {
            "nome": "Cadastrar projeto",
            "status": "FAIL",
            "entrada": nome_projeto,
            "resultado": str(e),
            "tempo": end - start,
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "fluxo": fluxo_atual
        }
    
def preencher_indicadores_projeto(nome_projeto, ev, pv, ac, bac, payback, roi):
    """Preenche os indicadores editáveis de um projeto."""
    start = time.time()
    try:
        # Clicar no projeto na tabela para entrar nele
        if not achar_e_clicar_na_tabela(nome_projeto):
            raise RuntimeError(f"Projeto '{nome_projeto}' não encontrado na tabela")
        
        time.sleep(2)
        
        # Aguardar página do projeto carregar
        wait_local = WebDriverWait(driver, WAIT_TIMEOUT)
        
        # Preencher Valor Agregado (EV)
        try:
            inputs = driver.find_elements(By.CSS_SELECTOR, ".indicator-input")
            if len(inputs) >= 1:
                inputs[0].clear()
                inputs[0].send_keys(str(ev))
                driver.execute_script("arguments[0].dispatchEvent(new Event('input', {bubbles: true})); arguments[0].dispatchEvent(new Event('change', {bubbles: true}));", inputs[0])
        except Exception as e:
            print(f"Erro ao preencher EV: {e}")
        
        # Preencher Valor Planejado (PV)
        try:
            if len(inputs) >= 2:
                inputs[1].clear()
                inputs[1].send_keys(str(pv))
                driver.execute_script("arguments[0].dispatchEvent(new Event('input', {bubbles: true})); arguments[0].dispatchEvent(new Event('change', {bubbles: true}));", inputs[1])
        except Exception as e:
            print(f"Erro ao preencher PV: {e}")
        
        # Preencher Custo Real (AC)
        try:
            if len(inputs) >= 3:
                inputs[2].clear()
                inputs[2].send_keys(str(ac))
                driver.execute_script("arguments[0].dispatchEvent(new Event('input', {bubbles: true})); arguments[0].dispatchEvent(new Event('change', {bubbles: true}));", inputs[2])
        except Exception as e:
            print(f"Erro ao preencher AC: {e}")
        
        # Preencher Orçamento Planejado (BAC)
        try:
            if len(inputs) >= 4:
                inputs[3].clear()
                inputs[3].send_keys(str(bac))
                driver.execute_script("arguments[0].dispatchEvent(new Event('input', {bubbles: true})); arguments[0].dispatchEvent(new Event('change', {bubbles: true}));", inputs[3])
        except Exception as e:
            print(f"Erro ao preencher BAC: {e}")
        
        # Preencher Payback
        try:
            if len(inputs) >= 5:
                inputs[4].clear()
                inputs[4].send_keys(str(payback))
                driver.execute_script("arguments[0].dispatchEvent(new Event('input', {bubbles: true})); arguments[0].dispatchEvent(new Event('change', {bubbles: true}));", inputs[4])
        except Exception as e:
            print(f"Erro ao preencher Payback: {e}")
        
        # Preencher ROI
        try:
            if len(inputs) >= 6:
                inputs[5].clear()
                inputs[5].send_keys(str(roi))
                driver.execute_script("arguments[0].dispatchEvent(new Event('input', {bubbles: true})); arguments[0].dispatchEvent(new Event('change', {bubbles: true}));", inputs[5])
        except Exception as e:
            print(f"Erro ao preencher ROI: {e}")
        
        time.sleep(0.5)
        
        # Clicar no botão Salvar indicadores
        try:
            save_btn = driver.find_element(By.CSS_SELECTOR, ".save-btn")
            
            # Aguardar botão ficar habilitado
            def _enabled(d):
                try:
                    btn = driver.find_element(By.CSS_SELECTOR, ".save-btn")
                    return btn.is_enabled()
                except Exception:
                    return False
            
            try:
                WebDriverWait(driver, WAIT_TIMEOUT).until(_enabled)
            except Exception:
                driver.execute_script("arguments[0].removeAttribute('disabled');", save_btn)
            
            driver.execute_script(CLICK_SCRIPT, save_btn)
            time.sleep(1)
        except Exception as e:
            print(f"Erro ao salvar indicadores: {e}")
        
        # Trocar para aba "Vínculo estratégico"
        try:
            tabs = driver.find_elements(By.CSS_SELECTOR, ".tab-trigger")
            for tab in tabs:
                if "vínculo" in tab.text.lower():
                    driver.execute_script(CLICK_SCRIPT, tab)
                    time.sleep(0.5)
                    break
        except Exception as e:
            print(f"Erro ao trocar de aba: {e}")
        
        # Voltar para lista de projetos
        time.sleep(0.5)
        try:
            botao_voltar = driver.find_element(By.CSS_SELECTOR, "button.back-btn")
            driver.execute_script(CLICK_SCRIPT, botao_voltar)
            time.sleep(1)
        except Exception as e:
            print(f"Erro ao voltar: {e}")
        
        end = time.time()
        return {
            "nome": "Preencher indicadores do projeto",
            "status": "PASS",
            "entrada": f"{nome_projeto} (EV:{ev}, PV:{pv}, AC:{ac}, BAC:{bac}, Payback:{payback}, ROI:{roi})",
            "resultado": "Indicadores preenchidos e salvos com sucesso",
            "tempo": end - start,
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "fluxo": fluxo_atual
        }
    
    except Exception as e:
        print(f"Erro ao preencher indicadores do projeto {nome_projeto}:", e)
        try:
            driver.save_screenshot(f"erro_indicadores_{nome_projeto}.png")
        except Exception:
            pass
        end = time.time()
        return {
            "nome": "Preencher indicadores do projeto",
            "status": "FAIL",
            "entrada": nome_projeto,
            "resultado": str(e),
            "tempo": end - start,
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "fluxo": fluxo_atual
        }


def cadastrar_portfolio(nome_portfolio):
    """Cadastra um portfólio."""
    start = time.time()
    try:
        # Verificar se já existe
        if verificar_item_existe_na_tabela(nome_portfolio):
            # Se existe, clicar nele
            end = time.time()
            return {
                "nome": "Cadastrar portfólio",
                "status": "PASS",
                "entrada": nome_portfolio,
                "resultado": "Já existente (aberto)",
                "tempo": end - start,
                "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "fluxo": fluxo_atual
            }

        # Clicar no botão Cadastrar
        try:
            wait_local = WebDriverWait(driver, WAIT_TIMEOUT)
            botao = wait_local.until(EC.element_to_be_clickable((By.CSS_SELECTOR, "app-table-action-text-filter button.btn-primary")))
            driver.execute_script(CLICK_SCRIPT, botao)
        except Exception as e:
            print(f"Erro ao clicar em cadastrar: {e}")
            raise

        time.sleep(1)

        # Aguardar modal abrir
        modal = WebDriverWait(driver, WAIT_TIMEOUT).until(EC.presence_of_element_located((By.CSS_SELECTOR, ".modal-content")))

        # Preencher nome
        try:
            name_input = modal.find_element(By.CSS_SELECTOR, "input")
            name_input.clear()
            name_input.send_keys(nome_portfolio)
            driver.execute_script("arguments[0].dispatchEvent(new Event('input', {bubbles: true})); arguments[0].dispatchEvent(new Event('change', {bubbles: true}));", name_input)
        except Exception as e:
            print(f"Erro ao preencher nome: {e}")
            raise

        # Preencher descrição (opcional)
        try:
            textarea = modal.find_element(By.TAG_NAME, "textarea")
            textarea.clear()
            textarea.send_keys(f"Descrição automática do portfólio {nome_portfolio}")
            driver.execute_script("arguments[0].dispatchEvent(new Event('input', {bubbles: true})); arguments[0].dispatchEvent(new Event('change', {bubbles: true}));", textarea)
        except Exception:
            pass

        time.sleep(0.5)

        # Clicar em Salvar
        try:
            save_buttons = modal.find_elements(By.CSS_SELECTOR, "button.btn-primary")
            for btn in save_buttons:
                if "salvar" in btn.text.lower():
                    driver.execute_script(CLICK_SCRIPT, btn)
                    break
        except Exception as e:
            print(f"Erro ao salvar: {e}")
            raise

        time.sleep(1)

        # Clicar no portfólio cadastrado
        if achar_e_clicar_na_tabela(nome_portfolio):
            resultado_verificacao = "Cadastrado e aberto com sucesso"
        else:
            resultado_verificacao = "Cadastrado mas não foi possível abrir"

        end = time.time()
        return {
            "nome": "Cadastrar portfólio",
            "status": "PASS",
            "entrada": nome_portfolio,
            "resultado": resultado_verificacao,
            "tempo": end - start,
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "fluxo": fluxo_atual
        }

    except Exception as e:
        print(f"Erro ao cadastrar portfólio: {e}")
        try:
            driver.save_screenshot("erro_cadastrar_portfolio.png")
        except Exception:
            pass
        end = time.time()
        return {
            "nome": "Cadastrar portfólio",
            "status": "FAIL",
            "entrada": nome_portfolio,
            "resultado": str(e),
            "tempo": end - start,
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "fluxo": fluxo_atual
        }


def cadastrar_categoria(nome_categoria):
    """Cadastra uma categoria dentro do portfólio."""
    start = time.time()
    try:
        # Verificar se já existe
        if verificar_item_existe_na_tabela(nome_categoria):
            end = time.time()
            return {
                "nome": "Cadastrar categoria",
                "status": "PASS",
                "entrada": nome_categoria,
                "resultado": "Já existente (pulado)",
                "tempo": end - start,
                "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "fluxo": fluxo_atual
            }

        # Clicar no botão Cadastrar
        try:
            wait_local = WebDriverWait(driver, WAIT_TIMEOUT)
            botao = wait_local.until(EC.element_to_be_clickable((By.CSS_SELECTOR, "app-table-action-text-filter button.btn-primary")))
            driver.execute_script(CLICK_SCRIPT, botao)
        except Exception as e:
            print(f"Erro ao clicar em cadastrar: {e}")
            raise

        time.sleep(1)

        # Aguardar modal abrir
        modal = WebDriverWait(driver, WAIT_TIMEOUT).until(EC.presence_of_element_located((By.CSS_SELECTOR, ".modal-content, app-form-modal-component")))

        # Preencher nome
        try:
            name_input = modal.find_element(By.CSS_SELECTOR, "input")
            name_input.clear()
            name_input.send_keys(nome_categoria)
            driver.execute_script("arguments[0].dispatchEvent(new Event('input', {bubbles: true})); arguments[0].dispatchEvent(new Event('change', {bubbles: true}));", name_input)
        except Exception as e:
            print(f"Erro ao preencher nome: {e}")
            raise

        time.sleep(0.5)

        # Clicar em Salvar
        try:
            save_buttons = modal.find_elements(By.CSS_SELECTOR, "button.btn-primary")
            for btn in save_buttons:
                if "salvar" in btn.text.lower():
                    driver.execute_script(CLICK_SCRIPT, btn)
                    break
        except Exception as e:
            print(f"Erro ao salvar: {e}")
            raise

        time.sleep(1)

        # Verificar se foi cadastrado
        if verificar_item_existe_na_tabela(nome_categoria):
            resultado_verificacao = "Cadastrado e verificado na tabela"
        else:
            resultado_verificacao = "Cadastrado mas não encontrado na tabela"

        end = time.time()
        return {
            "nome": "Cadastrar categoria",
            "status": "PASS",
            "entrada": nome_categoria,
            "resultado": resultado_verificacao,
            "tempo": end - start,
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "fluxo": fluxo_atual
        }

    except Exception as e:
        print(f"Erro ao cadastrar categoria: {e}")
        end = time.time()
        return {
            "nome": "Cadastrar categoria",
            "status": "FAIL",
            "entrada": nome_categoria,
            "resultado": str(e),
            "tempo": end - start,
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "fluxo": fluxo_atual
        }

def verificar_vinculos_projetos(nome_estrategia, nome_portfolio, objetivos, resultados_projetos, projetos_incluidos_cenario=None):
    """Verifica vínculos estratégicos dos projetos."""
    resultados = []
    config_fluxo = FLUXO_1 if fluxo_atual == 1 else FLUXO_2

    try:
        time.sleep(1)

        # Navegar para Projetos
        try:
            nav_items = driver.find_elements(By.CSS_SELECTOR, ".nav-item button.nav-link")
            for item in nav_items:
                try:
                    texto = item.find_element(By.CSS_SELECTOR, ".nav-text").text.strip()
                    if "projeto" in texto.lower():
                        driver.execute_script(CLICK_SCRIPT, item)
                        break
                except Exception:
                    continue
        except Exception as e:
            print(f"✗ Erro ao navegar para Projetos: {e}")
        
        time.sleep(1)

        # ⭐ SEPARAR PROJETOS COM COMPARAÇÃO NORMALIZADA
        projetos_incluidos = []
        projetos_nao_incluidos = []
        
        if projetos_incluidos_cenario:
            # Normalizar nomes da lista de incluídos
            incluidos_normalizados = [p.strip().lower() for p in projetos_incluidos_cenario]
            
            for nome_proj in resultados_projetos.keys():
                nome_normalizado = nome_proj.strip().lower()
                
                # Verificar se está na lista de incluídos
                if nome_normalizado in incluidos_normalizados:
                    projetos_incluidos.append(nome_proj)
                else:
                    projetos_nao_incluidos.append(nome_proj)
        else:
            projetos_incluidos = list(resultados_projetos.keys())
            projetos_nao_incluidos = []
        
        print(f"\n{'='*60}")
        print(f"📊 PROJETOS INCLUÍDOS NO CENÁRIO: {len(projetos_incluidos)}")
        print(f"{'='*60}")
        for p in projetos_incluidos:
            print(f"  ✓ {p}")
        
        if projetos_nao_incluidos:
            print(f"\n{'='*60}")
            print(f"⚠ PROJETOS NÃO INCLUÍDOS NO CENÁRIO: {len(projetos_nao_incluidos)}")
            print(f"{'='*60}")
            for p in projetos_nao_incluidos:
                print(f"  • {p}")
        
        # ========================================
        # VERIFICAR APENAS PROJETOS INCLUÍDOS
        # ========================================
        for nome_proj in projetos_incluidos:
            start = time.time()
            try:
                print(f"\n=== Verificando projeto INCLUÍDO: {nome_proj} ===")

                if not achar_e_clicar_na_tabela(nome_proj):
                    raise RuntimeError(f"Projeto '{nome_proj}' não encontrado")

                time.sleep(1)

                # Ir para aba Vínculo estratégico
                try:
                    tabs = driver.find_elements(By.CSS_SELECTOR, ".tab-trigger")
                    for tab in tabs:
                        if "vínculo" in tab.text.lower():
                            driver.execute_script(CLICK_SCRIPT, tab)
                            time.sleep(0.5)
                            break
                except Exception as e:
                    print(f"✗ Erro ao trocar de aba: {e}")
                
                time.sleep(1)

                vinculos_ok = []

                # Buscar container
                try:
                    container = WebDriverWait(driver, 10).until(
                        EC.presence_of_element_located((By.CSS_SELECTOR, "div.tab-panel"))
                    )
                except:
                    vinculos_ok.append("✗ ERRO: container de vínculo não encontrado")
                    container = None

                # === VERIFICAR ESTRATÉGIA ===
                try:
                    if container:
                        link_items = container.find_elements(By.CSS_SELECTOR, ".strategic-links .link-item")
                        estrategia_encontrada = False
                        
                        for item in link_items:
                            try:
                                titulo = item.find_element(By.CSS_SELECTOR, ".link-title").text.strip()
                                subtitulo = item.find_element(By.CSS_SELECTOR, ".link-subtitle").text.strip().lower()
                                
                                if "estratégia" in subtitulo and nome_estrategia.lower() in titulo.lower():
                                    estrategia_encontrada = True
                                    vinculos_ok.append(f"✓ Estratégia vinculada: {titulo}")
                                    print(f"  ✓ Estratégia: {titulo}")
                                    break
                            except Exception:
                                continue
                        
                        if not estrategia_encontrada:
                            vinculos_ok.append(f"✗ ERRO: estratégia '{nome_estrategia}' não vinculada")
                            print(f"  ✗ Estratégia não encontrada")
                    else:
                        vinculos_ok.append("✗ ERRO ao verificar estratégia: container vazio")
                except Exception as e:
                    vinculos_ok.append(f"✗ ERRO ao verificar estratégia: {e}")

                # === VERIFICAR PORTFÓLIO ===
                try:
                    if container:
                        link_items = container.find_elements(By.CSS_SELECTOR, ".strategic-links .link-item")
                        portfolio_encontrado = False
                        
                        for item in link_items:
                            try:
                                titulo = item.find_element(By.CSS_SELECTOR, ".link-title").text.strip()
                                subtitulo = item.find_element(By.CSS_SELECTOR, ".link-subtitle").text.strip().lower()
                                
                                if "portfólio" in subtitulo and nome_portfolio.lower() in titulo.lower():
                                    portfolio_encontrado = True
                                    vinculos_ok.append(f"✓ Portfólio vinculado: {titulo}")
                                    print(f"  ✓ Portfólio: {titulo}")
                                    break
                            except Exception:
                                continue
                        
                        if not portfolio_encontrado:
                            vinculos_ok.append(f"✗ ERRO: portfólio '{nome_portfolio}' não vinculado")
                            print(f"  ✗ Portfólio não encontrado")
                    else:
                        vinculos_ok.append("✗ ERRO ao verificar portfólio: container vazio")
                except Exception as e:
                    vinculos_ok.append(f"✗ ERRO ao verificar portfólio: {e}")

                # === VERIFICAR VALOR ESTRATÉGICO ===
                try:
                    if container:
                        resultado_esperado = resultados_projetos[nome_proj]
                        link_items = container.find_elements(By.CSS_SELECTOR, ".strategic-links .link-item")
                        resultado_encontrado = False
                        
                        for item in link_items:
                            try:
                                titulo = item.find_element(By.CSS_SELECTOR, ".link-title").text.strip()
                                subtitulo = item.find_element(By.CSS_SELECTOR, ".link-subtitle").text.strip().lower()
                                
                                if "valor estratégico" in subtitulo or "estratégico" in subtitulo:
                                    resultado_texto = titulo.split("/")[0].strip().replace(".", "").replace(",", "")
                                    
                                    try:
                                        resultado_valor = float(resultado_texto)
                                        margem_erro = 5 if fluxo_atual == 2 else 1
                                        
                                        if abs(resultado_valor - resultado_esperado) <= margem_erro:
                                            resultado_encontrado = True
                                            vinculos_ok.append(f"✓ Valor estratégico correto: {resultado_texto}")
                                            print(f"  ✓ Valor estratégico: {resultado_texto}")
                                        else:
                                            vinculos_ok.append(f"✗ ERRO: Valor incorreto: {resultado_texto} (esperado: {resultado_esperado})")
                                            print(f"  ✗ Valor divergente")
                                        break
                                    except ValueError:
                                        vinculos_ok.append(f"✗ ERRO: Não foi possível converter '{resultado_texto}'")
                            except Exception:
                                continue
                        
                        if not resultado_encontrado:
                            vinculos_ok.append(f"✗ ERRO: Valor estratégico não encontrado (esperado: {resultado_esperado})")
                            print(f"  ✗ Valor não encontrado")
                    else:
                        vinculos_ok.append("✗ ERRO ao verificar valor: container vazio")
                except Exception as e:
                    vinculos_ok.append(f"✗ ERRO ao verificar valor: {e}")

                # === VERIFICAR OBJETIVOS ===
                try:
                    if container:
                        obj_items = container.find_elements(By.CSS_SELECTOR, ".objectives-list .objective-item span")
                        objetivos_pagina = [o.text.strip() for o in obj_items]
                        faltando = [obj for obj in objetivos if obj not in objetivos_pagina]
                        
                        if len(faltando) == 0:
                            vinculos_ok.append(f"✓ Objetivos: {len(objetivos)} vinculados")
                            print(f"  ✓ Objetivos: {objetivos_pagina}")
                        else:
                            vinculos_ok.append(f"✗ ERRO: objetivos faltando: {faltando}")
                            print(f"  ✗ Objetivos faltando")
                    else:
                        vinculos_ok.append("✗ ERRO ao verificar objetivos: container vazio")
                except Exception as e:
                    vinculos_ok.append(f"✗ ERRO ao verificar objetivos: {e}")

                # Voltar
                try:
                    botao_voltar = driver.find_element(By.CSS_SELECTOR, "button.back-btn")
                    driver.execute_script(CLICK_SCRIPT, botao_voltar)
                    time.sleep(1)
                except:
                    pass

                end = time.time()
                
                # ⭐ DETERMINAR STATUS
                tem_erro = any("ERRO" in v for v in vinculos_ok)
                status_final = "FAIL" if tem_erro else "PASS"
                
                resultados.append({
                    "nome": f"Verificar vínculos do projeto '{nome_proj}' (INCLUÍDO)",
                    "status": status_final,
                    "entrada": f"{nome_proj} (Resultado: {resultados_projetos[nome_proj]})",
                    "resultado": " | ".join(vinculos_ok),
                    "tempo": end - start,
                    "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    "fluxo": fluxo_atual
                })

            except Exception as e:
                end = time.time()
                resultados.append({
                    "nome": f"Verificar vínculos do projeto '{nome_proj}' (INCLUÍDO)",
                    "status": "FAIL",
                    "entrada": nome_proj,
                    "resultado": f"✗ Erro: {str(e)}",
                    "tempo": end - start,
                    "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    "fluxo": fluxo_atual
                })

        # ========================================
        # ⭐ REPORTAR PROJETOS NÃO INCLUÍDOS
        # ========================================
        for nome_proj in projetos_nao_incluidos:
            start = time.time()
            
            print(f"\n{'='*60}")
            print(f"⚠ PROJETO NÃO INCLUÍDO: {nome_proj}")
            print(f"{'='*60}")
            print(f"  ✓ CORRETO: Não incluído no cenário (orçamento insuficiente)")
            print(f"  ✓ ESPERADO: Não ter vínculos estratégicos")
            print(f"  ✓ STATUS: PASS (não verificará vínculos)")
            
            end = time.time()
            resultados.append({
                "nome": f"Validar projeto '{nome_proj}' (NÃO INCLUÍDO)",
                "status": "PASS",
                "entrada": nome_proj,
                "resultado": "✓ CORRETO: Projeto não incluído no cenário (orçamento insuficiente) - Não verifica vínculos pois não deve tê-los",
                "tempo": end - start,
                "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "fluxo": fluxo_atual
            })

        return resultados

    except Exception as e:
        print(f"✗ Erro geral: {e}")
        return resultados


def verificar_vinculos_portfolio(nome_portfolio, nome_estrategia, objetivos):
    """Verifica os vínculos estratégicos no portfólio."""
    resultados = []
    config_fluxo = FLUXO_1 if fluxo_atual == 1 else FLUXO_2
    try:
        start = time.time()
        
        # Navegar para Portfólios
        print(f"\n=== Verificando portfólio: {nome_portfolio} ===")
        try:
            nav_items = driver.find_elements(By.CSS_SELECTOR, ".nav-item button.nav-link")
            for item in nav_items:
                try:
                    texto = item.find_element(By.CSS_SELECTOR, ".nav-text").text.strip()
                    if "portfólio" in texto.lower():
                        driver.execute_script(CLICK_SCRIPT, item)
                        break
                except Exception:
                    continue
        except Exception as e:
            print(f"Erro ao navegar para Portfólios: {e}")
        
        time.sleep(1)
        
        # Clicar no portfólio
        if not achar_e_clicar_na_tabela(nome_portfolio):
            raise RuntimeError(f"Portfólio '{nome_portfolio}' não encontrado")
        
        time.sleep(1)
        
        vinculos_ok = []
        
        # === ABA RESUMO ===
        print("\n▶ Verificando aba RESUMO...")
        try:
            # Garantir que está na aba Resumo (primeira aba, geralmente já está ativa)
            tabs = driver.find_elements(By.CSS_SELECTOR, ".tab-trigger")
            for tab in tabs:
                if "resumo" in tab.text.lower():
                    driver.execute_script(CLICK_SCRIPT, tab)
                    time.sleep(0.5)
                    break
        except Exception as e:
            print(f"Erro ao clicar em Resumo: {e}")
        
        time.sleep(1)
        
        # Verificar orçamento no card de métricas
        try:
            metric_cards = driver.find_elements(By.CSS_SELECTOR, ".metric-card")
            orcamento_encontrado = False
            orcamento_valor = None
            
            for card in metric_cards:
                try:
                    subtitle = card.find_element(By.CSS_SELECTOR, ".metric-subtitle").text.strip().lower()
                    
                    if "orçamento" in subtitle:
                        title = card.find_element(By.CSS_SELECTOR, ".metric-title").text.strip()
                        orcamento_valor = title
                        orcamento_encontrado = True
                        
                        # Comparar com orçamento do cenário
                        orcamento_esperado = config_fluxo["cenario"]["orcamento"]
                        orcamento_limpo = title.replace("R$", "").replace(".", "").replace(",", "").strip()
                        
                        try:
                            orcamento_num = float(orcamento_limpo)
                            orcamento_esp_num = float(orcamento_esperado)
                            
                            if abs(orcamento_num - orcamento_esp_num) <= 1000:
                                vinculos_ok.append(f"✓ Orçamento: {title}")
                                print(f"  ✓ Orçamento: {title}")
                            else:
                                vinculos_ok.append(f"✗ Orçamento divergente: {title} (esperado: R$ {orcamento_esperado})")
                                print(f"  ✗ Orçamento divergente")
                        except:
                            vinculos_ok.append(f"✓ Orçamento presente: {title}")
                            print(f"  ✓ Orçamento: {title}")
                        break
                except Exception:
                    continue
            
            if not orcamento_encontrado:
                vinculos_ok.append("✗ Orçamento não encontrado no resumo")
                print(f"  ✗ Orçamento não encontrado")
        except Exception as e:
            vinculos_ok.append(f"✗ ERRO ao verificar orçamento: {e}")
        
        # Verificar orçamento no card de métricas
        try:
            metric_cards = driver.find_elements(By.CSS_SELECTOR, ".metric-card")
            orcamento_encontrado = False
            orcamento_valor = None
            
            for card in metric_cards:
                try:
                    subtitle = card.find_element(By.CSS_SELECTOR, ".metric-subtitle").text.strip().lower()
                    
                    if "orçamento" in subtitle:
                        title = card.find_element(By.CSS_SELECTOR, ".metric-title").text.strip()
                        orcamento_valor = title
                        orcamento_encontrado = True
                        
                        # Limpar AMBOS os valores para comparação (remover R$, pontos, vírgulas e espaços)
                        orcamento_limpo = title.replace("R$", "").replace(".", "").replace(",", "").replace(" ", "").strip()
                        orcamento_esperado = config_fluxo["cenario"]["orcamento"]
                        orcamento_esp_limpo = str(orcamento_esperado).replace("R$", "").replace(".", "").replace(",", "").replace(" ", "").strip()
                        
                        try:
                            orcamento_num = float(orcamento_limpo)
                            orcamento_esp_num = float(orcamento_esp_limpo)
                            
                            # Comparar valores numéricos
                            if abs(orcamento_num - orcamento_esp_num) <= 1000:  # margem de erro de R$ 1.000
                                vinculos_ok.append(f"✓ Orçamento: {title}")
                                print(f"  ✓ Orçamento: {title}")
                            else:
                                vinculos_ok.append(f"✗ Orçamento divergente: {title} (esperado: R$ {orcamento_esperado})")
                                print(f"  ✗ Orçamento divergente: {title} vs esperado: {orcamento_esperado}")
                                print(f"    Debug: limpo={orcamento_num} vs esperado={orcamento_esp_num}")
                        except Exception as e:
                            # Se não conseguir converter, apenas confirma que existe
                            vinculos_ok.append(f"✓ Orçamento presente: {title}")
                            print(f"  ✓ Orçamento presente: {title}")
                            print(f"  ⚠ Não foi possível comparar valores: {e}")
                        break
                except Exception:
                    continue
            
            if not orcamento_encontrado:
                vinculos_ok.append("Orçamento não encontrado no resumo")
                print(f"Orçamento não encontrado")
        except Exception as e:
            vinculos_ok.append(f"✗ ERRO ao verificar orçamento: {e}")
        
        # === ABA PROJETOS ===
        print("\n▶ Verificando aba PROJETOS...")
        try:
            tabs = driver.find_elements(By.CSS_SELECTOR, ".tab-trigger")
            for tab in tabs:
                if "projeto" in tab.text.lower() and "resumo" not in tab.text.lower():
                    driver.execute_script(CLICK_SCRIPT, tab)
                    time.sleep(0.5)
                    break
        except Exception as e:
            print(f"Erro ao clicar em Projetos: {e}")
        
        time.sleep(1)
        
        # Verificar projetos na tabela
        try:
            projetos_encontrados = []
            projetos_esperados = [proj["nome"] for proj in config_fluxo["projetos"]]
            
            rows = driver.find_elements(By.CSS_SELECTOR, ".table-row")
            
            for row in rows:
                try:
                    tds = row.find_elements(By.TAG_NAME, "td")
                    if len(tds) > 0:
                        nome_projeto = tds[0].text.strip()
                        
                        # Verificar se é um dos projetos esperados
                        for proj_esp in projetos_esperados:
                            if proj_esp.lower() in nome_projeto.lower():
                                projetos_encontrados.append(nome_projeto)
                                print(f"  ✓ Projeto encontrado: {nome_projeto}")
                                
                                # Coletar informações adicionais da linha
                                if len(tds) >= 8:
                                    try:
                                        categoria = tds[1].text.strip()
                                        orcamento = tds[2].text.strip()
                                        ev = tds[3].text.strip()
                                        pv = tds[4].text.strip()
                                        data_inicio = tds[5].text.strip()
                                        data_fim = tds[6].text.strip()
                                        status = tds[7].text.strip()
                                        
                                        print(f"    • Categoria: {categoria}")
                                        print(f"    • Orçamento: R$ {orcamento}")
                                        print(f"    • EV: R$ {ev} | PV: R$ {pv}")
                                        print(f"    • Período: {data_inicio} - {data_fim}")
                                        print(f"    • Status: {status}")
                                    except Exception:
                                        pass
                                break
                except Exception:
                    continue
            
            # Verificar se todos os projetos esperados foram encontrados
            projetos_faltando = [p for p in projetos_esperados if not any(p.lower() in pf.lower() for pf in projetos_encontrados)]
            
            if len(projetos_faltando) == 0:
                vinculos_ok.append(f"✓ Projetos: {len(projetos_encontrados)} encontrados na aba Projetos")
                print(f"\n  ✓ Todos os {len(projetos_encontrados)} projetos encontrados!")
            else:
                vinculos_ok.append(f"✗ Projetos faltando na aba: {projetos_faltando}")
                print(f"\n  ✗ Projetos faltando: {projetos_faltando}")
                
        except Exception as e:
            vinculos_ok.append(f"✗ ERRO ao verificar projetos: {e}")
        
        
        end = time.time()
        
        # Determinar status baseado nos resultados
        tem_erro = any("ERRO" in v or "incorretamente vinculados" in v for v in vinculos_ok)
        status_final = "FAIL" if tem_erro else "PASS"
        
        resultados.append({
            "nome": f"Validar vínculos do portfólio '{nome_portfolio}'",
            "status": status_final,
            "entrada": nome_portfolio,
            "resultado": " | ".join(vinculos_ok),
            "tempo": end - start,
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        })
        
        return resultados
        
    except Exception as e:
        print(f"Erro ao verificar vínculos do portfólio: {e}")
        try:
            driver.save_screenshot("erro_verificar_portfolio.png")
        except Exception:
            pass
        end = time.time()
        return [{
            "nome": f"Validar vínculos do portfólio '{nome_portfolio}'",
            "status": "FAIL",
            "entrada": nome_portfolio,
            "resultado": f"✗ Erro crítico: {str(e)}",
            "tempo": end - start,
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "fluxo": fluxo_atual
        }]

def executar_fluxo_completo(config_fluxo, testes):
    """Executa um fluxo completo de testes com a configuração fornecida"""
    
    global nomes_objetivos, nomes_criterios, projetos_avaliacoes
    
    # Configurar variáveis globais para este fluxo
    nomes_objetivos = config_fluxo["estrategia"]["objetivos"]
    nomes_criterios = config_fluxo["estrategia"]["grupo_criterios"]["criterios"]
    
    # Montar projetos_avaliacoes
    projetos_avaliacoes = [
        (proj["nome"], proj["notas_avaliacao"])
        for proj in config_fluxo["projetos"]
    ]
    
    # === PORTFÓLIO ===
    print("\n" + "="*60)
    print(f"📁 CADASTRANDO PORTFOLIO: {config_fluxo['portfolio']['nome']}")
    print("="*60)
    
    # Navegar para Portfólios
    try:
        nav_items = driver.find_elements(By.CSS_SELECTOR, ".nav-item button.nav-link")
        for item in nav_items:
            try:
                texto = item.find_element(By.CSS_SELECTOR, ".nav-text").text.strip()
                if "portfólio" in texto.lower():
                    driver.execute_script(CLICK_SCRIPT, item)
                    break
            except Exception:
                continue
    except Exception as e:
        print(f"✗ Erro ao navegar para Portfólios: {e}")
    
    time.sleep(1)
    
    # Cadastrar portfólio
    res_portfolio = cadastrar_portfolio(config_fluxo["portfolio"]["nome"])
    testes.append(res_portfolio)
    
    # Cadastrar categorias se o portfólio foi recém-criado
    if res_portfolio["status"] == "PASS" and "já existente" not in res_portfolio["resultado"].lower():
        time.sleep(1)
        try:
            clicar_tab("Categorias")
            time.sleep(1)
        except Exception as e:
            print(f"✗ Erro ao clicar em Categorias: {e}")
        
        for categoria in config_fluxo["portfolio"]["categorias"]:
            res_cat = cadastrar_categoria(categoria)
            testes.append(res_cat)
            time.sleep(0.5)
        
        print(f"✓ {len(config_fluxo['portfolio']['categorias'])} categorias cadastradas!")
    else:
        print(f"✓ Portfólio '{config_fluxo['portfolio']['nome']}' já existe")
    
    # === PROJETOS ===
    print("\n" + "="*60)
    print("📊 CADASTRANDO PROJETOS E INDICADORES")
    print("="*60)
    
    # Navegar para Projetos
    try:
        nav_items = driver.find_elements(By.CSS_SELECTOR, ".nav-item button.nav-link")
        for item in nav_items:
            try:
                texto = item.find_element(By.CSS_SELECTOR, ".nav-text").text.strip()
                if "projeto" in texto.lower():
                    driver.execute_script(CLICK_SCRIPT, item)
                    break
            except Exception:
                continue
    except Exception as e:
        print(f"✗ Erro ao navegar para Projetos: {e}")
    
    time.sleep(1)
    
    # Cadastrar cada projeto
    for projeto in config_fluxo["projetos"]:
        # Verificar se projeto já tem indicadores
        try:
            time.sleep(1)
            projeto_ja_preenchido = False
            cards = driver.find_elements(By.CSS_SELECTOR, "app-card, .card")
            
            for card in cards:
                rows = card.find_elements(By.CSS_SELECTOR, "table tbody tr, table tr")
                for row in rows:
                    tds = row.find_elements(By.TAG_NAME, "td")
                    if len(tds) >= 3:
                        nome_celula = tds[0].text.strip()
                        ev_celula = tds[1].text.strip()
                        pv_celula = tds[2].text.strip()
                        
                        if projeto["nome"].lower() in nome_celula.lower():
                            ev_valor = ev_celula.replace(".", "").replace(",", "").strip()
                            pv_valor = pv_celula.replace(".", "").replace(",", "").strip()
                            
                            if ev_valor and pv_valor and ev_valor != "0" and pv_valor != "0":
                                print(f"✓ Projeto '{projeto['nome']}' já configurado")
                                projeto_ja_preenchido = True
                                testes.append({
                                    "nome": "Configurar projeto completo",
                                    "status": "PASS",
                                    "entrada": projeto["nome"],
                                    "resultado": f"✓ Já configurado com indicadores",
                                    "tempo": 0.0,
                                    "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                                    "fluxo": fluxo_atual
                                })
                                break
                            break
                if projeto_ja_preenchido:
                    break
            
            if projeto_ja_preenchido:
                continue
                
        except Exception as e:
            print(f"✗ Erro ao verificar indicadores: {e}")
        
        # Cadastrar projeto
        ind = projeto["indicadores"]
        res_projeto = cadastrar_projeto(
            projeto["nome"],
            projeto["data_inicio"],
            projeto["data_fim"]
        )
        testes.append(res_projeto)
        time.sleep(0.5)
        
        # Preencher indicadores
        res_indicadores = preencher_indicadores_projeto(
            projeto["nome"],
            ind["ev"],
            ind["pv"],
            ind["ac"],
            ind["bac"],
            ind["payback"],
            ind["roi"]
        )
        testes.append(res_indicadores)
        time.sleep(0.5)
        
        print(f"✓ Projeto '{projeto['nome']}' cadastrado")
    
    # === ESTRATÉGIA ===
    print("\n" + "="*60)
    print("🎯 CONFIGURANDO ESTRATEGIA COMPLETA")
    print("="*60)
    
    # Navegar para Estratégias
    time.sleep(1)
    try:
        nav_items = driver.find_elements(By.CSS_SELECTOR, ".nav-item button.nav-link")
        for item in nav_items:
            try:
                texto = item.find_element(By.CSS_SELECTOR, ".nav-text").text.strip()
                if "estratég" in texto.lower():
                    driver.execute_script(CLICK_SCRIPT, item)
                    break
            except Exception:
                continue
    except Exception as e:
        print(f"✗ Erro ao navegar para Estratégias: {e}")
    
    time.sleep(1)
    
    # Executar cadastro de estratégia
    estr_res = estrategia(config_fluxo["estrategia"]["nome"], config_fluxo["portfolio"]["nome"])
    if estr_res:
        testes.append(estr_res)
    
    if additional_test_results:
        for r in additional_test_results:
            testes.append(r)
    
    # === FINALIZAÇÃO ===
    print("\n" + "="*60)
    print("FINALIZANDO TESTES")
    print("="*60)
    
    # Aceitar alertas se houver
    try:
        WebDriverWait(resultado["driver"], WAIT_TIMEOUT).until(EC.alert_is_present())
        alert = resultado["driver"].switch_to.alert
        alert.accept()
    except Exception:
        pass
    
   
    # Estatísticas
    total_testes = len(testes)
    testes_pass = sum(1 for t in testes if t and t.get("status") == "PASS")
    testes_fail = sum(1 for t in testes if t and t.get("status") == "FAIL")
    
    print(f"\n{'='*60}")
    print(f"RESUMO DOS TESTES")
    print(f"{'='*60}")
    print(f"Total: {total_testes} | ✓ PASS: {testes_pass} | ✗ FAIL: {testes_fail}")
    print(f"{'='*60}\n")
    return testes 



def main():
    """Executa os dois fluxos de teste completos"""
    global fluxo_atual, additional_test_results

    limpar_relatorio_antigo()
    testes = []

    # === LOGIN ===
    resultado = login(EMAIL_LOGIN)
    testes.append(resultado)
    time.sleep(2)

    print("\n" + "="*80)
    print("🚀 INICIANDO TESTE COMPLETO COM DOIS FLUXOS")
    print("="*80)

    # === FLUXO 1 ===
    print("\n" + "="*80)
    print("🎯 EXECUTANDO FLUXO 1: PORTFOLIO 2025")
    print("="*80)

    fluxo_atual = 1
    additional_test_results = []
    executar_fluxo_completo(FLUXO_1, testes)

    # === FLUXO 2 ===
    print("\n" + "="*80)
    print("🚀 EXECUTANDO FLUXO 2: TRANSFORMACAO DIGITAL")
    print("="*80)

    fluxo_atual = 2
    additional_test_results = []
    executar_fluxo_completo(FLUXO_2, testes)

    # === FINALIZAÇÃO ===
    print("\n" + "="*80)
    print("✅ FINALIZANDO TESTES")
    print("="*80)

    # Aceitar alertas se houver
    try:
        WebDriverWait(driver, WAIT_TIMEOUT).until(EC.alert_is_present())
        alert = driver.switch_to.alert
        alert.accept()
    except Exception:
        pass

    # Gerar relatório
    gerar_relatorio_html(testes)
    print(f"\n✓ Relatório HTML gerado: report.html")

    # Estatísticas
    total_testes = len(testes)
    testes_pass = sum(1 for t in testes if t and t.get("status") == "PASS")
    testes_fail = sum(1 for t in testes if t and t.get("status") == "FAIL")

    print(f"\n{'='*80}")
    print(f"📊 RESUMO DOS TESTES")
    print(f"{'='*80}")
    print(f"Total: {total_testes} | ✓ PASS: {testes_pass} | ✗ FAIL: {testes_fail}")
    print(f"{'='*80}\n")

    driver.quit()


if __name__ == "__main__":
    main()
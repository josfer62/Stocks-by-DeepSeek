#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
PUBLICADOR DE RELATÓRIO DE AÇÕES (GitHub Pages)
- Recolhe dados via yfinance
- Aplica filtros (P/L < 15, P/VP < 1.5, DY > 4%)
- Gera relatório HTML em docs/index.html
- (Deve ser agendado via cron ou GitHub Actions)
"""

import os
import time
from datetime import datetime
import yfinance as yf

# ==================================================
# LISTA DE AÇÕES POR REGIÃO
# ==================================================
TICKERS = {
    "EUA": ["T", "PFE", "COP", "CVX", "QCOM", "BAC", "F"],
    "Europa": ["IMB.L", "NWG.L", "SNY.PA", "TTE.PA", "ULVR.L", "NVO.CO"],
    "Ásia": ["8031.T", "01579.HK", "HSBK.L"],
    "América do Sul": ["PETR4.SA", "VALE3.SA", "BRAP4.SA", "DIRR3.SA"]
}

# ==================================================
# FUNÇÕES AUXILIARES
# ==================================================

def get_stock_data(ticker):
    """Obtém os dados fundamentais de uma ação via yfinance."""
    try:
        stock = yf.Ticker(ticker)
        info = stock.info

        price = info.get('currentPrice') or info.get('regularMarketPrice') or info.get('previousClose')
        if not price:
            return None

        pe = info.get('trailingPE') or info.get('forwardPE')
        pb = info.get('priceToBook')
        dy = info.get('dividendYield')
        market_cap = info.get('marketCap')
        name = info.get('shortName') or info.get('longName') or ticker
        currency = info.get('currency', 'USD')
        sector = info.get('sector', 'N/A')

        if dy and dy < 1:
            dy_pct = dy * 100
        else:
            dy_pct = dy

        return {
            'ticker': ticker,
            'name': name,
            'price': price,
            'pe': pe,
            'pb': pb,
            'dy': dy_pct,
            'market_cap': market_cap,
            'currency': currency,
            'sector': sector
        }
    except Exception as e:
        print(f"  ⚠️ Erro ao buscar {ticker}: {e}")
        return None

def apply_filters(data):
    """Filtro: P/L 0-15, P/VP 0-1.5, DY > 4%, Market Cap > 1B."""
    if not data:
        return False

    pe = data.get('pe')
    pb = data.get('pb')
    dy = data.get('dy')
    mcap = data.get('market_cap')

    if pe is None or pe <= 0 or pe >= 15:
        return False
    if pb is None or pb <= 0 or pb >= 1.5:
        return False
    if dy is None or dy < 4.0:
        return False
    if mcap is None or mcap < 1_000_000_000:
        return False

    return True

def generate_html_report(results, timestamp):
    """Gera o relatório em HTML."""
    date_str = timestamp.strftime("%d/%m/%Y")
    time_str = timestamp.strftime("%H:%M")

    html = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Relatório Value Stocks - {date_str}</title>
        <style>
            * {{ margin: 0; padding: 0; box-sizing: border-box; }}
            body {{ font-family: 'Segoe UI', Tahoma, sans-serif; background: #f4f7fc; padding: 20px; color: #1e2a3a; }}
            .container {{ max-width: 1100px; margin: 0 auto; background: white; padding: 30px; border-radius: 10px; box-shadow: 0 4px 12px rgba(0,0,0,0.08); }}
            h1 {{ color: #0b1e33; border-bottom: 4px solid #1a3a5c; padding-bottom: 10px; }}
            .subtitle {{ color: #3e5a76; font-size: 18px; margin-bottom: 25px; }}
            .stats {{ background: #e6f0fa; padding: 12px 18px; border-radius: 8px; margin-bottom: 20px; }}
            table {{ width: 100%; border-collapse: collapse; font-size: 14px; margin-top: 15px; }}
            th {{ background: #1a3a5c; color: white; padding: 12px 10px; text-align: left; }}
            td {{ padding: 10px; border-bottom: 1px solid #e3e9f0; }}
            tr:nth-child(even) {{ background-color: #f8faff; }}
            .badge {{ display: inline-block; padding: 3px 12px; border-radius: 20px; font-weight: 600; font-size: 12px; background: #d4edda; color: #0b5e2e; }}
            .footer {{ margin-top: 30px; padding-top: 15px; border-top: 1px solid #dde4ed; font-size: 12px; color: #4d627c; }}
            .disclaimer {{ background: #f3f6fa; padding: 15px 20px; border-left: 5px solid #b22222; margin-top: 25px; border-radius: 4px; font-size: 13px; }}
            @media (max-width: 600px) {{ table {{ font-size: 11px; }} td, th {{ padding: 6px; }} }}
        </style>
    </head>
    <body>
    <div class="container">
        <h1>📈 RELATÓRIO DE AÇÕES BARATAS (VALUE STOCKS)</h1>
        <div class="subtitle">Cobertura Global · {date_str} · Gerado às {time_str} (UTC)</div>
        <div class="stats"><strong>✅ Ações aprovadas:</strong> {len(results)} em {sum(len(v) for v in TICKERS.values())} analisadas.</div>
    """

    if not results:
        html += "<p style='color: #b22222; font-size: 18px;'><strong>Nenhuma ação passou nos critérios hoje.</strong></p>"
    else:
        html += """
        <table>
            <thead><tr><th>#</th><th>Ticker</th><th>Empresa</th><th>Região</th><th>Preço</th><th>P/L</th><th>P/VP</th><th>DY (%)</th><th>Setor</th></tr></thead>
            <tbody>
        """
        for idx, item in enumerate(results, 1):
            region = "Global"
            ticker = item['ticker']
            if ticker.endswith(".SA"): region = "América do Sul"
            elif ticker.endswith(".L") or ticker.endswith(".PA") or ticker.endswith(".CO"): region = "Europa"
            elif ticker.endswith(".T") or ticker.endswith(".HK"): region = "Ásia"
            elif ticker in ["T", "PFE", "COP", "CVX", "QCOM", "BAC", "F"]: region = "EUA"

            dy_val = f"{item['dy']:.2f}" if item['dy'] else "N/A"
            pe_val = f"{item['pe']:.2f}" if item['pe'] else "N/A"
            pb_val = f"{item['pb']:.2f}" if item['pb'] else "N/A"
            price_val = f"{item['price']:.2f} {item['currency']}" if item['price'] else "N/A"

            html += f"""
                <tr>
                    <td>{idx}</td>
                    <td><strong>{ticker}</strong></td>
                    <td>{item['name'][:40]}</td>
                    <td>{region}</td>
                    <td>{price_val}</td>
                    <td>{pe_val}</td>
                    <td>{pb_val}</td>
                    <td>{dy_val}%</td>
                    <td>{item['sector'][:25]}</td>
                </tr>
            """
        html += "</tbody></table>"

    html += f"""
        <div class="disclaimer">
            ⚠️ <strong>DISCLAIMER:</strong> Esta análise é baseada em dados públicos recolhidos via Yahoo Finance em {date_str}.
            Não constitui recomendação de investimento personalizada. Consulte sempre um profissional qualificado.
        </div>
        <div class="footer">
            Relatório atualizado automaticamente todos os dias às 8:00 (UTC). · Dados indicativos.
        </div>
    </div>
    </body>
    </html>
    """
    return html

# ==================================================
# FUNÇÃO PRINCIPAL
# ==================================================

def main():
    print("🚀 Iniciando geração do relatório para publicação web...")
    timestamp = datetime.now()
    all_data = []

    for region, ticker_list in TICKERS.items():
        print(f"\n📡 Buscando {region} ({len(ticker_list)} tickers)...")
        for ticker in ticker_list:
            print(f"  - {ticker}", end="... ")
            data = get_stock_data(ticker)
            if data:
                if apply_filters(data):
                    all_data.append(data)
                    print("✅ APROVADA")
                else:
                    print("⏩ Não passou filtros")
            else:
                print("❌ Falha ao obter dados")
            time.sleep(0.3)

    print(f"\n📊 Aprovados: {len(all_data)}")

    # Ordenar por DY (maior primeiro)
    all_data.sort(key=lambda x: (x.get('dy', 0) or 0), reverse=True)

    # Gerar HTML
    html_report = generate_html_report(all_data, timestamp)

    # GARANTIR que a pasta 'docs' existe
    os.makedirs("docs", exist_ok=True)

    # Guardar como docs/index.html (ponto de entrada do GitHub Pages)
    with open("docs/index.html", "w", encoding="utf-8") as f:
        f.write(html_report)

    print("💾 Relatório guardado em 'docs/index.html' (pronto para GitHub Pages)")

if __name__ == "__main__":
    main()

Adiciona script

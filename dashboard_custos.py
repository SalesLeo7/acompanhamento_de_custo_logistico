import streamlit as st
import pandas as pd
import plotly.express as px

st.set_page_config(page_title="Dashboard Financeiro", layout="wide")

st.title("Dashboard Financeiro - Acompanhamento de Custos")

# =========================
# Upload do arquivo
# =========================
arquivo = st.file_uploader("Carregue sua planilha Excel", type=["xlsx"])

@st.cache_data
def carregar_dados(file):
    df = pd.read_excel(file)

    # Padronização
    df.columns = df.columns.str.strip()

    # Converter datas
    df['Mês'] = pd.to_datetime(df['Mês'], errors='coerce')
    df['ENVIADO'] = pd.to_datetime(df['ENVIADO'], errors='coerce')

    # Garantir valor numérico
    df['VALOR'] = pd.to_numeric(df['VALOR'], errors='coerce')

    return df

if arquivo:
    df = carregar_dados(arquivo)

    # =========================
    # SIDEBAR (Filtros)
    # =========================
    st.sidebar.header("Filtros")

    data_min = df['Mês'].min()
    data_max = df['Mês'].max()

    intervalo_data = st.sidebar.date_input(
        "Período",
        [data_min, data_max]
    )

    fornecedor = st.sidebar.multiselect(
        "Fornecedor",
        df['FORNECEDOR'].dropna().unique()
    )

    categoria = st.sidebar.multiselect(
        "Categoria",
        df['Account in PT'].dropna().unique()
    )

    centro_custo = st.sidebar.multiselect(
        "Centro de Custo",
        df['COST CENTER'].dropna().unique()
    )

    # =========================
    # Aplicar filtros
    # =========================
    df_filtrado = df.copy()

    if len(intervalo_data) == 2:
        df_filtrado = df_filtrado[
            (df_filtrado['Mês'] >= pd.to_datetime(intervalo_data[0])) &
            (df_filtrado['Mês'] <= pd.to_datetime(intervalo_data[1]))
        ]

    if fornecedor:
        df_filtrado = df_filtrado[df_filtrado['FORNECEDOR'].isin(fornecedor)]

    if categoria:
        df_filtrado = df_filtrado[df_filtrado['Account in PT'].isin(categoria)]

    if centro_custo:
        df_filtrado = df_filtrado[df_filtrado['COST CENTER'].isin(centro_custo)]

    # =========================
    # KPIs
    # =========================
    st.subheader("Indicadores")

    total = df_filtrado['VALOR'].sum()
    media = df_filtrado.groupby(df_filtrado['Mês'].dt.to_period("M"))['VALOR'].sum().mean()

    maior_categoria = df_filtrado.groupby('Account in PT')['VALOR'].sum().idxmax()

    # Variação mês a mês
    mensal = df_filtrado.groupby(df_filtrado['Mês'].dt.to_period("M"))['VALOR'].sum().sort_index()

    if len(mensal) >= 2:
        variacao = ((mensal.iloc[-1] - mensal.iloc[-2]) / mensal.iloc[-2]) * 100
    else:
        variacao = 0

    col1, col2, col3, col4 = st.columns(4)

    col1.metric("Custo Total", f"R$ {total:,.2f}")
    col2.metric("Média Mensal", f"R$ {media:,.2f}")
    col3.metric("Maior Categoria", maior_categoria)
    col4.metric("Variação Mensal", f"{variacao:.2f}%")

    # =========================
    # Gráfico de tendência
    # =========================
    st.subheader("Evolução dos Custos")

    df_tempo = df_filtrado.groupby('Mês')['VALOR'].sum().reset_index()

    fig_linha = px.line(df_tempo, x='Mês', y='VALOR', markers=True)
    st.plotly_chart(fig_linha, use_container_width=True)

    # =========================
    # Custos por categoria
    # =========================
    st.subheader("Custos por Categoria")

    df_categoria = df_filtrado.groupby('Account in PT')['VALOR'].sum().reset_index()
    df_categoria = df_categoria.sort_values(by='VALOR', ascending=False)

    fig_bar = px.bar(df_categoria, x='Account in PT', y='VALOR')
    st.plotly_chart(fig_bar, use_container_width=True)

    # =========================
    # Top fornecedores
    # =========================
    st.subheader("Top Fornecedores")

    df_forn = df_filtrado.groupby('FORNECEDOR')['VALOR'].sum().reset_index()
    df_forn = df_forn.sort_values(by='VALOR', ascending=False).head(10)

    fig_top = px.bar(df_forn, x='VALOR', y='FORNECEDOR', orientation='h')
    st.plotly_chart(fig_top, use_container_width=True)

    # =========================
    # Pizza distribuição
    # =========================
    st.subheader("Distribuição dos Custos")

    fig_pie = px.pie(df_categoria, names='Account in PT', values='VALOR')
    st.plotly_chart(fig_pie, use_container_width=True)

    # =========================
    # Insights automáticos
    # =========================
    st.subheader("Insights Automáticos")

    if len(mensal) >= 2:
        if variacao > 0:
            st.warning(f"📈 Os custos aumentaram {variacao:.2f}% no último mês.")
        else:
            st.success(f"📉 Os custos reduziram {abs(variacao):.2f}% no último mês.")

    top_categoria = df_categoria.iloc[0]
    st.info(f"💡 A categoria com maior custo é '{top_categoria['Account in PT']}'.")

    # =========================
    # Tabela detalhada
    # =========================
    st.subheader("Dados Detalhados")

    st.dataframe(df_filtrado, use_container_width=True)

    # Download
    csv = df_filtrado.to_csv(index=False).encode('utf-8')
    st.download_button(
        "⬇️ Baixar CSV",
        csv,
        "dados_filtrados.csv",
        "text/csv"
    )

else:
    st.info("Faça upload de um arquivo para iniciar.")

# =========================
# Previsão dos resultados
# =========================

from prophet import Prophet

if arquivo:

    st.subheader("Previsão de Custos")

    df_forecast = df_filtrado.copy()

    df_forecast = df_forecast.groupby('Mês')['VALOR'].sum().reset_index()
    df_forecast = df_forecast.rename(columns={'Mês': 'ds', 'VALOR': 'y'})

    df_forecast = df_forecast.dropna()

    # Padronizar datas
    df_forecast['ds'] = pd.to_datetime(df_forecast['ds']).dt.to_period('M').dt.to_timestamp()

    # Garantir continuidade
    df_forecast = df_forecast.set_index('ds').asfreq('MS').fillna(0).reset_index()

    if len(df_forecast) >= 6:

        modelo = Prophet(
            yearly_seasonality=True,
            weekly_seasonality=False,
            daily_seasonality=False
        )

        modelo.fit(df_forecast)

        futuro = modelo.make_future_dataframe(periods=6, freq='MS')

        previsao = modelo.predict(futuro)

        fig_prev = px.line()

        fig_prev.add_scatter(
            x=df_forecast['ds'],
            y=df_forecast['y'],
            mode='lines+markers',
            name='Real'
        )

        fig_prev.add_scatter(
            x=previsao['ds'],
            y=previsao['yhat'],
            mode='lines',
            name='Previsto'
        )

        st.plotly_chart(fig_prev, use_container_width=True)

        st.subheader("Insight de Tendência")

        ultimo_real = df_forecast['y'].iloc[-1]
        ultimo_prev = previsao['yhat'].iloc[-1]

        if ultimo_real != 0:
            variacao_prev = ((ultimo_prev - ultimo_real) / ultimo_real) * 100
        else:
            variacao_prev = 0

        if variacao_prev > 0:
            st.warning(f"📈 Tendência de aumento de {variacao_prev:.2f}% nos próximos meses.")
        else:
            st.success(f"📉 Tendência de redução de {abs(variacao_prev):.2f}% nos próximos meses.")

    else:
        st.info("⚠️ Necessário pelo menos 6 meses de dados para previsão.")

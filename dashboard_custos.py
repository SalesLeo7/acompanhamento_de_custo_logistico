import streamlit as st
import pandas as pd
import plotly.express as px

st.set_page_config(page_title="Dashboard Financeiro", layout="wide")

st.title("Dashboard Financeiro - Acompanhamento de Custos")

# =========================
# FORMATAÇÃO REAL
# =========================
def formatar_real(valor):
    return f"R$ {valor:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")

# =========================
# LIMPEZA DE VALOR (ROBUSTA)
# =========================
def limpar_valor(valor):
    if pd.isna(valor):
        return None

    valor = str(valor).strip()

    if ',' in valor and '.' in valor:
        valor = valor.replace('.', '').replace(',', '.')
    elif ',' in valor:
        valor = valor.replace(',', '.')
    else:
        valor = valor

    try:
        return float(valor)
    except:
        return None

# =========================
# UPLOAD
# =========================
arquivo = st.file_uploader("Carregue sua planilha Excel", type=["xlsx"])

@st.cache_data
def carregar_dados(file):
    df = pd.read_excel(file)

    df.columns = df.columns.str.strip()

    df['Mês'] = pd.to_datetime(df['Mês'], errors='coerce')
    df['ENVIADO'] = pd.to_datetime(df['ENVIADO'], errors='coerce')

    # CORREÇÃO PRINCIPAL
    df['VALOR'] = df['VALOR'].apply(limpar_valor)

    return df

if arquivo:
    df = carregar_dados(arquivo)

    # =========================
    # VALIDAÇÃO
    # =========================
    if df['VALOR'].max() > 1e9:
        st.error("Valores extremamente altos detectados. Verifique a base.")

    # =========================
    # FILTROS
    # =========================
    st.sidebar.header("Filtros")

    intervalo_data = st.sidebar.date_input(
        "Período",
        [df['Mês'].min(), df['Mês'].max()]
    )

    fornecedor = st.sidebar.multiselect("Fornecedor", df['FORNECEDOR'].dropna().unique())
    categoria = st.sidebar.multiselect("Categoria", df['Account in PT'].dropna().unique())
    centro_custo = st.sidebar.multiselect("Centro de Custo", df['COST CENTER'].dropna().unique())
    solicitante = st.sidebar.multiselect("Solicitante",df['SOLICITANTE'].dropna().unique())
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

    if solicitante:
        df_filtrado = df_filtrado[df_filtrado['SOLICITANTE'].isin(solicitante)]

    # =========================
    # KPIs
    # =========================
    st.subheader("Indicadores")

    total = df_filtrado['VALOR'].sum()

    media = df_filtrado.groupby(
        df_filtrado['Mês'].dt.to_period("M")
    )['VALOR'].sum().mean()

    maior_categoria = df_filtrado.groupby('Account in PT')['VALOR'].sum().idxmax()

    mensal = df_filtrado.groupby(
        df_filtrado['Mês'].dt.to_period("M")
    )['VALOR'].sum().sort_index()

    variacao = 0
    if len(mensal) >= 2 and mensal.iloc[-2] != 0:
        variacao = ((mensal.iloc[-1] - mensal.iloc[-2]) / mensal.iloc[-2]) * 100

    col1, col2, col3, col4 = st.columns(4)

    col1.metric("Custo Total", formatar_real(total))
    col2.metric("Média Mensal", formatar_real(media))
    col3.metric("Maior Categoria", maior_categoria)
    col4.metric("Variação Mensal", f"{variacao:.2f}%")

    # =========================
    # SOLICITANTE (CORRIGIDO)
    # =========================
    if 'SOLICITANTE' in df_filtrado.columns:

        st.subheader("💼 Custos por Solicitante")

        df_solic = df_filtrado.groupby('SOLICITANTE')['VALOR'].sum().reset_index()
        df_solic = df_solic.sort_values(by='VALOR', ascending=False).head(10)

        fig_solic = px.bar(
            df_solic,
            x='VALOR',
            y='SOLICITANTE',
            orientation='h'
        )

        fig_solic.update_layout(yaxis={'categoryorder': 'total ascending'})

        st.plotly_chart(fig_solic, use_container_width=True)

    else:
        st.warning("⚠️ Coluna 'SOLICITANTE' não encontrada.")

    # =========================
    # EVOLUÇÃO
    # =========================
    st.subheader("Evolução dos Custos")

    df_tempo = df_filtrado.groupby('Mês')['VALOR'].sum().reset_index()

    fig_linha = px.line(df_tempo, x='Mês', y='VALOR', markers=True)
    st.plotly_chart(fig_linha, use_container_width=True)

    # =========================
    # CATEGORIA
    # =========================
    st.subheader("Custos por Categoria")

    df_categoria = df_filtrado.groupby('Account in PT')['VALOR'].sum().reset_index()
    df_categoria = df_categoria.sort_values(by='VALOR', ascending=False)

    fig_bar = px.bar(df_categoria, x='Account in PT', y='VALOR')
    st.plotly_chart(fig_bar, use_container_width=True)

    # =========================
    # FORNECEDOR
    # =========================
    st.subheader("Top Fornecedores")

    df_forn = df_filtrado.groupby('FORNECEDOR')['VALOR'].sum().reset_index()
    df_forn = df_forn.sort_values(by='VALOR', ascending=False).head(10)

    fig_top = px.bar(df_forn, x='VALOR', y='FORNECEDOR', orientation='h')
    st.plotly_chart(fig_top, use_container_width=True)

    # =========================
    # DISTRIBUIÇÃO
    # =========================
    st.subheader("Distribuição dos Custos")

    fig_pie = px.pie(df_categoria, names='Account in PT', values='VALOR')
    st.plotly_chart(fig_pie, use_container_width=True)

    # =========================
    # INSIGHTS
    # =========================
    st.subheader("Insights Automáticos")

    if len(mensal) >= 2:
        if variacao > 0:
            st.warning(f"Os custos aumentaram {variacao:.2f}% no último mês.")
        else:
            st.success(f"Os custos reduziram {abs(variacao):.2f}% no último mês.")

    if not df_categoria.empty:
        st.info(f"Maior impacto: {df_categoria.iloc[0]['Account in PT']}")

    # =========================
    # DEBUG (OPCIONAL)
    # =========================
    with st.expander("Debug de dados"):
        st.write("Total geral:", total)
        st.write("Máximo valor:", df['VALOR'].max())
        st.write("Amostra:", df[['SOLICITANTE', 'VALOR']].head())

    # =========================
    # TABELA
    # =========================
    st.subheader("Dados Detalhados")

    st.dataframe(df_filtrado, use_container_width=True)

    csv = df_filtrado.to_csv(index=False).encode('utf-8')
    st.download_button("Baixar CSV", csv, "dados_filtrados.csv", "text/csv")

    # =========================
    # PREVISÃO
    # =========================
    try:
        from prophet import Prophet

        st.subheader("🔮 Previsão de Custos")

        df_forecast = df_filtrado.groupby('Mês')['VALOR'].sum().reset_index()
        df_forecast = df_forecast.rename(columns={'Mês': 'ds', 'VALOR': 'y'})
        df_forecast = df_forecast.dropna()

        df_forecast['ds'] = pd.to_datetime(df_forecast['ds']).dt.to_period('M').dt.to_timestamp()
        df_forecast = df_forecast.set_index('ds').asfreq('MS').fillna(0).reset_index()

        if len(df_forecast) >= 6:

            modelo = Prophet(yearly_seasonality=True)

            modelo.fit(df_forecast)

            futuro = modelo.make_future_dataframe(periods=6, freq='MS')
            previsao = modelo.predict(futuro)

            fig_prev = px.line()

            fig_prev.add_scatter(x=df_forecast['ds'], y=df_forecast['y'], mode='lines+markers', name='Real')
            fig_prev.add_scatter(x=previsao['ds'], y=previsao['yhat'], mode='lines', name='Previsto')

            st.plotly_chart(fig_prev, use_container_width=True)

        else:
            st.info("⚠️ Necessário pelo menos 6 meses de dados.")

    except:
        st.warning("⚠️ Prophet não instalado. Previsão desativada.")

else:
    st.info("Faça upload de um arquivo para iniciar.")

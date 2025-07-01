import pandas as pd
import plotly.express as px
import streamlit as st

# --- Configuração da Página ---
st.set_page_config(
    page_title="Simulador Financeiro",
    page_icon="📊",
    layout="wide",
)


def gerar_projecao(params, sazonalidade, mes_inicial):
    """Gera uma projeção de 12 meses para um único cenário."""
    dados = []
    receita_mes_anterior = params["receita_inicial"]

    for i in range(12):
        mes_atual = (mes_inicial + i - 1) % 12 + 1
        fator_sazonalidade = sazonalidade.get(mes_atual, 1.0)
        # desconto_mensal = params["descontos_mensais"][i]
        desconto_mensal = params["desconto_medio"]

        # 1. Cálculo da Receita
        if i == 0:
            receita_bruta = receita_mes_anterior * fator_sazonalidade
        else:
            receita_bruta = (
                receita_mes_anterior
                * (1 + params["crescimento_mensal"] / 100)
                * fator_sazonalidade
            )

        desconto_valor = receita_bruta * (desconto_mensal / 100)
        receita_liquida = receita_bruta * (1 - desconto_mensal / 100)

        # 2. Cálculo do CMV
        # markup_efetivo = params["markup_partida"] * (1 - desconto_mensal / 100)
        # if markup_efetivo <= 0:
        #     markup_efetivo = 0.01  # Evitar divisão por zero

        custo_produto = receita_bruta / params["markup_partida"]
        custo_icms = custo_produto * (params["icms_difal"] / 100)
        custo_embalagens = receita_bruta * (params["embalagens"] / 100)
        cmv_total = custo_produto + custo_icms + custo_embalagens

        # 3. Cálculo dos Custos Variáveis
        custo_impostos = receita_liquida * (params["impostos_vendas"] / 100)
        custo_cartao = receita_liquida * (params["tarifa_cartao"] / 100)
        custo_comissoes = receita_liquida * (params["comissoes_vendas"] / 100)
        custo_marketing = receita_liquida * (params["marketing_vendas"] / 100)
        custos_variaveis_total = (
            custo_impostos + custo_cartao + custo_comissoes + custo_marketing
        )
        fornecedores = params["fornecedores"]

        # 4. Cálculo dos Resultados
        margem_contribuicao = (
            receita_liquida - cmv_total - custos_variaveis_total
        )
        lucro_operacional = margem_contribuicao - params["custo_fixo_mensal"]
        outros_custos_total = (
            params["emprestimos"] + params["retiradas_socios"]
        )
        lucro_liquido = lucro_operacional - outros_custos_total

        dados.append(
            {
                "Mês": i + 1,
                "Receita Bruta": receita_bruta,
                "(-) Descontos": desconto_valor,
                "(=) Receita Líquida": receita_liquida,
                "(-) CMV": cmv_total,
                "(-) Fornecedores": fornecedores,
                "(-) Despesas Variáveis": custos_variaveis_total,
                "(=) Margem de Contribuição": margem_contribuicao,
                "(-) Despesas Fixas": params["custo_fixo_mensal"],
                "(=) Lucro Operacional": lucro_operacional,
                "(-) Outras Despesas": outros_custos_total,
                "(=) Lucro Líquido": lucro_liquido,
                "Custo Total": cmv_total
                + custos_variaveis_total
                + params["custo_fixo_mensal"]
                + outros_custos_total,
            }
        )

        receita_mes_anterior = receita_bruta

    return pd.DataFrame(dados)


def style_rows(row):
    """Aplica cor verde/vermelho em linhas específicas do DRE."""
    if row.name in [
        "(=) Margem de Contribuição",
        "(=) Lucro Operacional",
        "(=) Lucro Líquido",
        "(=) Geração de Caixa",
    ]:
        colors = ["color: green" if val >= 0 else "color: red" for val in row]
        return colors
    return ["" for _ in row]


# --- Inicialização do Session State ---
if "cenarios" not in st.session_state:
    st.session_state.cenarios = {}
    cenarios_base = {
        "Pessimista": {
            "receita_inicial": 80000,
            "crescimento_mensal": 0.5,
            "desconto_medio": 10.0,
            "markup_partida": 2.0,
            "custo_fixo_mensal": 40000,
            "fornecedores": 80000 / 2.0,
        },
        "Conservador": {
            "receita_inicial": 100000,
            "crescimento_mensal": 2.0,
            "desconto_medio": 5.0,
            "markup_partida": 2.2,
            "custo_fixo_mensal": 35000,
            "fornecedores": 100000 / 2.2,
        },
        "Otimista": {
            "receita_inicial": 120000,
            "crescimento_mensal": 4.0,
            "desconto_medio": 2.0,
            "markup_partida": 2.4,
            "custo_fixo_mensal": 25000,
            "fornecedores": 120000 / 2.4,
        },
    }
    for nome, base in cenarios_base.items():
        st.session_state.cenarios[nome] = {
            "receita_inicial": base["receita_inicial"],
            "crescimento_mensal": base["crescimento_mensal"],
            "desconto_medio": base["desconto_medio"],
            "descontos_mensais": [base["desconto_medio"]] * 12,
            "markup_partida": base["markup_partida"],
            "icms_difal": 13.0,
            "embalagens": 0.0,
            "custo_fixo_mensal": base["custo_fixo_mensal"],
            "impostos_vendas": 10.0,
            "tarifa_cartao": 4.5,
            "comissoes_vendas": 4.0,
            "marketing_vendas": 0.0,
            "emprestimos": 10000.0,
            "retiradas_socios": 5000.0,
            "fornecedores": base["fornecedores"],
            "pct_entradas": 95.0,
        }

if "sazonalidade" not in st.session_state:
    st.session_state.sazonalidade = {i: 1.0 for i in range(1, 13)}

st.session_state.mes_inicial = 1

# --- Barra Lateral ---
# with st.sidebar:
#     st.title("⚙️ Parâmetros Base da Simulação")

#     agora = datetime.now()
#     col1, col2 = st.columns(2)
#     mes_inicial = col1.number_input(
#         "Mês Inicial",
#         min_value=1,
#         max_value=12,
#         value=agora.month,
#     )
#     ano_inicial = col2.number_input(
#         "Ano Inicial",
#         min_value=agora.year,
#         value=agora.year,
#     )
#     st.session_state.mes_inicial = mes_inicial

#     with st.expander("Fatores de Sazonalidade (Opcional)"):
#         st.caption(
#             "Ajuste o multiplicador de vendas para cada mês. Ex: 1.2 para 20% mais vendas."
#         )
#         for i in range(1, 13):
#             st.session_state.sazonalidade[i] = st.number_input(
#                 f"Mês {i}",
#                 value=st.session_state.sazonalidade[i],
#                 key=f"saz_{i}",
#                 step=0.1,
#             )

# --- Tela Principal ---
st.title("📊 Simulador Financeiro: Ponto de Equilíbrio")
st.markdown("---")

nomes_cenarios = ["Pessimista", "Conservador", "Otimista"]
cols = st.columns(3, gap="large")

for col, nome in zip(cols, nomes_cenarios):
    params = st.session_state.cenarios[nome]
    with col:
        st.header(nome)

        # --- 1. Projeção de Receitas ---
        st.subheader("1. Projeção de Receitas")
        params["receita_inicial"] = st.number_input(
            "Receita no Primeiro Mês (R$)",
            min_value=0,
            value=params["receita_inicial"],
            key=f"rec_{nome}",
            step=1000,
        )
        params["crescimento_mensal"] = st.number_input(
            "Crescimento Mensal das Vendas (%)",
            value=params["crescimento_mensal"],
            key=f"cresc_{nome}",
            step=0.5,
        )
        params["desconto_medio"] = st.number_input(
            "Desconto Médio Mensal (%)",
            min_value=0.0,
            max_value=100.0,
            value=params["desconto_medio"],
            key=f"desc_{nome}",
            step=0.1,
        )
        # with st.expander("Alterar desconto por mês"):
        #     for i in range(12):
        #         params["descontos_mensais"][i] = st.number_input(
        #             f"Mês {i+1} (%)",
        #             min_value=0.0,
        #             value=params["desconto_medio"],
        #             key=f"desc_mes_{i}_{nome}",
        #             step=0.5,
        #         )

        # --- 2. CMV ---
        st.subheader("2. Fornecedores/CMV")
        params["markup_partida"] = st.number_input(
            "Markup de Partida",
            min_value=1.0,
            value=params["markup_partida"],
            key=f"mark_{nome}",
            step=0.1,
        )
        params["icms_difal"] = st.number_input(
            "ICMS DIFAL (%)",
            min_value=0.0,
            max_value=100.0,
            value=params["icms_difal"],
            key=f"icms_{nome}",
            step=0.1,
        )
        params["embalagens"] = st.number_input(
            "Embalagens (%)",
            min_value=0.0,
            max_value=100.0,
            value=params["embalagens"],
            key=f"emb_{nome}",
            step=0.1,
        )

        params["fornecedores"] = st.number_input(
            "Pgto. Mensal para Fornecedores (R$)",
            min_value=0.0,
            value=params["fornecedores"],
            key=f"forne_{nome}",
            step=1000.0,
        )

        # --- 3. Estrutura de Custos ---
        st.subheader("3. Estrutura de Despesas")

        st.markdown("##### 3.1 Despesas Variáveis")
        params["impostos_vendas"] = st.number_input(
            "Impostos sobre Vendas (%)",
            min_value=0.0,
            max_value=100.0,
            value=params["impostos_vendas"],
            key=f"imp_{nome}",
            step=0.1,
        )
        params["tarifa_cartao"] = st.number_input(
            "Tarifa de Cartão (%)",
            min_value=0.0,
            max_value=100.0,
            value=params["tarifa_cartao"],
            key=f"cart_{nome}",
            step=0.1,
        )
        params["comissoes_vendas"] = st.number_input(
            "Comissões sobre Vendas (%)",
            min_value=0.0,
            max_value=100.0,
            value=params["comissoes_vendas"],
            key=f"com_{nome}",
            step=0.1,
        )
        params["marketing_vendas"] = st.number_input(
            "Marketing sobre Vendas (%)",
            min_value=0.0,
            max_value=100.0,
            value=params["marketing_vendas"],
            key=f"mkt_{nome}",
            step=0.1,
        )

        st.markdown("##### 3.2 Despesas Fixas")
        params["custo_fixo_mensal"] = st.number_input(
            "Despesa Fixa Mensal (R$)",
            min_value=0,
            value=params["custo_fixo_mensal"],
            key=f"fixo_{nome}",
            step=500,
        )

        st.markdown("##### 3.3 Outras Despesas")
        params["emprestimos"] = st.number_input(
            "Empréstimos (R$)",
            min_value=0.0,
            value=params["emprestimos"],
            key=f"emp_{nome}",
            step=100.0,
        )
        params["retiradas_socios"] = st.number_input(
            "Retiradas dos Sócios (R$)",
            min_value=0.0,
            value=params["retiradas_socios"],
            key=f"soc_{nome}",
            step=500.0,
        )

        # --- 4. Resultados ---
        st.subheader("4. Resultados")

        # Gerar projeção para o cenário atual
        df_projecao = gerar_projecao(
            params,
            st.session_state.sazonalidade,
            st.session_state.mes_inicial,
        )

        # st.dataframe(df_projecao)

        resultados = df_projecao.sum()

        # Ponto de Equilíbrio
        st.markdown("##### Ponto de Equilíbrio")

        # total_receita = df_projecao.iloc[0]["Receita Bruta"]
        total_receita = df_projecao.iloc[0]["(=) Receita Líquida"]
        total_variavel = (
            df_projecao.iloc[0]["(-) CMV"]
            + df_projecao.iloc[0]["(-) Despesas Variáveis"]
        )
        total_fixo = df_projecao.iloc[0]["(-) Despesas Fixas"]
        total_outras_despesas = df_projecao.iloc[0]["(-) Outras Despesas"]
        margem_contribuicao = df_projecao.iloc[0]["(=) Margem de Contribuição"]
        pct_margem_contribuicao = margem_contribuicao / total_receita
        pct_variavel = total_variavel / total_receita

        ponto_equilibrio_operacional = (
            # total_fixo / (1 - pct_variavel)
            total_fixo / pct_margem_contribuicao
            if total_receita > 0 and margem_contribuicao > 0
            else float("inf")
        )

        ponto_equilibrio = (
            # (total_fixo + total_outras_despesas) / (1 - pct_variavel)
            (total_fixo + total_outras_despesas) / pct_margem_contribuicao
            if total_receita > 0 and margem_contribuicao > 0
            else float("inf")
        )

        dados_plot_pe = []
        for i in [0.7, 0.8, 0.9, 1, 1.1, 1.2, 1.3]:
            receitas = ponto_equilibrio_operacional * i
            despesas = total_fixo + (pct_variavel * receitas)
            dados_plot_pe.append({"Receitas": receitas, "Despesas": despesas})

        df_plot_pe = pd.DataFrame(dados_plot_pe)

        if margem_contribuicao > 0:
            st.metric(
                "Ponto de Equilíbrio Geral",
                f"R$ {ponto_equilibrio:,.2f}",
                help="A receita necessária para cobrir todos os custos e despesas fixas, incluindo outras despesas não operacionais.",
            )
            st.metric(
                "Ponto de Equilíbrio Operacional",
                f"R$ {ponto_equilibrio_operacional:,.2f}",
                help="A receita necessária para cobrir todos os custos e despesas fixas, incluindo apenas despesas operacionais.",
            )
        else:
            st.markdown(
                "Sua margem de contribuição é negativa ou quase zero, o ponto de equilíbrio, nesse caso, **não existe** (ou é infinito). Tente reduzir o desconto ou os seus custos variáveis."
            )

        fig_pe = px.line(
            df_plot_pe,
            y=["Receitas", "Despesas"],
            title="Ponto de Equilíbrio Operacional",
            template="plotly_white",
            markers=True,
            labels={
                "value": "Valor",
                "variable": "Varíavel",
                "index": "Índice",
            },
        )
        fig_pe.add_hline(
            y=ponto_equilibrio_operacional,
            line_dash="dot",
            annotation_text="Ponto de Equilíbrio",
            annotation_position="bottom right",
        )
        fig_pe.update_layout(
            xaxis={"visible": False, "showticklabels": False},
            yaxis_title="Valor",
            legend_title=None,
        )
        st.plotly_chart(fig_pe, use_container_width=True)

        # DRE Resumido
        st.markdown("##### DRE Consolidado (12 Meses)")

        # Criar o DataFrame do DRE a partir dos resultados somados
        df_dre_total = (
            resultados.drop("Mês")
            .drop("Custo Total")
            .drop("(-) Fornecedores")
            .drop("(=) Lucro Operacional")
            .to_frame(name="Total (R$)")
        )
        df_dre_total["(%)"] = (
            df_dre_total["Total (R$)"] / df_dre_total["Total (R$)"].iloc[0]
        ) * 100

        # Aplicar o estilo e o formato
        styled_dre = (
            df_dre_total.style.apply(style_rows, axis=1)
            .format("R$ {:,.2f}", subset=["Total (R$)"])
            .format("{:,.2f}%", subset=["(%)"])
        )

        # Exibir a tabela estilizada
        st.dataframe(styled_dre, use_container_width=True)

        # Composição dos Custos
        st.markdown("##### Composição das Despesas sobre a Receita Bruta")
        custos_donut = pd.DataFrame(
            [
                {
                    "Tipo": "CMV",
                    "Valor": resultados["(-) CMV"]
                    / resultados["Receita Bruta"],
                },
                {
                    "Tipo": "Despesas Variáveis",
                    "Valor": resultados["(-) Despesas Variáveis"]
                    / resultados["Receita Bruta"],
                },
                {
                    "Tipo": "Despesas Fixas",
                    "Valor": resultados["(-) Despesas Fixas"]
                    / resultados["Receita Bruta"],
                },
                {
                    "Tipo": "Outras Despesas",
                    "Valor": resultados["(-) Outras Despesas"]
                    / resultados["Receita Bruta"],
                },
            ]
        )

        mapa_de_cores = {
            "CMV": "#5c6b73",
            "Despesas Variáveis": "#8f9e8b",
            "Despesas Fixas": "#c9d1c8",
            "Outras Despesas": "#f0e2d0",
        }

        fig_donut = px.pie(
            custos_donut,
            names="Tipo",
            values="Valor",
            title="Percentual sobre a Receita",
            hole=0.4,
            template="plotly_white",
            color="Tipo",
            color_discrete_map=mapa_de_cores,
        )
        fig_donut.update_traces(
            text=custos_donut["Valor"].apply(lambda x: f"{x*100:,.2f}%"),
            textinfo="text",
        )
        st.plotly_chart(fig_donut, use_container_width=True)

        # Fluxo de Caixa
        st.markdown("##### Fluxo de Caixa Consolidado (12 Meses)")

        params["pct_entradas"] = st.slider(
            "Entradas de Caixa (% Receita Líquida)",
            value=params["pct_entradas"],
            min_value=0.0,
            max_value=100.0,
            key=f"entr_{nome}",
            step=0.1,
        )

        df_projecao_caixa = df_projecao.copy()
        df_projecao_caixa = df_projecao_caixa[
            [
                "Mês",
                "(=) Receita Líquida",
                "(-) Fornecedores",
                "(-) Despesas Variáveis",
                "(-) Despesas Fixas",
                "(-) Outras Despesas",
            ]
        ]
        df_projecao_caixa["(=) Receita Líquida"] = df_projecao_caixa[
            "(=) Receita Líquida"
        ] * (params["pct_entradas"] / 100)
        df_projecao_caixa["(=) Geração de Caixa"] = (
            df_projecao_caixa["(=) Receita Líquida"]
            - df_projecao_caixa["(-) Fornecedores"]
            - df_projecao_caixa["(-) Despesas Variáveis"]
            - df_projecao_caixa["(-) Despesas Fixas"]
            - df_projecao_caixa["(-) Outras Despesas"]
        )
        df_projecao_caixa = df_projecao_caixa.rename(
            columns={"(=) Receita Líquida": "Entradas"}
        )

        resultados_caixa = df_projecao_caixa.sum()

        # Criar o DataFrame do DRE a partir dos resultados somados
        df_caixa_total = resultados_caixa.drop("Mês").to_frame(
            name="Total (R$)"
        )
        # Aplicar o estilo e o formato
        styled_caixa = df_caixa_total.style.apply(style_rows, axis=1).format(
            "R$ {:,.2f}", subset=["Total (R$)"]
        )

        # Exibir a tabela estilizada
        st.dataframe(styled_caixa, use_container_width=True)

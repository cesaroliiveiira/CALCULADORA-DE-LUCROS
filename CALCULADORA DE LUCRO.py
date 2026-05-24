import streamlit as st

# Configuração da página web
st.set_page_config(
    page_title="Calculadora 3D Avançada", 
    page_icon="🖨️", 
    layout="centered"
)

st.title("🖨️ Calculadora de Precificação 3D + Acabamento")
st.write("Calcule o custo total incluindo fatiador, embalagem, tintas e sua mão de obra.")

# Menu lateral para configurações de custos fixos
st.sidebar.header("⚙️ Configurações Padrão")
valor_kwh = st.sidebar.number_input("Energia por Hora (R$)", value=0.115, format="%.3f")
valor_hora_tecnica = st.sidebar.number_input("Valor da sua Hora de Trabalho (R$)", value=20.00, step=1.0)

tipo_filamento = st.sidebar.selectbox(
    "Filamento Padrão",
    ["Média Segura (R$ 90/kg)", "Premium (R$ 100/kg)", "Econômico (R$ 75/kg)", "Personalizado"]
)

if tipo_filamento == "Média Segura (R$ 90/kg)":
    custo_g = 0.09
elif tipo_filamento == "Premium (R$ 100/kg)":
    custo_g = 0.10
elif tipo_filamento == "Econômico (R$ 75/kg)":
    custo_g = 0.075
else:
    preco_rolo = st.sidebar.number_input("Preço do Rolo (R$)", value=105.0)
    custo_g = preco_rolo / 1000

st.markdown("---")

# 1. Dados da Impressão (Máquina)
st.header("🤖 1. Dados do Fatiador (Impressão)")
col1, col2, col3 = st.columns(3)
with col1:
    peso = st.number_input("Peso da peça (g)", min_value=0.0, value=198.0, step=1.0)
with col2:
    horas_imp = st.number_input("Horas de Impressão", min_value=0, value=6, step=1)
with col3:
    minutos_imp = st.number_input("Minutos de Impressão", min_value=0, max_value=59, value=4, step=1)

# 2. Dados de Pós-Processamento e Pintura (Humano)
st.header("🎨 2. Acabamento, Pintura e Embalagem")
col4, col5, col6 = st.columns(3)
with col4:
    horas_pintura = st.number_input("Horas gastas lixando/pintando", min_value=0.0, value=0.5, step=0.1)
with col5:
    custo_tintas = st.number_input("Gasto estimado com Tintas/Lixa (R$)", min_value=0.0, value=3.00, step=0.5)
with col6:
    custo_embalagem = st.number_input("Custo da Embalagem (Caixa/Plástico) (R$)", min_value=0.0, value=3.50, step=0.5)

# --- CÁLCULOS AUTOMÁTICOS (ORGANIZADOS E SEM REPETIÇÃO) ---

# Custos de Impressão (Material + Energia)
tempo_horas_imp = horas_imp + (minutos_imp / 60)
custo_mat = peso * custo_g
custo_eng = tempo_horas_imp * valor_kwh

# Custos de Acabamento e Mão de Obra
custo_mao_de_obra = horas_pintura * valor_hora_tecnica
custo_pos_total = custo_tintas + custo_embalagem + custo_mao_de_obra

# Custo Geral do Projeto (Soma de tudo)
custo_total_projeto = custo_mat + custo_eng + custo_pos_total

st.markdown("---")

# 3. Margem e Preço Final
st.header("💰 Margem e Preço de Venda")

markup = st.slider("Multiplicador sobre o Custo Total", min_value=1.5, max_value=5.0, value=2.5, step=0.1)
preco_venda = custo_total_projeto * markup
lucro = preco_venda - custo_total_projeto

# Mostrando o detalhamento na tela
st.subheader("📋 Detalhamento dos Custos")
c1, c2, c3 = st.columns(3)
c1.metric("Fabricação (Mat. + Luz)", f"R$ {(custo_mat + custo_eng):.2f}")
c2.metric("Sua Mão de Obra (Tempo)", f"R$ {custo_mao_de_obra:.2f}")
c3.metric("Insumos + Embalagem", f"R$ {(custo_tintas + custo_embalagem):.2f}")

st.info(f"**Custo Real de Produção:** R$ {custo_total_projeto:.2f}")
st.success(f"### 🚀 Preço Sugerido de Venda: R$ {preco_venda:.2f}")
st.warning(f"Seu Lucro Líquido nessa peça: R$ {lucro:.2f}")

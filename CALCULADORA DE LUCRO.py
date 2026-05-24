import streamlit as st

# Configuração da página web
st.set_page_config(
    page_title="Calculadora 3D", 
    page_icon="🖨️", 
    layout="centered"
)

st.title("🖨️ Calculadora de Precificação 3D")
st.write("Acesse de onde estiver para calcular o custo e o preço dos seus projetos.")

# Menu lateral para configurações que mudam pouco
st.sidebar.header("⚙️ Configurações Padrão")
valor_kwh = st.sidebar.number_input("Energia por Hora (R$)", value=0.115, format="%.3f")

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

# Dados da peça atual
st.header("📦 Dados do Fatiador")

col1, col2, col3 = st.columns(3)
with col1:
    peso = st.number_input("Peso da peça (g)", min_value=0.0, value=198.0, step=1.0)
with col2:
    horas = st.number_input("Horas", min_value=0, value=6, step=1)
with col3:
    minutos = st.number_input("Minutos", min_value=0, max_value=59, value=4, step=1)

# Cálculos automáticos
tempo_horas = horas + (minutos / 60)
custo_mat = peso * custo_g
custo_eng = tempo_horas * valor_kwh
custo_total = custo_mat + custo_eng

st.markdown("---")

# Margem e Preço Final
st.header("💰 Margem e Preço de Venda")

markup = st.slider("Multiplicador (Quantas vezes cobrável sobre o custo)", min_value=1.5, max_value=5.0, value=3.0, step=0.1)
preco_venda = custo_total * markup
lucro = preco_venda - custo_total

# Mostrando os resultados na tela de forma limpa
c1, c2, c3 = st.columns(3)
c1.metric("Material", f"R$ {custo_mat:.2f}")
c2.metric("Energia", f"R$ {custo_eng:.2f}")
c3.metric("Custo Total", f"R$ {custo_total:.2f}")

st.success(f"### 🚀 Preço Sugerido: R$ {preco_venda:.2f}")
st.info(f"Lucro Bruto: R$ {lucro:.2f}")
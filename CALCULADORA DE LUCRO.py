"""
Calculadora de Precificação 3D - Max3dLab
Rodar:  python -m streamlit run app.py

Os números abaixo (CFG_PADRAO etc.) são o padrão FIXO do app.
Para mudar um valor para sempre: edite aqui e suba o arquivo no GitHub.
Mudanças feitas pela tela valem só até atualizar a página.
"""
import json
import math
from urllib.parse import quote

import pandas as pd
import streamlit as st
import streamlit.components.v1 as components

st.set_page_config(page_title="Max3dLab - Precificação", page_icon="🖨️", layout="centered")

# ===============================================================
# SEUS NÚMEROS (edite aqui)
# ===============================================================
CFG_PADRAO = {
    # Impressora (valor de UMA máquina: o custo por hora é igual para as duas)
    "preco_imp": 4242.0,    # Bambu Lab A1 + AMS Lite
    "residual": 850.0,      # ESTIMATIVA: ~20% do preço (você não soube informar)
    "vida_h": 10000.0,      # horas de vida útil
    "manut_pct": 10.0,      # % do preço guardado para manutenção
    "minimo_h": 1.0,        # amortização mínima por hora
    # Energia
    "potencia": 110.0,      # watts médios
    "kwh": 0.86,            # CONFIRA na sua conta de luz (veja explicação no chat)
    # Seu trabalho
    "mao_hora": 20.0,       # ESTIMATIVA: valor da sua hora
    "preparo_min": 10.0,    # ESTIMATIVA: minutos de preparo por impressão
    # Operação
    "horas_mes": 100.0,     # ESTIMATIVA: horas imprimindo por mês (somando as 2 impressoras)
    "falha_pct": 10.0,      # ESTIMATIVA: % de impressões que falham
    # Shopee
    "shopee_extra": 0.0,    # R$ extra por item (CPF com muitos pedidos paga +3,00)
}
MATERIAIS_PADRAO = [
    {"Material": "PLA", "R$/kg": 110.0},    # você paga entre 90 e 130
    {"Material": "PETG", "R$/kg": 120.0},   # você paga entre 100 e 140
]
ACESSORIOS_PADRAO = [  # exemplos: troque/apague pelos que você realmente usa
    {"Item": "Argola de chaveiro", "R$ por unidade": 0.50},
    {"Item": "Ímã", "R$ por unidade": 1.00},
    {"Item": "Parafuso / inserto", "R$ por unidade": 0.30},
]
FIXOS_PADRAO = [
    {"Custo": "Internet", "R$ por mês": 110.0},
    {"Custo": "App de modelagem", "R$ por mês": 25.0},
]
# Taxas da Shopee (comissão + taxa fixa por item). Conferido em out/2026.
# Formato: (preço mínimo, preço máximo, comissão %, taxa fixa R$)
TAXAS_SHOPEE = [
    (0.0, 80.0, 20.0, 4.50),
    (80.0, 100.0, 14.0, 16.00),
    (100.0, 200.0, 14.0, 20.00),
    (200.0, 1e9, 14.0, 26.00),
]


# ===============================================================
# FUNÇÕES
# ===============================================================
def brl(v: float) -> str:
    s = f"{v:,.2f}"
    return "R$ " + s.replace(",", "X").replace(".", ",").replace("X", ".")


def checar_senha():
    """Só pede senha se existir SENHA nos 'Secrets' do Streamlit Cloud."""
    try:
        senha = st.secrets.get("SENHA", None)
    except Exception:
        senha = None
    if not senha or st.session_state.get("autenticado"):
        return
    st.title("🔒 Max3dLab")
    entrada = st.text_input("Senha", type="password")
    if entrada:
        if entrada == senha:
            st.session_state.autenticado = True
            st.rerun()
        else:
            st.error("Senha incorreta")
    st.stop()


def taxa_shopee(preco: float, extra: float):
    """Retorna (comissão %, taxa fixa R$) para um preço de anúncio."""
    for lo, hi, com, fixa in TAXAS_SHOPEE:
        if lo <= preco < hi:
            return com, fixa + extra
    return TAXAS_SHOPEE[-1][2], TAXAS_SHOPEE[-1][3] + extra


def preco_para_margem(custo: float, margem: float, canal: str, extra: float):
    """Acha o preço (por unidade) que deixa a margem desejada DEPOIS das taxas."""
    if canal != "Shopee":
        return custo / (1 - margem)
    for lo, hi, com, fixa in TAXAS_SHOPEE:
        denom = 1 - margem - com / 100
        if denom <= 0:
            continue
        p = max((custo + fixa + extra) / denom, lo)
        if p < hi:
            return p
    return None


def usar_valor_hora():
    st.session_state.cfg_mao_hora = round(
        st.session_state.aux_ganho / max(st.session_state.aux_horas, 1), 2
    )


def botao_copiar(texto: str):
    """Botão que copia o texto para a área de transferência (celular e PC)."""
    js_texto = json.dumps(texto).replace("</", "<\\/")
    components.html(
        f"""
        <button id="b" style="width:100%;padding:10px;font-size:16px;border-radius:8px;
                border:1px solid #888;background:#ff4b4b;color:#fff;cursor:pointer;">
            📋 Copiar mensagem</button>
        <script>
        const t = {js_texto};
        const b = document.getElementById('b');
        function ok() {{
            b.textContent = '✅ Copiado!';
            setTimeout(() => b.textContent = '📋 Copiar mensagem', 2000);
        }}
        b.onclick = async () => {{
            try {{
                await navigator.clipboard.writeText(t);
                ok();
            }} catch (e) {{
                const a = document.createElement('textarea');
                a.value = t;
                document.body.appendChild(a);
                a.select();
                document.execCommand('copy');
                document.body.removeChild(a);
                ok();
            }}
        }};
        </script>
        """,
        height=60,
    )


def cfg(nome: str) -> float:
    return st.session_state[f"cfg_{nome}"]


checar_senha()

if "iniciado" not in st.session_state:
    for k, v in CFG_PADRAO.items():
        st.session_state[f"cfg_{k}"] = float(v)
    st.session_state.materiais = pd.DataFrame(MATERIAIS_PADRAO)
    st.session_state.acessorios = pd.DataFrame(ACESSORIOS_PADRAO)
    st.session_state.fixos = pd.DataFrame(FIXOS_PADRAO)
    st.session_state.iniciado = True

st.title("🖨️ Max3dLab")
st.caption("Calculadora de precificação 3D")

aba_calc, aba_cfg, aba_mat = st.tabs(["🧮 Calcular", "⚙️ Configurações", "🧵 Materiais"])

# ===============================================================
# ABA CONFIGURAÇÕES
# ===============================================================
with aba_cfg:
    st.info("👋 Seus números já estão preenchidos. Aqui você pode **testar cenários**; "
            "para mudar de forma permanente, edite o topo do `app.py`.")

    # ---------- 1. Impressora ----------
    st.header("1. Sua impressora")
    st.caption("Bambu Lab A1 com AMS Lite. Você tem duas, mas o custo por hora de máquina é o mesmo em cada uma.")
    c1, c2 = st.columns(2)
    c1.number_input("Preço que você pagou (R$)", min_value=0.0, step=100.0, key="cfg_preco_imp")
    c2.number_input("Valor de revenda no fim da vida (R$)", min_value=0.0, step=100.0, key="cfg_residual",
                    help="Quanto ela venderia usada. Se não sabe, use 20% do preço.")
    c1.number_input("Vida útil (horas de impressão)", min_value=1.0, step=500.0, key="cfg_vida_h")
    c2.number_input("Reserva de manutenção (% do preço)", min_value=0.0, step=1.0, key="cfg_manut_pct",
                    help="Bico, correia, mesa... Um valor comum é 10%.")
    st.number_input("Amortização mínima por hora (R$)", min_value=0.0, step=0.10, format="%.2f",
                    key="cfg_minimo_h", help="Regra prática: cobrar no mínimo R$ 1,00 por hora de máquina.")
    calc_amort = ((cfg("preco_imp") - cfg("residual")) +
                  cfg("preco_imp") * cfg("manut_pct") / 100) / cfg("vida_h")
    amort_hora = max(calc_amort, cfg("minimo_h"))
    st.success(
        f"📊 **Resultado:** o cálculo dá {brl(calc_amort)}/h.  \n"
        f"👉 **Valor usado: {brl(amort_hora)} por hora** (vale o maior entre o cálculo e o mínimo)."
    )

    # ---------- 2. Energia ----------
    st.header("2. Energia elétrica")
    c1, c2 = st.columns(2)
    c1.number_input("Consumo médio (watts)", min_value=1.0, step=10.0, key="cfg_potencia",
                    help="A etiqueta mostra o máximo (220 W). Na prática a média é menor (~110 W).")
    c2.number_input("Preço do kWh (R$)", min_value=0.0, step=0.05, format="%.2f", key="cfg_kwh",
                    help="Conta de luz: valor total ÷ kWh consumidos.")
    energia_hora = cfg("potencia") / 1000 * cfg("kwh")
    st.success(f"📊 **Resultado:** **{brl(energia_hora)} por hora**. "
               f"Uma impressão de 6 h gasta {brl(energia_hora * 6)} de luz.")

    # ---------- 3. Mão de obra ----------
    st.header("3. Seu trabalho")
    with st.expander("🤔 Me ajude a calcular o valor da minha hora"):
        c1, c2 = st.columns(2)
        c1.number_input("Quanto quero tirar por mês (R$)", min_value=0.0, value=1500.0, step=100.0,
                        key="aux_ganho")
        c2.number_input("Horas que trabalho por mês", min_value=1.0, value=75.0, step=5.0, key="aux_horas")
        st.write(f"Sugestão: {brl(st.session_state.aux_ganho / max(st.session_state.aux_horas, 1))} por hora")
        st.button("Usar esse valor", on_click=usar_valor_hora)
    c1, c2 = st.columns(2)
    c1.number_input("Valor da sua hora (R$)", min_value=0.0, step=1.0, key="cfg_mao_hora",
                    help="Exemplo: R$ 1.500 ÷ 75 h = R$ 20 por hora")
    c2.number_input("Preparo por impressão (minutos)", min_value=0.0, step=5.0, format="%.0f",
                    key="cfg_preparo_min", help="Fatiar, ligar, tirar da mesa, limpar.")

    # ---------- 4. Custos fixos ----------
    st.header("4. Custos fixos do mês")
    st.caption("Se a internet também é de uso pessoal, coloque só a parte que é do negócio.")
    st.session_state.fixos = st.data_editor(
        st.session_state.fixos, num_rows="dynamic", use_container_width=True, key="ed_fix",
        column_config={
            "Custo": st.column_config.TextColumn("Custo", required=True),
            "R$ por mês": st.column_config.NumberColumn("R$ por mês", min_value=0.0, format="%.2f"),
        },
    )
    st.number_input("Horas de impressão por mês (somando as 2 impressoras)", min_value=1.0, step=10.0,
                    key="cfg_horas_mes",
                    help="Depois de um mês de uso, troque pelo número real. "
                         "Quanto mais você imprime, menor o custo fixo por peça.")
    total_fixos = float(pd.to_numeric(st.session_state.fixos["R$ por mês"], errors="coerce").fillna(0).sum())
    fixo_hora = total_fixos / cfg("horas_mes")
    st.success(f"📊 **Resultado:** {brl(total_fixos)} ÷ {cfg('horas_mes'):.0f} h = "
               f"**{brl(fixo_hora)} por hora de impressão**.")

    # ---------- 5. Falhas ----------
    st.header("5. Impressões que falham")
    st.number_input("Taxa de falha (%)", min_value=0.0, max_value=90.0, step=1.0, key="cfg_falha_pct",
                    help="De 20 impressões, 1 falhou = 5%. Com AMS Lite, a troca de cor também gera "
                         "desperdício, então 10% é um bom começo.")

    # ---------- 6. Shopee ----------
    st.header("6. Taxas da Shopee")
    st.caption("Conferidas em out/2026. A Shopee muda isso com frequência: confirme na Central do Vendedor.")
    tabela = pd.DataFrame(
        [(f"R$ {lo:.2f}" + (f" a {hi - 0.01:.2f}" if hi < 1e8 else " ou mais"),
          f"{com:.0f}%", brl(fixa)) for lo, hi, com, fixa in TAXAS_SHOPEE],
        columns=["Preço do item", "Comissão", "Taxa fixa por item"],
    )
    st.dataframe(tabela, hide_index=True, use_container_width=True)
    st.number_input("Taxa extra por item (R$)", min_value=0.0, step=0.5, format="%.2f", key="cfg_shopee_extra",
                    help="Vendedor CPF com mais de 450 pedidos em 90 dias paga R$ 3,00 a mais por item. "
                         "Se não for seu caso, deixe 0.")

# ===============================================================
# ABA MATERIAIS
# ===============================================================
with aba_mat:
    st.header("Filamentos")
    st.caption("Clique na última linha para adicionar outros (TPU, ABS...). Edições valem até atualizar a página; "
               "para fixar, edite MATERIAIS_PADRAO no app.py.")
    st.session_state.materiais = st.data_editor(
        st.session_state.materiais, num_rows="dynamic", use_container_width=True, key="ed_mat",
        column_config={
            "Material": st.column_config.TextColumn("Material", required=True),
            "R$/kg": st.column_config.NumberColumn("R$/kg", min_value=0.0, format="%.2f", required=True),
        },
    )
    st.header("Acessórios")
    st.caption("Itens usados em algumas peças (aparecem na aba Calcular).")
    st.session_state.acessorios = st.data_editor(
        st.session_state.acessorios, num_rows="dynamic", use_container_width=True, key="ed_acc",
        column_config={
            "Item": st.column_config.TextColumn("Item", required=True),
            "R$ por unidade": st.column_config.NumberColumn("R$ por unidade", min_value=0.0,
                                                            format="%.2f", required=True),
        },
    )

# ===============================================================
# ABA CALCULAR
# ===============================================================
with aba_calc:
    mats = st.session_state.materiais.dropna(subset=["Material"])
    mats = mats[mats["Material"].astype(str).str.strip() != ""]
    if mats.empty:
        st.warning("Cadastre pelo menos um filamento na aba Materiais.")
        st.stop()

    nome_peca = st.text_input("Nome da peça ou pedido (opcional)", placeholder="Ex.: Suporte de headset")

    # ---------- 1. Impressão ----------
    st.header("🧵 1. Dados do fatiador")
    st.caption("Pegue no Bambu Studio / Orca depois de fatiar a peça.")
    c1, c2 = st.columns(2)
    material = c1.selectbox("Material", mats["Material"].tolist())
    qtd = c2.number_input("Quantas peças?", min_value=1, value=1, step=1,
                          help="Imprimiu 4 chaveiros juntos? Coloque o peso e o tempo TOTAIS e 4 aqui.")
    preco_kg = float(mats.loc[mats["Material"] == material, "R$/kg"].iloc[0])
    c1, c2, c3 = st.columns(3)
    gramas = c1.number_input("Peso total (g)", min_value=0.0, value=50.0, step=5.0, format="%.1f")
    horas_in = c2.number_input("Horas", min_value=0, value=3, step=1)
    min_in = c3.number_input("Minutos", min_value=0, max_value=59, value=0, step=5)
    horas = horas_in + min_in / 60

    # ---------- 2. Acabamento ----------
    st.header("🎨 2. Acabamento e embalagem")
    c1, c2, c3 = st.columns(3)
    h_acab = c1.number_input("Horas de acabamento", min_value=0.0, value=0.5, step=0.25, format="%.2f",
                             help="Lixar, pintar, montar. 15 minutos = 0,25")
    c_tinta = c2.number_input("Tinta / lixa / cola (R$)", min_value=0.0, value=0.0, step=0.5, format="%.2f")
    c_emb = c3.number_input("Embalagem por peça (R$)", min_value=0.0, value=3.5, step=0.5, format="%.2f")

    c_acess = 0.0
    acess = st.session_state.acessorios.dropna(subset=["Item"])
    if not acess.empty:
        with st.expander("➕ Acessórios (argola, ímã, parafuso...)"):
            for i, row in acess.reset_index(drop=True).iterrows():
                q = st.number_input(f"{row['Item']}  ({brl(row['R$ por unidade'])} cada) - por peça",
                                    min_value=0, value=0, step=1, key=f"acc_{i}_{row['Item']}")
                c_acess += q * float(row["R$ por unidade"]) * qtd

    # ---------- 3. Venda e lucro ----------
    st.header("💰 3. Onde vender e quanto lucrar")
    canal = st.radio("Canal de venda", ["Shopee", "Venda direta (Pix/WhatsApp)"], horizontal=True)
    modo = st.radio("Como ajustar o lucro?", ["Multiplicador (como no app antigo)", "Margem %"], horizontal=True)
    if modo.startswith("Multiplicador"):
        mult = st.slider("Multiplicador sobre o custo", 1.2, 3.0, 1.7, step=0.1)
        margem = 1 - 1 / mult
        st.caption("💡 **×1,3 a ×1,5** = preço bem competitivo · **×1,7 a ×2,0** = padrão · "
                   "**×2,2 ou mais** = peça personalizada ou exclusiva.")
    else:
        margem_pct = st.slider("Margem de lucro (%)", 10, 70, 40, step=5,
                               help="Parte do preço final que sobra de lucro.")
        margem = margem_pct / 100
        st.caption("💡 **20–30%** = competitivo · **40%** = padrão · **50–60%** = personalizada/exclusiva.")
    st.caption(f"Isso equivale a ficar com **{margem * 100:.0f}%** do preço de venda como lucro "
               f"(antes dos impostos que você eventualmente pague).")

    # ---------- cálculos ----------
    c_material = gramas / 1000 * preco_kg
    c_energia = horas * energia_hora
    c_maquina = horas * amort_hora
    c_base = c_material + c_energia + c_maquina
    c_falha = c_base / (1 - cfg("falha_pct") / 100) - c_base
    c_fabric = c_base + c_falha
    c_fixo = horas * fixo_hora
    c_mao = (h_acab + cfg("preparo_min") / 60) * cfg("mao_hora")
    c_insumos = c_tinta + c_emb * qtd + c_acess

    custo_total = c_fabric + c_fixo + c_mao + c_insumos
    custo_un = custo_total / qtd

    p_exato = preco_para_margem(custo_un, margem, canal, cfg("shopee_extra"))

    # ---------- resultado ----------
    st.divider()
    st.header("📋 Resultado" + (f": {nome_peca}" if nome_peca else ""))

    a, b = st.columns(2)
    a.metric("Fabricação", brl(c_fabric), help="Material + luz + desgaste da impressora + reserva para falhas")
    b.metric("Custos fixos", brl(c_fixo), help="Sua parte das contas do mês")
    a, b = st.columns(2)
    a.metric("Sua mão de obra", brl(c_mao), help="Preparo + acabamento")
    b.metric("Insumos + embalagem", brl(c_insumos))

    st.info(f"**Custo real de produção:** {brl(custo_total)}"
            + (f" ({brl(custo_un)} por peça)" if qtd > 1 else "") +
            "  \n🚫 Nunca venda abaixo disso, senão você paga para trabalhar.")

    if p_exato is None:
        st.error("Com essa margem e as taxas da Shopee, não existe preço que feche a conta. "
                 "Diminua o lucro ou escolha venda direta.")
        st.stop()

    preco_un = math.ceil(p_exato)  # preço para anunciar (arredondado para cima)
    if canal == "Shopee":
        com, fixa = taxa_shopee(preco_un, cfg("shopee_extra"))
        taxas_un = preco_un * com / 100 + fixa
    else:
        com, fixa, taxas_un = 0.0, 0.0, 0.0
    lucro_un = preco_un - taxas_un - custo_un

    st.success(f"### 🚀 Preço para anunciar: {brl(preco_un)}"
               + (" por peça" if qtd > 1 else ""))
    if qtd > 1:
        st.write(f"Pedido com {qtd} peças: **{brl(preco_un * qtd)}**")
    if canal == "Shopee":
        st.warning(f"**Taxas da Shopee:** {brl(taxas_un)} por item ({com:.0f}% + {brl(fixa)})  \n"
                   f"**Você recebe:** {brl(preco_un - taxas_un)} por item  \n"
                   f"**Seu lucro:** {brl(lucro_un)} por peça ({lucro_un / preco_un * 100:.0f}% do preço)")
    else:
        st.warning(f"**Seu lucro:** {brl(lucro_un)} por peça ({lucro_un / preco_un * 100:.0f}% do preço)")
    if qtd > 1:
        st.write(f"Lucro total do pedido: **{brl(lucro_un * qtd)}**")

    with st.expander("🔎 Ver onde vai cada centavo (por peça)"):
        det = pd.DataFrame(
            [
                ("Filamento", c_material / qtd),
                ("Energia", c_energia / qtd),
                ("Amortização da impressora", c_maquina / qtd),
                ("Reserva para falhas", c_falha / qtd),
                ("Custos fixos", c_fixo / qtd),
                ("Mão de obra", c_mao / qtd),
                ("Insumos + embalagem", c_insumos / qtd),
                ("Taxas da Shopee", taxas_un),
                ("Lucro", lucro_un),
            ],
            columns=["Item", "Valor"],
        )
        det["% do preço"] = (det["Valor"] / preco_un * 100).round(1)
        det["Valor"] = det["Valor"].apply(brl)
        st.dataframe(det, hide_index=True, use_container_width=True)
        st.caption("O preço é arredondado para cima. Perto de R$ 80, R$ 100 e R$ 200 a taxa da Shopee muda de "
                   "faixa, e o app já considera isso.")

    # ---------- 4. Mensagem para o WhatsApp ----------
    st.divider()
    st.header("📲 Mensagem para o WhatsApp")
    tipo_msg = st.radio("Qual mensagem?", ["Para o cliente", "Resumo interno (meus custos)"], horizontal=True)
    prazo = st.text_input("Prazo de entrega (opcional)", placeholder="Ex.: 3 dias úteis")

    titulo_peca = nome_peca.strip() if nome_peca.strip() else "Peça impressa em 3D"
    if tipo_msg == "Para o cliente":
        linhas = [
            "*Orçamento - Max3dLab* 🖨️",
            "",
            f"Peça: {titulo_peca}",
            f"Material: {material}",
            f"Quantidade: {qtd}",
        ]
        if qtd > 1:
            linhas.append(f"Valor unitário: {brl(preco_un)}")
        linhas.append(f"*Total: {brl(preco_un * qtd)}*")
        if prazo.strip():
            linhas.append(f"Prazo: {prazo.strip()}")
        mensagem = "\n".join(linhas)
    else:
        linhas = [
            f"*Resumo interno - {titulo_peca}*",
            f"Material: {material} | {gramas:.0f} g | {horas_in}h{min_in:02d}",
            f"Quantidade: {qtd}",
            f"Canal: {canal}",
            f"Custo total: {brl(custo_total)}",
            f"Preço por peça: {brl(preco_un)}",
        ]
        if canal == "Shopee":
            linhas.append(f"Taxas Shopee (por peça): {brl(taxas_un)}")
        linhas.append(f"*Lucro total: {brl(lucro_un * qtd)}*")
        mensagem = "\n".join(linhas)

    st.code(mensagem, language=None)  # o ícone no canto também copia o texto
    botao_copiar(mensagem)
    st.link_button("🟢 Abrir no WhatsApp", f"https://wa.me/?text={quote(mensagem)}",
                   use_container_width=True)
    st.caption("A mensagem **para o cliente** não mostra seus custos nem seu lucro. "
               "Para orçamento direto, escolha o canal **Venda direta** no passo 3, "
               "para o preço não incluir as taxas da Shopee.")

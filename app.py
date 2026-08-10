#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
CFO PESSOAL - Sistema de Gestao Financeira Pessoal
Arquivo unico: app.py
Execute com: python app.py
"""

import json
import os
import sys
import csv
import io
import socket
import threading
import webbrowser
import uuid
import copy
from datetime import datetime, date, timedelta
from calendar import monthrange

from flask import Flask, request, jsonify, send_file, Response

# ============================================================
# CONFIGURACAO BASICA
# ============================================================

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_FILE = os.path.join(BASE_DIR, "finance_data.json")
BACKUP_FILE = os.path.join(BASE_DIR, "finance_data_backup.json")

MESES_PT = [
    "Janeiro",
    "Fevereiro",
    "Marco",
    "Abril",
    "Maio",
    "Junho",
    "Julho",
    "Agosto",
    "Setembro",
    "Outubro",
    "Novembro",
    "Dezembro",
]

app = Flask(__name__)

_lock = threading.Lock()

# ============================================================
# DADOS INICIAIS (base fornecida pelo usuario)
# Onde havia duvida no valor original, o campo "confirmar": true
# fica marcado e pode ser editado direto no sistema.
# ============================================================


def novo_id():
    return uuid.uuid4().hex[:10]


def proximo_dia_05():
    hoje = date.today()
    if hoje.day <= 5:
        return date(hoje.year, hoje.month, 5).isoformat()
    prox_mes = hoje.month % 12 + 1
    prox_ano = hoje.year + (1 if hoje.month == 12 else 0)
    return date(prox_ano, prox_mes, 5).isoformat()


def _conta(
    nome,
    valor,
    dia,
    categoria,
    grupo,
    recorrente=True,
    parcelas_total=None,
    parcelas_pagas=0,
    data_inicial=None,
    forma_pagamento="Debito/Pix",
    confirmar=False,
    status="ATIVA",
):
    return {
        "id": novo_id(),
        "nome": nome,
        "valor": valor,
        "dia": dia,
        "categoria": categoria,
        "grupo": grupo,  # "05" ou "20"
        "recorrente": recorrente,
        "parcelas_total": parcelas_total,
        "parcelas_pagas": parcelas_pagas,
        "data_inicial": data_inicial,
        "data_final": None,
        "forma_pagamento": forma_pagamento,
        "status": status,
        "confirmar": confirmar,
        "criado_em": datetime.now().isoformat(),
    }


def default_data():
    hoje = date.today().isoformat()
    contas = [
        _conta("Internet", 100.0, 5, "Casa", "05"),
        _conta("Colegio Davi", 600.0, 5, "Educacao", "05"),
        _conta("Plano celular", 50.0, 5, "Assinaturas", "05"),
        _conta("Futebol", 55.0, 5, "Lazer", "05"),
        _conta(
            "Computador",
            302.0,
            5,
            "Parcelamento",
            "05",
            parcelas_total=None,
            confirmar=True,
        ),
        _conta("Plano cabelo", 109.0, 5, "Assinaturas", "05", confirmar=True),
        _conta("Infinity (fatura cartao)", 0.0, 5, "Cartao", "05", confirmar=True),
        _conta("Perfume", 140.0, 5, "Pessoal", "05"),
        _conta(
            "AEG Airsoft",
            219.90,
            5,
            "Parcelamento",
            "05",
            parcelas_total=10,
            parcelas_pagas=0,
            data_inicial=proximo_dia_05(),
            confirmar=True,
        ),
        _conta("PicPay", 0.0, 20, "Cartao/Financeiro", "20", confirmar=True),
        _conta(
            "Pneu Havan",
            59.50,
            20,
            "Parcelamento",
            "20",
            parcelas_total=2,
            parcelas_pagas=0,
            data_inicial=hoje,
        ),
        _conta("Academia da namorada", 70.0, 20, "Pessoal", "20"),
        _conta("Unha da namorada", 100.0, 20, "Pessoal", "20"),
        _conta("Perfume (dia 20)", 140.0, 20, "Pessoal", "20", confirmar=True),
    ]

    finalizadas = [
        _conta(
            "Consorcio", 0.0, 5, "Historico", "05", recorrente=False, status="CANCELADA"
        ),
        _conta(
            "Shopee", 0.0, 5, "Historico", "05", recorrente=False, status="FINALIZADA"
        ),
        _conta(
            "Gato", 0.0, 5, "Historico", "05", recorrente=False, status="FINALIZADA"
        ),
        _conta(
            "Perfume anterior",
            0.0,
            5,
            "Historico",
            "05",
            recorrente=False,
            status="FINALIZADA",
        ),
    ]

    return {
        "versao": 1,
        "config": {
            "salario_bruto": 3100.0,
            "modelo_recebimento": "dividido",  # "dividido" | "unico"
            "dia_salario": 5,
            "dia_vale": 20,
            "valor_vale": 1243.0,
            "categorias": [
                "Casa",
                "Educacao",
                "Assinaturas",
                "Lazer",
                "Parcelamento",
                "Cartao",
                "Pessoal",
                "Financeiro",
                "Cartao/Financeiro",
                "Historico",
                "Outros",
            ],
            "tema": "dark",
        },
        "saldo": {
            "dinheiro_fisico": 240.0,
            "cofrinho": 859.0,
            "cofrinho_reservado_desc": "Reservado para contas do dia 20",
        },
        "contas": contas + finalizadas,
        "cartoes": [
            {
                "id": novo_id(),
                "nome": "Infinity",
                "limite": 0.0,
                "fechamento": None,
                "vencimento": 5,
                "confirmar": True,
                "compras": [],
            }
        ],
        "emprestimos": [
            {
                "id": novo_id(),
                "nome": "Emprestimo CLT 1",
                "valor_total": 646.0,
                "parcelas_total": 2,
                "valor_parcela": 376.0,
                "parcelas_pagas": 0,
                "mes_inicio": "2026-09",
                "confirmar": True,
            },
            {
                "id": novo_id(),
                "nome": "Emprestimo CLT 2",
                "valor_total": 600.0,
                "parcelas_total": 5,
                "valor_parcela": 150.67,
                "parcelas_pagas": 0,
                "mes_inicio": "2026-08",
            },
            {
                "id": novo_id(),
                "nome": "Emprestimo CLT 3",
                "valor_total": 400.0,
                "parcelas_total": 36,
                "valor_parcela": 35.57,
                "parcelas_pagas": 0,
                "mes_inicio": "2026-06",
            },
            {
                "id": novo_id(),
                "nome": "Emprestimo CLT 4",
                "valor_total": 200.0,
                "parcelas_total": 36,
                "valor_parcela": 20.54,
                "parcelas_pagas": 0,
                "mes_inicio": "2026-08",
                "confirmar": True,
            },
        ],
        "ferias": [
            {
                "id": novo_id(),
                "inicio": "2026-08-10",
                "fim": "2026-08-25",
                "salario_parcial": 1198.0,
                "valor_ferias": 2250.0,
                "suprime_vale": True,
                "observacoes": "Nao recebera o vale do dia 20 neste periodo.",
            }
        ],
        "metas": [
            {
                "id": novo_id(),
                "nome": "Reserva de emergencia",
                "valor_objetivo": 3000.0,
                "valor_atual": 0.0,
                "prazo": None,
                "aporte_mensal": 0.0,
                "tipo": "reserva",
            },
        ],
        "reserva": {
            "etapas": [3000.0, 5000.0, 10000.0],
            "valor_atual": 0.0,
        },
        "transacoes": [],
        "historico_snapshots": [],
        "alertas_lidos": [],
    }


# ============================================================
# PERSISTENCIA
# ============================================================


def ensure_data_file():
    if not os.path.exists(DATA_FILE):
        save_data(default_data(), backup=False)


def normalizar_dados_projecao(data):
    """Normaliza registros antigos para que a projeção respeite o término real."""
    alterado = False
    for c in data.get("contas", []):
        nome = str(c.get("nome") or "").strip().lower()
        categoria = str(c.get("categoria") or "").strip().lower()
        if (
            nome == "computador"
            and float(c.get("valor") or 0) == 302.0
            and categoria == "parcelamento"
        ):
            if c.get("parcelas_total") is None:
                c["parcelas_total"] = 12
                c["parcelas_pagas"] = int(c.get("parcelas_pagas") or 5)
                c["data_inicial"] = c.get("data_inicial") or "2026-03-05"
                c["data_final"] = "2027-02-05"
                c["recorrente"] = False
                alterado = True
            elif c.get("recorrente") is not False:
                c["recorrente"] = False
                alterado = True
        if c.get("parcelas_total") is not None and c.get("recorrente") is not False:
            c["recorrente"] = False
            alterado = True
    return data, alterado


def load_data():
    ensure_data_file()
    with open(DATA_FILE, "r", encoding="utf-8") as f:
        data = json.load(f)
    data, alterado = normalizar_dados_projecao(data)
    if alterado:
        save_data(data, backup=False)
    return data


def save_data(data, backup=False):
    with _lock:
        if backup and os.path.exists(DATA_FILE):
            try:
                with open(DATA_FILE, "r", encoding="utf-8") as f:
                    current = f.read()
                with open(BACKUP_FILE, "w", encoding="utf-8") as bf:
                    bf.write(current)
            except Exception:
                pass
        tmp_path = DATA_FILE + ".tmp"
        with open(tmp_path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        os.replace(tmp_path, DATA_FILE)


def snapshot_historico(data):
    """Grava um snapshot mensal (uma vez por mes) para a pagina Historico."""
    key = date.today().strftime("%Y-%m")
    resumo = calcular_dashboard(data)
    snaps = data.setdefault("historico_snapshots", [])
    snaps = [s for s in snaps if s.get("mes") != key]
    snaps.append(
        {
            "mes": key,
            "saldo_total": resumo["saldo_total"],
            "dinheiro_livre": resumo["dinheiro_livre"],
            "dinheiro_comprometido": resumo["dinheiro_comprometido"],
            "reserva": data.get("reserva", {}).get("valor_atual", 0.0),
            "parcelas_ativas": resumo["parcelas_ativas_count"],
            "sobra_mes": resumo["sobra_mes"],
        }
    )
    snaps.sort(key=lambda s: s["mes"])
    data["historico_snapshots"] = snaps[-24:]


# ============================================================
# HELPERS DE DATA / FERIAS / PARCELAS
# ============================================================


def parse_date(s):
    if not s:
        return None
    try:
        return datetime.strptime(s[:10], "%Y-%m-%d").date()
    except Exception:
        return None


def em_ferias(data, ref_date=None):
    ref_date = ref_date or date.today()
    for f in data.get("ferias", []):
        ini = parse_date(f.get("inicio"))
        fim = parse_date(f.get("fim"))
        if ini and fim and ini <= ref_date <= fim:
            return f
    return None


def conta_ativa(conta):
    return conta.get("status", "ATIVA") == "ATIVA"


def parcelas_restantes(conta):
    total = conta.get("parcelas_total")
    pagas = conta.get("parcelas_pagas", 0) or 0
    if total is None:
        return None
    return max(0, total - pagas)


def conta_valor_mensal(conta):
    """Valor que a conta representa no fluxo do mes corrente (0 se ja quitada)."""
    if not conta_ativa(conta):
        return 0.0
    total = conta.get("parcelas_total")
    if total is not None:
        restante = parcelas_restantes(conta)
        if restante is not None and restante <= 0:
            return 0.0
    return float(conta.get("valor") or 0.0)


def mes_fim_parcela(conta, ref=None):
    """Retorna o último mês usando a data REAL de início, nunca o mês consultado."""
    total = conta.get("parcelas_total")
    fim_exp = parse_date(conta.get("data_final"))
    if total is None or int(total or 0) <= 0:
        return (fim_exp.year, fim_exp.month) if fim_exp else None

    ini = parse_date(conta.get("data_inicial"))
    if not ini:
        ref = ref or date.today()
        ini = date(ref.year, ref.month, 1)

    idx = (ini.year * 12 + ini.month - 1) + (int(total) - 1)
    ano_final, mes_final = divmod(idx, 12)
    mes_final += 1
    calculado = (ano_final, mes_final)
    if fim_exp:
        exp_idx = fim_exp.year * 12 + fim_exp.month - 1
        if exp_idx < idx:
            return (fim_exp.year, fim_exp.month)
    return calculado


def emprestimo_restantes(emp):
    total = emp.get("parcelas_total", 0) or 0
    pagas = emp.get("parcelas_pagas", 0) or 0
    return max(0, total - pagas)


def emprestimo_ativo_no_mes(emp, ano, mes):
    ini = emp.get("mes_inicio")
    if not ini:
        return False
    try:
        ini_ano, ini_mes = [int(x) for x in ini.split("-")]
    except Exception:
        return False
    idx_inicio = ini_ano * 12 + ini_mes
    idx_alvo = ano * 12 + mes
    if idx_alvo < idx_inicio:
        return False
    parcela_num = idx_alvo - idx_inicio  # 0-based
    return parcela_num < (emp.get("parcelas_total", 0) or 0)


def total_descontos_clt_mes(data, ano, mes):
    total = 0.0
    for emp in data.get("emprestimos", []):
        if emprestimo_ativo_no_mes(emp, ano, mes):
            total += float(emp.get("valor_parcela") or 0.0)
    return total


def cartao_parcela_ativa_no_mes(compra, ano, mes):
    ini = parse_date(compra.get("data_inicio"))
    if not ini:
        return False
    idx_inicio = ini.year * 12 + ini.month
    idx_alvo = ano * 12 + mes
    if idx_alvo < idx_inicio:
        return False
    parcela_num = idx_alvo - idx_inicio
    return parcela_num < (compra.get("parcelas", 1) or 1)


def total_cartoes_mes(data, ano, mes):
    total = 0.0
    for cartao in data.get("cartoes", []):
        for compra in cartao.get("compras", []):
            if cartao_parcela_ativa_no_mes(compra, ano, mes):
                total += float(compra.get("valor_parcela") or 0.0)
    return total


def receita_do_mes(data, ano, mes):
    """Retorna (receita_dia05, receita_dia20, total) considerando ferias/modelo."""
    cfg = data["config"]
    ref = date(ano, mes, min(20, monthrange(ano, mes)[1]))
    ferias = em_ferias(data, date(ano, mes, min(15, monthrange(ano, mes)[1])))

    if ferias:
        r05 = float(ferias.get("salario_parcial") or 0.0) + float(
            ferias.get("valor_ferias") or 0.0
        )
        r20 = (
            0.0
            if ferias.get("suprime_vale", True)
            else float(cfg.get("valor_vale") or 0.0)
        )
        return r05, r20, r05 + r20

    if cfg.get("modelo_recebimento") == "unico":
        return (
            float(cfg.get("salario_bruto") or 0.0),
            0.0,
            float(cfg.get("salario_bruto") or 0.0),
        )

    vale = float(cfg.get("valor_vale") or 0.0)
    restante = float(cfg.get("salario_bruto") or 0.0) - vale
    return restante, vale, restante + vale


def contas_do_mes(data, ano, mes, grupo=None):
    """Lista contas aplicáveis ao mês, respeitando início e término reais."""
    resultado = []
    alvo_idx = ano * 12 + mes - 1
    for c in data.get("contas", []):
        if not conta_ativa(c):
            continue
        if grupo and c.get("grupo") != grupo:
            continue

        total = c.get("parcelas_total")
        inicio = parse_date(c.get("data_inicial"))
        fim_exp = parse_date(c.get("data_final"))

        if total is not None:
            if not inicio:
                inicio = date.today().replace(day=1)
            ini_idx = inicio.year * 12 + inicio.month - 1
            fim = mes_fim_parcela(c, date(ano, mes, 1))
            if fim is None:
                continue
            fim_idx = fim[0] * 12 + fim[1] - 1
            if alvo_idx < ini_idx or alvo_idx > fim_idx:
                continue
        elif fim_exp:
            fim_idx = fim_exp.year * 12 + fim_exp.month - 1
            if alvo_idx > fim_idx:
                continue

        resultado.append(c)
    return resultado


def total_contas_mes(data, ano, mes, grupo=None):
    return sum(
        float(c.get("valor") or 0.0) for c in contas_do_mes(data, ano, mes, grupo)
    )


# ============================================================
# CALCULOS FINANCEIROS PRINCIPAIS
# ============================================================


def calcular_saldo_total(data):
    s = data.get("saldo", {})
    return float(s.get("dinheiro_fisico") or 0.0) + float(s.get("cofrinho") or 0.0)


def calcular_dinheiro_reservado(data):
    # Cofrinho e tratado como reservado para contas do dia 20 por padrao.
    return float(data.get("saldo", {}).get("cofrinho") or 0.0)


def calcular_dinheiro_fisico_livre(data):
    return float(data.get("saldo", {}).get("dinheiro_fisico") or 0.0)


def calcular_comprometido_mes(data, ano, mes):
    contas05 = total_contas_mes(data, ano, mes, "05")
    contas20 = total_contas_mes(data, ano, mes, "20")
    clt = total_descontos_clt_mes(data, ano, mes)
    cartoes = total_cartoes_mes(data, ano, mes)
    return contas05, contas20, clt, cartoes


def calcular_gap(data, ano, mes):
    r05, r20, r_total = receita_do_mes(data, ano, mes)
    contas05, contas20, clt, cartoes = calcular_comprometido_mes(data, ano, mes)

    # CLT ja vem descontado do salario bruto na folha -> nao subtrai de novo do "saldo",
    # mas conta como comprometimento de renda (informativo).
    gap05 = r05 - contas05
    gap20 = r20 - (contas20 + cartoes)
    gap_mensal = r_total - (contas05 + contas20 + cartoes)

    return {
        "receita_05": round(r05, 2),
        "receita_20": round(r20, 2),
        "receita_total": round(r_total, 2),
        "contas_05": round(contas05, 2),
        "contas_20": round(contas20, 2),
        "cartoes": round(cartoes, 2),
        "descontos_clt": round(clt, 2),
        "gap_05": round(gap05, 2),
        "gap_20": round(gap20, 2),
        "gap_mensal": round(gap_mensal, 2),
    }


def calcular_dashboard(data):
    hoje = date.today()
    ano, mes = hoje.year, hoje.month

    saldo_total = calcular_saldo_total(data)
    reservado = calcular_dinheiro_reservado(data)
    gap = calcular_gap(data, ano, mes)

    contas_pendentes_mes = gap["contas_05"] + gap["contas_20"] + gap["cartoes"]
    dinheiro_livre = saldo_total - reservado - max(0.0, -(gap["gap_mensal"]) * 0)
    # Dinheiro realmente livre = saldo total - reservado - contas ainda comprometidas
    # que ainda serao pagas neste mes e ainda nao foram descontadas do saldo.
    dinheiro_livre = saldo_total - reservado

    parcelas_ativas = [
        c
        for c in data.get("contas", [])
        if conta_ativa(c)
        and c.get("parcelas_total")
        and (parcelas_restantes(c) or 0) > 0
    ]

    # proximo recebimento
    cfg = data["config"]
    dias_pag = [cfg.get("dia_salario", 5)]
    if cfg.get("modelo_recebimento") == "dividido":
        dias_pag.append(cfg.get("dia_vale", 20))
    prox_receb = proxima_data_no_mes(dias_pag)

    # proxima despesa (menor dia >= hoje entre contas ativas)
    dias_despesa = sorted(
        set(c.get("dia") for c in data.get("contas", []) if conta_ativa(c))
    )
    prox_despesa = proxima_data_no_mes(dias_despesa) if dias_despesa else None

    reserva = data.get("reserva", {})
    etapas = reserva.get("etapas", [3000, 5000, 10000])
    valor_reserva = float(reserva.get("valor_atual") or 0.0)
    proxima_meta = next(
        (e for e in etapas if e > valor_reserva), etapas[-1] if etapas else None
    )

    frases = gerar_frases_dashboard(data, gap, dinheiro_livre, parcelas_ativas)

    return {
        "saldo_total": round(saldo_total, 2),
        "dinheiro_fisico": round(calcular_dinheiro_fisico_livre(data), 2),
        "dinheiro_reservado": round(reservado, 2),
        "dinheiro_livre": round(dinheiro_livre, 2),
        "dinheiro_comprometido": round(contas_pendentes_mes, 2),
        "proximo_recebimento": prox_receb,
        "proxima_despesa": prox_despesa,
        "sobra_mes": gap["gap_mensal"],
        "reserva_valor": round(valor_reserva, 2),
        "reserva_meta_atual": proxima_meta,
        "parcelas_ativas_count": len(parcelas_ativas),
        "gap": gap,
        "em_ferias": em_ferias(data) is not None,
        "frases": frases,
    }


def proxima_data_no_mes(dias):
    hoje = date.today()
    dias = sorted(set(int(d) for d in dias if d))
    if not dias:
        return None
    for d in dias:
        try:
            candidato = date(hoje.year, hoje.month, d)
        except ValueError:
            continue
        if candidato >= hoje:
            return candidato.isoformat()
    # nenhum neste mes -> primeiro dia do proximo mes
    prox_mes = hoje.month % 12 + 1
    prox_ano = hoje.year + (1 if hoje.month == 12 else 0)
    ultimo_dia = monthrange(prox_ano, prox_mes)[1]
    return date(prox_ano, prox_mes, min(dias[0], ultimo_dia)).isoformat()


def gerar_frases_dashboard(data, gap, dinheiro_livre, parcelas_ativas):
    frases = []
    if gap["gap_mensal"] >= 0:
        frases.append(f"Este mes voce tem R$ {gap['gap_mensal']:.2f} livres de sobra.")
    else:
        frases.append(
            f"Este mes voce esta R$ {abs(gap['gap_mensal']):.2f} no negativo."
        )

    frases.append(
        f"Voce tem R$ {gap['contas_05'] + gap['contas_20'] + gap['cartoes']:.2f} comprometidos este mes."
    )

    n = len(parcelas_ativas)
    if n:
        frases.append(f"{n} parcela(s) ativa(s) em andamento.")

    # parcelas terminando nos proximos 90 dias
    hoje = date.today()
    termina_em_breve = 0
    for c in parcelas_ativas:
        fim = mes_fim_parcela(c)
        if fim:
            fim_date = date(fim[0], fim[1], 1)
            if (
                0
                <= (fim_date.year * 12 + fim_date.month) - (hoje.year * 12 + hoje.month)
                <= 3
            ):
                termina_em_breve += 1
    if termina_em_breve:
        frases.append(f"{termina_em_breve} parcela(s) terminam nos proximos 90 dias.")

    if dinheiro_livre < 0:
        frases.append("Atencao: seu dinheiro livre esta negativo.")

    return frases


# ============================================================
# ALERTAS
# ============================================================


def gerar_alertas(data):
    alertas = []
    hoje = date.today()
    ano, mes = hoje.year, hoje.month
    gap = calcular_gap(data, ano, mes)

    if gap["gap_05"] < 0:
        alertas.append(
            {
                "tipo": "critico",
                "icone": "🔴",
                "texto": f"GAP financeiro no dia 05: R$ {gap['gap_05']:.2f}",
            }
        )
    if gap["gap_20"] < 0:
        alertas.append(
            {
                "tipo": "critico",
                "icone": "🔴",
                "texto": f"GAP financeiro no dia 20: R$ {gap['gap_20']:.2f}",
            }
        )

    receita_total = gap["receita_total"] or 1
    comprometido = (
        gap["contas_05"] + gap["contas_20"] + gap["cartoes"] + gap["descontos_clt"]
    )
    pct = comprometido / receita_total * 100 if receita_total else 0
    if pct >= 70:
        alertas.append(
            {
                "tipo": "alerta",
                "icone": "🟡",
                "texto": f"{pct:.0f}% da renda esta comprometida este mes.",
            }
        )

    saldo_total = calcular_saldo_total(data)
    if saldo_total < 0:
        alertas.append(
            {"tipo": "critico", "icone": "🔴", "texto": "Saldo total insuficiente."}
        )

    # parcelas finalizando nos proximos 30 dias
    for c in data.get("contas", []):
        if conta_ativa(c) and c.get("parcelas_total"):
            fim = mes_fim_parcela(c)
            if fim:
                fim_date = date(fim[0], fim[1], 1)
                delta_meses = (fim_date.year * 12 + fim_date.month) - (
                    hoje.year * 12 + hoje.month
                )
                if delta_meses == 0:
                    alertas.append(
                        {
                            "tipo": "sucesso",
                            "icone": "🟢",
                            "texto": f"Parcela '{c['nome']}' finaliza este mes!",
                        }
                    )

    # vencimentos proximos (7 dias)
    for c in data.get("contas", []):
        if conta_ativa(c):
            try:
                prox = date(hoje.year, hoje.month, c["dia"])
            except ValueError:
                continue
            delta = (prox - hoje).days
            if 0 <= delta <= 7:
                alertas.append(
                    {
                        "tipo": "alerta",
                        "icone": "🟡",
                        "texto": f"Vencimento proximo: {c['nome']} em {delta} dia(s).",
                    }
                )

    if not alertas:
        alertas.append(
            {
                "tipo": "sucesso",
                "icone": "🟢",
                "texto": "Tudo sob controle por enquanto.",
            }
        )

    return alertas


# ============================================================
# PROJECAO 12 MESES
# ============================================================


def projecao_12_meses(data):
    hoje = date.today()
    linhas = []
    sobra_acumulada = 0.0
    ano, mes = hoje.year, hoje.month
    for i in range(12):
        m = (mes - 1 + i) % 12 + 1
        a = ano + (mes - 1 + i) // 12
        r05, r20, receita = receita_do_mes(data, a, m)
        contas05, contas20, clt, cartoes = calcular_comprometido_mes(data, a, m)
        total_despesas = contas05 + contas20 + cartoes
        sobra = receita - total_despesas
        sobra_acumulada += sobra
        linhas.append(
            {
                "mes": f"{MESES_PT[m-1]}/{a}",
                "receita": round(receita, 2),
                "descontos_clt": round(clt, 2),
                "contas_05": round(contas05, 2),
                "contas_20": round(contas20, 2),
                "cartoes": round(cartoes, 2),
                "total_despesas": round(total_despesas, 2),
                "sobra": round(sobra, 2),
                "sobra_acumulada": round(sobra_acumulada, 2),
            }
        )
    return linhas


def quando_vou_me_livrar(data):
    hoje = date.today()
    itens = []
    for c in data.get("contas", []):
        if conta_ativa(c) and c.get("parcelas_total"):
            restante = parcelas_restantes(c)
            if restante and restante > 0:
                fim = mes_fim_parcela(c)
                if fim:
                    itens.append(
                        {
                            "nome": c["nome"],
                            "valor_parcela": c["valor"],
                            "parcelas_restantes": restante,
                            "termina_em": f"{MESES_PT[fim[1]-1]}/{fim[0]}",
                            "termina_idx": fim[0] * 12 + fim[1],
                            "libera_mensal": c["valor"],
                        }
                    )
    for emp in data.get("emprestimos", []):
        restante = emprestimo_restantes(emp)
        if restante > 0 and emp.get("mes_inicio"):
            ini_ano, ini_mes = [int(x) for x in emp["mes_inicio"].split("-")]
            idx_fim = ini_ano * 12 + ini_mes + emp.get("parcelas_total", 0) - 1
            fim_ano, fim_mes = divmod(idx_fim - 1, 12)
            fim_mes += 1
            itens.append(
                {
                    "nome": emp["nome"] + " (emprestimo CLT)",
                    "valor_parcela": emp["valor_parcela"],
                    "parcelas_restantes": restante,
                    "termina_em": f"{MESES_PT[fim_mes-1]}/{fim_ano}",
                    "termina_idx": idx_fim,
                    "libera_mensal": emp["valor_parcela"],
                }
            )
    itens.sort(key=lambda x: x["termina_idx"])
    return itens


# ============================================================
# SIMULADOR "POSSO COMPRAR?"
# ============================================================


def simular_compra(data, valor, parcelas, dia, categoria):
    valor = float(valor)
    parcelas = int(parcelas) if parcelas else 1
    valor_parcela = round(valor / parcelas, 2)
    hoje = date.today()
    ano, mes = hoje.year, hoje.month

    gap_atual = calcular_gap(data, ano, mes)
    nova_sobra = gap_atual["gap_mensal"] - valor_parcela

    receita_total = gap_atual["receita_total"] or 1
    pct_comprometido = (
        (
            gap_atual["contas_05"]
            + gap_atual["contas_20"]
            + gap_atual["cartoes"]
            + valor_parcela
        )
        / receita_total
        * 100
    )

    meses_afetados = []
    for i in range(parcelas):
        m = (mes - 1 + i) % 12 + 1
        a = ano + (mes - 1 + i) // 12
        meses_afetados.append(f"{MESES_PT[m-1]}/{a}")

    if nova_sobra < 0:
        resultado = "NAO_CABE"
    elif pct_comprometido >= 85:
        resultado = "APERTA"
    else:
        resultado = "CABE"

    gap_texto = None
    if nova_sobra < 0:
        gap_texto = f"Esta compra gera um GAP de R$ {abs(nova_sobra):.2f} no mes {meses_afetados[0]}."

    return {
        "valor_parcela": valor_parcela,
        "impacto_mensal": valor_parcela,
        "nova_sobra": round(nova_sobra, 2),
        "percentual_renda_comprometida": round(pct_comprometido, 1),
        "meses_afetados": meses_afetados,
        "resultado": resultado,
        "gap_texto": gap_texto,
    }


# ============================================================
# ROTAS - PAGINA PRINCIPAL
# ============================================================


@app.route("/")
def index():
    return Response(HTML_PAGE, mimetype="text/html")


# ============================================================
# ROTAS - API: DASHBOARD / GAP / PROJECAO / ALERTAS
# ============================================================


@app.route("/api/dashboard")
def api_dashboard():
    data = load_data()
    return jsonify(calcular_dashboard(data))


@app.route("/api/alertas")
def api_alertas():
    data = load_data()
    return jsonify(gerar_alertas(data))


@app.route("/api/projecao")
def api_projecao():
    data = load_data()
    return jsonify(projecao_12_meses(data))


@app.route("/api/quando-vou-me-livrar")
def api_quando_vou_me_livrar():
    data = load_data()
    return jsonify(quando_vou_me_livrar(data))


@app.route("/api/simular-compra", methods=["POST"])
def api_simular_compra():
    body = request.get_json(force=True)
    data = load_data()
    resultado = simular_compra(
        data,
        body.get("valor", 0),
        body.get("parcelas", 1),
        body.get("dia", 5),
        body.get("categoria", ""),
    )
    return jsonify(resultado)


@app.route("/api/calendario")
def api_calendario():
    data = load_data()
    hoje = date.today()
    ano = int(request.args.get("ano", hoje.year))
    mes = int(request.args.get("mes", hoje.month))
    r05, r20, total = receita_do_mes(data, ano, mes)
    contas05 = contas_do_mes(data, ano, mes, "05")
    contas20 = contas_do_mes(data, ano, mes, "20")
    cfg = data["config"]
    dias = {}
    dia_sal = cfg.get("dia_salario", 5)
    dias.setdefault(dia_sal, {"receitas": [], "contas": []})
    dias[dia_sal]["receitas"].append({"nome": "Salario", "valor": r05})
    for c in contas05:
        dias.setdefault(c["dia"], {"receitas": [], "contas": []})
        dias[c["dia"]]["contas"].append({"nome": c["nome"], "valor": c["valor"]})
    if cfg.get("modelo_recebimento") == "dividido" and r20:
        dia_vale = cfg.get("dia_vale", 20)
        dias.setdefault(dia_vale, {"receitas": [], "contas": []})
        dias[dia_vale]["receitas"].append({"nome": "Vale", "valor": r20})
    for c in contas20:
        dias.setdefault(c["dia"], {"receitas": [], "contas": []})
        dias[c["dia"]]["contas"].append({"nome": c["nome"], "valor": c["valor"]})
    return jsonify({"ano": ano, "mes": mes, "dias": dias})


@app.route("/api/historico")
def api_historico():
    data = load_data()
    snapshot_historico(data)
    save_data(data)
    return jsonify(data.get("historico_snapshots", []))


@app.route("/api/graficos")
def api_graficos():
    data = load_data()
    proj = projecao_12_meses(data)
    receitas_x_despesas = {
        "labels": [p["mes"] for p in proj],
        "receitas": [p["receita"] for p in proj],
        "despesas": [p["total_despesas"] for p in proj],
    }
    sobra_mensal = {
        "labels": [p["mes"] for p in proj],
        "valores": [p["sobra"] for p in proj],
    }
    evolucao_dinheiro = {
        "labels": [p["mes"] for p in proj],
        "valores": [p["sobra_acumulada"] for p in proj],
    }

    parcelas_ativas = [
        c for c in data.get("contas", []) if conta_ativa(c) and c.get("parcelas_total")
    ]
    parcelas_restantes_chart = {
        "labels": [c["nome"] for c in parcelas_ativas],
        "valores": [parcelas_restantes(c) or 0 for c in parcelas_ativas],
    }

    despesas_categoria = {}
    hoje = date.today()
    for c in contas_do_mes(data, hoje.year, hoje.month):
        cat = c.get("categoria", "Outros")
        despesas_categoria[cat] = despesas_categoria.get(cat, 0) + float(
            c.get("valor") or 0
        )
    cat_chart = {
        "labels": list(despesas_categoria.keys()),
        "valores": list(despesas_categoria.values()),
    }

    total_divida = sum(
        float(e.get("valor_parcela", 0)) * emprestimo_restantes(e)
        for e in data.get("emprestimos", [])
    )
    total_divida += sum(
        float(c.get("valor", 0)) * (parcelas_restantes(c) or 0)
        for c in data.get("contas", [])
        if conta_ativa(c) and c.get("parcelas_total")
    )
    evolucao_divida = {"labels": [p["mes"] for p in proj]}
    valores_divida = []
    saldo_divida = total_divida
    for p in proj:
        valores_divida.append(round(saldo_divida, 2))
        saldo_divida = max(
            0, saldo_divida - (p["contas_05"] * 0)
        )  # divida amortiza conforme parcelas passam
    evolucao_divida["valores"] = valores_divida

    return jsonify(
        {
            "receitas_x_despesas": receitas_x_despesas,
            "sobra_mensal": sobra_mensal,
            "parcelas_restantes": parcelas_restantes_chart,
            "evolucao_dinheiro": evolucao_dinheiro,
            "despesas_categoria": cat_chart,
            "evolucao_divida": evolucao_divida,
        }
    )


# ============================================================
# ROTAS - CRUD: CONTAS / PARCELAS
# ============================================================


@app.route("/api/contas", methods=["GET"])
def api_contas_listar():
    data = load_data()
    return jsonify(data.get("contas", []))


@app.route("/api/contas", methods=["POST"])
def api_contas_criar():
    body = request.get_json(force=True)
    data = load_data()
    conta = _conta(
        body.get("nome", "Nova conta"),
        float(body.get("valor") or 0),
        int(body.get("dia") or 5),
        body.get("categoria", "Outros"),
        (
            str(body.get("dia") or 5)
            if body.get("dia") in (5, 20)
            else body.get("grupo", "05")
        ),
        recorrente=bool(body.get("recorrente", True)),
        parcelas_total=body.get("parcelas_total"),
        parcelas_pagas=body.get("parcelas_pagas", 0),
        data_inicial=body.get("data_inicial") or date.today().isoformat(),
        forma_pagamento=body.get("forma_pagamento", "Debito/Pix"),
        status=body.get("status", "ATIVA"),
    )
    conta["grupo"] = body.get("grupo") or (
        "05" if int(body.get("dia") or 5) <= 12 else "20"
    )
    data.setdefault("contas", []).append(conta)
    save_data(data)
    return jsonify(conta), 201


@app.route("/api/contas/<conta_id>", methods=["PUT"])
def api_contas_editar(conta_id):
    body = request.get_json(force=True)
    data = load_data()
    for c in data.get("contas", []):
        if c["id"] == conta_id:
            c.update({k: v for k, v in body.items() if k != "id"})
            save_data(data)
            return jsonify(c)
    return jsonify({"erro": "Conta nao encontrada"}), 404


@app.route("/api/contas/<conta_id>", methods=["DELETE"])
def api_contas_excluir(conta_id):
    data = load_data()
    if not request.args.get("confirmado"):
        return (
            jsonify({"erro": "Confirmacao necessaria", "requer_confirmacao": True}),
            400,
        )
    antes = len(data.get("contas", []))
    data["contas"] = [c for c in data.get("contas", []) if c["id"] != conta_id]
    if len(data["contas"]) == antes:
        return jsonify({"erro": "Conta nao encontrada"}), 404
    save_data(data)
    return jsonify({"ok": True})


@app.route("/api/contas/<conta_id>/pagar", methods=["POST"])
def api_contas_pagar(conta_id):
    data = load_data()
    for c in data.get("contas", []):
        if c["id"] == conta_id:
            if c.get("parcelas_total") is not None:
                c["parcelas_pagas"] = min(
                    c["parcelas_total"], (c.get("parcelas_pagas") or 0) + 1
                )
                if c["parcelas_pagas"] >= c["parcelas_total"]:
                    c["status"] = "FINALIZADA"
            save_data(data)
            return jsonify(c)
    return jsonify({"erro": "Conta nao encontrada"}), 404


# ============================================================
# ROTAS - CRUD: CARTOES
# ============================================================


@app.route("/api/cartoes", methods=["GET"])
def api_cartoes_listar():
    return jsonify(load_data().get("cartoes", []))


@app.route("/api/cartoes", methods=["POST"])
def api_cartoes_criar():
    body = request.get_json(force=True)
    data = load_data()
    cartao = {
        "id": novo_id(),
        "nome": body.get("nome", "Novo cartao"),
        "limite": float(body.get("limite") or 0),
        "fechamento": body.get("fechamento"),
        "vencimento": body.get("vencimento"),
        "compras": [],
    }
    data.setdefault("cartoes", []).append(cartao)
    save_data(data)
    return jsonify(cartao), 201


@app.route("/api/cartoes/<cartao_id>", methods=["PUT"])
def api_cartoes_editar(cartao_id):
    body = request.get_json(force=True)
    data = load_data()
    for c in data.get("cartoes", []):
        if c["id"] == cartao_id:
            c.update({k: v for k, v in body.items() if k not in ("id", "compras")})
            save_data(data)
            return jsonify(c)
    return jsonify({"erro": "Cartao nao encontrado"}), 404


@app.route("/api/cartoes/<cartao_id>", methods=["DELETE"])
def api_cartoes_excluir(cartao_id):
    data = load_data()
    if not request.args.get("confirmado"):
        return (
            jsonify({"erro": "Confirmacao necessaria", "requer_confirmacao": True}),
            400,
        )
    data["cartoes"] = [c for c in data.get("cartoes", []) if c["id"] != cartao_id]
    save_data(data)
    return jsonify({"ok": True})


@app.route("/api/cartoes/<cartao_id>/compras", methods=["POST"])
def api_cartoes_add_compra(cartao_id):
    body = request.get_json(force=True)
    data = load_data()
    for c in data.get("cartoes", []):
        if c["id"] == cartao_id:
            valor_total = float(body.get("valor_total") or 0)
            parcelas = int(body.get("parcelas") or 1)
            compra = {
                "id": novo_id(),
                "nome": body.get("nome", "Compra"),
                "valor_total": valor_total,
                "parcelas": parcelas,
                "valor_parcela": round(valor_total / parcelas, 2),
                "data_inicio": body.get("data_inicio") or date.today().isoformat(),
            }
            c.setdefault("compras", []).append(compra)
            save_data(data)
            return jsonify(compra), 201
    return jsonify({"erro": "Cartao nao encontrado"}), 404


@app.route("/api/cartoes/<cartao_id>/compras/<compra_id>", methods=["DELETE"])
def api_cartoes_del_compra(cartao_id, compra_id):
    data = load_data()
    for c in data.get("cartoes", []):
        if c["id"] == cartao_id:
            c["compras"] = [p for p in c.get("compras", []) if p["id"] != compra_id]
            save_data(data)
            return jsonify({"ok": True})
    return jsonify({"erro": "Cartao nao encontrado"}), 404


# ============================================================
# ROTAS - CRUD: EMPRESTIMOS CLT
# ============================================================


@app.route("/api/emprestimos", methods=["GET"])
def api_emprestimos_listar():
    return jsonify(load_data().get("emprestimos", []))


@app.route("/api/emprestimos", methods=["POST"])
def api_emprestimos_criar():
    body = request.get_json(force=True)
    data = load_data()
    emp = {
        "id": novo_id(),
        "nome": body.get("nome", "Emprestimo"),
        "valor_total": float(body.get("valor_total") or 0),
        "parcelas_total": int(body.get("parcelas_total") or 1),
        "valor_parcela": float(body.get("valor_parcela") or 0),
        "parcelas_pagas": int(body.get("parcelas_pagas") or 0),
        "mes_inicio": body.get("mes_inicio") or date.today().strftime("%Y-%m"),
    }
    data.setdefault("emprestimos", []).append(emp)
    save_data(data)
    return jsonify(emp), 201


@app.route("/api/emprestimos/<emp_id>", methods=["PUT"])
def api_emprestimos_editar(emp_id):
    body = request.get_json(force=True)
    data = load_data()
    for e in data.get("emprestimos", []):
        if e["id"] == emp_id:
            e.update({k: v for k, v in body.items() if k != "id"})
            save_data(data)
            return jsonify(e)
    return jsonify({"erro": "Emprestimo nao encontrado"}), 404


@app.route("/api/emprestimos/<emp_id>", methods=["DELETE"])
def api_emprestimos_excluir(emp_id):
    data = load_data()
    if not request.args.get("confirmado"):
        return (
            jsonify({"erro": "Confirmacao necessaria", "requer_confirmacao": True}),
            400,
        )
    data["emprestimos"] = [e for e in data.get("emprestimos", []) if e["id"] != emp_id]
    save_data(data)
    return jsonify({"ok": True})


# ============================================================
# ROTAS - FERIAS
# ============================================================


@app.route("/api/ferias", methods=["GET"])
def api_ferias_listar():
    return jsonify(load_data().get("ferias", []))


@app.route("/api/ferias", methods=["POST"])
def api_ferias_criar():
    body = request.get_json(force=True)
    data = load_data()
    f = {
        "id": novo_id(),
        "inicio": body.get("inicio"),
        "fim": body.get("fim"),
        "salario_parcial": float(body.get("salario_parcial") or 0),
        "valor_ferias": float(body.get("valor_ferias") or 0),
        "suprime_vale": bool(body.get("suprime_vale", True)),
        "observacoes": body.get("observacoes", ""),
    }
    data.setdefault("ferias", []).append(f)
    save_data(data)
    return jsonify(f), 201


@app.route("/api/ferias/<f_id>", methods=["DELETE"])
def api_ferias_excluir(f_id):
    data = load_data()
    if not request.args.get("confirmado"):
        return (
            jsonify({"erro": "Confirmacao necessaria", "requer_confirmacao": True}),
            400,
        )
    data["ferias"] = [f for f in data.get("ferias", []) if f["id"] != f_id]
    save_data(data)
    return jsonify({"ok": True})


# ============================================================
# ROTAS - METAS / RESERVA
# ============================================================


@app.route("/api/metas", methods=["GET"])
def api_metas_listar():
    return jsonify(load_data().get("metas", []))


@app.route("/api/metas", methods=["POST"])
def api_metas_criar():
    body = request.get_json(force=True)
    data = load_data()
    meta = {
        "id": novo_id(),
        "nome": body.get("nome", "Meta"),
        "valor_objetivo": float(body.get("valor_objetivo") or 0),
        "valor_atual": float(body.get("valor_atual") or 0),
        "prazo": body.get("prazo"),
        "aporte_mensal": float(body.get("aporte_mensal") or 0),
        "tipo": body.get("tipo", "meta"),
    }
    data.setdefault("metas", []).append(meta)
    save_data(data)
    return jsonify(meta), 201


@app.route("/api/metas/<meta_id>", methods=["PUT"])
def api_metas_editar(meta_id):
    body = request.get_json(force=True)
    data = load_data()
    for m in data.get("metas", []):
        if m["id"] == meta_id:
            m.update({k: v for k, v in body.items() if k != "id"})
            save_data(data)
            return jsonify(m)
    return jsonify({"erro": "Meta nao encontrada"}), 404


@app.route("/api/metas/<meta_id>", methods=["DELETE"])
def api_metas_excluir(meta_id):
    data = load_data()
    if not request.args.get("confirmado"):
        return (
            jsonify({"erro": "Confirmacao necessaria", "requer_confirmacao": True}),
            400,
        )
    data["metas"] = [m for m in data.get("metas", []) if m["id"] != meta_id]
    save_data(data)
    return jsonify({"ok": True})


@app.route("/api/reserva", methods=["GET"])
def api_reserva_get():
    return jsonify(load_data().get("reserva", {}))


@app.route("/api/reserva", methods=["PUT"])
def api_reserva_put():
    body = request.get_json(force=True)
    data = load_data()
    data.setdefault("reserva", {})
    data["reserva"].update({k: v for k, v in body.items()})
    save_data(data)
    return jsonify(data["reserva"])


# ============================================================
# ROTAS - SALDO / CONFIG
# ============================================================


@app.route("/api/saldo", methods=["GET"])
def api_saldo_get():
    return jsonify(load_data().get("saldo", {}))


@app.route("/api/saldo", methods=["PUT"])
def api_saldo_put():
    body = request.get_json(force=True)
    data = load_data()
    data.setdefault("saldo", {})
    data["saldo"].update({k: v for k, v in body.items()})
    save_data(data)
    return jsonify(data["saldo"])


@app.route("/api/config", methods=["GET"])
def api_config_get():
    return jsonify(load_data().get("config", {}))


@app.route("/api/config", methods=["PUT"])
def api_config_put():
    body = request.get_json(force=True)
    data = load_data()
    data.setdefault("config", {})
    data["config"].update({k: v for k, v in body.items()})
    save_data(data)
    return jsonify(data["config"])


# ============================================================
# ROTAS - FLUXO DE CAIXA (transacoes manuais)
# ============================================================


@app.route("/api/transacoes", methods=["GET"])
def api_transacoes_listar():
    data = load_data()
    txs = sorted(
        data.get("transacoes", []), key=lambda t: t.get("data", ""), reverse=True
    )
    return jsonify(txs)


@app.route("/api/transacoes", methods=["POST"])
def api_transacoes_criar():
    body = request.get_json(force=True)
    data = load_data()
    tx = {
        "id": novo_id(),
        "data": body.get("data") or date.today().isoformat(),
        "descricao": body.get("descricao", ""),
        "categoria": body.get("categoria", "Outros"),
        "entrada": float(body.get("entrada") or 0),
        "saida": float(body.get("saida") or 0),
        "conta": body.get("conta", ""),
        "forma_pagamento": body.get("forma_pagamento", ""),
        "status": body.get("status", "CONFIRMADO"),
    }
    data.setdefault("transacoes", []).append(tx)
    save_data(data)
    return jsonify(tx), 201


@app.route("/api/transacoes/<tx_id>", methods=["DELETE"])
def api_transacoes_excluir(tx_id):
    data = load_data()
    data["transacoes"] = [t for t in data.get("transacoes", []) if t["id"] != tx_id]
    save_data(data)
    return jsonify({"ok": True})


# ============================================================
# ROTAS - EXPORTACAO / BACKUP
# ============================================================


@app.route("/api/export/json")
def api_export_json():
    data = load_data()
    buf = io.BytesIO(json.dumps(data, ensure_ascii=False, indent=2).encode("utf-8"))
    buf.seek(0)
    return send_file(
        buf,
        mimetype="application/json",
        as_attachment=True,
        download_name=f"finance_export_{date.today().isoformat()}.json",
    )


@app.route("/api/export/csv")
def api_export_csv():
    data = load_data()
    buf = io.StringIO()
    writer = csv.writer(buf)
    writer.writerow(["Tipo", "Nome", "Valor", "Dia/Mes", "Categoria", "Status"])
    for c in data.get("contas", []):
        writer.writerow(
            [
                "Conta",
                c["nome"],
                c["valor"],
                c.get("dia"),
                c.get("categoria"),
                c.get("status"),
            ]
        )
    for e in data.get("emprestimos", []):
        writer.writerow(
            [
                "Emprestimo CLT",
                e["nome"],
                e["valor_parcela"],
                e.get("mes_inicio"),
                "CLT",
                "ATIVA",
            ]
        )
    for cartao in data.get("cartoes", []):
        for compra in cartao.get("compras", []):
            writer.writerow(
                [
                    "Cartao:" + cartao["nome"],
                    compra["nome"],
                    compra["valor_parcela"],
                    compra.get("data_inicio"),
                    "Cartao",
                    "ATIVA",
                ]
            )
    mem = io.BytesIO(buf.getvalue().encode("utf-8-sig"))
    mem.seek(0)
    return send_file(
        mem,
        mimetype="text/csv",
        as_attachment=True,
        download_name=f"finance_export_{date.today().isoformat()}.csv",
    )


@app.route("/api/backup", methods=["POST"])
def api_backup():
    data = load_data()
    save_data(data, backup=True)
    return jsonify({"ok": True, "arquivo": os.path.basename(BACKUP_FILE)})


@app.route("/api/restore", methods=["POST"])
def api_restore():
    if not os.path.exists(BACKUP_FILE):
        return jsonify({"erro": "Nenhum backup encontrado"}), 404
    with open(BACKUP_FILE, "r", encoding="utf-8") as f:
        backup_data = json.load(f)
    save_data(backup_data, backup=False)
    return jsonify({"ok": True})


# ============================================================
# FRONTEND (HTML + CSS + JS embutidos)
# ============================================================

HTML_PAGE = r"""<!DOCTYPE html>
<html lang="pt-BR">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">
<title>CFO Pessoal - Gestao Financeira</title>
<link rel="icon" href="data:,">
<link rel="preconnect" href="https://fonts.googleapis.com">
<link href="https://fonts.googleapis.com/css2?family=Space+Grotesk:wght@500;600;700&family=Inter:wght@400;500;600;700&display=swap" rel="stylesheet">
<script src="https://cdnjs.cloudflare.com/ajax/libs/Chart.js/4.4.0/chart.umd.min.js"></script>
<style>
:root{
  --bg:#0B0E14;
  --surface:#141824;
  --surface-2:#1B2130;
  --border:#262D3D;
  --text:#EDF0F5;
  --muted:#8891A6;
  --green:#33D6A0;
  --red:#FF6B6B;
  --amber:#FFC862;
  --blue:#5B9DFF;
  --gray:#6B7280;
  --radius:16px;
  --radius-sm:10px;
  --shadow:0 8px 24px rgba(0,0,0,.35);
  --font-display:'Space Grotesk',sans-serif;
  --font-body:'Inter',sans-serif;
}
[data-theme="light"]{
  --bg:#F4F6FA;
  --surface:#FFFFFF;
  --surface-2:#EEF1F6;
  --border:#E1E5EE;
  --text:#151A24;
  --muted:#666F84;
  --shadow:0 8px 24px rgba(20,30,60,.08);
}
*{box-sizing:border-box; margin:0; padding:0;}
body{
  background:var(--bg); color:var(--text); font-family:var(--font-body);
  min-height:100vh; -webkit-font-smoothing:antialiased; transition:background .2s,color .2s;
  padding-bottom:78px;
}
h1,h2,h3,.num,.mono{ font-family:var(--font-display); letter-spacing:-.01em; }
a{color:inherit;}
button{font-family:var(--font-body); cursor:pointer;}
::-webkit-scrollbar{width:8px; height:8px;}
::-webkit-scrollbar-thumb{background:var(--border); border-radius:8px;}

/* ---------- LAYOUT ---------- */
.app{ display:flex; min-height:100vh; }
.sidebar{
  width:230px; background:var(--surface); border-right:1px solid var(--border);
  padding:20px 14px; position:sticky; top:0; height:100vh; display:flex; flex-direction:column; gap:4px;
}
.brand{ display:flex; align-items:center; gap:10px; padding:8px 10px 22px; }
.brand-badge{ width:34px; height:34px; border-radius:10px; background:linear-gradient(135deg,var(--green),var(--blue)); display:flex; align-items:center; justify-content:center; font-weight:700; font-family:var(--font-display); color:#08130F; }
.brand-name{ font-family:var(--font-display); font-weight:700; font-size:15px; }
.brand-sub{ font-size:11px; color:var(--muted); }
.nav-item{
  display:flex; align-items:center; gap:10px; padding:10px 12px; border-radius:var(--radius-sm);
  color:var(--muted); font-size:13.5px; font-weight:500; border:none; background:transparent; text-align:left; width:100%;
}
.nav-item .ic{ font-size:16px; width:20px; text-align:center; }
.nav-item.active{ background:var(--surface-2); color:var(--text); }
.nav-item:hover{ color:var(--text); }
.sidebar-footer{ margin-top:auto; padding-top:10px; border-top:1px solid var(--border); }

.main{ flex:1; min-width:0; padding:26px 30px 50px; }
.topbar{ display:flex; align-items:center; justify-content:space-between; margin-bottom:22px; gap:12px; flex-wrap:wrap; }
.page-title{ font-size:22px; font-weight:700; }
.page-sub{ color:var(--muted); font-size:13px; margin-top:2px; }
.top-actions{ display:flex; gap:8px; align-items:center; }

.btn{
  border:1px solid var(--border); background:var(--surface); color:var(--text);
  padding:9px 14px; border-radius:var(--radius-sm); font-size:13px; font-weight:600;
  display:inline-flex; align-items:center; gap:6px; transition:transform .1s, background .15s;
}
.btn:hover{ background:var(--surface-2); }
.btn:active{ transform:scale(.97); }
.btn-primary{ background:var(--green); color:#06120D; border-color:transparent; }
.btn-primary:hover{ background:#28c393; }
.btn-danger{ background:transparent; color:var(--red); border-color:var(--red); }
.btn-ghost{ background:transparent; }
.btn-sm{ padding:6px 10px; font-size:12px; }
.icon-btn{ width:34px; height:34px; border-radius:10px; display:inline-flex; align-items:center; justify-content:center; border:1px solid var(--border); background:var(--surface); }

/* ---------- CARDS / GRID ---------- */
.grid{ display:grid; gap:14px; }
.grid-cards{ grid-template-columns:repeat(4,1fr); }
.grid-2{ grid-template-columns:2fr 1fr; }
.grid-3{ grid-template-columns:repeat(3,1fr); }
.card{
  background:var(--surface); border:1px solid var(--border); border-radius:var(--radius);
  padding:18px; box-shadow:var(--shadow);
}
.stat-card{ display:flex; flex-direction:column; gap:8px; }
.stat-label{ font-size:12px; color:var(--muted); display:flex; align-items:center; gap:6px; font-weight:600; text-transform:uppercase; letter-spacing:.03em; }
.stat-value{ font-size:26px; font-weight:700; font-family:var(--font-display); }
.stat-sub{ font-size:12px; color:var(--muted); }
.pos{ color:var(--green); } .neg{ color:var(--red); } .warn{ color:var(--amber); } .info{ color:var(--blue); }

/* signature: barra de composicao do saldo */
.balance-bar-wrap{ margin-top:6px; }
.balance-bar{ height:14px; border-radius:999px; overflow:hidden; display:flex; background:var(--surface-2); border:1px solid var(--border); }
.balance-bar div{ height:100%; }
.balance-legend{ display:flex; gap:16px; margin-top:10px; flex-wrap:wrap; font-size:12px; color:var(--muted); }
.balance-legend span{ display:inline-flex; align-items:center; gap:6px; }
.dot{ width:9px; height:9px; border-radius:50%; display:inline-block; }

.section-title{ font-size:15px; font-weight:700; margin:26px 0 12px; display:flex; align-items:center; justify-content:space-between; }
.pill{ font-size:11px; padding:3px 9px; border-radius:999px; font-weight:700; }
.pill-green{ background:rgba(51,214,160,.15); color:var(--green); }
.pill-red{ background:rgba(255,107,107,.15); color:var(--red); }
.pill-amber{ background:rgba(255,200,98,.15); color:var(--amber); }
.pill-blue{ background:rgba(91,157,255,.15); color:var(--blue); }
.pill-gray{ background:rgba(107,114,128,.15); color:var(--gray); }

.list-row{
  display:flex; align-items:center; justify-content:space-between; padding:12px 14px;
  border-radius:var(--radius-sm); background:var(--surface-2); margin-bottom:8px; gap:10px; flex-wrap:wrap;
}
.list-row .left{ display:flex; flex-direction:column; gap:2px; min-width:0; }
.list-row .name{ font-weight:600; font-size:13.5px; }
.list-row .meta{ font-size:11.5px; color:var(--muted); }
.list-row .right{ display:flex; align-items:center; gap:10px; }
.progress{ height:6px; border-radius:99px; background:var(--border); width:100%; overflow:hidden; margin-top:6px; }
.progress > div{ height:100%; background:var(--green); }

table{ width:100%; border-collapse:collapse; font-size:13px; }
th{ text-align:left; color:var(--muted); font-weight:600; font-size:11.5px; text-transform:uppercase; letter-spacing:.03em; padding:8px 10px; border-bottom:1px solid var(--border); }
td{ padding:10px; border-bottom:1px solid var(--border); }
tr:last-child td{ border-bottom:none; }
.table-wrap{ overflow-x:auto; }

.frase{ padding:10px 14px; background:var(--surface-2); border-left:3px solid var(--blue); border-radius:8px; font-size:13px; margin-bottom:8px; }

.chart-box{ position:relative; height:260px; }

/* ---------- FORMS / MODAL ---------- */
.modal-overlay{ position:fixed; inset:0; background:rgba(4,6,10,.6); display:none; align-items:center; justify-content:center; z-index:100; padding:16px; backdrop-filter:blur(2px); }
.modal-overlay.open{ display:flex; }
.modal{ background:var(--surface); border:1px solid var(--border); border-radius:var(--radius); padding:22px; width:100%; max-width:440px; max-height:88vh; overflow-y:auto; }
.modal h3{ font-size:16px; margin-bottom:14px; }
.field{ margin-bottom:12px; }
.field label{ display:block; font-size:12px; color:var(--muted); margin-bottom:5px; font-weight:600; }
.field input, .field select, .field textarea{
  width:100%; padding:10px 12px; background:var(--surface-2); border:1px solid var(--border);
  border-radius:var(--radius-sm); color:var(--text); font-size:13.5px; font-family:var(--font-body);
}
.field input:focus, .field select:focus, .field textarea:focus{ outline:2px solid var(--blue); outline-offset:1px; }
.field-row{ display:flex; gap:10px; }
.field-row .field{ flex:1; }
.modal-actions{ display:flex; gap:10px; margin-top:16px; justify-content:flex-end; }
.toggle-group{ display:flex; background:var(--surface-2); border:1px solid var(--border); border-radius:var(--radius-sm); padding:3px; }
.toggle-group button{ flex:1; padding:8px; border-radius:8px; border:none; background:transparent; color:var(--muted); font-weight:600; font-size:12.5px; }
.toggle-group button.active{ background:var(--green); color:#06120D; }

.toast-wrap{ position:fixed; bottom:90px; right:20px; display:flex; flex-direction:column; gap:8px; z-index:200; }
.toast{ background:var(--surface); border:1px solid var(--border); box-shadow:var(--shadow); padding:12px 16px; border-radius:10px; font-size:13px; min-width:220px; animation:slidein .2s ease; }
@keyframes slidein{ from{ transform:translateY(10px); opacity:0;} to{ transform:translateY(0); opacity:1;} }

.empty{ text-align:center; padding:40px 10px; color:var(--muted); font-size:13px; }
.result-badge{ font-size:34px; font-weight:700; font-family:var(--font-display); text-align:center; padding:18px; border-radius:var(--radius); margin-bottom:14px; }

.bottom-nav{ display:none; }

/* ---------- RESPONSIVE / MOBILE FIRST ADJUSTMENTS ---------- */
@media (max-width:960px){
  .grid-cards{ grid-template-columns:repeat(2,1fr); }
  .grid-2{ grid-template-columns:1fr; }
  .grid-3{ grid-template-columns:1fr; }
}
@media (max-width:720px){
  .sidebar{ display:none; }
  .main{ padding:16px 14px 90px; }
  .grid-cards{ grid-template-columns:repeat(2,1fr); gap:10px; }
  .stat-value{ font-size:21px; }
  .page-title{ font-size:19px; }
  .bottom-nav{
    display:flex; position:fixed; bottom:0; left:0; right:0; background:var(--surface);
    border-top:1px solid var(--border); z-index:50; padding:6px 4px calc(6px + env(safe-area-inset-bottom));
    overflow-x:auto; gap:2px;
  }
  .bottom-nav button{
    flex:1; min-width:64px; display:flex; flex-direction:column; align-items:center; gap:2px;
    background:transparent; border:none; color:var(--muted); font-size:10px; padding:6px 2px; border-radius:10px; font-weight:600;
  }
  .bottom-nav button.active{ color:var(--green); }
  .bottom-nav .ic{ font-size:18px; }
  table{ font-size:12px; }
  .card{ padding:14px; }
  .toast-wrap{ bottom:80px; right:10px; left:10px; }
  .toast{ min-width:0; }
}
@media (max-width:480px){
  .grid-cards{ grid-template-columns:1fr 1fr; }
}
</style>
</head>
"""

HTML_PAGE += r"""
<body>
<div class="app">
  <aside class="sidebar">
    <div class="brand">
      <div class="brand-badge">CFO</div>
      <div>
        <div class="brand-name">CFO Pessoal</div>
        <div class="brand-sub">Gestao financeira</div>
      </div>
    </div>
    <nav id="nav-desktop"></nav>
    <div class="sidebar-footer">
      <button class="nav-item" id="theme-toggle-btn"><span class="ic">&#9789;</span><span id="theme-toggle-label">Modo claro</span></button>
    </div>
  </aside>

  <main class="main">
    <div class="topbar">
      <div>
        <div class="page-title" id="page-title">Dashboard</div>
        <div class="page-sub" id="page-sub"></div>
      </div>
      <div class="top-actions" id="top-actions"></div>
    </div>
    <div id="view"></div>
  </main>
</div>

<nav class="bottom-nav" id="nav-mobile"></nav>
<div class="toast-wrap" id="toast-wrap"></div>

<div class="modal-overlay" id="modal-overlay">
  <div class="modal" id="modal-content"></div>
</div>

<script>
const NAV = [
  {id:"dashboard", label:"Dashboard", ic:"&#128202;"},
  {id:"contas", label:"Contas", ic:"&#128179;"},
  {id:"cartoes", label:"Cartoes", ic:"&#128180;"},
  {id:"emprestimos", label:"Emprestimos", ic:"&#127974;"},
  {id:"parcelas", label:"Parcelas", ic:"&#128203;"},
  {id:"fluxo", label:"Fluxo de caixa", ic:"&#128200;"},
  {id:"projecao", label:"Projecao 12m", ic:"&#128197;"},
  {id:"livrar", label:"Quando vou me livrar", ic:"&#127939;"},
  {id:"graficos", label:"Graficos", ic:"&#128201;"},
  {id:"reserva", label:"Reserva e metas", ic:"&#127974;"},
  {id:"simulador", label:"Posso comprar?", ic:"&#129518;"},
  {id:"alertas", label:"Alertas", ic:"&#128276;"},
  {id:"calendario", label:"Calendario", ic:"&#128198;"},
  {id:"historico", label:"Historico", ic:"&#128337;"},
  {id:"config", label:"Configuracoes", ic:"&#9881;"},
];
const MOBILE_NAV_IDS = ["dashboard","contas","cartoes","parcelas","simulador","config"];

let STATE = { view:"dashboard", theme: localStorage.getItem("__nouse")||"dark" };
let CATEGORIAS = ["Casa","Educacao","Assinaturas","Lazer","Parcelamento","Cartao","Pessoal","Financeiro","Outros"];

function fmt(v){
  v = Number(v||0);
  return v.toLocaleString('pt-BR', {style:'currency', currency:'BRL'});
}
function fmtNum(v){ return Number(v||0).toLocaleString('pt-BR'); }

async function api(path, opts){
  opts = opts || {};
  opts.headers = Object.assign({"Content-Type":"application/json"}, opts.headers||{});
  const res = await fetch(path, opts);
  if(!res.ok){
    let body = {};
    try{ body = await res.json(); }catch(e){}
    throw {status: res.status, body};
  }
  const ct = res.headers.get("content-type")||"";
  if(ct.includes("application/json")) return res.json();
  return res;
}

function toast(msg, type){
  const wrap = document.getElementById("toast-wrap");
  const el = document.createElement("div");
  el.className = "toast";
  el.style.borderLeft = "3px solid " + (type==="error"?"var(--red)":type==="warn"?"var(--amber)":"var(--green)");
  el.textContent = msg;
  wrap.appendChild(el);
  setTimeout(()=>el.remove(), 3800);
}

function closeModal(){ document.getElementById("modal-overlay").classList.remove("open"); }
function openModal(html){
  document.getElementById("modal-content").innerHTML = html;
  document.getElementById("modal-overlay").classList.add("open");
}
document.getElementById("modal-overlay").addEventListener("click", (e)=>{
  if(e.target.id === "modal-overlay") closeModal();
});

function confirmarAcao(msg, onOk){
  openModal(`
    <h3>Confirmar acao</h3>
    <p style="color:var(--muted); font-size:13.5px; margin-bottom:16px;">${msg}</p>
    <div class="modal-actions">
      <button class="btn" onclick="closeModal()">Cancelar</button>
      <button class="btn btn-danger" id="confirm-yes">Sim, confirmar</button>
    </div>
  `);
  document.getElementById("confirm-yes").onclick = ()=>{ closeModal(); onOk(); };
}

function renderNav(){
  const desktop = document.getElementById("nav-desktop");
  desktop.innerHTML = NAV.map(n=>`
    <button class="nav-item ${STATE.view===n.id?'active':''}" data-view="${n.id}">
      <span class="ic">${n.ic}</span><span>${n.label}</span>
    </button>`).join("");
  desktop.querySelectorAll("button").forEach(b=> b.onclick = ()=> setView(b.dataset.view));

  const mobile = document.getElementById("nav-mobile");
  mobile.innerHTML = NAV.filter(n=>MOBILE_NAV_IDS.includes(n.id)).map(n=>`
    <button class="${STATE.view===n.id?'active':''}" data-view="${n.id}">
      <span class="ic">${n.ic}</span><span>${n.label.split(' ')[0]}</span>
    </button>`).join("");
  mobile.querySelectorAll("button").forEach(b=> b.onclick = ()=> setView(b.dataset.view));
}

function setView(view){
  STATE.view = view;
  renderNav();
  const found = NAV.find(n=>n.id===view);
  document.getElementById("page-title").textContent = found ? found.label : view;
  document.getElementById("top-actions").innerHTML = "";
  RENDERERS[view]();
}

function applyTheme(){
  document.documentElement.setAttribute("data-theme", STATE.theme);
  document.getElementById("theme-toggle-label").textContent = STATE.theme==="dark" ? "Modo claro" : "Modo escuro";
}
document.getElementById("theme-toggle-btn").onclick = ()=>{
  STATE.theme = STATE.theme==="dark" ? "light" : "dark";
  applyTheme();
  api("/api/config", {method:"PUT", body: JSON.stringify({tema: STATE.theme})});
};
</script>
"""

HTML_PAGE += r"""
<script>
const RENDERERS = {};

// ---------------- DASHBOARD ----------------
RENDERERS.dashboard = async function(){
  document.getElementById("page-sub").textContent = "Sua vida financeira em 30 segundos";
  const view = document.getElementById("view");
  view.innerHTML = `<div class="empty">Carregando...</div>`;
  const [d, alertas, livrar] = await Promise.all([
    api("/api/dashboard"), api("/api/alertas"), api("/api/quando-vou-me-livrar")
  ]);

  const total = Math.max(1, d.saldo_total);
  const pctReservado = Math.max(0, Math.min(100, (d.dinheiro_reservado/total)*100));
  const pctLivre = Math.max(0, Math.min(100, (d.dinheiro_fisico/total)*100));

  const gap = d.gap;
  const gapColor = gap.gap_mensal >= 0 ? "pos" : "neg";
  const gapIcon = gap.gap_mensal >= 0 ? "&#128994;" : "&#128308;";

  view.innerHTML = `
    ${d.em_ferias ? `<div class="frase" style="border-left-color:var(--amber)">&#127958; Voce esta em periodo de ferias configurado. O vale do dia 20 nao sera gerado automaticamente.</div>` : ""}

    <div class="grid grid-cards">
      <div class="card stat-card">
        <div class="stat-label">&#128176; Saldo total</div>
        <div class="stat-value">${fmt(d.saldo_total)}</div>
        <div class="balance-bar-wrap">
          <div class="balance-bar">
            <div style="width:${pctLivre}%; background:var(--green)"></div>
            <div style="width:${pctReservado}%; background:var(--amber)"></div>
          </div>
          <div class="balance-legend">
            <span><span class="dot" style="background:var(--green)"></span>Livre</span>
            <span><span class="dot" style="background:var(--amber)"></span>Reservado</span>
          </div>
        </div>
      </div>
      <div class="card stat-card">
        <div class="stat-label">&#128181; Dinheiro livre</div>
        <div class="stat-value pos">${fmt(d.dinheiro_livre)}</div>
        <div class="stat-sub">Fisico disponivel: ${fmt(d.dinheiro_fisico)}</div>
      </div>
      <div class="card stat-card">
        <div class="stat-label">&#128274; Comprometido no mes</div>
        <div class="stat-value warn">${fmt(d.dinheiro_comprometido)}</div>
        <div class="stat-sub">Reservado: ${fmt(d.dinheiro_reservado)}</div>
      </div>
      <div class="card stat-card">
        <div class="stat-label">&#128197; Proximo recebimento</div>
        <div class="stat-value" style="font-size:18px">${d.proximo_recebimento ? new Date(d.proximo_recebimento+"T00:00:00").toLocaleDateString('pt-BR') : "-"}</div>
      </div>
      <div class="card stat-card">
        <div class="stat-label">&#128184; Proxima despesa</div>
        <div class="stat-value" style="font-size:18px">${d.proxima_despesa ? new Date(d.proxima_despesa+"T00:00:00").toLocaleDateString('pt-BR') : "-"}</div>
      </div>
      <div class="card stat-card">
        <div class="stat-label">&#128202; Sobra do mes</div>
        <div class="stat-value ${gapColor}">${fmt(d.sobra_mes)}</div>
      </div>
      <div class="card stat-card">
        <div class="stat-label">&#127974; Reserva</div>
        <div class="stat-value info">${fmt(d.reserva_valor)}</div>
        <div class="stat-sub">Proxima meta: ${d.reserva_meta_atual ? fmt(d.reserva_meta_atual) : "-"}</div>
      </div>
      <div class="card stat-card">
        <div class="stat-label">&#128199; Parcelas ativas</div>
        <div class="stat-value">${d.parcelas_ativas_count}</div>
      </div>
    </div>

    <div class="grid grid-2" style="margin-top:16px;">
      <div class="card">
        <div class="section-title" style="margin-top:0;">GAP financeiro ${gapIcon}
          <span class="pill ${gap.gap_mensal>=0?'pill-green':'pill-red'}">${gap.gap_mensal>=0?'SOBRA':'GAP'} ${fmt(gap.gap_mensal)}</span>
        </div>
        <div class="list-row"><div class="left"><div class="name">Dia 05</div><div class="meta">Receita ${fmt(gap.receita_05)} - Contas ${fmt(gap.contas_05)}</div></div><div class="right"><b class="${gap.gap_05>=0?'pos':'neg'}">${fmt(gap.gap_05)}</b></div></div>
        <div class="list-row"><div class="left"><div class="name">Dia 20</div><div class="meta">Receita ${fmt(gap.receita_20)} - Contas ${fmt(gap.contas_20+gap.cartoes)}</div></div><div class="right"><b class="${gap.gap_20>=0?'pos':'neg'}">${fmt(gap.gap_20)}</b></div></div>
        <div class="list-row" style="background:transparent; border:1px dashed var(--border);"><div class="left"><div class="name">Mensal</div><div class="meta">Descontos CLT (informativo): ${fmt(gap.descontos_clt)}</div></div><div class="right"><b class="${gapColor}" style="font-size:16px">${fmt(gap.gap_mensal)}</b></div></div>
        <p style="font-size:12px; color:var(--muted); margin-top:8px;">${gap.gap_mensal<0 ? "Voce precisara utilizar R$ "+Math.abs(gap.gap_mensal).toFixed(2)+" da reserva ou de outro recebimento." : "Sua sobra pode reforcar a reserva ou as metas."}</p>
      </div>
      <div class="card">
        <div class="section-title" style="margin-top:0;">&#128276; Alertas</div>
        ${alertas.slice(0,5).map(a=>`<div class="frase">${a.icone} ${a.texto}</div>`).join("") || '<div class="empty">Sem alertas</div>'}
      </div>
    </div>

    <div class="section-title">Frases do dia</div>
    <div class="card">
      ${d.frases.map(f=>`<div class="frase">&#128161; ${f}</div>`).join("")}
    </div>

    <div class="section-title">&#127939; Quando vou me livrar das parcelas?</div>
    <div class="card">
      ${livrar.slice(0,4).map(i=>`
        <div class="list-row">
          <div class="left"><div class="name">${i.nome}</div><div class="meta">${fmt(i.valor_parcela)}/mes - ${i.parcelas_restantes} restante(s)</div></div>
          <div class="right"><span class="pill pill-blue">termina ${i.termina_em}</span></div>
        </div>`).join("") || '<div class="empty">Nenhuma parcela ativa</div>'}
    </div>
  `;
};
</script>
"""

HTML_PAGE += r"""
<script>
// ---------------- CONTAS ----------------
RENDERERS.contas = async function(){
  document.getElementById("page-sub").textContent = "Contas fixas e parceladas dos dias 05 e 20";
  document.getElementById("top-actions").innerHTML = `<button class="btn btn-primary" id="btn-nova-conta">+ Nova conta</button>`;
  document.getElementById("btn-nova-conta").onclick = ()=> abrirModalConta();

  const contas = await api("/api/contas");
  const ativas = contas.filter(c=>c.status==="ATIVA");
  const finalizadas = contas.filter(c=>c.status!=="ATIVA");
  const g05 = ativas.filter(c=>c.grupo==="05");
  const g20 = ativas.filter(c=>c.grupo==="20");

  function linha(c){
    const parcInfo = c.parcelas_total ? `${(c.parcelas_pagas||0)}/${c.parcelas_total} parcelas` : (c.recorrente? "Recorrente" : "Unica");
    return `<div class="list-row">
      <div class="left">
        <div class="name">${c.nome} ${c.confirmar?'<span class="pill pill-amber">CONFIRMAR</span>':''}</div>
        <div class="meta">Dia ${c.dia} - ${c.categoria} - ${parcInfo} - ${c.forma_pagamento||''}</div>
      </div>
      <div class="right">
        <b>${fmt(c.valor)}</b>
        ${c.parcelas_total ? `<button class="icon-btn btn-sm" title="Registrar pagamento" onclick="pagarConta('${c.id}')">&#10003;</button>`:''}
        <button class="icon-btn btn-sm" onclick='abrirModalConta(${JSON.stringify(c)})'>&#9998;</button>
        <button class="icon-btn btn-sm" onclick="excluirConta('${c.id}','${c.nome.replace(/'/g,"")}')">&#128465;</button>
      </div>
    </div>`;
  }

  document.getElementById("view").innerHTML = `
    <div class="section-title" style="margin-top:0;">Dia 05 <span class="pill pill-blue">${fmt(g05.reduce((s,c)=>s+c.valor,0))}</span></div>
    <div class="card">${g05.map(linha).join("") || '<div class="empty">Nenhuma conta cadastrada</div>'}</div>
    <div class="section-title">Dia 20 <span class="pill pill-blue">${fmt(g20.reduce((s,c)=>s+c.valor,0))}</span></div>
    <div class="card">${g20.map(linha).join("") || '<div class="empty">Nenhuma conta cadastrada</div>'}</div>
    <div class="section-title">Historico (finalizadas / canceladas)</div>
    <div class="card">${finalizadas.map(c=>`<div class="list-row"><div class="left"><div class="name">${c.nome}</div><div class="meta">${c.categoria}</div></div><div class="right"><span class="pill pill-gray">${c.status}</span></div></div>`).join("") || '<div class="empty">Nada por aqui</div>'}</div>
  `;
};

function abrirModalConta(conta){
  conta = conta || {};
  const isEdit = !!conta.id;
  openModal(`
    <h3>${isEdit? "Editar conta" : "Nova conta"}</h3>
    <div class="field"><label>Nome</label><input id="f-nome" value="${conta.nome||''}"></div>
    <div class="field-row">
      <div class="field"><label>Valor (R$)</label><input id="f-valor" type="number" step="0.01" value="${conta.valor||''}"></div>
      <div class="field"><label>Dia do vencimento</label><input id="f-dia" type="number" min="1" max="31" value="${conta.dia||5}"></div>
    </div>
    <div class="field"><label>Grupo</label>
      <div class="toggle-group">
        <button type="button" class="grupo-btn ${conta.grupo!=='20'?'active':''}" data-g="05">Dia 05</button>
        <button type="button" class="grupo-btn ${conta.grupo==='20'?'active':''}" data-g="20">Dia 20</button>
      </div>
    </div>
    <div class="field"><label>Categoria</label>
      <select id="f-categoria">${CATEGORIAS.map(c=>`<option ${conta.categoria===c?'selected':''}>${c}</option>`).join("")}</select>
    </div>
    <div class="field"><label>Forma de pagamento</label><input id="f-forma" value="${conta.forma_pagamento||'Debito/Pix'}"></div>
    <div class="field-row">
      <div class="field"><label>Numero de parcelas (vazio = recorrente/unica)</label><input id="f-parcelas-total" type="number" value="${conta.parcelas_total??''}"></div>
      <div class="field"><label>Parcelas ja pagas</label><input id="f-parcelas-pagas" type="number" value="${conta.parcelas_pagas||0}"></div>
    </div>
    <div class="field"><label>Data inicial</label><input id="f-data-inicial" type="date" value="${(conta.data_inicial||'').slice(0,10)}"></div>
    <div class="modal-actions">
      <button class="btn" onclick="closeModal()">Cancelar</button>
      <button class="btn btn-primary" id="btn-salvar-conta">Salvar</button>
    </div>
  `);
  document.querySelectorAll(".grupo-btn").forEach(b=>{
    b.onclick = ()=>{ document.querySelectorAll(".grupo-btn").forEach(x=>x.classList.remove("active")); b.classList.add("active"); };
  });
  document.getElementById("btn-salvar-conta").onclick = async ()=>{
    const grupo = document.querySelector(".grupo-btn.active").dataset.g;
    const body = {
      nome: document.getElementById("f-nome").value || "Conta",
      valor: parseFloat(document.getElementById("f-valor").value)||0,
      dia: parseInt(document.getElementById("f-dia").value)||5,
      grupo: grupo,
      categoria: document.getElementById("f-categoria").value,
      forma_pagamento: document.getElementById("f-forma").value,
      parcelas_total: document.getElementById("f-parcelas-total").value ? parseInt(document.getElementById("f-parcelas-total").value) : null,
      parcelas_pagas: parseInt(document.getElementById("f-parcelas-pagas").value)||0,
      data_inicial: document.getElementById("f-data-inicial").value || null,
      confirmar: false,
    };
    try{
      if(isEdit){ await api(`/api/contas/${conta.id}`, {method:"PUT", body: JSON.stringify(body)}); }
      else{ await api("/api/contas", {method:"POST", body: JSON.stringify(body)}); }
      closeModal(); toast("Conta salva com sucesso"); RENDERERS.contas();
    }catch(e){ toast("Erro ao salvar conta", "error"); }
  };
}

async function pagarConta(id){
  await api(`/api/contas/${id}/pagar`, {method:"POST"});
  toast("Parcela registrada");
  RENDERERS.contas();
}

function excluirConta(id, nome){
  confirmarAcao(`Excluir a conta "${nome}"? Essa acao nao pode ser desfeita.`, async ()=>{
    try{ await api(`/api/contas/${id}?confirmado=1`, {method:"DELETE"}); toast("Conta excluida"); RENDERERS.contas(); }
    catch(e){ toast("Erro ao excluir", "error"); }
  });
}
</script>
"""

HTML_PAGE += r"""
<script>
// ---------------- CARTOES ----------------
RENDERERS.cartoes = async function(){
  document.getElementById("page-sub").textContent = "Cartoes de credito e compras parceladas";
  document.getElementById("top-actions").innerHTML = `<button class="btn btn-primary" id="btn-novo-cartao">+ Novo cartao</button>`;
  document.getElementById("btn-novo-cartao").onclick = ()=> abrirModalCartao();

  const cartoes = await api("/api/cartoes");
  document.getElementById("view").innerHTML = cartoes.map(cartao=>{
    const totalMes = (cartao.compras||[]).reduce((s,c)=>s+c.valor_parcela,0);
    return `
    <div class="card" style="margin-bottom:14px;">
      <div class="section-title" style="margin-top:0;">
        &#128179; ${cartao.nome} ${cartao.confirmar?'<span class="pill pill-amber">CONFIRMAR</span>':''}
        <span>
          <button class="btn btn-sm" onclick='abrirModalCartao(${JSON.stringify(cartao)})'>Editar</button>
          <button class="btn btn-sm btn-danger" onclick="excluirCartao('${cartao.id}','${cartao.nome}')">Excluir</button>
        </span>
      </div>
      <div class="stat-sub">Limite: ${fmt(cartao.limite)} - Fechamento: ${cartao.fechamento||'-'} - Vencimento: ${cartao.vencimento||'-'} - Fatura atual (parcelas do mes): <b>${fmt(totalMes)}</b></div>
      <div style="margin-top:12px;">
        ${(cartao.compras||[]).map(compra=>`
          <div class="list-row">
            <div class="left"><div class="name">${compra.nome}</div><div class="meta">${fmt(compra.valor_total)} em ${compra.parcelas}x de ${fmt(compra.valor_parcela)} - inicio ${new Date(compra.data_inicio+'T00:00:00').toLocaleDateString('pt-BR')}</div></div>
            <div class="right"><button class="icon-btn btn-sm" onclick="delCompraCartao('${cartao.id}','${compra.id}')">&#128465;</button></div>
          </div>`).join("") || '<div class="empty">Nenhuma compra cadastrada</div>'}
      </div>
      <button class="btn btn-sm" style="margin-top:10px;" onclick="abrirModalCompra('${cartao.id}')">+ Nova compra</button>
    </div>`;
  }).join("") || '<div class="empty">Nenhum cartao cadastrado</div>';
};

function abrirModalCartao(cartao){
  cartao = cartao || {};
  const isEdit = !!cartao.id;
  openModal(`
    <h3>${isEdit?'Editar cartao':'Novo cartao'}</h3>
    <div class="field"><label>Nome</label><input id="f-nome" value="${cartao.nome||''}"></div>
    <div class="field-row">
      <div class="field"><label>Limite (R$)</label><input id="f-limite" type="number" step="0.01" value="${cartao.limite||''}"></div>
      <div class="field"><label>Vencimento (dia)</label><input id="f-venc" type="number" value="${cartao.vencimento||''}"></div>
    </div>
    <div class="field"><label>Fechamento (dia)</label><input id="f-fech" type="number" value="${cartao.fechamento||''}"></div>
    <div class="modal-actions">
      <button class="btn" onclick="closeModal()">Cancelar</button>
      <button class="btn btn-primary" id="btn-salvar-cartao">Salvar</button>
    </div>
  `);
  document.getElementById("btn-salvar-cartao").onclick = async ()=>{
    const body = {
      nome: document.getElementById("f-nome").value || "Cartao",
      limite: parseFloat(document.getElementById("f-limite").value)||0,
      vencimento: parseInt(document.getElementById("f-venc").value)||null,
      fechamento: parseInt(document.getElementById("f-fech").value)||null,
    };
    try{
      if(isEdit){ await api(`/api/cartoes/${cartao.id}`, {method:"PUT", body: JSON.stringify(body)}); }
      else{ await api("/api/cartoes", {method:"POST", body: JSON.stringify(body)}); }
      closeModal(); toast("Cartao salvo"); RENDERERS.cartoes();
    }catch(e){ toast("Erro ao salvar", "error"); }
  };
}

function excluirCartao(id, nome){
  confirmarAcao(`Excluir o cartao "${nome}" e todas as compras associadas?`, async ()=>{
    await api(`/api/cartoes/${id}?confirmado=1`, {method:"DELETE"});
    toast("Cartao excluido"); RENDERERS.cartoes();
  });
}

function abrirModalCompra(cartaoId){
  openModal(`
    <h3>Nova compra no cartao</h3>
    <div class="field"><label>Descricao</label><input id="f-nome" placeholder="Ex: Tela iPhone"></div>
    <div class="field-row">
      <div class="field"><label>Valor total (R$)</label><input id="f-valor" type="number" step="0.01" placeholder="1000"></div>
      <div class="field"><label>Parcelas</label><input id="f-parcelas" type="number" value="1"></div>
    </div>
    <div class="field"><label>Data da 1a parcela</label><input id="f-data" type="date" value="${new Date().toISOString().slice(0,10)}"></div>
    <div class="modal-actions">
      <button class="btn" onclick="closeModal()">Cancelar</button>
      <button class="btn btn-primary" id="btn-salvar-compra">Salvar</button>
    </div>
  `);
  document.getElementById("btn-salvar-compra").onclick = async ()=>{
    const body = {
      nome: document.getElementById("f-nome").value || "Compra",
      valor_total: parseFloat(document.getElementById("f-valor").value)||0,
      parcelas: parseInt(document.getElementById("f-parcelas").value)||1,
      data_inicio: document.getElementById("f-data").value,
    };
    try{
      await api(`/api/cartoes/${cartaoId}/compras`, {method:"POST", body: JSON.stringify(body)});
      closeModal(); toast("Compra adicionada"); RENDERERS.cartoes();
    }catch(e){ toast("Erro ao salvar", "error"); }
  };
}

async function delCompraCartao(cartaoId, compraId){
  await api(`/api/cartoes/${cartaoId}/compras/${compraId}`, {method:"DELETE"});
  toast("Compra removida"); RENDERERS.cartoes();
}

// ---------------- EMPRESTIMOS CLT ----------------
RENDERERS.emprestimos = async function(){
  document.getElementById("page-sub").textContent = "Descontados diretamente do salario (folha CLT)";
  document.getElementById("top-actions").innerHTML = `<button class="btn btn-primary" id="btn-novo-emp">+ Novo emprestimo</button>`;
  document.getElementById("btn-novo-emp").onclick = ()=> abrirModalEmprestimo();

  const emprestimos = await api("/api/emprestimos");
  const hoje = new Date();
  let totalMes = 0;
  const linhas = emprestimos.map(e=>{
    const restante = Math.max(0, e.parcelas_total - (e.parcelas_pagas||0));
    const pct = e.parcelas_total ? Math.round(((e.parcelas_pagas||0)/e.parcelas_total)*100) : 0;
    if(restante>0) totalMes += e.valor_parcela;
    return `<div class="list-row" style="display:block;">
      <div style="display:flex; justify-content:space-between; align-items:center; gap:10px; flex-wrap:wrap;">
        <div class="left"><div class="name">${e.nome} ${e.confirmar?'<span class="pill pill-amber">CONFIRMAR</span>':''}</div>
        <div class="meta">${fmt(e.valor_total)} total - ${e.parcelas_total}x de ${fmt(e.valor_parcela)} - inicio ${e.mes_inicio}</div></div>
        <div class="right"><span class="pill ${restante>0?'pill-blue':'pill-green'}">${restante>0? restante+' restante(s)' : 'QUITADO'}</span>
        <button class="icon-btn btn-sm" onclick='abrirModalEmprestimo(${JSON.stringify(e)})'>&#9998;</button>
        <button class="icon-btn btn-sm" onclick="excluirEmprestimo('${e.id}','${e.nome}')">&#128465;</button></div>
      </div>
      <div class="progress"><div style="width:${pct}%"></div></div>
    </div>`;
  }).join("");

  document.getElementById("view").innerHTML = `
    <div class="card" style="margin-bottom:14px;">
      <div class="stat-label">Total descontado da folha este mes</div>
      <div class="stat-value neg">${fmt(totalMes)}</div>
    </div>
    <div class="card">${linhas || '<div class="empty">Nenhum emprestimo cadastrado</div>'}</div>
  `;
};

function abrirModalEmprestimo(emp){
  emp = emp || {};
  const isEdit = !!emp.id;
  openModal(`
    <h3>${isEdit?'Editar emprestimo':'Novo emprestimo CLT'}</h3>
    <div class="field"><label>Nome</label><input id="f-nome" value="${emp.nome||''}"></div>
    <div class="field-row">
      <div class="field"><label>Valor total (R$)</label><input id="f-total" type="number" step="0.01" value="${emp.valor_total||''}"></div>
      <div class="field"><label>Valor da parcela (R$)</label><input id="f-parcela" type="number" step="0.01" value="${emp.valor_parcela||''}"></div>
    </div>
    <div class="field-row">
      <div class="field"><label>Numero de parcelas</label><input id="f-total-parc" type="number" value="${emp.parcelas_total||''}"></div>
      <div class="field"><label>Parcelas pagas</label><input id="f-pagas" type="number" value="${emp.parcelas_pagas||0}"></div>
    </div>
    <div class="field"><label>Mes de inicio (AAAA-MM)</label><input id="f-inicio" type="month" value="${emp.mes_inicio||''}"></div>
    <div class="modal-actions">
      <button class="btn" onclick="closeModal()">Cancelar</button>
      <button class="btn btn-primary" id="btn-salvar-emp">Salvar</button>
    </div>
  `);
  document.getElementById("btn-salvar-emp").onclick = async ()=>{
    const body = {
      nome: document.getElementById("f-nome").value || "Emprestimo",
      valor_total: parseFloat(document.getElementById("f-total").value)||0,
      valor_parcela: parseFloat(document.getElementById("f-parcela").value)||0,
      parcelas_total: parseInt(document.getElementById("f-total-parc").value)||1,
      parcelas_pagas: parseInt(document.getElementById("f-pagas").value)||0,
      mes_inicio: document.getElementById("f-inicio").value,
    };
    try{
      if(isEdit){ await api(`/api/emprestimos/${emp.id}`, {method:"PUT", body: JSON.stringify(body)}); }
      else{ await api("/api/emprestimos", {method:"POST", body: JSON.stringify(body)}); }
      closeModal(); toast("Emprestimo salvo"); RENDERERS.emprestimos();
    }catch(e){ toast("Erro ao salvar", "error"); }
  };
}

function excluirEmprestimo(id, nome){
  confirmarAcao(`Excluir o emprestimo "${nome}"?`, async ()=>{
    await api(`/api/emprestimos/${id}?confirmado=1`, {method:"DELETE"});
    toast("Emprestimo excluido"); RENDERERS.emprestimos();
  });
}
</script>
"""

HTML_PAGE += r"""
<script>
// ---------------- PARCELAS (visao unificada) ----------------
RENDERERS.parcelas = async function(){
  document.getElementById("page-sub").textContent = "Todas as parcelas ativas em um so lugar";
  document.getElementById("top-actions").innerHTML = "";
  const contas = await api("/api/contas");
  const parceladas = contas.filter(c=>c.parcelas_total);

  document.getElementById("view").innerHTML = `
  <div class="card">
    <div class="table-wrap">
    <table>
      <thead><tr><th>Nome</th><th>Valor total</th><th>Parcela</th><th>Qtd</th><th>Pagas</th><th>Restam</th><th>Inicio</th><th>Forma</th><th>Status</th></tr></thead>
      <tbody>
      ${parceladas.map(c=>{
        const restante = Math.max(0,(c.parcelas_total||0)-(c.parcelas_pagas||0));
        return `<tr>
          <td>${c.nome}</td>
          <td>${fmt((c.valor||0)*(c.parcelas_total||1))}</td>
          <td>${fmt(c.valor)}</td>
          <td>${c.parcelas_total}</td>
          <td>${c.parcelas_pagas||0}</td>
          <td>${restante}</td>
          <td>${c.data_inicial ? new Date(c.data_inicial+'T00:00:00').toLocaleDateString('pt-BR') : '-'}</td>
          <td>${c.forma_pagamento||'-'}</td>
          <td><span class="pill ${c.status==='ATIVA'?'pill-blue':'pill-gray'}">${c.status}</span></td>
        </tr>`;
      }).join("") || `<tr><td colspan="9" class="empty">Nenhuma parcela cadastrada</td></tr>`}
      </tbody>
    </table>
    </div>
  </div>`;
};

// ---------------- FLUXO DE CAIXA ----------------
RENDERERS.fluxo = async function(){
  document.getElementById("page-sub").textContent = "Entradas e saidas registradas manualmente";
  document.getElementById("top-actions").innerHTML = `<button class="btn btn-primary" id="btn-nova-tx">+ Novo lancamento</button>`;
  document.getElementById("btn-nova-tx").onclick = ()=> abrirModalTx();

  const txs = await api("/api/transacoes");
  let saldo = 0;
  const linhas = [...txs].reverse().map(t=>{ saldo += (t.entrada||0)-(t.saida||0); return {...t, saldoAcumulado: saldo}; }).reverse();

  document.getElementById("view").innerHTML = `
  <div class="card">
    <div class="table-wrap">
    <table>
      <thead><tr><th>Data</th><th>Descricao</th><th>Categoria</th><th>Entrada</th><th>Saida</th><th>Status</th><th></th></tr></thead>
      <tbody>
      ${linhas.map(t=>`<tr>
        <td>${new Date(t.data+'T00:00:00').toLocaleDateString('pt-BR')}</td>
        <td>${t.descricao}</td>
        <td>${t.categoria}</td>
        <td class="pos">${t.entrada?fmt(t.entrada):''}</td>
        <td class="neg">${t.saida?fmt(t.saida):''}</td>
        <td><span class="pill pill-blue">${t.status}</span></td>
        <td><button class="icon-btn btn-sm" onclick="delTx('${t.id}')">&#128465;</button></td>
      </tr>`).join("") || `<tr><td colspan="7" class="empty">Nenhum lancamento registrado</td></tr>`}
      </tbody>
    </table>
    </div>
  </div>`;
};

function abrirModalTx(){
  openModal(`
    <h3>Novo lancamento</h3>
    <div class="field"><label>Data</label><input id="f-data" type="date" value="${new Date().toISOString().slice(0,10)}"></div>
    <div class="field"><label>Descricao</label><input id="f-desc" placeholder="Ex: Compra no mercado"></div>
    <div class="field-row">
      <div class="field"><label>Entrada (R$)</label><input id="f-entrada" type="number" step="0.01" value="0"></div>
      <div class="field"><label>Saida (R$)</label><input id="f-saida" type="number" step="0.01" value="0"></div>
    </div>
    <div class="field"><label>Categoria</label><select id="f-cat">${CATEGORIAS.map(c=>`<option>${c}</option>`).join("")}</select></div>
    <div class="modal-actions">
      <button class="btn" onclick="closeModal()">Cancelar</button>
      <button class="btn btn-primary" id="btn-salvar-tx">Salvar</button>
    </div>
  `);
  document.getElementById("btn-salvar-tx").onclick = async ()=>{
    const body = {
      data: document.getElementById("f-data").value,
      descricao: document.getElementById("f-desc").value || "Lancamento",
      entrada: parseFloat(document.getElementById("f-entrada").value)||0,
      saida: parseFloat(document.getElementById("f-saida").value)||0,
      categoria: document.getElementById("f-cat").value,
      status: "CONFIRMADO",
    };
    await api("/api/transacoes", {method:"POST", body: JSON.stringify(body)});
    closeModal(); toast("Lancamento salvo"); RENDERERS.fluxo();
  };
}
async function delTx(id){ await api(`/api/transacoes/${id}`, {method:"DELETE"}); toast("Removido"); RENDERERS.fluxo(); }

// ---------------- PROJECAO 12 MESES ----------------
RENDERERS.projecao = async function(){
  document.getElementById("page-sub").textContent = "Como sua sobra evolui nos proximos 12 meses";
  document.getElementById("top-actions").innerHTML = "";
  const proj = await api("/api/projecao");
  document.getElementById("view").innerHTML = `
  <div class="card">
    <div class="table-wrap">
    <table>
      <thead><tr><th>Mes</th><th>Receita</th><th>Desc. CLT</th><th>Contas 05</th><th>Contas 20</th><th>Cartoes</th><th>Total desp.</th><th>Sobra</th><th>Sobra acum.</th></tr></thead>
      <tbody>
      ${proj.map(p=>`<tr>
        <td><b>${p.mes}</b></td>
        <td>${fmt(p.receita)}</td>
        <td>${fmt(p.descontos_clt)}</td>
        <td>${fmt(p.contas_05)}</td>
        <td>${fmt(p.contas_20)}</td>
        <td>${fmt(p.cartoes)}</td>
        <td>${fmt(p.total_despesas)}</td>
        <td class="${p.sobra>=0?'pos':'neg'}">${fmt(p.sobra)}</td>
        <td class="${p.sobra_acumulada>=0?'pos':'neg'}"><b>${fmt(p.sobra_acumulada)}</b></td>
      </tr>`).join("")}
      </tbody>
    </table>
    </div>
  </div>`;
};

// ---------------- QUANDO VOU ME LIVRAR ----------------
RENDERERS.livrar = async function(){
  document.getElementById("page-sub").textContent = "Ordem em que suas parcelas vao terminar";
  document.getElementById("top-actions").innerHTML = "";
  const itens = await api("/api/quando-vou-me-livrar");
  let liberadoAcumulado = 0;
  document.getElementById("view").innerHTML = `
  <div class="card">
    ${itens.map(i=>{ liberadoAcumulado += i.libera_mensal; return `
    <div class="list-row">
      <div class="left"><div class="name">${i.nome}</div><div class="meta">${fmt(i.valor_parcela)}/mes - ${i.parcelas_restantes} parcela(s) restante(s)</div></div>
      <div class="right"><span class="pill pill-green">termina em ${i.termina_em}</span></div>
    </div>`;}).join("") || '<div class="empty">Nenhuma parcela ativa. Voce esta livre!</div>'}
    ${itens.length?`<div class="frase" style="margin-top:10px;">Ao final de todas as parcelas, ate ${fmt(liberadoAcumulado)}/mes serao liberados no seu orcamento.</div>`:''}
  </div>`;
};

// ---------------- GRAFICOS ----------------
let CHARTS = {};
RENDERERS.graficos = async function(){
  document.getElementById("page-sub").textContent = "Visao grafica das suas financas";
  document.getElementById("top-actions").innerHTML = "";
  const g = await api("/api/graficos");
  document.getElementById("view").innerHTML = `
    <div class="grid grid-2">
      <div class="card"><div class="section-title" style="margin-top:0">Receita x despesas</div><div class="chart-box"><canvas id="ch1"></canvas></div></div>
      <div class="card"><div class="section-title" style="margin-top:0">Sobra mensal</div><div class="chart-box"><canvas id="ch2"></canvas></div></div>
    </div>
    <div class="grid grid-2" style="margin-top:14px;">
      <div class="card"><div class="section-title" style="margin-top:0">Parcelas restantes</div><div class="chart-box"><canvas id="ch3"></canvas></div></div>
      <div class="card"><div class="section-title" style="margin-top:0">Evolucao do dinheiro (sobra acumulada)</div><div class="chart-box"><canvas id="ch4"></canvas></div></div>
    </div>
    <div class="grid grid-2" style="margin-top:14px;">
      <div class="card"><div class="section-title" style="margin-top:0">Despesas por categoria</div><div class="chart-box"><canvas id="ch5"></canvas></div></div>
      <div class="card"><div class="section-title" style="margin-top:0">Evolucao da divida</div><div class="chart-box"><canvas id="ch6"></canvas></div></div>
    </div>
  `;
  const css = getComputedStyle(document.documentElement);
  const green = css.getPropertyValue('--green').trim(), red = css.getPropertyValue('--red').trim(),
        blue = css.getPropertyValue('--blue').trim(), amber = css.getPropertyValue('--amber').trim(),
        muted = css.getPropertyValue('--muted').trim(), text = css.getPropertyValue('--text').trim();
  Chart.defaults.color = muted; Chart.defaults.borderColor = "rgba(128,128,128,.15)";
  Object.values(CHARTS).forEach(c=>c && c.destroy());

  CHARTS.c1 = new Chart(document.getElementById("ch1"), {type:"bar", data:{labels:g.receitas_x_despesas.labels,
    datasets:[{label:"Receita", data:g.receitas_x_despesas.receitas, backgroundColor:green},
              {label:"Despesas", data:g.receitas_x_despesas.despesas, backgroundColor:red}]},
    options:{responsive:true, maintainAspectRatio:false}});

  CHARTS.c2 = new Chart(document.getElementById("ch2"), {type:"line", data:{labels:g.sobra_mensal.labels,
    datasets:[{label:"Sobra", data:g.sobra_mensal.valores, borderColor:blue, backgroundColor:"transparent", tension:.3}]},
    options:{responsive:true, maintainAspectRatio:false}});

  CHARTS.c3 = new Chart(document.getElementById("ch3"), {type:"bar", data:{labels:g.parcelas_restantes.labels,
    datasets:[{label:"Parcelas restantes", data:g.parcelas_restantes.valores, backgroundColor:amber}]},
    options:{responsive:true, maintainAspectRatio:false, indexAxis:"y"}});

  CHARTS.c4 = new Chart(document.getElementById("ch4"), {type:"line", data:{labels:g.evolucao_dinheiro.labels,
    datasets:[{label:"Sobra acumulada", data:g.evolucao_dinheiro.valores, borderColor:green, backgroundColor:"rgba(51,214,160,.15)", fill:true, tension:.3}]},
    options:{responsive:true, maintainAspectRatio:false}});

  CHARTS.c5 = new Chart(document.getElementById("ch5"), {type:"doughnut", data:{labels:g.despesas_categoria.labels,
    datasets:[{data:g.despesas_categoria.valores, backgroundColor:[green,red,blue,amber,muted,"#9D7BFF","#4FD0E9","#FF9E5B"]}]},
    options:{responsive:true, maintainAspectRatio:false}});

  CHARTS.c6 = new Chart(document.getElementById("ch6"), {type:"line", data:{labels:g.evolucao_divida.labels,
    datasets:[{label:"Divida total", data:g.evolucao_divida.valores, borderColor:red, backgroundColor:"transparent", tension:.3}]},
    options:{responsive:true, maintainAspectRatio:false}});
};
</script>
"""

HTML_PAGE += r"""
<script>
// ---------------- RESERVA & METAS ----------------
RENDERERS.reserva = async function(){
  document.getElementById("page-sub").textContent = "Reserva de emergencia e metas pessoais";
  document.getElementById("top-actions").innerHTML = `<button class="btn btn-primary" id="btn-nova-meta">+ Nova meta</button>`;
  document.getElementById("btn-nova-meta").onclick = ()=> abrirModalMeta();

  const [reserva, metas] = await Promise.all([api("/api/reserva"), api("/api/metas")]);
  const etapas = reserva.etapas||[3000,5000,10000];
  const atual = reserva.valor_atual||0;
  const proxima = etapas.find(e=>e>atual) || etapas[etapas.length-1] || 1;
  const pct = Math.min(100, Math.round((atual/proxima)*100));

  document.getElementById("view").innerHTML = `
  <div class="card">
    <div class="section-title" style="margin-top:0">&#127974; Meta de reserva <button class="btn btn-sm" onclick="editarReserva(${atual})">Atualizar valor</button></div>
    <div class="stat-value">${fmt(atual)} <span style="font-size:14px; color:var(--muted); font-weight:400;">de ${fmt(proxima)}</span></div>
    <div class="progress" style="height:10px;"><div style="width:${pct}%"></div></div>
    <div class="stat-sub" style="margin-top:6px;">${pct}% da proxima etapa - etapas: ${etapas.map(fmt).join(" -> ")}</div>
  </div>
  <div class="section-title">Metas</div>
  ${metas.map(m=>{
    const p = m.valor_objetivo? Math.min(100, Math.round((m.valor_atual/m.valor_objetivo)*100)) : 0;
    return `<div class="card" style="margin-bottom:10px;">
      <div style="display:flex; justify-content:space-between; align-items:center;">
        <div>
          <div class="name" style="font-weight:700;">${m.nome}</div>
          <div class="meta">${fmt(m.valor_atual)} de ${fmt(m.valor_objetivo)} ${m.prazo?(' - prazo '+m.prazo):''} ${m.aporte_mensal?(' - aporte '+fmt(m.aporte_mensal)+'/mes'):''}</div>
        </div>
        <div><button class="icon-btn btn-sm" onclick='abrirModalMeta(${JSON.stringify(m)})'>&#9998;</button>
        <button class="icon-btn btn-sm" onclick="excluirMeta('${m.id}','${m.nome}')">&#128465;</button></div>
      </div>
      <div class="progress"><div style="width:${p}%"></div></div>
    </div>`;
  }).join("") || '<div class="card empty">Nenhuma meta cadastrada</div>'}
  `;
};

function editarReserva(atual){
  openModal(`
    <h3>Atualizar valor da reserva</h3>
    <div class="field"><label>Valor atual (R$)</label><input id="f-reserva" type="number" step="0.01" value="${atual}"></div>
    <div class="modal-actions"><button class="btn" onclick="closeModal()">Cancelar</button>
    <button class="btn btn-primary" id="btn-salvar-reserva">Salvar</button></div>
  `);
  document.getElementById("btn-salvar-reserva").onclick = async ()=>{
    await api("/api/reserva", {method:"PUT", body: JSON.stringify({valor_atual: parseFloat(document.getElementById("f-reserva").value)||0})});
    closeModal(); toast("Reserva atualizada"); RENDERERS.reserva();
  };
}

function abrirModalMeta(meta){
  meta = meta||{};
  const isEdit = !!meta.id;
  openModal(`
    <h3>${isEdit?'Editar meta':'Nova meta'}</h3>
    <div class="field"><label>Nome</label><input id="f-nome" value="${meta.nome||''}"></div>
    <div class="field-row">
      <div class="field"><label>Valor objetivo (R$)</label><input id="f-obj" type="number" step="0.01" value="${meta.valor_objetivo||''}"></div>
      <div class="field"><label>Valor atual (R$)</label><input id="f-atual" type="number" step="0.01" value="${meta.valor_atual||0}"></div>
    </div>
    <div class="field-row">
      <div class="field"><label>Prazo</label><input id="f-prazo" type="month" value="${meta.prazo||''}"></div>
      <div class="field"><label>Aporte mensal (R$)</label><input id="f-aporte" type="number" step="0.01" value="${meta.aporte_mensal||0}"></div>
    </div>
    <div class="modal-actions"><button class="btn" onclick="closeModal()">Cancelar</button>
    <button class="btn btn-primary" id="btn-salvar-meta">Salvar</button></div>
  `);
  document.getElementById("btn-salvar-meta").onclick = async ()=>{
    const body = {
      nome: document.getElementById("f-nome").value || "Meta",
      valor_objetivo: parseFloat(document.getElementById("f-obj").value)||0,
      valor_atual: parseFloat(document.getElementById("f-atual").value)||0,
      prazo: document.getElementById("f-prazo").value,
      aporte_mensal: parseFloat(document.getElementById("f-aporte").value)||0,
    };
    if(isEdit){ await api(`/api/metas/${meta.id}`, {method:"PUT", body: JSON.stringify(body)}); }
    else{ await api("/api/metas", {method:"POST", body: JSON.stringify(body)}); }
    closeModal(); toast("Meta salva"); RENDERERS.reserva();
  };
}
function excluirMeta(id, nome){
  confirmarAcao(`Excluir a meta "${nome}"?`, async ()=>{
    await api(`/api/metas/${id}?confirmado=1`, {method:"DELETE"}); toast("Meta excluida"); RENDERERS.reserva();
  });
}

// ---------------- SIMULADOR "POSSO COMPRAR?" ----------------
RENDERERS.simulador = async function(){
  document.getElementById("page-sub").textContent = "Simule o impacto de uma nova compra antes de decidir";
  document.getElementById("top-actions").innerHTML = "";
  document.getElementById("view").innerHTML = `
  <div class="card" style="max-width:480px;">
    <div class="field"><label>Valor da compra (R$)</label><input id="s-valor" type="number" step="0.01" placeholder="1000"></div>
    <div class="field-row">
      <div class="field"><label>Numero de parcelas</label><input id="s-parcelas" type="number" value="1"></div>
      <div class="field"><label>Dia de cobranca</label><input id="s-dia" type="number" value="5"></div>
    </div>
    <div class="field"><label>Categoria</label><select id="s-cat">${CATEGORIAS.map(c=>`<option>${c}</option>`).join("")}</select></div>
    <button class="btn btn-primary" id="btn-simular" style="width:100%; justify-content:center;">Simular</button>
  </div>
  <div id="s-resultado" style="max-width:480px; margin-top:14px;"></div>
  `;
  document.getElementById("btn-simular").onclick = async ()=>{
    const body = {
      valor: parseFloat(document.getElementById("s-valor").value)||0,
      parcelas: parseInt(document.getElementById("s-parcelas").value)||1,
      dia: parseInt(document.getElementById("s-dia").value)||5,
      categoria: document.getElementById("s-cat").value,
    };
    const r = await api("/api/simular-compra", {method:"POST", body: JSON.stringify(body)});
    const cor = r.resultado==="CABE" ? "pos" : r.resultado==="APERTA" ? "warn" : "neg";
    const bg = r.resultado==="CABE" ? "rgba(51,214,160,.12)" : r.resultado==="APERTA" ? "rgba(255,200,98,.12)" : "rgba(255,107,107,.12)";
    const label = r.resultado==="CABE" ? "&#128994; CABE" : r.resultado==="APERTA" ? "&#128993; APERTA" : "&#128308; NAO CABE";
    document.getElementById("s-resultado").innerHTML = `
      <div class="result-badge ${cor}" style="background:${bg};">${label}</div>
      <div class="card">
        <div class="list-row"><div class="left"><div class="name">Valor da parcela</div></div><div class="right"><b>${fmt(r.valor_parcela)}</b></div></div>
        <div class="list-row"><div class="left"><div class="name">Impacto mensal</div></div><div class="right"><b>${fmt(r.impacto_mensal)}</b></div></div>
        <div class="list-row"><div class="left"><div class="name">Nova sobra do mes</div></div><div class="right"><b class="${r.nova_sobra>=0?'pos':'neg'}">${fmt(r.nova_sobra)}</b></div></div>
        <div class="list-row"><div class="left"><div class="name">% da renda comprometida</div></div><div class="right"><b>${r.percentual_renda_comprometida}%</b></div></div>
        <div class="list-row"><div class="left"><div class="name">Meses afetados</div></div><div class="right">${r.meses_afetados.join(", ")}</div></div>
      </div>
      ${r.gap_texto ? `<div class="frase" style="border-left-color:var(--red); margin-top:10px;">&#9888; ${r.gap_texto}</div>` : ""}
    `;
  };
};

// ---------------- ALERTAS ----------------
RENDERERS.alertas = async function(){
  document.getElementById("page-sub").textContent = "Avisos importantes sobre sua situacao financeira";
  document.getElementById("top-actions").innerHTML = "";
  const alertas = await api("/api/alertas");
  document.getElementById("view").innerHTML = `<div class="card">
    ${alertas.map(a=>`<div class="frase" style="border-left-color:${a.tipo==='critico'?'var(--red)':a.tipo==='alerta'?'var(--amber)':'var(--green)'}">${a.icone} ${a.texto}</div>`).join("")}
  </div>`;
};

// ---------------- CALENDARIO ----------------
RENDERERS.calendario = async function(){
  document.getElementById("page-sub").textContent = "Datas criticas do mes";
  document.getElementById("top-actions").innerHTML = "";
  const hoje = new Date();
  const d = await api(`/api/calendario?ano=${hoje.getFullYear()}&mes=${hoje.getMonth()+1}`);
  const diasDoMes = new Date(d.ano, d.mes, 0).getDate();
  const primeiroDiaSemana = new Date(d.ano, d.mes-1, 1).getDay();
  let cells = "";
  for(let i=0;i<primeiroDiaSemana;i++) cells += `<div></div>`;
  for(let dia=1; dia<=diasDoMes; dia++){
    const info = d.dias[dia];
    const critico = info && (info.contas.length || info.receitas.length);
    const totalDia = info ? info.contas.reduce((s,c)=>s+c.valor,0) : 0;
    const receitaDia = info ? info.receitas.reduce((s,c)=>s+c.valor,0) : 0;
    cells += `<div class="card" style="padding:8px; min-height:70px; ${critico?'border-color:var(--blue);':''}">
      <div style="font-weight:700; font-size:12px;">${dia}</div>
      ${receitaDia? `<div style="font-size:10px; color:var(--green);">+${fmt(receitaDia)}</div>`:''}
      ${totalDia? `<div style="font-size:10px; color:var(--red);">-${fmt(totalDia)}</div>`:''}
    </div>`;
  }
  document.getElementById("view").innerHTML = `
    <div class="card" style="margin-bottom:12px;"><b>${MESES_JS[d.mes-1]} de ${d.ano}</b></div>
    <div style="display:grid; grid-template-columns:repeat(7,1fr); gap:6px;">
      ${["D","S","T","Q","Q","S","S"].map(x=>`<div style="text-align:center; font-size:11px; color:var(--muted); font-weight:700;">${x}</div>`).join("")}
      ${cells}
    </div>
  `;
};
const MESES_JS = ["Janeiro","Fevereiro","Marco","Abril","Maio","Junho","Julho","Agosto","Setembro","Outubro","Novembro","Dezembro"];

// ---------------- HISTORICO ----------------
RENDERERS.historico = async function(){
  document.getElementById("page-sub").textContent = "Evolucao mensal do seu patrimonio";
  document.getElementById("top-actions").innerHTML = "";
  const snaps = await api("/api/historico");
  document.getElementById("view").innerHTML = `
  <div class="card">
    <div class="table-wrap">
    <table>
      <thead><tr><th>Mes</th><th>Saldo</th><th>Livre</th><th>Comprometido</th><th>Reserva</th><th>Parcelas ativas</th><th>Sobra</th></tr></thead>
      <tbody>
      ${[...snaps].reverse().map(s=>`<tr>
        <td><b>${s.mes}</b></td><td>${fmt(s.saldo_total)}</td><td>${fmt(s.dinheiro_livre)}</td>
        <td>${fmt(s.dinheiro_comprometido)}</td><td>${fmt(s.reserva)}</td><td>${s.parcelas_ativas}</td>
        <td class="${s.sobra_mes>=0?'pos':'neg'}">${fmt(s.sobra_mes)}</td>
      </tr>`).join("") || `<tr><td colspan="7" class="empty">Ainda sem historico registrado (um snapshot e criado por mes)</td></tr>`}
      </tbody>
    </table>
    </div>
  </div>`;
};
</script>
"""

HTML_PAGE += r"""
<script>
// ---------------- CONFIGURACOES ----------------
RENDERERS.config = async function(){
  document.getElementById("page-sub").textContent = "Salario, saldo, ferias, backup e exportacao";
  document.getElementById("top-actions").innerHTML = "";
  const [cfg, saldo, ferias] = await Promise.all([api("/api/config"), api("/api/saldo"), api("/api/ferias")]);

  document.getElementById("view").innerHTML = `
  <div class="grid grid-2">
    <div class="card">
      <div class="section-title" style="margin-top:0;">&#128176; Salario e recebimento</div>
      <div class="field"><label>Salario bruto (R$)</label><input id="c-salario" type="number" step="0.01" value="${cfg.salario_bruto}"></div>
      <div class="field"><label>Modelo de recebimento</label>
        <div class="toggle-group">
          <button type="button" class="modelo-btn ${cfg.modelo_recebimento!=='unico'?'active':''}" data-m="dividido">Recebimento dividido</button>
          <button type="button" class="modelo-btn ${cfg.modelo_recebimento==='unico'?'active':''}" data-m="unico">Recebimento unico</button>
        </div>
      </div>
      <div class="field-row">
        <div class="field"><label>Dia do salario</label><input id="c-dia-sal" type="number" value="${cfg.dia_salario}"></div>
        <div class="field"><label>Dia do vale</label><input id="c-dia-vale" type="number" value="${cfg.dia_vale}"></div>
      </div>
      <div class="field"><label>Valor do vale (R$)</label><input id="c-vale" type="number" step="0.01" value="${cfg.valor_vale}"></div>
      <button class="btn btn-primary" id="btn-salvar-cfg">Salvar configuracoes</button>
    </div>

    <div class="card">
      <div class="section-title" style="margin-top:0;">&#128181; Saldo atual</div>
      <div class="field"><label>Dinheiro fisico / livre (R$)</label><input id="s-fisico" type="number" step="0.01" value="${saldo.dinheiro_fisico}"></div>
      <div class="field"><label>Cofrinho (reservado) (R$)</label><input id="s-cofrinho" type="number" step="0.01" value="${saldo.cofrinho}"></div>
      <div class="field"><label>Descricao da reserva</label><input id="s-desc" value="${saldo.cofrinho_reservado_desc||''}"></div>
      <button class="btn btn-primary" id="btn-salvar-saldo">Salvar saldo</button>
    </div>
  </div>

  <div class="section-title">&#127958; Ferias</div>
  <div class="card">
    ${ferias.map(f=>`<div class="list-row">
      <div class="left"><div class="name">${new Date(f.inicio+'T00:00:00').toLocaleDateString('pt-BR')} a ${new Date(f.fim+'T00:00:00').toLocaleDateString('pt-BR')}</div>
      <div class="meta">Salario parcial ${fmt(f.salario_parcial)} + Ferias ${fmt(f.valor_ferias)} ${f.suprime_vale?'- sem vale do dia 20':''}</div></div>
      <div class="right"><button class="icon-btn btn-sm" onclick="excluirFerias('${f.id}')">&#128465;</button></div>
    </div>`).join("") || '<div class="empty">Nenhum periodo de ferias cadastrado</div>'}
    <button class="btn btn-sm" style="margin-top:8px;" id="btn-nova-ferias">+ Cadastrar ferias</button>
  </div>

  <div class="section-title">&#128190; Backup e exportacao</div>
  <div class="card" style="display:flex; gap:10px; flex-wrap:wrap;">
    <a class="btn" href="/api/export/json">Exportar JSON</a>
    <a class="btn" href="/api/export/csv">Exportar CSV</a>
    <button class="btn" id="btn-backup">Fazer backup agora</button>
    <button class="btn btn-danger" id="btn-restore">Restaurar ultimo backup</button>
  </div>
  `;

  document.querySelectorAll(".modelo-btn").forEach(b=>{
    b.onclick = ()=>{ document.querySelectorAll(".modelo-btn").forEach(x=>x.classList.remove("active")); b.classList.add("active"); };
  });

  document.getElementById("btn-salvar-cfg").onclick = async ()=>{
    const modelo = document.querySelector(".modelo-btn.active").dataset.m;
    const body = {
      salario_bruto: parseFloat(document.getElementById("c-salario").value)||0,
      modelo_recebimento: modelo,
      dia_salario: parseInt(document.getElementById("c-dia-sal").value)||5,
      dia_vale: parseInt(document.getElementById("c-dia-vale").value)||20,
      valor_vale: parseFloat(document.getElementById("c-vale").value)||0,
    };
    await api("/api/config", {method:"PUT", body: JSON.stringify(body)});
    toast("Configuracoes salvas");
  };

  document.getElementById("btn-salvar-saldo").onclick = async ()=>{
    const body = {
      dinheiro_fisico: parseFloat(document.getElementById("s-fisico").value)||0,
      cofrinho: parseFloat(document.getElementById("s-cofrinho").value)||0,
      cofrinho_reservado_desc: document.getElementById("s-desc").value,
    };
    await api("/api/saldo", {method:"PUT", body: JSON.stringify(body)});
    toast("Saldo salvo");
  };

  document.getElementById("btn-nova-ferias").onclick = ()=>{
    openModal(`
      <h3>Cadastrar ferias</h3>
      <div class="field-row">
        <div class="field"><label>Inicio</label><input id="f-ini" type="date"></div>
        <div class="field"><label>Fim</label><input id="f-fim" type="date"></div>
      </div>
      <div class="field-row">
        <div class="field"><label>Salario parcial (R$)</label><input id="f-sal" type="number" step="0.01"></div>
        <div class="field"><label>Valor das ferias (R$)</label><input id="f-fer" type="number" step="0.01"></div>
      </div>
      <div class="field"><label><input type="checkbox" id="f-suprime" checked style="width:auto; display:inline-block;"> Suprime o vale do dia 20 neste periodo</label></div>
      <div class="modal-actions"><button class="btn" onclick="closeModal()">Cancelar</button>
      <button class="btn btn-primary" id="btn-salvar-ferias">Salvar</button></div>
    `);
    document.getElementById("btn-salvar-ferias").onclick = async ()=>{
      const body = {
        inicio: document.getElementById("f-ini").value, fim: document.getElementById("f-fim").value,
        salario_parcial: parseFloat(document.getElementById("f-sal").value)||0,
        valor_ferias: parseFloat(document.getElementById("f-fer").value)||0,
        suprime_vale: document.getElementById("f-suprime").checked,
      };
      await api("/api/ferias", {method:"POST", body: JSON.stringify(body)});
      closeModal(); toast("Ferias cadastradas"); RENDERERS.config();
    };
  };

  document.getElementById("btn-backup").onclick = async ()=>{ await api("/api/backup", {method:"POST"}); toast("Backup realizado"); };
  document.getElementById("btn-restore").onclick = ()=>{
    confirmarAcao("Restaurar o ultimo backup ira substituir os dados atuais. Deseja continuar?", async ()=>{
      await api("/api/restore", {method:"POST"}); toast("Backup restaurado"); setView(STATE.view);
    });
  };
};
async function excluirFerias(id){
  confirmarAcao("Excluir este periodo de ferias?", async ()=>{
    await api(`/api/ferias/${id}?confirmado=1`, {method:"DELETE"}); toast("Removido"); RENDERERS.config();
  });
}

// ---------------- BOOTSTRAP ----------------
(async function init(){
  const cfg = await api("/api/config");
  STATE.theme = cfg.tema || "dark";
  applyTheme();
  renderNav();
  setView("dashboard");
})();
</script>
</body>
</html>
"""


# ============================================================
# EXECUCAO
# ============================================================


def get_ip_local():
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.settimeout(0)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except Exception:
        return "127.0.0.1"


def abrir_navegador(url):
    try:
        webbrowser.open(url)
    except Exception:
        pass


def main():
    ensure_data_file()
    port = 5000
    ip_local = get_ip_local()

    print("=" * 50)
    print("GESTAO FINANCEIRA - CFO PESSOAL")
    print("=" * 50)
    print("")
    print(f"LOCAL: http://localhost:{port}")
    print(f"REDE:  http://{ip_local}:{port}")
    print("")
    print("Abrindo automaticamente no navegador...")
    print("Pressione CTRL+C para encerrar o servidor.")
    print("=" * 50)

    threading.Timer(1.2, abrir_navegador, args=[f"http://localhost:{port}"]).start()

    app.run(host="0.0.0.0", port=port, debug=False, use_reloader=False)


if __name__ == "__main__":
    main()

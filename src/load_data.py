import pandas as pd
import json


## Gera conjuntos
# Função para carregar os dados de Estoque.xlsx
def carregar_estoque(filepath):
    estoque = pd.read_excel(filepath)
    estoque.rename(columns={"COD_DEP": "cod_dep", "COD_MAT": "cod_mat", "ESTOQ": "estoque"}, inplace=True)
    return estoque

# Função para carregar os dados de Obras.xlsx
def carregar_obras(filepath):
    obras = pd.read_excel(filepath)
    obras.rename(columns={"OBRA": "obra", "COD_DEP": "cod_dep", "PRIOR": "prioridade", 
                        "COD_MAT": "cod_mat", "QTD_DEM": "qtd_dem"}, inplace=True)
    return obras

# Função para carregar os dados de CustosTransp.json
def carregar_custos_transporte(filepath):
    with open(filepath, 'r') as file:
        custos_transporte = json.load(file)
    return custos_transporte
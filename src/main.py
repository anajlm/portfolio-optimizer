import pandas as pd
import json

# Define caminhos dos arquivos de dados
estoque_file = "../data/Estoque.xlsx"
obras_file = "../data/Obras.xlsx"
custos_transporte_file = "../data/CustosTransp.json"


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


estoque = carregar_estoque(estoque_file)
obras = carregar_obras(obras_file)
custos_transporte = carregar_custos_transporte(custos_transporte_file)

print("Dados do Estoque:")
print(estoque.head())

print("\nDados das Obras:")
print(obras.head())

print("\nDados de Custos de Transporte:")
for key, value in list(custos_transporte.items())[:5]:  # Mostrando os 5 primeiros itens
    print(f"{key}: {value}")


## Gera subconjuntos
# Função para gerar subconjuntos de depósitos capazes de executar uma obra i
def depositos_por_obra(obras_df):
    depositos_por_obra = {}
    for _, obra in obras_df.iterrows():
        obra_id = obra["obra"]
        cod_dep = obra["cod_dep"]  # Relaciona obra e depósito

        # Adiciona o depósito relacionado à obra
        if obra_id not in depositos_por_obra:
            depositos_por_obra[obra_id] = []
        depositos_por_obra[obra_id].append(cod_dep)
    return depositos_por_obra

# Função para gerar subconjuntos de obras que um depósito j pode executar
def obras_por_deposito(obras_df):
    obras_por_deposito = {}
    for _, obra in obras_df.iterrows():
        obra_id = obra["obra"]
        cod_dep = obra["cod_dep"]

        # Adiciona a obra ao depósito relacionado
        if cod_dep not in obras_por_deposito:
            obras_por_deposito[cod_dep] = []
        obras_por_deposito[cod_dep].append(obra_id)
    return obras_por_deposito

# Função para identificar materiais necessários para uma obra i
def materiais_por_obra(obras_df):
    materiais_por_obra = {}
    for _, obra in obras_df.iterrows():
        obra_id = obra["obra"]
        cod_mat = obra["cod_mat"]
        qtd_dem = obra["qtd_dem"]

        # Adiciona os materiais necessários para a obra
        if obra_id not in materiais_por_obra:
            materiais_por_obra[obra_id] = []
        materiais_por_obra[obra_id].append((cod_mat, qtd_dem))
    return materiais_por_obra

depositos_por_obra = depositos_por_obra(obras)
obras_por_deposito = obras_por_deposito(obras)
materiais_por_obra = materiais_por_obra(obras)

print("Depósitos que podem executar cada obra:")
for obra, depositos in depositos_por_obra.items():
    print(f"Obra {obra}: Depósitos {depositos}")

print("\nObras que cada depósito pode executar:")
for dep, obras in obras_por_deposito.items():
    print(f"Depósito {dep}: Obras {obras}")

print("\nMateriais necessários para cada obra:")
for obra, materiais in materiais_por_obra.items():
    print(f"Obra {obra}: Materiais {materiais}")

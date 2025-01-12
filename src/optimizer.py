import pandas as pd
import json
from abc import abstractmethod
from src.load_data import carregar_estoque, carregar_custos_transporte, carregar_obras
import numpy as np

from gurobipy import Model, GRB, quicksum
from tqdm import tqdm

class PortfolioOptimizer:

    def __init__(self, estoque_file, obras_file, custos_transporte_file):
        """
        Argrs:
            estoque_file (str): Arquivo de estoque
            obras_file (str): Arquivo de obras
            custo_transporte_file (str): Arquivo com custos de transporte
        """
        self.estoque_file = estoque_file
        self.obras_file = obras_file
        self.custos_transporte_file = custos_transporte_file
        
    def run(self):
        # Inicializando o modelo
        self.model = Model('PortfolioOptimization')

        # Leitura de preparação de dados
        self.read_inputs()
        self.define_sets()
        self.define_parameters()

        # Criação do modelo
        self.create_decision_variables()
        self.create_constraints()
        self.set_obj_priority()

        # Otimiza
        self.model.optimize()
        self.generate_results()


    def read_inputs(self):

        print('Lendo inputs')
        self.estoque = carregar_estoque(self.estoque_file)
        self.obras = carregar_obras(self.obras_file)
        self.custos_transporte = carregar_custos_transporte(self.custos_transporte_file)
    

    def define_sets(self):
        
        print('Definindo conjuntos')
        # Inicializa conjuntos
        model_sets = dict()

        # I - Conjunto de Obras
        model_sets['I'] = self.obras["obra"].unique()

        # J - Conjuntos de depósitos
        model_sets['J'] = self.estoque["cod_dep"].unique()
        
        # M - Conjunto de materiais
        model_sets['M'] = self.estoque["cod_mat"].unique()

        # J_i - Subconjunto de depósitos que executam a obra i
        model_sets['J_i'] = (
            self.obras
            .drop_duplicates(subset=['obra', 'cod_dep'])
            .groupby('obra')
            .agg({'cod_dep': 'unique'})
            .to_dict()
            ['cod_dep']
        )

        # I[j] - Subconjunto de obras que o depósito j pode executar
        model_sets['I_j'] = (
            self.obras
            .drop_duplicates(subset=['obra', 'cod_dep'])
            .groupby('cod_dep')
            .agg({'obra': 'unique'})
            .to_dict()
            ['obra']
        )

        # M[i] - Subconjunto de materiais que a obra i requere
        model_sets['M_i'] = (
            self.obras
            .drop_duplicates(subset=['obra', 'cod_mat'])
            .groupby('obra')
            .agg({'cod_mat': 'unique'})
            .to_dict()
            ['cod_mat']
        )
        self.model_sets = model_sets

        
    def define_parameters(self):
        
        print('Criando parâmetros')
        # Inicializa parâmetros
        parameters = dict()

        # w[i] - prioridade de uma dada ordem i
        parameters['w'] = (
            self.obras
            .drop_duplicates(subset=['obra', 'prioridade'])
            .set_index('obra')
            .to_dict()
            ['prioridade']
        )

        # q[i,m] - quantidade do material m necessario na obra i
        parameters['q'] = (
            self.obras
            .groupby(['obra', 'cod_mat'])
            .agg({'qtd_dem': 'sum'})
            .to_dict()
            ['qtd_dem']
        )

        # Q[j,m] - estoque inicial do material m no deposito j
        parameters['Q'] = (
            self.estoque
            .set_index(['cod_dep', 'cod_mat'])
            .to_dict()
            ['estoque']
        )
        
        # c[k,j,m] - custo de transporte de uma unidade do material m do deposito k para o deposito j
        parameters['c'] = self.custos_transporte

        # N - quantidade total de obras
        parameters['N'] = self.obras['obra'].nunique()

        # D - quantidade total de depositos
        parameters['D'] = self.obras['cod_dep'].nunique()

        self.params = parameters


    def create_decision_variables(self):

        print('Criando variáveis de decisão')
        decision_variables = dict()

        # x[i,j] - Binária: 1 se a obra i é executada no depósito j
        decision_variables['x'] = self.model.addVars(
            [(i, j) for i in self.model_sets['I'] for j in self.model_sets['J_i'][i]],
            vtype=GRB.BINARY,
            name="x"
        )

        # t[k,j,m]: Continua: Quantidade de material m transferida do depósito k para o depósito j
        decision_variables['t'] = self.model.addVars(
            [(k, j, m) for k in self.model_sets['J'] for j in self.model_sets['J'] for m in self.model_sets['M'] if j != k],
            vtype=GRB.CONTINUOUS,
            name="t",
            lb=0
        )

        self.vars = decision_variables


    def create_constraints(self):

        # Restrição 1 - Obra executada no máximo uma vez
        print('Criando restrição 1')
        for i in tqdm(self.model_sets['I']):
            self.model.addConstr(
                quicksum(self.vars['x'][i,j] for j in self.model_sets['J_i'][i]) <= 1,
                name=f"C1_OneExecution_{i}"
            )
        
        # Restrição 2 - Balanço de massa do estoque de materiais
        print('Criando restrição 2')
        for m in tqdm(self.model_sets['M']):
            for j in self.model_sets['J']:  

                LHS = quicksum(self.vars['x'][i, j] * self.params['q'][i, m] for i in self.model_sets['I_j'][j] if m in self.model_sets['M_i'][i]) + \
                      quicksum(self.vars['t'][j, k, m] for k in self.model_sets['J'] if k!=j)              
                

                tuple_get = (j,m)
                initial_stock = self.params['Q'].get(tuple_get, 0)
                RHS = initial_stock + \
                      quicksum(self.vars['t'][k,j,m] for k in self.model_sets['J'] if k!=j)

                self.model.addConstr(
                    # LHS
                    LHS <= RHS,                    
                    name=f"C2_StockBalance_{m}_{j}"
                )

        
    def set_obj_priority(self):
        # obj1
        self.model.setObjective(
            quicksum(self.vars['x'][i,j] * self.params['w'][i] for i in self.model_sets['I'] for j in self.model_sets['J_i'][i]),
            GRB.MAXIMIZE
        )


    def generate_results(self):

        # Generating X var output
        
        # Get var X result and create a DF with it
        vars_x_on = [key for key, elem in self.vars['x'].items() if np.isclose(elem.X, 1) ]
        array_i = [elem[0] for elem in vars_x_on]
        array_j = [elem[1] for elem in vars_x_on]
        df_output_X = pd.DataFrame({
            'obra': array_i,
            'cod_dep': array_j
        })
        df_output_X['obra_atendida'] = 1
        df_output_X.to_csv('output_var_X.csv')

        # Generate DF grouped to compare with professor's solution
        df_real_output = (
            self.obras[['obra', 'cod_dep', 'prioridade']]
            .drop_duplicates()
            .merge(df_output_X, on=['cod_dep', 'obra'], how='left', validate='1:1')
        )
        df_real_output['obra_atendida'] = df_real_output['obra_atendida'].fillna(0)
        df_real_output['prioridade_atendida'] = df_real_output['obra_atendida'] * df_real_output['prioridade']

        df_grouped = (
            df_real_output
            .groupby(['cod_dep'])
            .agg({
                # NUM_OBRAS_ASSOCIADAS
                'obra': 'nunique', 
                # OBRAS_EXECUTADAS
                'obra_atendida': 'sum',
                # SOMA_PRIORIDADES_EXECUTADAS
                'prioridade_atendida': 'sum',
                # SOMA_PRIORIDADES_ASSOCIADAS
                'prioridade': 'sum'
            })
            .reset_index()
            .rename(
                columns={
                    'obra':'NUM_OBRAS_ASSOCIADAS',
                    'obra_atendida': 'OBRAS_EXECUTADAS',
                    'prioridade_atendida': 'SOMA_PRIORIDADES_EXECUTADAS',
                    'prioridade': 'SOMA_PRIORIDADES_ASSOCIADAS'
                }
            )
        )
        df_grouped.to_csv('output_agrupado.csv')


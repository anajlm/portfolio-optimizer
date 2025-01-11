from gurobipy import Model, GRB, quicksum

class PortfolioOptimizer:
    def __init__(self, obras_por_deposito, depositos_por_obra, materiais_por_obra, estoque, custos_transporte, pesos_prioridade):
        """
        Args:
            obras (pd.DataFrame): Informações sobre as obras.
            estoque (pd.DataFrame): Estoques disponíveis nos depósitos.
            custos_transporte (dict): Custos de transporte entre depósitos.
            w (dict): Prioridade de cada obra.
        """
        self.obras = obras
        self.estoque = estoque
        self.custos_transporte = custos_transporte
        self.pesos_prioridade = pesos_prioridade
        self.model = None
        self.solution = None

    def _setup_model(self):
        """Configura o modelo de otimização."""
        # Inicializando o modelo
        self.model = Model("PortfolioOptimization")

        # Conjuntos e parâmetros
        self.obras_ids = self.obras["obra"].unique()
        self.depositos_ids = self.estoque["cod_dep"].unique()
        self.materiais_ids = self.estoque["cod_mat"].unique()

        # Define variáveis de decisão
        # x_ij: Binária: 1 se a obra i é executada no depósito j
        self.x = self.model.addVars(
            [(i, j) for i in self.obras_ids for j in self.depositos_ids],
            vtype=GRB.BINARY,
            name="x"
        )
        # t_kjm: Continua: Quantidade de material m transferida do depósito k para o depósito j
        self.t = self.model.addVars(
            [(k, j, m) for k in self.depositos_ids for j in self.depositos_ids for m in self.materiais_ids],
            vtype=GRB.CONTINUOUS,
            name="t"
        )

        # Função objetivo 1: Maximiza a soma total das prioridades
        self.model.setObjective(
            quicksum(self.x[i, j] * self.w[i] for i in self.obras_ids for j in self.depositos_ids),
            GRB.MAXIMIZE
        )

        # Função objetivo 2: Minimiza o custo total de transporte
        self.model.setObjective(
            quicksum(self.t[k, j, m] * self.c[k, j, m] for i in self.obras_ids for j in self.depositos_ids),
            GRB.MAXIMIZE
        )

        # Restrições
        # 1. Cada obra pode ser executada uma única vez
        for i in self.obras_ids:
            self.model.addConstr(
                quicksum(self.x[i, j] for j in self.depositos_ids) <= 1,
                name=f"OneExecution_{i}"
            )

        # 2. Balanço de massa do estoque de materiais
        for j in self.depositos_ids:
            for m in self.materiais_ids:
                self.model.addConstr(
                    quicksum(obras[obras["obra"] == i]["qtd_dem"].iloc[0] * self.x[i, j] for i in obras[j])
                        + quicksum(self.t[j, k, m] for k in self.depositos_ids if k != j)
                    <= self.estoque[(self.estoque["cod_dep"] == j) & (self.estoque["cod_mat"] == m)]["estoq"].iloc[0]
                        + quicksum(self.t[k, j, m] for k in self.depositos_ids if k != j)
                    name=f"Stock_{j}_{m}"
                )


    def solve(self):
        """Resolve o problema de otimização."""
        if self.model is None:
            self._setup_model()

        self.model.optimize()

        # Capturar os resultados
        if self.model.status == GRB.OPTIMAL:
            solution_x = {var.varName: var.x for var in self.model.getVars() if var.varName.startswith("x")}
            solution_t = {var.varName: var.x for var in self.model.getVars() if var.varName.startswith("t")}
            self.solution = {"x": solution_x, "t": solution_t}
        else:
            print("Não foi encontrada solução ótima.")
            self.solution = None

    def get_solution(self):
        """Retorna a solução encontrada."""
        return self.solution

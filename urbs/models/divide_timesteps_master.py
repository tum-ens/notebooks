from .divide_timesteps_super import *
from ..pyomoio import get_entity


class DivideTimestepsMaster(DivideTimestepsSuper):
    def __init__(self, data, timesteps=None, supportsteps=[], dt=1, dual=False, model_type=urbsType.master):
        """Initiates this class as a ConcreteModel urbs object from given input data.

        Args:
            data: a dict of 6 DataFrames with the keys 'commodity', 'process',
                'transmission', 'storage', 'demand' and 'supim'.
            timesteps: optional list of timesteps, default: demand timeseries
            dt: timestep duration in hours (default: 1)
            dual: set True to add dual variables to model (slower); default: False
            model_type: model_type of the problem; 0: Normal(default), 1:Sub, 2: Master
        """
        super().__init__(data, timesteps, supportsteps, dt, dual, model_type)
        # Initialize sub model specific things
        self.name = 'urbs-master'
        print(self.name + ' is created.')

        # Sets

        # add cost_type future cost
        self.cost_type.add('FutureCosts')

        # Parameters

        # weight = length of year (hours) / length of simulation (hours)
        # weight scales costs and emissions from length of simulation to a full
        # year, making comparisons among cost types (invest is annualized, fixed
        # costs are annual by default, variable costs are scaled by weight) and
        # among different simulation durations meaningful.
        self.weight = pyomo.Param(
            initialize=float(8760) / ((max(timesteps) - min(timesteps)) * dt),
            # initialize=float(8760) / (len(self.tm) * dt),
            doc='Pre-factor for variable costs and emissions for an annual result')

        # Variables

        # process
        self.cap_pro_new = pyomo.Var(
            self.pro_tuples,
            within=pyomo.NonNegativeReals,
            doc='New process capacity (MW)')

        # transmission
        self.cap_tra_new = pyomo.Var(
            self.tra_tuples,
            within=pyomo.NonNegativeReals,
            doc='New transmission capacity (MW)')

        # storage
        self.cap_sto_c_new = pyomo.Var(
            self.sto_tuples,
            within=pyomo.NonNegativeReals,
            doc='New storage size (MWh)')
        self.cap_sto_p_new = pyomo.Var(
            self.sto_tuples,
            within=pyomo.NonNegativeReals,
            doc='New  storage power (MW)')
        self.e_sto_con = pyomo.Var(
            self.t, self.sto_tuples,
            within=pyomo.NonNegativeReals,
            doc='Energy content of storage (MWh) in timestep')

        # Benders Specific
        # Parameters, Variables, Expressions, Constraints, Objective
        # MASTER
        # Eta Variable
        self.eta = pyomo.Var(
            self.tm,
            within=pyomo.NonNegativeReals,
            bounds=(0.0, None),
            doc='eta')

        # Storage
        self.master_storage_state_upper = pyomo.Constraint(
            self.tm, self.sto_tuples,
            rule=res_storage_state_upper_rule,
            doc='master does not store more power than sub can provide')

        self.master_storage_state_lower = pyomo.Constraint(
            self.tm, self.sto_tuples,
            rule=res_storage_state_lower_rule,
            doc='master does not remove more power from storage than sub can use')

        # CO2 Generation
        self.master_co2_generation = pyomo.Constraint(
            self.com_env,
            rule=res_co2_generation_rule,
            doc='sum of all sites\' CO2 generation should be lower than co2_limit')

        # Cut List
        self.Cut_Defn = pyomo.ConstraintList(noruleinit=True)

        for pro in self.pro_tuples:
            self.pro_new[pro].expr = self.cap_pro_new[pro]
        for tra in self.tra_tuples:
            self.tra_new[tra].expr = self.cap_tra_new[tra]
        for sto in self.sto_tuples:
            self.sto_c_new[sto].expr = self.cap_sto_c_new[sto]
            self.sto_p_new[sto].expr = self.cap_sto_p_new[sto]
            for t in self.t:
                self.e_sto_state[t, sto].expr = self.cap_sto_c[sto] * self.storage_dict['init'][sto]

        # Equation declarations
        # equation bodies are defined in separate functions, referred to here by
        # their name in the "rule" keyword.

        # costs
        self.def_costs = pyomo.Constraint(
            self.cost_type,
            rule=def_costs_rule,
            doc='main cost function by cost type')

        # commodity
        self.res_stock_total = pyomo.Constraint(
            self.com_tuples,
            rule=res_stock_total_rule,
            doc='total stock commodity input <= commodity.max')

        # transmission
        self.res_transmission_symmetry = pyomo.Constraint(
            self.tra_tuples,
            rule=res_transmission_symmetry_rule,
            doc='total transmission capacity must be symmetric in both directions')

        # Objective
        self.obj = pyomo.Objective(
            rule=obj_rule,
            sense=pyomo.minimize,
            doc='minimize(cost = sum of all cost types)')

        # storage
        self.res_storage_state_by_capacity = pyomo.Constraint(
            self.t, self.sto_tuples,
            rule=res_storage_state_by_capacity_rule,
            doc='storage content <= storage capacity')
        self.res_initial_and_final_storage_state = pyomo.Constraint(
            self.t, self.sto_tuples,
            rule=res_initial_and_final_storage_state_rule,
            doc='storage content initial == and final >= storage.init * capacity')

    def add_cut(self, cut_generating_problem, readable_cuts=False):
        """
        Adds a cut to the master problem, which is generated by a sub problem

        Args:
            cut_generating_problem: sub problem which generates the cut
            readable_cuts:  scale cuts to make them easier to read (may cause numerical issues)
        """
        if cut_generating_problem.Lambda() < 0.000001:
            print('Cut skipped for subproblem ' + str(cut_generating_problem) + ' (Lambda = ' + str(
                cut_generating_problem.Lambda()) + ')')
            return

        # dual variables
        multi_index = pd.MultiIndex.from_tuples([(t,) + sto
                                                 for t in self.t
                                                 for sto in self.sto_tuples],
                                                names=['t', 'sit', 'sto', 'com'])
        dual_sto = pd.Series(0, index=multi_index)
        dual_sto_help = get_entity(cut_generating_problem, 'res_initial_and_final_storage_state')
        dual_sto = dual_sto.add(-abs(dual_sto_help.loc[[cut_generating_problem.ts[1]]]), fill_value=0)
        dual_sto = dual_sto.add(abs(dual_sto_help.loc[[cut_generating_problem.ts[-1]]]), fill_value=0)

        dual_pro = get_entity(cut_generating_problem, 'def_process_capacity')
        dual_tra = get_entity(cut_generating_problem, 'def_transmission_capacity')
        dual_sto_cap = get_entity(cut_generating_problem, 'def_storage_capacity')
        dual_sto_capl = get_entity(cut_generating_problem, 'def_storage_capacity_l')
        dual_sto_pow = get_entity(cut_generating_problem, 'def_storage_power')
        dual_com_src = get_entity(cut_generating_problem, 'sub_commodity_source')
        dual_env = get_entity(cut_generating_problem, 'res_global_co2_limit')

        dual_zero = cut_generating_problem.dual[cut_generating_problem.sub_costs]
        Lambda = cut_generating_problem.Lambda()

        cut_expression = - 1 * (sum(dual_pro[pro] * self.cap_pro[pro] for pro in self.pro_tuples) +
                                sum(dual_tra[tra] * self.cap_tra[tra] for tra in self.tra_tuples) +
                                sum((dual_sto_cap[sto] - dual_sto_capl[sto]) * self.cap_sto_c[sto] for sto in self.sto_tuples) +
                                sum(dual_sto_pow[sto] * self.cap_sto_p[sto] for sto in self.sto_tuples) +
                                sum([dual_sto[(t,) + sto] * self.e_sto_con[(t,) + sto]
                                     for t in self.t
                                     for sto in self.sto_tuples]) +
                                sum([dual_com_src[com] * self.e_co_stock[(cut_generating_problem.tm[-1],) + com]
                                     for com in self.com_tuples if
                                     com[1] in self.com_stock
                                     and not math.isinf(self.commodity_dict['max'][com])]) +
                                sum([dual_env[0] * self.e_co_stock[(cut_generating_problem.tm[-1],) + com]
                                     for com in self.com_tuples
                                     if com[1] in self.com_env]) +
                                dual_zero * self.eta[cut_generating_problem.tm[-1]])

        # cut generation
        if readable_cuts and dual_zero != 0:
            cut = 1 / (-dual_zero) * cut_expression >= 1 / (-dual_zero) * (Lambda + cut_expression())
        else:
            cut = cut_expression >= Lambda + cut_expression()
        self.Cut_Defn.add(cut)


# DivideTimestepsMaster specific Constraints


# CO2 generation of master problem <= global co2 limit
def res_co2_generation_rule(m, com):
    return (sum(m.e_co_stock[tm, sit, com, 'Env']
                for tm in m.tm for sit in m.sit) <=
            m.global_prop.loc['CO2 limit', 'value'])


# costs rule for master
# Objective
def def_costs_rule(m, cost_type):
    """Calculate total costs by cost type.

    Sums up process activity and capacity expansions
    and sums them in the cost types that are specified in the set
    m.cost_type. To change or add cost types, add/change entries
    there and modify the if/elif cases in this function accordingly.

    Cost types are
      - Investment costs for process power, storage power and
        storage capacity. They are multiplied by the annuity
        factors.
      - Fixed costs for process power, storage power and storage
        capacity.
      - Variables costs for usage of processes, storage and transmission.
      - Fuel costs for stock commodity purchase.

    """
    if cost_type == 'Invest':
        return m.costs[cost_type] == \
               sum(m.cap_pro_new[p] *
                   m.process_dict['inv-cost'][p] *
                   m.process_dict['annuity-factor'][p]
                   for p in m.pro_tuples) + \
               sum(m.cap_tra_new[t] *
                   m.transmission_dict['inv-cost'][t] *
                   m.transmission_dict['annuity-factor'][t]
                   for t in m.tra_tuples) + \
               sum(m.cap_sto_p_new[s] *
                   m.storage_dict['inv-cost-p'][s] *
                   m.storage_dict['annuity-factor'][s] +
                   m.cap_sto_c_new[s] *
                   m.storage_dict['inv-cost-c'][s] *
                   m.storage_dict['annuity-factor'][s]
                   for s in m.sto_tuples)

    elif cost_type == 'Fixed':
        return m.costs[cost_type] == \
               sum(m.cap_pro[p] * m.process_dict['fix-cost'][p]
                   for p in m.pro_tuples) + \
               sum(m.cap_tra[t] * m.transmission_dict['fix-cost'][t]
                   for t in m.tra_tuples) + \
               sum(m.cap_sto_p[s] * m.storage_dict['fix-cost-p'][s] +
                   m.cap_sto_c[s] * m.storage_dict['fix-cost-c'][s]
                   for s in m.sto_tuples)

    elif cost_type == 'Variable':
        return m.costs[cost_type] == 0.0

    elif cost_type == 'Fuel':
        return m.costs[cost_type] == 0.0

    elif cost_type == 'Environmental':
        return m.costs[cost_type] == 0.0

    elif cost_type == 'FutureCosts':
        return m.costs[cost_type] == sum(m.eta[t] for t in m.tm)

    else:
        raise NotImplementedError("Unknown cost type.")


from .sddp_super import *


class SddpMaster(SddpSuper):
    def __init__(self, data, timesteps=None, supportsteps=[], dt=1, dual=False, model_type=urbsType.master, first_timestep=0):
        """Initiates SddpMaster as a pyomo ConcreteModel urbs object from given input data.

        Args:
            data: a dict of 6 DataFrames with the keys 'commodity', 'process',
                'transmission', 'storage', 'demand' and 'supim'.
            timesteps: optional list of timesteps, default: demand timeseries
            dt: timestep duration in hours (default: 1)
            dual: set True to add dual variables to model (slower); default: False
            model_type: model_type of the problem; 0: Normal(default), 1:Sub, 2: Master
            first_timestep: The timestep at which the non decomposed problem starts. This is needed to calculate the weight parameter correctly. The default is set to 0.
        """
        super().__init__(data, timesteps, supportsteps, dt, dual, model_type, first_timestep=first_timestep)
        # Initialize master model specific things
        self.name = 'urbs-master'
        print(self.name + ' is created.')

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

        # Benders Specific
        # Parameters, Variables, Expressions, Constraints, Objective

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

        # transmission
        self.res_transmission_symmetry = pyomo.Constraint(
            self.tra_tuples,
            rule=res_transmission_symmetry_rule,
            doc='total transmission capacity must be symmetric in both'
                'directions')

        # objective
        self.obj = pyomo.Objective(
            rule=obj_rule,
            sense=pyomo.minimize,
            doc='minimize(cost = sum of all cost types)')

        self.res_initial_and_final_storage_state = pyomo.Constraint(
            self.t, self.sto_tuples,
            rule=res_initial_and_final_storage_state_rule,
            doc='storage content initial == and final >= storage.init * capacity')


# SddpMaster specific Constraints

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
        return m.costs[cost_type] == \
               sum(m.tau_pro[(tm,) + p] * m.dt *
                   m.process_dict['var-cost'][p] *
                   m.weight
                   for tm in m.tm
                   for p in m.pro_tuples) + \
               sum(m.e_tra_in[(tm,) + t] * m.dt *
                   m.transmission_dict['var-cost'][t] *
                   m.weight
                   for tm in m.tm
                   for t in m.tra_tuples) + \
               sum(m.e_sto_con[(tm,) + s] *
                   m.storage_dict['var-cost-c'][s] * m.weight +
                   (m.e_sto_in[(tm,) + s] + m.e_sto_out[(tm,) + s]) * m.dt *
                   m.storage_dict['var-cost-p'][s] * m.weight
                   for tm in m.tm
                   for s in m.sto_tuples)

    elif cost_type == 'Fuel':
        return m.costs[cost_type] == sum(
            m.e_co_stock[(tm,) + c] * m.dt *
            m.commodity_dict['price'][c] *
            m.weight
            for tm in m.tm for c in m.com_tuples
            if c[1] in m.com_stock)

    elif cost_type == 'Environmental':
        return m.costs[cost_type] == sum(
            - commodity_balance(m, tm, sit, com) *
            m.weight * m.dt *
            m.commodity_dict['price'][sit, com, com_type]
            for tm in m.tm
            for sit, com, com_type in m.com_tuples
            if com in m.com_env)

    elif cost_type == 'FutureCosts':
        return m.costs[cost_type] == m.eta

    else:
        raise NotImplementedError("Unknown cost type.")



# initialization of storage content in first timestep t[1]
# forced minimun  storage content in final timestep t[len(m.t)]
# content[t=1] == storage capacity * fraction <= content[t=final]
# TODO: compare with rule in super.py and see if it can be unified
def res_initial_and_final_storage_state_rule(m, t, sit, sto, com):
    if t == m.t[1]:  # first and last timestep (Pyomo uses 1-based indexing)
        return (m.e_sto_con[t, sit, sto, com] ==
                m.cap_sto_c[sit, sto, com] *
                m.storage_dict['init'][sit, sto, com])
    else:
        return pyomo.Constraint.Skip





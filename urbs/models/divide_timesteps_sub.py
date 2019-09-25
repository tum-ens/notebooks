from .divide_timesteps_super import *


class DivideTimestepsSub(DivideTimestepsSuper):
    def __init__(self, data, timesteps=None, supportsteps=[], dt=1, dual=False, model_type=urbsType.sub):
        """Initiates this class as a pyomo ConcreteModel urbs object from given input data.

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
        self.name = 'urbs-sub' + str(timesteps[0])
        print(self.name + ' is created.')

        # Parameters

        # weight = length of year (hours) / length of simulation (hours)
        # weight scales costs and emissions from length of simulation to a full
        # year, making comparisons among cost types (invest is annualized, fixed
        # costs are annual by default, variable costs are scaled by weight) and
        # among different simulation durations meaningful.
        self.weight = pyomo.Param(
            initialize=float(8760) / ((max(supportsteps) - min(supportsteps)) * dt),
            # initialize=float(8760) / (len(self.tm) * dt),
            doc='Pre-factor for variable costs and emissions for an annual result')

        # Variables

        # process
        self.tau_pro = pyomo.Var(
            self.t, self.pro_tuples,
            within=pyomo.NonNegativeReals,
            doc='Power flow (MW) through process')
        self.e_pro_in = pyomo.Var(
            self.tm, self.pro_input_tuples,
            within=pyomo.NonNegativeReals,
            doc='Power flow of commodity into process (MW) per timestep')
        self.e_pro_out = pyomo.Var(
            self.tm, self.pro_output_tuples,
            within=pyomo.NonNegativeReals,
            doc='Power flow out of process (MW) per timestep')

        # transmission
        self.e_tra_in = pyomo.Var(
            self.tm, self.tra_tuples,
            within=pyomo.NonNegativeReals,
            doc='Power flow into transmission line (MW) per timestep')
        self.e_tra_out = pyomo.Var(
            self.tm, self.tra_tuples,
            within=pyomo.NonNegativeReals,
            doc='Power flow out of transmission line (MW) per timestep')
        # storage
        self.e_sto_in = pyomo.Var(
            self.tm, self.sto_tuples,
            within=pyomo.NonNegativeReals,
            doc='Power flow into storage (MW) per timestep')
        self.e_sto_out = pyomo.Var(
            self.tm, self.sto_tuples,
            within=pyomo.NonNegativeReals,
            doc='Power flow out of storage (MW) per timestep')
        self.e_sto_con = pyomo.Var(
            self.t, self.sto_tuples,
            within=pyomo.Reals,
            doc='Energy content of storage (MWh) in timestep')

        # Benders Specific
        # Parameters, Variables, Expressions, Constraints, Objective
        # SUB
        # Omegas
        self.omega = 1
        self.omegazero = 1

        # Dual Variable
        self.dual = pyomo.Suffix(direction=pyomo.Suffix.IMPORT)

        # Lambda Variable
        self.Lambda = pyomo.Var(
            within=pyomo.NonNegativeReals,
            bounds=(0.0, None),
            doc='Sub Problem Objective')

        # Expressions
        self.e_co_stock_res = pyomo.Expression(
            self.com_tuples,
            doc='commodity source restriction (SUB)')
        self.eta_res = pyomo.Expression(
            self.ts,
            doc='eta variable restriction (SUB)')

        # Constraints
        self.sub_commodity_source = pyomo.Constraint(
            self.com_tuples,
            rule=sub_commodity_source_rule,
            doc='sub commodity source <= master commodity source')
        self.sub_costs = pyomo.Constraint(rule=sub_costs_rule)

        # Sub Objective
        self.obj = pyomo.Objective(
            rule=sub_obj_rule,
            sense=pyomo.minimize,
            doc='minimize(Lambda)')

        for pro in self.pro_tuples:
            self.pro_relax[pro].expr = self.Lambda * self.omega
        for tra in self.tra_tuples:
            self.tra_relax[tra].expr = self.Lambda * self.omega
        for sto in self.sto_tuples:
            self.sto_c_relax[sto].expr = self.Lambda * self.omega
            self.sto_p_relax[sto].expr = self.Lambda * self.omega
            for t in self.t:
                self.e_sto_relax[t, sto].expr = self.Lambda * self.omega

        # Equation declarations
        # equation bodies are defined in separate functions, referred to here by
        # their name in the "rule" keyword.

        # costs
        self.def_costs = pyomo.Constraint(
            self.cost_type,
            rule=def_costs_rule,
            doc='main cost function by cost type')

        # commodity
        self.res_vertex = pyomo.Constraint(
            self.tm, self.com_tuples,
            rule=res_vertex_rule,
            doc='storage + transmission + process + source == demand')
        self.res_stock_step = pyomo.Constraint(
            self.tm, self.com_tuples,
            rule=res_stock_step_rule,
            doc='stock commodity input per step <= commodity.maxperstep')
        self.res_env_step = pyomo.Constraint(
            self.tm, self.com_tuples,
            rule=res_env_step_rule,
            doc='environmental output per step <= commodity.maxperstep')
        self.res_env_total = pyomo.Constraint(
            self.com_tuples,
            rule=res_env_total_rule,
            doc='total environmental commodity output <= commodity.max')

        # process
        self.def_process_input = pyomo.Constraint(
            self.tm, self.pro_input_tuples,  # - self.pro_partial_input_tuples,
            rule=def_process_input_rule,
            doc='process input = process throughput * input ratio')
        self.def_process_output = pyomo.Constraint(
            self.tm, self.pro_output_tuples,
            rule=def_process_output_rule,
            doc='process output = process throughput * output ratio')
        self.def_intermittent_supply = pyomo.Constraint(
            self.tm, self.pro_input_tuples,
            rule=def_intermittent_supply_rule,
            doc='process output = process capacity * supim timeseries')
        self.res_process_throughput_by_capacity = pyomo.Constraint(
            self.tm, self.pro_tuples,
            rule=res_process_throughput_by_capacity_rule,
            doc='process throughput <= total process capacity')
        self.res_process_maxgrad_lower = pyomo.Constraint(
            self.tm, self.pro_maxgrad_tuples,
            rule=res_process_maxgrad_lower_rule,
            doc='throughput may not decrease faster than maximal gradient')
        self.res_process_maxgrad_upper = pyomo.Constraint(
            self.tm, self.pro_maxgrad_tuples,
            rule=res_process_maxgrad_upper_rule,
            doc='throughput may not increase faster than maximal gradient')
        self.res_area = pyomo.Constraint(
            self.sit,
            rule=res_area_rule,
            doc='used process area <= total process area')

        # transmission
        self.res_transmission_input_by_capacity = pyomo.Constraint(
            self.tm, self.tra_tuples,
            rule=res_transmission_input_by_capacity_rule,
            doc='transmission input <= total transmission capacity')
        self.def_transmission_output = pyomo.Constraint(
            self.tm, self.tra_tuples,
            rule=def_transmission_output_rule,
            doc='transmission output = transmission input * efficiency')

        # storage
        self.def_storage_state = pyomo.Constraint(
            self.tm, self.sto_tuples,
            rule=def_storage_state_rule,
            doc='storage[t] = storage[t-1] + (1 - discharge) + input - output')
        self.res_storage_input_by_power = pyomo.Constraint(
            self.tm, self.sto_tuples,
            rule=res_storage_input_by_power_rule,
            doc='storage input <= storage power')
        self.res_storage_output_by_power = pyomo.Constraint(
            self.tm, self.sto_tuples,
            rule=res_storage_output_by_power_rule,
            doc='storage output <= storage power')

        self.res_storage_state_by_capacity = pyomo.Constraint(
            self.t, self.sto_tuples,
            rule=res_storage_state_by_capacity_rule,
            doc='storage content <= storage capacity')
        self.res_initial_and_final_storage_state = pyomo.Constraint(
            self.t, self.sto_tuples,
            rule=res_initial_and_final_storage_state_rule,
            doc='storage content initial == and final >= storage.init * capacity')

        self.res_global_co2_limit = pyomo.Constraint(
            rule=res_global_co2_limit_rule,
            doc='total co2 commodity output <= global_prop.Global CO2 limit')


# DivideTimestepsSub specific Constraints


# Benders specific functions
# sub commodity source <= master commodity source
# TODO: rule is similar to sub_com_generation_rule in sddp. com_max_tuples feature is missing here, but would be nice.
def sub_commodity_source_rule(m, sit, com, com_type):
    if com not in m.com_stock or math.isinf(m.commodity_dict['max'][sit, com, com_type]):
        return pyomo.Constraint.Skip
    else:
        return (sum(m.e_co_stock[tm, sit, com, com_type] for tm in m.tm) <=
                m.e_co_stock_res[sit, com, com_type] +
                m.Lambda * m.omega)


# sub costs rule
def sub_costs_rule(m):
    return (pyomo.summation(m.costs) <= m.eta_res[m.t[-1]] + m.Lambda * m.omegazero)


# total CO2 output <= Global CO2 limit
def res_global_co2_limit_rule(m):
    if math.isinf(m.global_prop.loc['CO2 limit', 'value']):
        return pyomo.Constraint.Skip
    elif m.global_prop.loc['CO2 limit', 'value'] >= 0:
        co2_output_sum = 0
        for tm in m.tm:
            for sit in m.sit:
                # minus because negative commodity_balance represents creation of
                # that commodity.
                co2_output_sum += (- commodity_balance(m, tm, sit, 'CO2') * m.dt)

        # scaling to annual output (cf. definition of m.weight)
        co2_output_sum *= m.weight
        return (co2_output_sum <= sum(m.e_co_stock_res[sit, 'CO2', 'Env'] for sit in m.sit) + m.Lambda * m.omega)
    else:
        return pyomo.Constraint.Skip


# costs rule for sub
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
        return m.costs[cost_type] == 0.0

    elif cost_type == 'Fixed':
        return m.costs[cost_type] == 0.0

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

    else:
        raise NotImplementedError("Unknown cost type.")







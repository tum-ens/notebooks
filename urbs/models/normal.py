from .super import *
import math


class Normal(ModelSuper):
    def __init__(self, data, timesteps=None, dt=1, dual=False):
        """Initiates this class as a pyomo ConcreteModel URBS object from given input data.

            Args:
                data: a dict of 6 DataFrames with the keys 'commodity', 'process',
                    'transmission', 'storage', 'demand' and 'supim'.
                timesteps: optional list of timesteps, default: demand timeseries
                dt: timestep duration in hours (default: 1)
                dual: set True to add dual variables to model (slower); default: False
            """
        super().__init__(data, timesteps, dt, dual, model_type=urbsType.normal, decomposition_method=None)

        self.name = 'urbs-normal'

        self.model_type = urbsType.normal

        print(self.name + ' is created.')

        # Sets
        # ====
        # Syntax: self.{name} = Set({domain}, initialize={values})
        # where name: set name
        #       domain: set domain for tuple sets, a cartesian set product
        #       values: set values, a list or array of element tuples

        # Parameters

        # weight = length of year (hours) / length of simulation (hours)
        # weight scales costs and emissions from length of simulation to a full
        # year, making comparisons among cost types (invest is annualized, fixed
        # costs are annual by default, variable costs are scaled by weight) and
        # among different simulation durations meaningful.
        self.weight = pyomo.Param(
            initialize=float(8760) / (len(self.tm) * dt),
            doc='Pre-factor for variable costs and emissions for an annual result')

        # Variables

        # process
        self.cap_pro = pyomo.Var(
            self.pro_tuples,
            within=pyomo.NonNegativeReals,
            doc='Total process capacity (MW)')
        self.cap_pro_new = pyomo.Var(
            self.pro_tuples,
            within=pyomo.NonNegativeReals,
            doc='New process capacity (MW)')
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
        self.cap_tra = pyomo.Var(
            self.tra_tuples,
            within=pyomo.NonNegativeReals,
            doc='Total transmission capacity (MW)')
        self.cap_tra_new = pyomo.Var(
            self.tra_tuples,
            within=pyomo.NonNegativeReals,
            doc='New transmission capacity (MW)')
        self.e_tra_in = pyomo.Var(
            self.tm, self.tra_tuples,
            within=pyomo.NonNegativeReals,
            doc='Power flow into transmission line (MW) per timestep')
        self.e_tra_out = pyomo.Var(
            self.tm, self.tra_tuples,
            within=pyomo.NonNegativeReals,
            doc='Power flow out of transmission line (MW) per timestep')

        # storage
        self.cap_sto_c = pyomo.Var(
            self.sto_tuples,
            within=pyomo.NonNegativeReals,
            doc='Total storage size (MWh)')
        self.cap_sto_c_new = pyomo.Var(
            self.sto_tuples,
            within=pyomo.NonNegativeReals,
            doc='New storage size (MWh)')
        self.cap_sto_p = pyomo.Var(
            self.sto_tuples,
            within=pyomo.NonNegativeReals,
            doc='Total storage power (MW)')
        self.cap_sto_p_new = pyomo.Var(
            self.sto_tuples,
            within=pyomo.NonNegativeReals,
            doc='New  storage power (MW)')
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
            within=pyomo.NonNegativeReals,
            doc='Energy content of storage (MWh) in timestep')

        for pro in self.pro_tuples:
            self.pro_new[pro].expr = self.cap_pro_new[pro]
        for tra in self.tra_tuples:
            self.tra_new[tra].expr = self.cap_tra_new[tra]
        for sto in self.sto_tuples:
            self.sto_c_new[sto].expr = self.cap_sto_c_new[sto]
            self.sto_p_new[sto].expr = self.cap_sto_p_new[sto]
            for t in self.t:
                self.e_sto_state[t, sto].expr = self.cap_sto_c[sto] * self.storage.loc[sto]['init']

        # Equation declarations
        # equation bodies are defined in separate functions, referred to here by
        # their name in the "rule" keyword.

        # commodity
        self.res_vertex = pyomo.Constraint(
            self.tm, self.com_tuples,
            rule=res_vertex_rule,
            doc='storage + transmission + process + source + buy - sell == demand')
        self.res_stock_step = pyomo.Constraint(
            self.tm, self.com_tuples,
            rule=res_stock_step_rule,
            doc='stock commodity input per step <= commodity.maxperstep')
        self.res_stock_total = pyomo.Constraint(
            self.com_tuples,
            rule=res_stock_total_rule,
            doc='total stock commodity input <= commodity.max')
        self.res_env_step = pyomo.Constraint(
            self.tm, self.com_tuples,
            rule=res_env_step_rule,
            doc='environmental output per step <= commodity.maxperstep')
        self.res_env_total = pyomo.Constraint(
            self.com_tuples,
            rule=res_env_total_rule,
            doc='total environmental commodity output <= commodity.max')

        # process
        self.def_process_capacity = pyomo.Constraint(
            self.pro_tuples,
            rule=def_process_capacity_rule,
            doc='total process capacity = inst-cap + new capacity')
        self.def_process_input = pyomo.Constraint(
            self.tm, self.pro_input_tuples,# - self.pro_partial_input_tuples,
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
        self.res_process_capacity = pyomo.Constraint(
            self.pro_tuples,
            rule=res_process_capacity_rule,
            doc='process.cap-lo <= total process capacity <= process.cap-up')

        self.res_area = pyomo.Constraint(
            self.sit,
            rule=res_area_rule,
            doc='used process area <= total process area')

        # transmission
        self.def_transmission_capacity = pyomo.Constraint(
            self.tra_tuples,
            rule=def_transmission_capacity_rule,
            doc='total transmission capacity = inst-cap + new capacity')
        self.def_transmission_output = pyomo.Constraint(
            self.tm, self.tra_tuples,
            rule=def_transmission_output_rule,
            doc='transmission output = transmission input * efficiency')
        self.res_transmission_input_by_capacity = pyomo.Constraint(
            self.tm, self.tra_tuples,
            rule=res_transmission_input_by_capacity_rule,
            doc='transmission input <= total transmission capacity')
        self.res_transmission_capacity = pyomo.Constraint(
            self.tra_tuples,
            rule=res_transmission_capacity_rule,
            doc='transmission.cap-lo <= total transmission capacity <= '
                'transmission.cap-up')
        self.res_transmission_symmetry = pyomo.Constraint(
            self.tra_tuples,
            rule=res_transmission_symmetry_rule,
            doc='total transmission capacity must be symmetric in both directions')

        # storage
        self.def_storage_state = pyomo.Constraint(
            self.tm, self.sto_tuples,
            rule=def_storage_state_rule,
            doc='storage[t] = storage[t-1] + input - output')
        self.def_storage_power = pyomo.Constraint(
            self.sto_tuples,
            rule=def_storage_power_rule,
            doc='storage power = inst-cap + new power')
        self.def_storage_capacity = pyomo.Constraint(
            self.sto_tuples,
            rule=def_storage_capacity_rule,
            doc='storage capacity = inst-cap + new capacity')
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
        self.res_storage_power = pyomo.Constraint(
            self.sto_tuples,
            rule=res_storage_power_rule,
            doc='storage.cap-lo-p <= storage power <= storage.cap-up-p')
        self.res_storage_capacity = pyomo.Constraint(
            self.sto_tuples,
            rule=res_storage_capacity_rule,
            doc='storage.cap-lo-c <= storage capacity <= storage.cap-up-c')
        self.res_initial_and_final_storage_state = pyomo.Constraint(
            self.t, self.sto_tuples,
            rule=res_initial_and_final_storage_state_rule,
            doc='storage content initial == and final >= storage.init * capacity')

        # costs
        self.def_costs = pyomo.Constraint(
            self.cost_type,
            rule=def_costs_rule,
            doc='main cost function by cost type')
        self.obj = pyomo.Objective(
            rule=obj_rule,
            sense=pyomo.minimize,
            doc='minimize(cost = sum of all cost types)')

        self.res_global_co2_limit = pyomo.Constraint(
            rule=res_global_co2_limit_rule,
            doc='total co2 commodity output <= Global CO2 limit')


# Normal specific Constraints


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
    else:
        raise NotImplementedError("Unknown cost type.")


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
        return (co2_output_sum <= m.global_prop.loc['CO2 limit', 'value'])
    else:
        return pyomo.Constraint.Skip


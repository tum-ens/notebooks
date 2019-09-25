from .regional_super import *


class RegionalSub(RegionalSuper):
    def __init__(self, data, timesteps=None, dt=1, dual=False, model_type=urbsType.sub, site=None, msites=None):
        """Inititates this class as a pyomo ConcreteModel urbs object from given input data.

        Args:
            data: a dict of 6 DataFrames with the keys 'commodity', 'process',
                'transmission', 'storage', 'demand' and 'supim'.
            timesteps: optional list of timesteps, default: demand timeseries
            dt: timestep duration in hours (default: 1)
            dual: set True to add dual variables to model (slower); default: False
            model_type: model_type of the problem; 0: Normal(default), 1:Sub, 2: Master
            site: site of the sub problem
            msites: set of the master problem sites
        """
        super().__init__(data, timesteps, dt, dual, model_type, site, msites)
        # Initialize sub model specific things
        # Check Input File Errors
        if model_type is urbsType.subwfile and data['site'].index.isin(msites).any():
            raise KeyError('A site which appears in a separate ' + str(site) + ' input file ' +
                           'cannot have the same name as a site in the master input file.')
        self.name = 'urbs-sub' + str(site)
        print(self.name + ' is created.')

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

        # Omegas
        self.omega = pyomo.Param(mutable=True, initialize=1)
        self.omegazero = pyomo.Param(mutable=True, initialize=1)

        # Dual Variable
        self.dual = pyomo.Suffix(direction=pyomo.Suffix.IMPORT)

        # Lambda Variable
        self.Lambda = pyomo.Var(
            within=pyomo.NonNegativeReals,
            doc='Sub Problem Objective')

        # Parameters
        self.eta_res = pyomo.Param(
            self.sub_site,
            mutable=True, initialize=0.0,
            doc='Eta variable restriction (SUB)')

        # Constraints
        self.sub_costs = pyomo.Constraint(
            rule=sub_costs_rule,
            doc='sub costs <= Lambda')

        # Sub Objective
        self.obj = pyomo.Objective(
            rule=sub_obj_rule,
            sense=pyomo.minimize,
            doc='minimize(Lambda)')

        for pro in self.pro_tuples:
            self.pro_new[pro].expr = self.cap_pro_new[pro]
        for sto in self.sto_tuples:
            self.sto_c_new[sto].expr = self.cap_sto_c_new[sto]
            self.sto_p_new[sto].expr = self.cap_sto_p_new[sto]
            for t in self.t:
                self.e_sto_state[t, sto].expr = self.cap_sto_c[sto] * self.storage_dict['init'][sto]


        # subproblem without input file
        # For some strange reason direct comparison with urbsType.sub doesn't work here
        if model_type.name == 'sub':
            # Parameters
            self.e_co_stock_res = pyomo.Param(
                self.tm, self.com_tuples,
                mutable=True, initialize=0.0,
                doc='commodity source restriction (SUB)')
            self.e_tra_res = pyomo.Param(
                self.tm, self.tra_tuples,
                mutable=True, initialize=0.0,
                doc='Power Flow in restriction (SUB)')

            # Constraints
            self.sub_e_tra = pyomo.Constraint(
                self.tm, self.tra_tuples,
                rule=sub_e_tra_rule,
                doc='sub e_tra_in <= master e_tra_in')

        # subproblem with input file
        else:
            # Variables
            self.cap_tra = pyomo.Var(
                self.tra_tuples,
                within=pyomo.NonNegativeReals,
                doc='Total transmission capacity (MW)')
            self.cap_tra_new = pyomo.Var(
                self.tra_tuples,
                within=pyomo.NonNegativeReals,
                doc='New transmission capacity (MW)')
                
            for tra in self.tra_tuples:
                self.tra_new[tra].expr = self.cap_tra_new[tra]

            # Parameters
            self.e_co_stock_res = pyomo.Param(
                self.tm,
                mutable=True, initialize=0.0,
                doc='commodity source restriction (SUB)')
            self.e_import_res = pyomo.Param(
                self.tm, self.sit_out,
                mutable=True, initialize=0.0,
                doc='Transmission variable (Import) restriction (SUB)')
            self.e_export_res = pyomo.Param(
                self.tm, self.sit_out,
                mutable=True, initialize=0.0,
                doc='Transmission variable (Export) restriction (SUB)')

            # Constraints
            self.def_transmission_capacity = pyomo.Constraint(
                self.tra_tuples,
                rule=def_transmission_capacity_rule,
                doc='total transmission capacity = inst-cap + new capacity')
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
                doc='total tra. capacity must be symmetric in both directions')
            self.res_hvac = pyomo.Constraint(
                self.sit_out,
                rule=res_hvac_rule,
                doc='transmission capacity restriction')
            self.res_import = pyomo.Constraint(
                self.tm, self.sit_out,
                rule=res_import_rule,
                doc='Electric import restriction')
            self.res_export = pyomo.Constraint(
                self.tm, self.sit_out,
                rule=res_export_rule,
                doc='Electric export restriction')

        # commodity
        self.res_vertex = pyomo.Constraint(
            self.tm, self.com_tuples,
            rule=res_vertex_rule,
            doc='storage + transmission + process + source == demand')
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
            self.tm, self.pro_input_tuples,  # - self.pro_partial_input_tuples,
            rule=def_process_input_rule,
            doc='process input = process throughput * input ratio')
        self.def_process_output = pyomo.Constraint(
            self.tm, self.pro_output_tuples,  # - self.pro_partial_output_tuples,
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
            self.sub_sit,
            rule=res_area_rule,
            doc='used process area <= total process area')

        # storage
        self.def_storage_state = pyomo.Constraint(
            self.tm, self.sto_tuples,
            rule=def_storage_state_rule,
            doc='storage[t] = storage[t-1] * (1 - discharge) + input - output')
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
            doc='storage content init == and final >= storage.init * capacity')

        # Equation Declarations
        # costs
        self.def_costs = pyomo.Constraint(
            self.cost_type,
            rule=def_costs_rule,
            doc='main cost function by cost type')

        self.res_global_co2_limit = pyomo.Constraint(
            rule=res_global_co2_limit_rule,
            doc='total co2 commodity output <= Global CO2 limit')


# RegionalSub specific Constraints


# process input (for supim commodity) = process capacity * timeseries
#TODO: everywhere else this rule uses <= instead of ==. can it just be changed and the rules be unified?
def def_intermittent_supply_rule(m, tm, sit, pro, coin):
    if coin in m.com_supim:
        return (m.e_pro_in[tm, sit, pro, coin] ==
                m.cap_pro[sit, pro] * m.supim_dict[(sit, coin)][tm])
    else:
        return pyomo.Constraint.Skip


# storage

# initialization of storage content in first timestep t[1]
# forced minimun  storage content in final timestep t[len(m.t)]
# content[t=1] == storage capacity * fraction <= content[t=final]
# TODO: compare and possibly merge with res_initial_and_final_storage_state_rule in divide-timesteps, sddp
def res_initial_and_final_storage_state_rule(m, t, sit, sto, com):
    if t == m.t[1]:  # first timestep (Pyomo uses 1-based indexing)
        return (m.e_sto_con[t, sit, sto, com] ==
                m.cap_sto_c[sit, sto, com] *
                m.storage_dict['init'][(sit, sto, com)])
    elif t == m.t[len(m.t)]:  # last timestep
        return (m.e_sto_con[t, sit, sto, com] >=
                m.cap_sto_c[sit, sto, com] *
                m.storage_dict['init'][(sit, sto, com)])
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
    # SUB
    if m.model_type.name == 'sub':
        if cost_type is 'Invest':
            return m.costs[cost_type] == \
                   sum(m.cap_pro_new[p] *
                       m.process_dict['inv-cost'][p] *
                       m.process_dict['annuity-factor'][p]
                       for p in m.pro_tuples) + \
                   sum(m.cap_sto_p_new[s] *
                       m.storage_dict['inv-cost-p'][s] *
                       m.storage_dict['annuity-factor'][s] +
                       m.cap_sto_c_new[s] *
                       m.storage_dict['inv-cost-c'][s] *
                       m.storage_dict['annuity-factor'][s]
                       for s in m.sto_tuples)

        elif cost_type is 'Fixed':
            return m.costs[cost_type] == \
                   sum(m.cap_pro[p] * m.process_dict['fix-cost'][p]
                       for p in m.pro_tuples) + \
                   sum(m.cap_sto_p[s] * m.storage_dict['fix-cost-p'][s] +
                       m.cap_sto_c[s] * m.storage_dict['fix-cost-c'][s]
                       for s in m.sto_tuples)

        elif cost_type is 'Variable':
            return m.costs[cost_type] == \
                   sum(m.tau_pro[(tm,) + p] * m.dt * m.weight *
                       m.process_dict['var-cost'][p]
                       for tm in m.tm
                       for p in m.pro_tuples) + \
                   sum(m.e_sto_con[(tm,) + s] * m.weight *
                       m.storage_dict['var-cost-c'][s] +
                       m.dt * m.weight *
                       (m.e_sto_in[(tm,) + s] + m.e_sto_out[(tm,) + s]) *
                       m.storage_dict['var-cost-p'][s]
                       for tm in m.tm
                       for s in m.sto_tuples)

        elif cost_type is 'Fuel':
            return m.costs[cost_type] == sum(
                m.e_co_stock[(tm,) + c] * m.dt * m.weight *
                m.commodity_dict['price'][c]
                for tm in m.tm for c in m.com_tuples
                if c[1] in m.com_stock)

        elif cost_type is 'Environmental':
            return m.costs[cost_type] == sum(
                - commodity_balance(m, tm, sit, com) *
                m.weight * m.dt *
                m.commodity_dict['price'][(sit, com, com_type)]
                for tm in m.tm
                for sit, com, com_type in m.com_tuples
                if com in m.com_env)

        else:
            raise NotImplementedError("Unknown cost type.")

    elif m.model_type.name == 'subwfile':
        if cost_type is 'Invest':
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

        elif cost_type is 'Fixed':
            return m.costs[cost_type] == \
                   sum(m.cap_pro[p] * m.process_dict['fix-cost'][p]
                       for p in m.pro_tuples) + \
                   sum(m.cap_tra[t] * m.transmission_dict['fix-cost'][t]
                       for t in m.tra_tuples) + \
                   sum(m.cap_sto_p[s] * m.storage_dict['fix-cost-p'][s] +
                       m.cap_sto_c[s] * m.storage_dict['fix-cost-c'][s]
                       for s in m.sto_tuples)

        elif cost_type is 'Variable':
            return m.costs[cost_type] == \
                   sum(m.tau_pro[(tm,) + p] * m.dt * m.weight *
                       m.process_dict['var-cost'][p]
                       for tm in m.tm
                       for p in m.pro_tuples) + \
                   sum(m.e_tra_in[(tm,) + t] * m.dt * m.weight *
                       m.transmission_dict['var-cost'][t]
                       for tm in m.tm
                       for t in m.tra_tuples) + \
                   sum(m.e_sto_con[(tm,) + s] * m.weight *
                       m.storage_dict['var-cost-c'][s] +
                       m.dt * m.weight *
                       (m.e_sto_in[(tm,) + s] + m.e_sto_out[(tm,) + s]) *
                       m.storage_dict['var-cost-p'][s]
                       for tm in m.tm
                       for s in m.sto_tuples)

        elif cost_type is 'Fuel':
            return m.costs[cost_type] == sum(
                m.e_co_stock[(tm,) + c] * m.dt * m.weight *
                m.commodity_dict['price'][c]
                for tm in m.tm for c in m.com_tuples
                if c[1] in m.com_stock)

        elif cost_type is 'Environmental':
            return m.costs[cost_type] == sum(
                - commodity_balance(m, tm, sit, com) *
                m.weight * m.dt *
                m.commodity_dict['price'][(sit, com, com_type)]
                for tm in m.tm
                for sit, com, com_type in m.com_tuples
                if com in m.com_env)

        else:
            raise NotImplementedError("Unknown cost type.")


# Benders specific functions
# Sub e_tra_in = master e_tra_in
def sub_e_tra_rule(m, tm, sin, sout, tra, com):
    # Export
    if sin == m.sub_site[1]:
        return (-m.e_tra_out[tm, sin, sout, tra, com] <=
                -m.e_tra_res[tm, sin, sout, tra, com] + m.Lambda * m.omega)
    # Import
    else:
        return (m.e_tra_in[tm, sin, sout, tra, com] <=
                m.e_tra_res[tm, sin, sout, tra, com] + m.Lambda * m.omega)


# Electric export restriction
def res_export_rule(m, tm, sit_out):
    total_exp = sum(m.e_tra_out[tm, tra] for tra in m.tra_tuples
                    if tra[1] == sit_out)

    return (-total_exp <= -m.e_export_res[tm, sit_out] + m.Lambda * m.omega)


# Electric import restriction
def res_import_rule(m, tm, sit_out):
    total_imp = sum(m.e_tra_in[tm, tra] for tra in m.tra_tuples
                    if tra[0] == sit_out)

    return (total_imp <= m.e_import_res[tm, sit_out] + m.Lambda * m.omega)


# Transmission capacity restriction rule
def res_hvac_rule(m, sit_out):
    total_hvac = sum(m.cap_tra[tra] for tra in m.tra_tuples
                     if tra[0] == sit_out)

    return (total_hvac <= m.hvac[sit_out] + m.Lambda * m.omega)


# Sub costs rule
def sub_costs_rule(m):
    return (pyomo.summation(m.costs) <= m.eta_res[m.sub_site[1]] + m.Lambda * m.omegazero)


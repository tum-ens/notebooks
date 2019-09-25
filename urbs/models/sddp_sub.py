from .sddp_super import *


class SddpSub(SddpSuper):

    def create_uncertainty_supim(self, supim, factor):
        """
        create convex combination of supim time series for different scenarios

        Args:
            supim: pandas Series or DataFrame of supim time series of a specific commodity
            factor: float, between -1 and 1, which corresponds to the realization of the uncertainty

        Returns:
            pandas Series or DataFrame with convex combination
        """
        if factor < 0:
            supim_convex = (1 - abs(factor)) * supim
        elif factor > 0:
            supim_convex = abs(factor) + (1 - abs(factor)) * supim
        else:
            supim_convex = supim

        return supim_convex

    def create_uncertainty_data(self, data, factor):
        """
        Change dataframe to include modified uncertain time series

        Args:
            data: pandas DataFrame with original data
            factor: float, between -1 and 1, which corresponds to the realization of the uncertainty

        Returns:
            pandas DataFrame with modified data
        """

        # get supim sheet
        supim = data['supim']
        new_data = data.copy()
        new_supim = supim.copy(deep=True)
        wind_supim = new_supim.xs('Wind', axis=1, level=1)
        help_df = self.create_uncertainty_supim(wind_supim, factor)
        help_df.columns = pd.MultiIndex.from_product([help_df.columns, ['Wind']])
        new_supim.loc[:, (slice(None), 'Wind')] = help_df
        new_data['supim'] = new_supim

        return new_data

    def __init__(self, data, timesteps=None, supportsteps=[], dt=1, dual=False, model_type=urbsType.sub,
                 uncertainty_factor=0, first_timestep=0):
        """Initiates SddpSub as a pyomo ConcreteModel urbs object from given input data.

        Args:
            data: a dict of 6 DataFrames with the keys 'commodity', 'process',
                'transmission', 'storage', 'demand' and 'supim'.
            timesteps: optional list of timesteps, default: demand timeseries
            dt: timestep duration in hours (default: 1)
            dual: set True to add dual variables to model (slower); default: False
            model_type: model_type of the problem; 0: Normal(default), 1:Sub, 2: Master
            first_timestep: The timestep at which the non decomposed problem starts. This is needed to calculate the weight parameter correctly. The default is set to 0.
        """
        uncertainty_data = self.create_uncertainty_data(data, uncertainty_factor)
        super().__init__(uncertainty_data, timesteps, supportsteps, dt, dual, model_type, first_timestep=first_timestep)
        # Initialize sub model specific things
        self.name = 'urbs-sub' + str(timesteps[0])
        print(self.name + ' is created.')

        # Benders Specific
        # Parameters, Variables, Expressions, Constraints, Objective

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
        self.e_co_stock_state_res = pyomo.Expression(
            self.ts, self.com_tuples,
            initialize=0,
            doc='commodity source restriction (SUB)')
        self.e_sto_con_res = pyomo.Expression(
            self.ts, self.sto_tuples,
            initialize=0,
            doc='storage content restriction (SUB)')
        self.eta_res = pyomo.Expression(
            initialize=0,
            doc='eta variable restriction (SUB)')
        # TODO change to mutuable parameter without indices for all subs

        # Constraints
        # self.sub_commodity_source = pyomo.Constraint(
        #     self.com_tuples,
        #     rule=sub_commodity_source_rule,
        #     doc='sub commodity source <= master commodity source')
        self.sub_storage_content = pyomo.Constraint(
            self.t, self.sto_tuples,
            rule=sub_storage_content_rule,
            doc='sub storage content <= master storage content')
        self.sub_costs = pyomo.Constraint(
            rule=sub_costs_rule)
        self.sub_com_generation = pyomo.Constraint(
            self.t, self.com_max_tuples,
            rule=sub_com_generation_rule,
            doc='previous co2 generation >= master co2 generation'
        )

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


# SddpSub specific Constraints

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

    elif cost_type == 'FutureCosts':
        return m.costs[cost_type] == m.eta

    else:
        raise NotImplementedError("Unknown cost type.")


# Benders specific functions

# sub commodity source <= master commodity source
# def sub_commodity_source_rule(m, sit, com, com_type):
#     if com not in m.com_stock or math.isinf(m.commodity_dict['max'][sit, com, com_type]):
#         return pyomo.Constraint.Skip
#     else:
#         return (sum(m.e_co_stock[tm, sit, com, com_type] for tm in m.tm) <=
#                 m.e_co_stock_state[sit, com, com_type] +
#                 m.Lambda * m.omega)


# sub storage content <= master storage content
# These constraints have to be written in exactly this way in order
# not to get the wrong signs for the dual variables
def sub_storage_content_rule(m, t, sit, sto, com):
    if t == m.ts[1]:
        return (m.e_sto_con[t, sit, sto, com] -
                m.e_sto_con_res[t, sit, sto, com] <= m.Lambda * m.omega)
    # if t == m.ts[2]:
    #    return (m.e_sto_con[t, sit, sto, com] -
    #            m.e_sto_con_res[t, sit, sto, com] >= - m.Lambda * m.omega)
    else:
        return pyomo.Constraint.Skip


# previous env/stock output >= master env/stock consumption/output
def sub_com_generation_rule(m, t, sit, com, com_type):
    if t == m.ts[1] and (sit, com, com_type) in m.com_max_tuples:
        return (m.e_co_stock_state[t, sit, com, com_type] -
                m.e_co_stock_state_res[t, sit, com, com_type] >= - m.Lambda * m.omega)
    # if t == m.ts[2]:
    #    return (m.e_sto_con[t, sit, sto, com] -
    #            m.e_sto_con_res[t, sit, sto, com] >= - m.Lambda * m.omega)
    else:
        return pyomo.Constraint.Skip


# sub costs rule
def sub_costs_rule(m):
    return pyomo.summation(m.costs) <= m.eta_res + m.Lambda * m.omegazero



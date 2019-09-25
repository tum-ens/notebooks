from .super import *


class SddpSuper(ModelSuper, ABC):
    @abstractmethod
    def __init__(self,data, timesteps=None, supportsteps=[], dt=1, dual=False, model_type=urbsType.normal, first_timestep=0):
        """Initializes model parameters which are the same for Sddp master and sub.

        Args:
            data: a dict of 6 DataFrames with the keys 'commodity', 'process',
                'transmission', 'storage', 'demand' and 'supim'.
            timesteps: optional list of timesteps, default: demand timeseries
            dt: timestep duration in hours (default: 1)
            dual: set True to add dual variables to model (slower); default: False
            model_type: model_type of the problem; 0: Normal(default), 1:Sub, 2: Master
            first_timestep: The timestep at which the non decomposed problem starts. This is needed to calculate the weight parameter correctly. The default is set to 0.
        """
        super().__init__(data, timesteps, dt, dual, model_type, decomposition_method='sddp')
        self.supportsteps = supportsteps

        # Sets
        # ====
        # Syntax: self.{name} = Set({domain}, initialize={values})
        # where name: set name
        #       domain: set domain for tuple sets, a cartesian set product
        #       values: set values, a list or array of element tuples

        # generate support time step sets
        self.s = pyomo.Set(
            initialize=self.supportsteps,
            ordered=True,
            doc='Set of all support timesteps')

        # modelled support time step sets
        self.ts = pyomo.Set(
            within=self.s,
            initialize=self.t & self.s,
            ordered=True,
            doc='Set of modelled support timesteps')

        # commodity tuple subsets
        self.com_max_tuples = pyomo.Set(
            within=self.sit * self.com * self.com_type,
            initialize=[(site, commodity, commodity_type)
                        for (site, commodity, commodity_type) in self.com_tuples
                        if commodity_type == 'Env' or
                        (commodity_type == 'Stock' and
                         not math.isinf(float(self.commodity_dict['max'][site, commodity, commodity_type])))
                        ]
        )

        # add cost_type future cost
        self.cost_type.add('FutureCosts')

        # Parameters

        # weight = length of year (hours) / length of simulation (hours)
        # weight scales costs and emissions from length of simulation to a full
        # year, making comparisons among cost types (invest is annualized, fixed
        # costs are annual by default, variable costs are scaled by weight) and
        # among different simulation durations meaningful.
        self.weight = pyomo.Param(
            initialize=float(8760) / ((max(supportsteps) - first_timestep) * dt),
            # initialize=float(8760) / (len(self.tm) * dt),
            doc='Pre-factor for variable costs and emissions for an annual result')

        # Variables

        # commodity
        self.e_co_stock_state = pyomo.Var(
            self.t, self.com_tuples,
            initialize=0.0,
            within=pyomo.NonNegativeReals,
            doc='Use of stock commodity source until timestep')

        # process
        self.cap_pro = pyomo.Var(
            self.pro_tuples,
            within=pyomo.NonNegativeReals,
            doc='Total process capacity (MW)')
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
        self.cap_sto_p = pyomo.Var(
            self.sto_tuples,
            within=pyomo.NonNegativeReals,
            doc='Total storage power (MW)')
        self.e_sto_con = pyomo.Var(
            self.t, self.sto_tuples,
            within=pyomo.NonNegativeReals,
            doc='Energy content of storage (MWh) in timestep')
        self.e_sto_in = pyomo.Var(
            self.tm, self.sto_tuples,
            within=pyomo.NonNegativeReals,
            doc='Power flow into storage (MW) per timestep')
        self.e_sto_out = pyomo.Var(
            self.tm, self.sto_tuples,
            within=pyomo.NonNegativeReals,
            doc='Power flow out of storage (MW) per timestep')

        # Eta Variable
        self.eta = pyomo.Var(
            within=pyomo.NonNegativeReals,
            bounds=(0.0, None),
            doc='eta')

        # Cut List
        self.Cut_Defn = pyomo.ConstraintList(noruleinit=True)

        # Equation declarations
        # equation bodies are defined in separate functions, referred to here by
        # their name in the "rule" keyword.

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

        # process
        self.res_process_capacity = pyomo.Constraint(
            self.pro_tuples,
            rule=res_process_capacity_rule,
            doc='process.cap-lo <= total process capacity <= process.cap-up')
        self.def_process_capacity = pyomo.Constraint(
            self.pro_tuples,
            rule=def_process_capacity_rule,
            doc='total process capacity = inst-cap + new capacity')
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
        self.res_transmission_capacity = pyomo.Constraint(
            self.tra_tuples,
            rule=res_transmission_capacity_rule,
            doc='transmission.cap-lo <= total transmission capacity <= '
                'transmission.cap-up')
        self.def_transmission_capacity = pyomo.Constraint(
            self.tra_tuples,
            rule=def_transmission_capacity_rule,
            doc='total transmission capacity = inst-cap + new capacity')
        self.res_transmission_input_by_capacity = pyomo.Constraint(
            self.tm, self.tra_tuples,
            rule=res_transmission_input_by_capacity_rule,
            doc='transmission input <= total transmission capacity')
        self.def_transmission_output = pyomo.Constraint(
            self.tm, self.tra_tuples,
            rule=def_transmission_output_rule,
            doc='transmission output = transmission input * efficiency')

        # storage
        self.res_storage_capacity = pyomo.Constraint(
            self.sto_tuples,
            rule=res_storage_capacity_rule,
            doc='storage.cap-lo-c <= storage capacity <= storage.cap-up-c')
        self.res_storage_power = pyomo.Constraint(
            self.sto_tuples,
            rule=res_storage_power_rule,
            doc='storage.cap-lo-p <= storage power <= storage.cap-up-p')
        self.def_storage_capacity = pyomo.Constraint(
            self.sto_tuples,
            rule=def_storage_capacity_rule,
            doc='storage capacity <= inst-cap + new capacity + lambda*omega')
        self.def_storage_capacity_l = pyomo.Constraint(
            self.sto_tuples,
            rule=def_storage_capacity_l_rule,
            doc='storage capacity >= inst-cap + new capacity - lambda*omega')
        self.def_storage_power = pyomo.Constraint(
            self.sto_tuples,
            rule=def_storage_power_rule,
            doc='storage power = inst-cap + new power')
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

        self.final_storage_state = pyomo.Constraint(
            self.t, self.sto_tuples,
            rule=final_storage_state,
            doc='storage content final >= storage.init * capacity')
        # CO2 Generation
        self.global_co2_limit = pyomo.Constraint(
            self.tm, self.com_env,
            rule=global_co2_limit_rule,
            doc='sum of all sites\' CO2 generation should be lower than global_co2_limit')
        self.com_state = pyomo.Constraint(
            self.tm, self.com_max_tuples,
            rule=com_state_rule,
            doc="sum of environmental consumption, e.g. CO2"
        )
        self.com_total = pyomo.Constraint(
            self.tm, self.com_max_tuples,
            rule=com_total_rule,
            doc='total environmental commodity output until time step t <= commodity.max')

    def get_cut_expression(self, cut_generating_problem):
        """
        Calculates the cut expression for one realization

        Args:
            cut_generating problem: the realization which generates the cut

        Returns:
            the generated cut expression
        """
        multi_index = pd.MultiIndex.from_tuples([(t,) + sto
                                                 for t in cut_generating_problem.t
                                                 for sto in cut_generating_problem.sto_tuples],
                                                names=['t', 'sit', 'sto', 'com'])
        dual_sto = pd.Series(0, index=multi_index)

        dual_sto_help = get_entity(cut_generating_problem, 'sub_storage_content')
        dual_sto = dual_sto.add(-abs(dual_sto_help.loc[[cut_generating_problem.ts[1]]]), fill_value=0)

        dual_pro = get_entity(cut_generating_problem, 'def_process_capacity')
        dual_tra = get_entity(cut_generating_problem, 'def_transmission_capacity')
        dual_sto_cap = get_entity(cut_generating_problem, 'def_storage_capacity')
        dual_sto_capl = get_entity(cut_generating_problem, 'def_storage_capacity_l')
        dual_sto_pow = get_entity(cut_generating_problem, 'def_storage_power')
        dual_com = get_entity(cut_generating_problem, 'sub_com_generation')
        dual_zero = cut_generating_problem.dual[cut_generating_problem.sub_costs]

        cut_expression = - 1 * (sum(dual_pro[pro] * self.cap_pro[pro]
                              for pro in self.pro_tuples) +
                          sum(dual_tra[tra] * self.cap_tra[tra]
                              for tra in self.tra_tuples) +
                          sum((dual_sto_cap[sto] - dual_sto_capl[sto]) * self.cap_sto_c[sto]
                              for sto in self.sto_tuples) +
                          sum(dual_sto_pow[sto] * self.cap_sto_p[sto]
                              for sto in self.sto_tuples) +
                          dual_zero * self.eta)

        cut_expression += -1 * (sum([dual_sto[(self.t[-1],) + sto] * self.e_sto_con[(self.t[-1],) + sto]
                               for sto in self.sto_tuples]) -
                          sum([dual_com[(self.t[-1],) + com] * self.e_co_stock_state[
                              (self.t[-1],) + com]
                               for com in self.com_tuples if com in self.com_max_tuples])
                          )

        return cut_expression

    def add_cut(self, realizations, cut_generating_problems, current_realized, probabilities):
        """
        Adds a cut to this problem (in Sddp cuts can be added to both master and sub problems)

        Args:
            realizations: possible realizations (e.g. "low", "mid", "high") of the following supportsteps problem (= cut generating problems)
            cut_generating_problems: the realizations of the sub problem in the next timestep which generate the cut
            current_realized: realized instance of current problem
            probabilities: probabilities of realizations
        """
        cur_probs = {}
        for cur_real in realizations:
            if cut_generating_problems[cur_real].Lambda() > 0.0000001:
                cur_probs[cur_real] = cut_generating_problems[cur_real]
            else:
                print('Cut skipped for subproblem ' + '(' + str(cut_generating_problems[cur_real].ts[1]) + ', ' + cur_real +
                      '), Lambda = ' + str(cut_generating_problems[cur_real].Lambda()))

        if len(cur_probs) > 0:
            self.Cut_Defn.add(
                sum(probabilities[cur_real] * self.get_cut_expression(cur_probs[cur_real])
                    for cur_real in cur_probs)
                >= sum(probabilities[cur_real] *
                       (cur_probs[cur_real].Lambda() + current_realized.get_cut_expression(cur_probs[cur_real])())
                       for cur_real in cur_probs))

# Constraints, which are Sddp specific, but equal in Master and Subs.

# storage

# storage content <= storage capacity
def res_storage_state_by_capacity_rule(m, t, sit, sto, com):
    if m.model_type.name == 'sub':
        if t == m.ts[1]:  # or t == m.ts[2]:
            return pyomo.Constraint.Skip  # in the first timestep of the subproblem, the content is set by the previous
            # problem, hence we don't need to enforce that it respects the capacity
        else:
            return m.e_sto_con[t, sit, sto, com] <= m.cap_sto_c[sit, sto, com]
    else:
        return m.e_sto_con[t, sit, sto, com] <= m.cap_sto_c[sit, sto, com]


# Env/Stock generation per site limitation
def com_total_rule(m, tm, sit, com, com_type):
    return (m.e_co_stock_state[tm, sit, com, com_type] * m.weight <=
            m.commodity_dict['max'][sit, com, com_type])


# CO2 generation summation
def com_state_rule(m, tm, sit, com, com_type):
    if com in m.com_env:
        return (m.e_co_stock_state[tm, sit, com, com_type] ==
                m.e_co_stock_state[tm - 1, sit, com, com_type] - commodity_balance(m, tm, sit, com) * m.dt)
    elif com in m.com_stock:
        return (m.e_co_stock_state[tm, sit, com, com_type] ==
                m.e_co_stock_state[tm - 1, sit, com, com_type] + m.e_co_stock[tm, sit, com, com_type] * m.dt)
    else:
        return pyomo.Constraint.Skip


# CO2 generation of master problem <= global co2 limit
def global_co2_limit_rule(m, tm, com):
    return (sum(m.e_co_stock_state[tm, sit, com, 'Env']
                for sit in m.sit) * m.weight <=
            m.global_prop.loc['CO2 limit', 'value'])


def final_storage_state(m, t, sit, sto, com):
    if t == m.supportsteps[-1]:  # last timestep
        return (m.e_sto_con[t, sit, sto, com] >=
                m.cap_sto_c[sit, sto, com] *
                m.storage_dict['init'][sit, sto, com])
    else:
        return pyomo.Constraint.Skip







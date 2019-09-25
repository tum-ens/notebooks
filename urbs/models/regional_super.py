from .super import *


class RegionalSuper(ModelSuper, ABC):
    @abstractmethod
    def __init__(self, data, timesteps=None, dt=1, dual=False, model_type=urbsType.normal, site=None, msites=None):
        """Initializes parameters which are the same for master and sub.

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

        super().__init__(data, timesteps, dt, dual, model_type, site, msites, decomposition_method='regional')
        # Parameters

        # weight = length of year (hours) / length of simulation (hours)
        # weight scales costs and emissions from length of simulation to a full
        # year, making comparisons among cost types (invest is annualized, fixed
        # costs are annual by default, variable costs are scaled by weight) and
        # among different simulation durations meaningful.
        self.weight = pyomo.Param(
            initialize=float(8760) / (len(self.tm) * dt),
            doc='Pre-factor for variable costs and emissions for an annual result')

        # hvac = upper bound for connections to the destination site
        self.hvac = pyomo.Param(
            self.sit_out,
            initialize=hvac_rule,
            mutable=True,
            doc='Upper bound for connections to the destination site')

        # Variables

        # transmission
        self.e_tra_in = pyomo.Var(
            self.tm, self.tra_tuples,
            within=pyomo.NonNegativeReals,
            doc='Power flow into transmission line (MW) per timestep')
        self.e_tra_out = pyomo.Var(
            self.tm, self.tra_tuples,
            within=pyomo.NonNegativeReals,
            doc='Power flow out of transmission line (MW) per timestep')

        # Equation declarations
        # equation bodies are defined in separate functions, referred to here by
        # their name in the "rule" keyword.

        self.def_transmission_output = pyomo.Constraint(
            self.tm, self.tra_tuples,
            rule=def_transmission_output_rule,
            doc='transmission output = transmission input * efficiency')


# Constraints, which are regional specific, but the same for Master and Subs


# transmission


# transmission output == transmission input * efficiency
def def_transmission_output_rule(m, tm, sin, sout, tra, com):
    return (m.e_tra_out[tm, sin, sout, tra, com] ==
            m.e_tra_in[tm, sin, sout, tra, com] *
            math.sqrt(m.transmission_dict['eff'][(sin, sout, tra, com)]))


# Hvac parameter setting function
def hvac_rule(m, sit):
    return sum(value for index, value in m.transmission_dict['inst-cap'].items()
               if index[0] == sit)


# total CO2 output <= Global CO2 limit
def res_global_co2_limit_rule(m):
    if math.isinf(m.global_prop.loc['CO2 limit', 'value']):
        return pyomo.Constraint.Skip
    elif m.global_prop.loc['CO2 limit', 'value'] >= 0:
        # subproblem specific res_global_co2_limit constraint
        if m.model_type.name == 'sub':
            co2_output_sum = 0
            for tm in m.tm:
                for sit in m.sub_sit:
                    # minus because negative commodity_balance represents creation of
                    # that commodity.
                    co2_output_sum += (- commodity_balance(m, tm, sit, 'CO2') * m.dt)

            # scaling to annual output (cf. definition of m.weight)
            co2_output_sum *= m.weight
            return (co2_output_sum <= sum(m.e_co_stock_res[tm, m.sub_site[1], 'CO2', 'Env']
                                          for tm in m.tm) + m.Lambda * m.omega)

        elif m.model_type.name == 'subwfile':
            co2_output_sum = 0
            for tm in m.tm:
                for sit in m.sub_sit:
                    # minus because negative commodity_balance represents creation of
                    # that commodity.
                    co2_output_sum += (- commodity_balance(m, tm, sit, 'CO2') * m.dt)

            # scaling to annual output (cf. definition of m.weight)
            co2_output_sum *= m.weight
            return (co2_output_sum <= sum(m.e_co_stock_res[tm] for tm in m.tm) + m.Lambda * m.omega)

        elif m.model_type.name == 'master':
            return (sum(m.e_co_stock[tm, sit, 'CO2', 'Env']
                        for tm in m.tm for sit in m.sit) <=
                    m.global_prop.loc['CO2 limit', 'value'])
    else:
        return pyomo.Constraint.Skip


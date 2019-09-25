from .super import *


class DivideTimestepsSuper(ModelSuper, ABC):
    @abstractmethod
    def __init__(self,data, timesteps=None, supportsteps=[], dt=1, dual=False, model_type=urbsType.normal):
        """Initializes model parameters which are the same for master and sub

        Args:
            data: a dict of 6 DataFrames with the keys 'commodity', 'process',
                'transmission', 'storage', 'demand' and 'supim'.
            timesteps: optional list of timesteps, default: demand timeseries
            dt: timestep duration in hours (default: 1)
            dual: set True to add dual variables to model (slower); default: False
            model_type: model_type of the problem; 0: Normal(default), 1:Sub, 2: Master
        """
        super().__init__(data, timesteps, dt, dual, model_type, decomposition_method='divide-timesteps')
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

        # Parameters

        # Variables

        # process
        self.cap_pro = pyomo.Var(
            self.pro_tuples,
            within=pyomo.NonNegativeReals,
            doc='Total process capacity (MW)')

        # transmission
        self.cap_tra = pyomo.Var(
            self.tra_tuples,
            within=pyomo.NonNegativeReals,
            doc='Total transmission capacity (MW)')

        # storage
        self.cap_sto_c = pyomo.Var(
            self.sto_tuples,
            within=pyomo.NonNegativeReals,
            doc='Total storage size (MWh)')
        self.cap_sto_p = pyomo.Var(
            self.sto_tuples,
            within=pyomo.NonNegativeReals,
            doc='Total storage power (MW)')

        # Equation declarations
        # equation bodies are defined in separate functions, referred to here by
        # their name in the "rule" keyword.

        # ALL MODELS
        # process
        self.res_process_capacity = pyomo.Constraint(
            self.pro_tuples,
            rule=res_process_capacity_rule,
            doc='process.cap-lo <= total process capacity <= process.cap-up')
        self.def_process_capacity = pyomo.Constraint(
            self.pro_tuples,
            rule=def_process_capacity_rule,
            doc='total process capacity = inst-cap + new capacity')

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
            doc='storage capacity = inst-cap + new capacity')
        self.def_storage_capacity_l = pyomo.Constraint(
            self.sto_tuples,
            rule=def_storage_capacity_l_rule,
            doc='storage capacity >= inst-cap + new capacity - lambda*omega')
        self.def_storage_power = pyomo.Constraint(
            self.sto_tuples,
            rule=def_storage_power_rule,
            doc='storage power = inst-cap + new power')


# Constraints which are the same for Divide Timesteps Master and Subs

# storage

# storage content <= storage capacity
def res_storage_state_by_capacity_rule(m, t, sit, sto, com):
    if m.model_type.name == 'sub':
        if t == m.ts[1] or t == m.ts[2]:
            return pyomo.Constraint.Skip
        else:
            return m.e_sto_con[t, sit, sto, com] <= m.cap_sto_c[sit, sto, com]
    else:
        return m.e_sto_con[t, sit, sto, com] <= m.cap_sto_c[sit, sto, com]






from enum import Enum
import pandas as pd
from ..pyomoio import get_entity, _get_onset_names
import pyomo.core as pyomo
from datetime import datetime
from ..input import *
from abc import ABC, abstractmethod
import math


class urbsType(Enum):
    normal = 0
    sub = 1
    subwfile = 1.5
    master = 2


class ModelSuper(pyomo.ConcreteModel, ABC):
    @abstractmethod
    def __init__(self, data, timesteps=None, dt=1, dual=False, model_type=urbsType.normal, site=None, msites=None,
                 decomposition_method=None):
        """Initializes model parameters which are the same in all model types.

        Args:
            data: a dict of 6 DataFrames with the keys 'commodity', 'process',
                'transmission', 'storage', 'demand' and 'supim'.
            timesteps: optional list of timesteps, default: demand timeseries
            dt: timestep duration in hours (default: 1)
            dual: set True to add dual variables to model (slower); default: False
            model_type: model_type of the problem; 0: Normal(default), 1:Sub, 2: Master
            site: site of the sub problem for regional, None for all others
            msites: set of the master problem sites
            decomposition_method: Either None, divide-timesteps,regional or sddp
        """
        # Initialize this as a pyomo ConcreteModel
        super().__init__()

        if not timesteps:
            timesteps = data['demand'].index.tolist()

        # Preparations
        # ============
        # Data import. Syntax to access a value within equation definitions looks
        # like this:
        #
        #     self.storage.loc[site, storage, commodity][attribute]
        #
        if site in data['site'].index:
            self.global_prop = data['global_prop'].drop('description', axis=1)
            self.site = data['site'].loc[[site]]
            self.commodity = data['commodity'].loc[[site]]
            self.process = data['process'].loc[[site]]
            self.process_commodity = data['process_commodity']
            self.transmission = data['transmission'].loc[
                (data['transmission'].index.get_level_values('Site In') == site) |
                (data['transmission'].index.get_level_values('Site Out') == site)]
            self.storage = data['storage'].loc[[site]]
            self.demand = data['demand'][[site]]
            self.supim = data['supim'][[site]]
            self.timesteps = timesteps
        else:
            self.global_prop = data['global_prop'].drop('description', axis=1)
            self.site = data['site']
            self.commodity = data['commodity']
            self.process = data['process']
            self.process_commodity = data['process_commodity']
            self.transmission = data['transmission']
            self.storage = data['storage']
            self.demand = data['demand']
            self.supim = data['supim']
            self.timesteps = timesteps

        # Converting Data frames to dict
        self.commodity_dict = self.commodity.to_dict()
        self.demand_dict = self.demand.to_dict()
        self.supim_dict = self.supim.to_dict()

        # process input/output ratios
        self.r_in = self.process_commodity.xs('In', level='Direction')['ratio']
        self.r_out = self.process_commodity.xs('Out', level='Direction')['ratio']
        self.r_in_dict = self.r_in.to_dict()
        self.r_out_dict = self.r_out.to_dict()

        # process areas
        self.proc_area = self.process['area-per-cap']
        self.sit_area = self.site['area']
        self.proc_area = self.proc_area[self.proc_area >= 0]
        self.sit_area = self.sit_area[self.sit_area >= 0]

        # input ratios for partial efficiencies
        # only keep those entries whose values are
        # a) positive and
        # b) numeric (implicitely, as NaN or NV compare false against 0)
        self.r_in_min_fraction = self.process_commodity.xs('In', level='Direction')
        self.r_in_min_fraction = self.r_in_min_fraction['ratio-min']
        self.r_in_min_fraction = self.r_in_min_fraction[self.r_in_min_fraction > 0]

        # output ratios for partial efficiencies
        # only keep those entries whose values are
        # a) positive and
        # b) numeric (implicitely, as NaN or NV compare false against 0)
        self.r_out_min_fraction = self.process_commodity.xs('Out', level='Direction')
        self.r_out_min_fraction = self.r_out_min_fraction['ratio-min']
        self.r_out_min_fraction = self.r_out_min_fraction[self.r_out_min_fraction > 0]

        # derive annuity factor from WACC and depreciation duration
        pd.set_option('mode.chained_assignment', None)  # Remove SettingWithCopyError Warning
        self.process['annuity-factor'] = annuity_factor(
            self.process['depreciation'],
            self.process['wacc'])
        self.transmission['annuity-factor'] = annuity_factor(
            self.transmission['depreciation'],
            self.transmission['wacc'])
        self.storage['annuity-factor'] = annuity_factor(
            self.storage['depreciation'],
            self.storage['wacc'])

        # Converting Data frames to dictionaries
        self.process_dict = self.process.to_dict()
        self.transmission_dict = self.transmission.to_dict()
        self.storage_dict = self.storage.to_dict()

        self.created = datetime.now().strftime('%Y%m%dT%H%M')
        self._data = data

        self.model_type = model_type

        # Sets
        # ====
        # Syntax: self.{name} = Set({domain}, initialize={values})
        # where name: set name
        #       domain: set domain for tuple sets, a cartesian set product
        #       values: set values, a list or array of element tuples

        # generate ordered time step sets
        self.t = pyomo.Set(
            initialize=self.timesteps,
            ordered=True,
            doc='Set of timesteps')

        # modelled (i.e. excluding init time step for storage) time steps
        self.tm = pyomo.Set(
            within=self.t,
            initialize=self.timesteps[1:],
            ordered=True,
            doc='Set of modelled timesteps')

        # This needs to be defines in the super class, because site depends on initializing the model and coming definitions depend on site
        if decomposition_method == 'regional':
            # argument sites
            self.sub_site = pyomo.Set(
                initialize=[site],
                ordered=True,
                doc='site of sub problem')
            self.master_sites = pyomo.Set(
                initialize=msites,
                doc='site of master problem')

            # sub_sit
            self.sub_sit = pyomo.Set(
                initialize=self.site.index.get_level_values('Name').unique(),
                doc='site of sub problem')

            # sit_out
            self.sit_out = pyomo.Set(
                initialize=self.master_sites.difference(self.sub_site),
                doc='Set of outside connections')

            # site (e.g. north, middle, south...)
            self.sit = pyomo.Set(
                initialize=self.sub_sit.union(self.sit_out),
                doc='Set of sites')
        else:
            # site (e.g. north, middle, south...)
            self.sit = pyomo.Set(
                initialize=self.commodity.index.get_level_values('Site').unique(),
                doc='Set of sites')
        # commodity (e.g. solar, wind, coal...)
        self.com = pyomo.Set(
            initialize=self.commodity.index.get_level_values('Commodity').unique(),
            doc='Set of commodities')

        # commodity type (i.e. SupIm, Demand, Stock, Env)
        self.com_type = pyomo.Set(
            initialize=self.commodity.index.get_level_values('Type').unique(),
            doc='Set of commodity types')

        # process (e.g. Wind turbine, Gas plant, Photovoltaics...)
        self.pro = pyomo.Set(
            initialize=self.process.index.get_level_values('Process').unique(),
            doc='Set of conversion processes')

        # transmission (e.g. hvac, hvdc, pipeline...)
        self.tra = pyomo.Set(
            initialize=self.transmission.index.get_level_values('Transmission')
                .unique(),
            doc='Set of transmission technologies')

        # storage (e.g. hydrogen, pump storage)
        self.sto = pyomo.Set(
            initialize=self.storage.index.get_level_values('Storage').unique(),
            doc='Set of storage technologies')

        # cost_type
        self.cost_type = pyomo.Set(
            initialize=['Invest', 'Fixed', 'Variable', 'Fuel',
                        'Environmental'],
            doc='Set of cost types (hard-coded)')

        # tuple sets
        self.com_tuples = pyomo.Set(
            within=self.sit * self.com * self.com_type,
            initialize=self.commodity.index,
            doc='Combinations of defined commodities, e.g. (Mid,Elec,Demand)')
        self.pro_tuples = pyomo.Set(
            within=self.sit * self.pro,
            initialize=self.process.index,
            doc='Combinations of possible processes, e.g. (North,Coal plant)')
        self.tra_tuples = pyomo.Set(
            within=self.sit * self.sit * self.tra * self.com,
            initialize=self.transmission.index,
            doc='Combinations of possible transmissions, e.g. '
                '(South,Mid,hvac,Elec)')
        self.sto_tuples = pyomo.Set(
            within=self.sit * self.sto * self.com,
            initialize=self.storage.index,
            doc='Combinations of possible storage by site, e.g. (Mid,Bat,Elec)')

        # process tuples for area rule
        self.pro_area_tuples = pyomo.Set(
            within=self.sit * self.pro,
            initialize=self.proc_area.index,
            doc='Processes and Sites with area Restriction')

        # process input/output
        self.pro_input_tuples = pyomo.Set(
            within=self.sit * self.pro * self.com,
            initialize=[(site, process, commodity)
                        for (site, process) in self.pro_tuples
                        for (pro, commodity) in self.r_in.index
                        if process == pro],
            doc='Commodities consumed by process by site, e.g. (Mid,PV,Solar)')
        self.pro_output_tuples = pyomo.Set(
            within=self.sit * self.pro * self.com,
            initialize=[(site, process, commodity)
                        for (site, process) in self.pro_tuples
                        for (pro, commodity) in self.r_out.index
                        if process == pro],
            doc='Commodities produced by process by site, e.g. (Mid,PV,Elec)')

        # process tuples for maximum gradient feature
        self.pro_maxgrad_tuples = pyomo.Set(
            within=self.sit * self.pro,
            initialize=[(sit, pro)
                        for (sit, pro) in self.pro_tuples
                        if self.process_dict['max-grad'][sit, pro] < 1.0 / dt],
            doc='Processes with maximum gradient smaller than timestep length')

        # commodity type subsets
        self.com_supim = pyomo.Set(
            within=self.com,
            initialize=commodity_subset(self.com_tuples, 'SupIm'),
            doc='Commodities that have intermittent (timeseries) input')
        self.com_stock = pyomo.Set(
            within=self.com,
            initialize=commodity_subset(self.com_tuples, 'Stock'),
            doc='Commodities that can be purchased at some site(s)')
        self.com_demand = pyomo.Set(
            within=self.com,
            initialize=commodity_subset(self.com_tuples, 'Demand'),
            doc='Commodities that have a demand (implies timeseries)')
        self.com_env = pyomo.Set(
            within=self.com,
            initialize=commodity_subset(self.com_tuples, 'Env'),
            doc='Commodities that (might) have a maximum creation limit')

        # Parameters

        # dt = spacing between timesteps. Required for storage equation that
        # converts between energy (storage content, e_sto_con) and power (all other
        # quantities that start with "e_")
        self.dt = pyomo.Param(
            initialize=dt,
            doc='Time step duration (in hours), default: 1')

        # Variables

        # costs
        self.costs = pyomo.Var(
            self.cost_type,
            within=pyomo.Reals,
            doc='Costs by type (EUR/a)')

        # commodity
        self.e_co_stock = pyomo.Var(
            self.tm, self.com_tuples,
            initialize=0.0,
            within=pyomo.NonNegativeReals,
            doc='Use of stock commodity source (MW) per timestep')

        # Process
        self.pro_new = pyomo.Expression(
            self.pro_tuples,
            initialize=0.0,
            doc='cap_pro_new')
        self.pro_inst = pyomo.Param(
            self.pro_tuples,
            mutable=True,
            initialize=self.process['inst-cap'].to_dict(),
            doc='inst-pro-capacity')
        self.pro_relax = pyomo.Expression(
            self.pro_tuples,
            initialize=0.0,
            doc='lambda*omega')

        # Transmission
        self.tra_new = pyomo.Expression(
            self.tra_tuples,
            initialize=0.0,
            doc='cap_tra_new')
        self.tra_inst = pyomo.Param(
            self.tra_tuples,
            mutable=True,
            initialize=self.transmission['inst-cap'].to_dict(),
            doc='inst-tra-capacity')
        self.tra_relax = pyomo.Expression(
            self.tra_tuples,
            initialize=0.0,
            doc='lambda*omega')

        # Storage Capacity
        self.sto_c_new = pyomo.Expression(
            self.sto_tuples,
            initialize=0.0,
            doc='cap_sto_c_new')
        self.sto_c_inst = pyomo.Param(
            self.sto_tuples,
            mutable=True,
            initialize=self.storage['inst-cap-c'].to_dict(),
            doc='inst-sto_c-capacity')
        self.sto_c_relax = pyomo.Expression(
            self.sto_tuples,
            initialize=0.0,
            doc='lambda*omega')

        # Storage Power
        self.sto_p_new = pyomo.Expression(
            self.sto_tuples,
            initialize=0.0,
            doc='cap_sto_p_new')
        self.sto_p_inst = pyomo.Param(
            self.sto_tuples,
            mutable=True,
            initialize=self.storage['inst-cap-p'].to_dict(),
            doc='inst-sto_p-capacity')
        self.sto_p_relax = pyomo.Expression(
            self.sto_tuples,
            initialize=0.0,
            doc='lambda*omega')

        # Storage Content
        self.e_sto_state = pyomo.Expression(
            self.t, self.sto_tuples,
            initialize=0.0,
            doc='cap_sto_c * sto_c_inst')
        self.e_sto_relax = pyomo.Expression(
            self.t, self.sto_tuples,
            initialize=0.0,
            doc='lambda*omega')

        if dual:
            self.dual = pyomo.Suffix(direction=pyomo.Suffix.IMPORT)

    def solve(self, optim):
        """
        Solves the pyomo model and returns the result
        """
        return optim.solve(self, tee=False)

    def get_attribute(self, name):
        """ Get attribute name

        Args:
            name: name of a Set, Param, Var, Constraint or Objective

        Returns:
            attribute of the model
        """
        return self.__getattribute__(name)

    def get_attribute_at(self, name, index):
        """ Get attribute name at index

        Args:
            name: name of a Set, Param, Var, Constraint or Objective
            index: required index

        Returns:
            attribute at a given index
        """
        return self.__getattribute__(name)[index]

    def get_cost(self, cost_type):
        """ Get cost of subproblem for a given type

        Args:
            cost_type: desired cost type

        Returns:
            costs
        """
        return self.costs[cost_type]()

    def set_boundaries(self, master, name, bound_name):
        """ Set Boundaries to an entity in self.

        Args:
            master: a Pyomo ConcreteModel Master instance
            name: name of a Set, Param, Var, Constraint or Objective
            self: a Pyomo ConcreteModel self.m instance
            bound_name: name of an Expression

        Returns:
            None

        Example:
            >>> master_inst = create_model(data, range(1,25), type=2)
            >>> sub_inst = create_model(data, range(1,25), type=1)
            >>> sub_inst.set_boundaries(master_inst, 'cap_pro', 'cap_pro_res')
        """

        # retrieve master entity, and it's index
        entity = master.__getattribute__(name)
        index_entity = entity._index

        # retrieve self entity, and it's index
        entity_bound = self.__getattribute__(bound_name)
        index_bound = entity_bound._index

        # if indices of entities do not match,
        # try putting boundaries to same indices
        if index_entity != index_bound:
            for i in index_entity:
                try:
                    entity_bound[i].expr = entity[i]()
                except AttributeError:
                    entity_bound[i] = entity[i]()
                except KeyError:
                    pass
        else:
            for i in index_entity:
                try:
                    entity_bound[i].expr = entity[i]()
                except AttributeError:
                    entity_bound[i] = entity[i]()

    # TODO: So far this function is never used
    def get_duals(self, name, const):
        """ Get Duals from a constraint of self

        Args:
            name: name of a dual var
            self: a Pyomo ConcreteModel self
            const: name of the constraint from which duals are generated

        Returns:
            a Pandas Series with domain as index and values of the dual variable

        Example:
            >>> inst = create_model(data, range(1,25))
            >>> PiPro = get_duals(PiPro, inst, 'sub_process_capacity')
        """

        # retrieve constraint, and it's index
        entity = self.__getattribute__(const)
        labels = _get_onset_names(entity)

        # Cannot get duals from a Pyomo Set
        if isinstance(entity, pyomo.Set):
            raise TypeError("Cannot get duals from a Pyomo Set")

        # Cannot get duals from a Pyomo Param
        elif isinstance(entity, pyomo.Param):
            raise TypeError("Cannot get duals from a Pyomo Parameter")

        # Cannot get duals from a Pyomo Var
        elif isinstance(entity, pyomo.Var):
            raise TypeError("Cannot get duals from a Pyomo Variable")

        # Can only get duals from a Pyomo Constraint
        elif isinstance(entity, pyomo.Constraint):

            # check for duplicate onset names and append one to several "_" to make
            # them unique, e.g. ['sit', 'sit', 'com'] becomes ['sit', 'sit_', 'com']
            for k, label in enumerate(labels):
                if label in labels[:k] or label == const:
                    labels[k] = labels[k] + "_"

            # TODO: extract addition to DataFrame in another function

            # Check if name is a pandas Series object, if not create it.
            if not isinstance(name, pd.Series):
                if entity.dim() == 0:
                    name += get_entity(self, const)[0]
                    return name

                else:
                    # name columns according to labels + entity name
                    name = pd.DataFrame(pd.np.empty((0, len(labels) + 1)), dtype=object)

                    name.columns = labels + [const]
                    name.set_index(labels, inplace=True)

                    # convert to Series
                    name = name[const]

            # try adding the duals to previously created pandas Series object
            try:
                name = pd.concat([name, get_entity(self, const)]).groupby(by=labels).sum()
            except ValueError:
                pass

            return name

        # Cannot get duals from anything else
        else:
            raise TypeError("Cannot get duals from '{}'".format(const))


# Constraints which are the same for all decomposition methods

# commodity

# vertex equation: calculate balance for given commodity and site;
# contains implicit constraints for process activity, import/export and
# storage activity (calculated by function commodity_balance);
# contains implicit constraint for stock commodity source term
def res_vertex_rule(m, tm, sit, com, com_type):
    # environmental or supim commodities don't have this constraint (yet)
    if com in m.com_env:
        return pyomo.Constraint.Skip
    if com in m.com_supim:
        return pyomo.Constraint.Skip

    # helper function commodity_balance calculates balance from input to
    # and output from processes, storage and transmission.
    # if power_surplus > 0: production/storage/imports create net positive
    #                       amount of commodity com
    # if power_surplus < 0: production/storage/exports consume a net
    #                       amount of the commodity com
    power_surplus = - commodity_balance(m, tm, sit, com)

    # if com is a stock commodity, the commodity source term e_co_stock
    # can supply a possibly negative power_surplus
    if com in m.com_stock:
        power_surplus += m.e_co_stock[tm, sit, com, com_type]

    # if com is a demand commodity, the power_surplus is reduced by the
    # demand value; no scaling by m.dt or m.weight is needed here, as this
    # constraint is about power (MW), not energy (MWh)
    if com in m.com_demand:
        try:
            power_surplus -= m.demand_dict[(sit, com)][tm]
        except KeyError:
            pass

    return power_surplus == 0


# stock commodity purchase == commodity consumption, according to
# commodity_balance of current (time step, site, commodity);
# limit stock commodity use per time step
def res_stock_step_rule(m, tm, sit, com, com_type):
    if com not in m.com_stock:
        return pyomo.Constraint.Skip
    else:
        return (m.e_co_stock[tm, sit, com, com_type] <=
                m.commodity_dict['maxperstep'][(sit, com, com_type)])


# limit stock commodity use in total (scaled to annual consumption, thanks
# to m.weight)
def res_stock_total_rule(m, sit, com, com_type):
    if com not in m.com_stock or math.isinf(float(m.commodity.loc[sit, com, com_type]['max'])):
        return pyomo.Constraint.Skip
    else:
        # calculate total consumption of commodity com
        total_consumption = 0
        for tm in m.tm:
            total_consumption += (
                    m.e_co_stock[tm, sit, com, com_type] * m.dt)
        total_consumption *= m.weight
        return (total_consumption <=
                m.commodity_dict['max'][(sit, com, com_type)])


# environmental commodity creation == - commodity_balance of that commodity
# used for modelling emissions (e.g. CO2) or other end-of-pipe results of
# any process activity;
# limit environmental commodity output per time step
def res_env_step_rule(m, tm, sit, com, com_type):
    if com not in m.com_env:
        return pyomo.Constraint.Skip
    else:
        environmental_output = - commodity_balance(m, tm, sit, com)
        return (environmental_output <=
                m.commodity_dict['maxperstep'][(sit, com, com_type)])


# limit environmental commodity output in total (scaled to annual
# emissions, thanks to m.weight)
def res_env_total_rule(m, sit, com, com_type):
    if com not in m.com_env or math.isinf(float(m.commodity.loc[sit, com, com_type]['max'])):
        return pyomo.Constraint.Skip
    else:
        # calculate total creation of environmental commodity com
        env_output_sum = 0
        for tm in m.tm:
            env_output_sum += (- commodity_balance(m, tm, sit, com) * m.dt)
        env_output_sum *= m.weight
        return (env_output_sum <=
                m.commodity_dict['max'][(sit, com, com_type)])


# process

# process capacity == new capacity + existing capacity
def def_process_capacity_rule(m, sit, pro):
    return (m.cap_pro[sit, pro] <=
            m.pro_new[sit, pro] +
            m.pro_inst[sit, pro] +
            m.pro_relax[sit, pro])


# process input power == process throughput * input ratio
def def_process_input_rule(m, tm, sit, pro, co):
    return (m.e_pro_in[tm, sit, pro, co] ==
            m.tau_pro[tm, sit, pro] * m.r_in_dict[(pro, co)])


# process output power = process throughput * output ratio
def def_process_output_rule(m, tm, sit, pro, co):
    return (m.e_pro_out[tm, sit, pro, co] ==
            m.tau_pro[tm, sit, pro] * m.r_out_dict[(pro, co)])


# TODO: slightly different in regional, can it be unified?
# process input (for supim commodity) = process capacity * timeseries
def def_intermittent_supply_rule(m, tm, sit, pro, coin):
    if coin in m.com_supim:
        return (m.e_pro_in[tm, sit, pro, coin] <=
                m.cap_pro[sit, pro] * m.supim_dict[sit, coin][tm])
    else:
        return pyomo.Constraint.Skip


# process throughput <= process capacity
def res_process_throughput_by_capacity_rule(m, tm, sit, pro):
    return (m.tau_pro[tm, sit, pro] <= m.cap_pro[sit, pro])


def res_process_maxgrad_lower_rule(m, t, sit, pro):
    return (m.tau_pro[t - 1, sit, pro] -
            m.cap_pro[sit, pro] * m.process_dict['max-grad'][(sit, pro)] *
            m.dt <= m.tau_pro[t, sit, pro])


def res_process_maxgrad_upper_rule(m, t, sit, pro):
    return (m.tau_pro[t - 1, sit, pro] +
            m.cap_pro[sit, pro] * m.process_dict['max-grad'][(sit, pro)] *
            m.dt >= m.tau_pro[t, sit, pro])


# lower bound <= process capacity <= upper bound
def res_process_capacity_rule(m, sit, pro):
    return (m.process_dict['cap-lo'][sit, pro],
            m.cap_pro[sit, pro],
            m.process_dict['cap-up'][sit, pro])


# used process area <= maximal process area
def res_area_rule(m, sit):
    if m.site.loc[sit]['area'] >= 0 and sum(
            m.process.loc[(s, p), 'area-per-cap']
            for (s, p) in m.pro_area_tuples
            if s == sit) > 0:
        total_area = sum(m.cap_pro[s, p] * m.process.loc[(s, p), 'area-per-cap']
                         for (s, p) in m.pro_area_tuples
                         if s == sit)
        return total_area <= m.site.loc[sit]['area']
    else:
        # Skip constraint, if area is not numeric
        return pyomo.Constraint.Skip


# transmission

# transmission capacity == new capacity + existing capacity
def def_transmission_capacity_rule(m, sin, sout, tra, com):
    return (m.cap_tra[sin, sout, tra, com] <=
            m.tra_new[sin, sout, tra, com] +
            m.tra_inst[sin, sout, tra, com] +
            m.tra_relax[sin, sout, tra, com])


# TODO: slightly different in normal, sddp, divide-timesteps compared to regional: See warning in regional documentation
# transmission output == transmission input * efficiency
def def_transmission_output_rule(m, tm, sin, sout, tra, com):
    return (m.e_tra_out[tm, sin, sout, tra, com] ==
            m.e_tra_in[tm, sin, sout, tra, com] *
            m.transmission_dict['eff'][(sin, sout, tra, com)])


# transmission input <= transmission capacity
def res_transmission_input_by_capacity_rule(m, tm, sin, sout, tra, com):
    return (m.e_tra_in[tm, sin, sout, tra, com] <=
            m.cap_tra[sin, sout, tra, com])


# lower bound <= transmission capacity <= upper bound
def res_transmission_capacity_rule(m, sin, sout, tra, com):
    return (m.transmission_dict['cap-lo'][(sin, sout, tra, com)],
            m.cap_tra[sin, sout, tra, com],
            m.transmission_dict['cap-up'][(sin, sout, tra, com)])


# transmission capacity from A to B == transmission capacity from B to A
def res_transmission_symmetry_rule(m, sin, sout, tra, com):
    return m.cap_tra[sin, sout, tra, com] == m.cap_tra[sout, sin, tra, com]


# storage

# storage content in timestep [t] == storage content[t-1] * (1-discharge)
# + newly stored energy * input efficiency
# - retrieved energy / output efficiency
def def_storage_state_rule(m, t, sit, sto, com):
    return (m.e_sto_con[t, sit, sto, com] ==
            m.e_sto_con[t - 1, sit, sto, com] *
            (1 - m.storage_dict['discharge'][(sit, sto, com)]) ** m.dt.value +
            m.e_sto_in[t, sit, sto, com] *
            m.storage_dict['eff-in'][(sit, sto, com)] * m.dt -
            m.e_sto_out[t, sit, sto, com] /
            m.storage_dict['eff-out'][(sit, sto, com)] * m.dt)


# only for divide-timesteps, sddp
def res_storage_state_upper_rule(m, t, sit, sto, com):
    delta_t = t - m.t.prev(t)
    return (m.e_sto_con[t, sit, sto, com] <=
            m.e_sto_con[m.t.prev(t), sit, sto, com] *
            (1 - m.storage_dict['discharge'][sit, sto, com]) ** delta_t +
            sum(m.cap_sto_p[sit, sto, com] *
                m.storage_dict['eff-in'][sit, sto, com] * m.dt *
                (1 - m.storage_dict['discharge'][sit, sto, com]) ** (delta_t - i)
                for i in range(1, delta_t + 1)))


# only for divide-timesteps, sddp
def res_storage_state_lower_rule(m, t, sit, sto, com):
    delta_t = t - m.t.prev(t)
    return (m.e_sto_con[t, sit, sto, com] >=
            m.e_sto_con[m.t.prev(t), sit, sto, com] *
            (1 - m.storage_dict['discharge'][sit, sto, com]) ** delta_t -
            sum(m.cap_sto_p[sit, sto, com] /
                m.storage_dict['eff-out'][sit, sto, com] * m.dt *
                (1 - m.storage_dict['discharge'][sit, sto, com]) ** (delta_t - i)
                for i in range(1, delta_t + 1)))


# storage capacity == new storage capacity + existing storage capacity
def def_storage_capacity_rule(m, sit, sto, com):
    return (m.cap_sto_c[sit, sto, com] <=
            m.sto_c_new[sit, sto, com] +
            m.sto_c_inst[sit, sto, com] +
            m.sto_c_relax[sit, sto, com])


# storage capacity == new storage capacity + existing storage capacity
def def_storage_capacity_l_rule(m, sit, sto, com):
    return (m.cap_sto_c[sit, sto, com] >=
            m.sto_c_new[sit, sto, com] +
            m.sto_c_inst[sit, sto, com] -
            m.sto_c_relax[sit, sto, com])


# storage power == new storage power + existing storage power
def def_storage_power_rule(m, sit, sto, com):
    return (m.cap_sto_p[sit, sto, com] <=
            m.sto_p_new[sit, sto, com] +
            m.sto_p_inst[sit, sto, com] +
            m.sto_p_relax[sit, sto, com])


# storage input <= storage power
def res_storage_input_by_power_rule(m, t, sit, sto, com):
    return m.e_sto_in[t, sit, sto, com] <= m.cap_sto_p[sit, sto, com]


# storage output <= storage power
def res_storage_output_by_power_rule(m, t, sit, sto, co):
    return m.e_sto_out[t, sit, sto, co] <= m.cap_sto_p[sit, sto, co]


# storage content <= storage capacity
def res_storage_state_by_capacity_rule(m, t, sit, sto, com):
    return m.e_sto_con[t, sit, sto, com] <= m.cap_sto_c[sit, sto, com]


# lower bound <= storage power <= upper bound
def res_storage_power_rule(m, sit, sto, com):
    return (m.storage_dict['cap-lo-p'][(sit, sto, com)],
            m.cap_sto_p[sit, sto, com],
            m.storage_dict['cap-up-p'][(sit, sto, com)])


# lower bound <= storage capacity <= upper bound
def res_storage_capacity_rule(m, sit, sto, com):
    return (m.storage_dict['cap-lo-c'][(sit, sto, com)],
            m.cap_sto_c[sit, sto, com],
            m.storage_dict['cap-up-c'][(sit, sto, com)])


# initialization of storage content in first timestep t[1]
# forced minimum storage content in final timestep t[-1]
# content[t=1] == storage capacity * fraction <= content[t=final]
# TODO: different in sddp, see sddp_super.py, also different in regional => See if it can be merged
def res_initial_and_final_storage_state_rule(m, t, sit, sto, com):
    if t == m.t[1]:  # first timestep (Pyomo uses 1-based indexing)
        return (m.e_sto_con[t, sit, sto, com] -
                m.e_sto_state[t, sit, sto, com] <=
                m.e_sto_relax[t, sit, sto, com])
    elif t == m.t[-1]:  # last timestep
        return (m.e_sto_con[t, sit, sto, com] -
                m.e_sto_state[t, sit, sto, com] >=
                - m.e_sto_relax[t, sit, sto, com])
    else:
        return m.e_sto_con[t, sit, sto, com] >= - m.e_sto_relax[t, sit, sto, com]


def sub_obj_rule(m):
    return m.Lambda


def obj_rule(m):
    return pyomo.summation(m.costs)

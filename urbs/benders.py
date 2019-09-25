import pyomo.core as pyomo


def get_production_cost(master, subs, name, type):
    """ Get Production Cost from sub instances

    Args:
        master: a Pyomo ConcreteModel Master instance
        subs: a Pyomo ConcreteModel Sub instances dict
        name: name of a Set, Param, Var, Constraint or Objective
        type: process = 'pro', transmission = 'tra',
              storage capacity = 'sto_c', storage power = 'sto_p'

    Returns:
        a calculated value of the extra production costs.

    Example:
        >>> master_inst = create_model(data, range(1,25), type=2)
        >>> sub_inst = create_model(data, range(1,25), type=1)
        >>> get_production_cost(master_inst, sub_inst, 'cap_pro', 'pro')
    """

    # retrieve master entity, and it's index
    entity = master.__getattribute__(name)
    index_entity = entity._index

    # retrieve sub entity from subs list
    entity_sub = []
    for inst in subs:
        entity_sub.append(subs[inst].__getattribute__(name))

    # get max value between subs and calculate extra production costs
    cost = 0
    for i in index_entity:
        max_cost = max(inst[i]() for inst in entity_sub)

        if type == 'pro':
            if max_cost > entity[i]():
                cost += ((max_cost - entity[i]()) *
                         master.process.loc[i]['inv-cost'] *
                         master.process.loc[i]['annuity-factor'])

        if type == 'tra':
            if max_cost > entity[i]():
                cost += ((max_cost - entity[i]()) *
                         master.transmission.loc[i]['inv-cost'] *
                         master.transmission.loc[i]['annuity-factor'])

        if type == 'sto_c':
            if max_cost > entity[i]():
                cost += ((max_cost - entity[i]()) *
                         master.storage.loc[i]['inv-cost-c'] *
                         master.storage.loc[i]['annuity-factor'])

        if type == 'sto_p':
            if max_cost > entity[i]():
                cost += ((max_cost - entity[i]()) *
                         master.storage.loc[i]['inv-cost-p'] *
                         master.storage.loc[i]['annuity-factor'])
    return cost


def convergence_check(master, subs, upper_bound, costs, decomposition_method):
    """ Convergence Check

    Args:
        master: a Pyomo ConcreteModel Master instance
        subs: a Pyomo ConcreteModel Sub instances dict
        upper_bound: previously defined upper bound
        costs: extra costs calculated by get_production_cost()
        decomposition_method: The decomposition method which is used. Must be in ['divide-timesteps', 'regional', 'sddp']

    Returns:
        GAP = Dual Gap of the Bender's Decomposition
        Zdo = Lower Bound
        Zup = Upper Bound

    Example:
        >>> upper_bound = float('Inf')
        >>> master_inst = create_model(data, range(1,25), type=2)
        >>> sub_inst = create_model(data, range(1,25), type=1)
        >>> costs = get_production_cost(...)
        >>> convergence_check(master_inst, sub_inst, Zup, costs)
    """
    lower_bound = master.obj()
    new_upper_bound = 0.0

    for inst in subs:
        new_upper_bound += sum(subs[inst].costs[ct]() for ct in subs[inst].cost_type)

    if decomposition_method == 'divide-timesteps':
        new_upper_bound += master.obj() - sum(master.eta[t]() for t in master.tm) + costs
    elif decomposition_method == 'regional':
        new_upper_bound += master.obj() - sum(master.eta[s]() for s in master.sit) + costs
    else:
        raise Exception('Invalid decomposition Method')

    upper_bound = min(upper_bound, new_upper_bound)
    gap = upper_bound - lower_bound

    return gap, lower_bound, upper_bound


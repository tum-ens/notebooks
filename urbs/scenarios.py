import pandas as pd
import numpy as np

# SCENARIO GENERATORS
# In this script a variety of scenario generator functions are defined to
# facilitate scenario definitions.


# SCENARIOS
def scenario_base(data):
    # do nothing
    return data


def scenario_ls(data):
    # set storage
    sto = data['storage']
    for site_sto_tuple in sto.index:
        sto.loc[site_sto_tuple, 'inst-cap-c'] *= 3
        sto.loc[site_sto_tuple, 'cap-up-c'] *= 3
        sto.loc[site_sto_tuple, 'inst-cap-p'] *= 3
        sto.loc[site_sto_tuple, 'cap-up-p'] *= 3
    return data


def scenario_ls_exp(data):
    # set storage
    sto = data['storage']
    for site_sto_tuple in sto.index:
        sto.loc[site_sto_tuple, 'cap-up-c'] *= 3
        sto.loc[site_sto_tuple, 'cap-up-p'] *= 3
    return data


def scenario_fix_all(data):
    # set process
    pro = data['process']
    for site_pro_tuple in pro.index:
        pro.loc[site_pro_tuple, 'inst-cap'] = pro.loc[site_pro_tuple, 'cap-up']
        pro.loc[site_pro_tuple, 'cap-lo'] = pro.loc[site_pro_tuple, 'cap-up']
        pro.loc[site_pro_tuple, 'area-per-cap'] = np.nan
        # pro.loc[site_pro_tuple, 'cap-up'] =

    # set transmission
    tra = data['transmission']
    for site_tra_tuple in tra.index:
        tra.loc[site_tra_tuple, 'inst-cap'] = 1000
        tra.loc[site_tra_tuple, 'cap-lo'] = tra.loc[site_tra_tuple, 'inst-cap']
        tra.loc[site_tra_tuple, 'cap-up'] = tra.loc[site_tra_tuple, 'inst-cap']

    # set storage
    sto = data['storage']
    for site_sto_tuple in sto.index:
        sto.loc[site_sto_tuple, 'inst-cap-c'] = sto.loc[site_sto_tuple, 'cap-lo-c']
        sto.loc[site_sto_tuple, 'cap-up-c'] = sto.loc[site_sto_tuple, 'cap-lo-c']
        sto.loc[site_sto_tuple, 'inst-cap-p'] = sto.loc[site_sto_tuple, 'cap-lo-p']
        sto.loc[site_sto_tuple, 'cap-up-p'] = sto.loc[site_sto_tuple, 'cap-lo-p']
        # pro.loc[site_pro_tuple, 'cap-up'] =
    return data


def scenario_sto_exp(data):
    # set process
    pro = data['process']
    for site_pro_tuple in pro.index:
        pro.loc[site_pro_tuple, 'inst-cap'] = pro.loc[site_pro_tuple, 'cap-up']
        pro.loc[site_pro_tuple, 'cap-lo'] = pro.loc[site_pro_tuple, 'cap-up']
        pro.loc[site_pro_tuple, 'area-per-cap'] = np.nan
        # pro.loc[site_pro_tuple, 'cap-up'] =

    # set transmission
    tra = data['transmission']
    for site_tra_tuple in tra.index:
        tra.loc[site_tra_tuple, 'inst-cap'] = 1000
        tra.loc[site_tra_tuple, 'cap-lo'] = tra.loc[site_tra_tuple, 'inst-cap']
        tra.loc[site_tra_tuple, 'cap-up'] = tra.loc[site_tra_tuple, 'inst-cap']
        # tra.loc[site_tra_tuple, 'cap-up'] =

    # set storage
    sto = data['storage']
    for site_sto_tuple in sto.index:
        sto.loc[site_sto_tuple, 'inst-cap-c'] = sto.loc[site_sto_tuple, 'cap-lo-c']
        sto.loc[site_sto_tuple, 'cap-up-c'] = np.inf
        sto.loc[site_sto_tuple, 'inst-cap-p'] = sto.loc[site_sto_tuple, 'cap-lo-p']
        sto.loc[site_sto_tuple, 'cap-up-p'] = np.inf
        # pro.loc[site_pro_tuple, 'cap-up'] =
    return data


def scenario_tra_exp(data):
    # set process
    pro = data['process']
    for site_pro_tuple in pro.index:
        pro.loc[site_pro_tuple, 'inst-cap'] = pro.loc[site_pro_tuple, 'cap-up']
        pro.loc[site_pro_tuple, 'cap-lo'] = pro.loc[site_pro_tuple, 'cap-up']
        pro.loc[site_pro_tuple, 'area-per-cap'] = np.nan
        # pro.loc[site_pro_tuple, 'cap-up'] =

    # set transmission
    tra = data['transmission']
    for site_tra_tuple in tra.index:
        tra.loc[site_tra_tuple, 'inst-cap'] = 1000
        tra.loc[site_tra_tuple, 'cap-lo'] = tra.loc[site_tra_tuple, 'inst-cap']
        tra.loc[site_tra_tuple, 'cap-up'] = np.inf

    # set storage
    sto = data['storage']
    for site_sto_tuple in sto.index:
        sto.loc[site_sto_tuple, 'inst-cap-c'] = sto.loc[site_sto_tuple, 'cap-lo-c']
        sto.loc[site_sto_tuple, 'cap-up-c'] = sto.loc[site_sto_tuple, 'cap-lo-c']
        sto.loc[site_sto_tuple, 'inst-cap-p'] = sto.loc[site_sto_tuple, 'cap-lo-p']
        sto.loc[site_sto_tuple, 'cap-up-p'] = sto.loc[site_sto_tuple, 'cap-lo-p']
        # pro.loc[site_pro_tuple, 'cap-up'] =
    return data


def scenario_pro_exp(data):
    # set process
    pro = data['process']
    for site_pro_tuple in pro.index:
        pro.loc[site_pro_tuple, 'inst-cap'] = pro.loc[site_pro_tuple, 'cap-up']
        pro.loc[site_pro_tuple, 'cap-lo'] = pro.loc[site_pro_tuple, 'cap-up']
        pro.loc[site_pro_tuple, 'cap-up'] = np.inf
        pro.loc[site_pro_tuple, 'area-per-cap'] = np.nan

    # set transmission
    tra = data['transmission']
    for site_tra_tuple in tra.index:
        tra.loc[site_tra_tuple, 'inst-cap'] = 1000
        tra.loc[site_tra_tuple, 'cap-lo'] = tra.loc[site_tra_tuple, 'inst-cap']
        tra.loc[site_tra_tuple, 'cap-up'] = tra.loc[site_tra_tuple, 'inst-cap']
        # tra.loc[site_tra_tuple, 'cap-up'] =

    # set storage
    sto = data['storage']
    for site_sto_tuple in sto.index:
        sto.loc[site_sto_tuple, 'inst-cap-c'] = sto.loc[site_sto_tuple, 'cap-lo-c']
        sto.loc[site_sto_tuple, 'cap-up-c'] = sto.loc[site_sto_tuple, 'cap-lo-c']
        sto.loc[site_sto_tuple, 'inst-cap-p'] = sto.loc[site_sto_tuple, 'cap-lo-p']
        sto.loc[site_sto_tuple, 'cap-up-p'] = sto.loc[site_sto_tuple, 'cap-lo-p']
        # pro.loc[site_pro_tuple, 'cap-up'] =
    return data


def scenario_green_field(data):
    # set process
    pro = data['process']
    for site_pro_tuple in pro.index:
        pro.loc[site_pro_tuple, 'inst-cap'] = 0
        pro.loc[site_pro_tuple, 'cap-lo'] = 0
        pro.loc[site_pro_tuple, 'cap-up'] = np.inf

    # set transmission
    tra = data['transmission']
    for site_tra_tuple in tra.index:
        tra.loc[site_tra_tuple, 'inst-cap'] = 0
        tra.loc[site_tra_tuple, 'cap-lo'] = 0
        tra.loc[site_tra_tuple, 'cap-up'] = np.inf

    # set storage
    sto = data['storage']
    for site_sto_tuple in sto.index:
        sto.loc[site_sto_tuple, 'inst-cap-c'] = 0
        sto.loc[site_sto_tuple, 'cap-lo-c'] = 0
        sto.loc[site_sto_tuple, 'cap-up-c'] = np.inf
        sto.loc[site_sto_tuple, 'inst-cap-p'] = 0
        sto.loc[site_sto_tuple, 'cap-lo-p'] = 0
        sto.loc[site_sto_tuple, 'cap-up-p'] = np.inf
    return data


def scenario_fix_all_ger(data):
    # do nothing: data is already fixed
    return data


def scenario_sto_exp_ger(data):
    # set storage
    sto = data['storage']
    for site_sto_tuple in sto.index:
        sto.loc[site_sto_tuple, 'cap-up-c'] = np.inf
        sto.loc[site_sto_tuple, 'cap-up-p'] = np.inf
    return data


def scenario_tra_exp_ger(data):
    # set transmission
    tra = data['transmission']
    for site_tra_tuple in tra.index:
        tra.loc[site_tra_tuple, 'cap-up'] = np.inf
    return data


def scenario_pro_exp_ger(data):
    # set process
    pro = data['process']
    for site_pro_tuple in pro.index:
        pro.loc[site_pro_tuple, 'cap-up'] = np.inf
    return data


def test_time_1(data):
    data['test_timesteps'] = range(1, 3)
    return data


def test_time_2(data):
    data['test_timesteps'] = range(5, 7)
    return data


def test_time_3(data):
    data['test_timesteps'] = range(4305, 4307)
    return data


def test_supim_1(data):
    data['test_timesteps'] = range(5, 7)
    supim = data['supim']
    supim.loc[:] = 0.1
    return data


def test_supim_2(data):
    data['test_timesteps'] = range(5, 7)
    supim = data['supim']
    supim.loc[:] = 1
    return data


def test_tra_var(data):
    data['test_timesteps'] = range(5, 7)
    tra = data['transmission']
    lines = (tra.index.get_level_values('Transmission') == 'hvac')
    tra.loc[lines, 'cap-up'] = float('inf')
    return data


def scenario_co2_limit(data):
    # change global CO2 limit
    global_prop = data['global_prop']
    global_prop.loc['CO2 limit', 'value'] *= 0.05
    return data


def scenario_co2_tax_mid(data):
    # change CO2 price in Mid
    co = data['commodity']
    co.loc[('Mid', 'CO2', 'Env'), 'price'] = 50
    return data


def scenario_north_process_caps(data):
    # change maximum installable capacity
    pro = data['process']
    pro.loc[('North', 'Hydro plant'), 'cap-up'] *= 0.5
    pro.loc[('North', 'Biomass plant'), 'cap-up'] *= 0.25
    return data

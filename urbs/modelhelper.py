import pandas as pd


def annuity_factor(n, i):
    """Annuity factor formula.

    Evaluates the annuity factor formula for depreciation duration
    and interest rate. Works also well for equally sized numpy arrays
    of values for n and i.

    Args:
        n: depreciation period (years)
        i: interest rate (e.g. 0.06 means 6 %)

    Returns:
        Value of the expression :math:`\\frac{(1+i)^n i}{(1+i)^n - 1}`

    Example:
        >>> round(annuity_factor(20, 0.07), 5)
        0.09439

    """
    return (1+i)**n * i / ((1+i)**n - 1)


def commodity_balance(m, tm, sit, com):
    """Calculate commodity balance at given timestep.

    For a given commodity com and timestep tm, calculate the balance of
    consumed (to process/storage/transmission, counts positive) and provided
    (from process/storage/transmission, counts negative) power. Used as helper
    function in create_model for constraints on demand and stock commodities.

    Args:
        m: the model object
        tm: the timestep
        site: the site
        com: the commodity

    Returns
        balance: net value of consumed (positive) or provided (negative) power

    """
    balance = (sum(m.e_pro_in[(tm, site, process, com)]
                   # usage as input for process increases balance
                   for site, process in m.pro_tuples
                   if site == sit and (process, com) in m.r_in_dict)
               - sum(m.e_pro_out[(tm, site, process, com)]
                     # output from processes decreases balance
                     for site, process in m.pro_tuples
                     if site == sit and (process, com) in m.r_out_dict)
               + sum(m.e_tra_in[(tm, site_in, site_out, transmission, com)]
                     # exports increase balance
                     for site_in, site_out, transmission, commodity
                     in m.tra_tuples
                     if site_in == sit and commodity == com)
               - sum(m.e_tra_out[(tm, site_in, site_out, transmission, com)]
                     # imports decrease balance
                     for site_in, site_out, transmission, commodity
                     in m.tra_tuples
                     if site_out == sit and commodity == com)
               + sum(m.e_sto_in[(tm, site, storage, com)] -
                     m.e_sto_out[(tm, site, storage, com)]
                     # usage as input for storage increases consumption
                     # output from storage decreases consumption
                     for site, storage, commodity in m.sto_tuples
                     if site == sit and commodity == com))
    return balance


def commodity_subset(com_tuples, type_name):
    """ Unique list of commodity names for given type.

    Args:
        com_tuples: a list of (site, commodity, commodity type) tuples
        type_name: a commodity type or a ist of a commodity types

    Returns:
        The set (unique elements/list) of commodity names of the desired type
    """
    if type(type_name) is str:
        # type_name: ('Stock', 'SupIm', 'Env' or 'Demand')
        return set(com for sit, com, com_type in com_tuples
                   if com_type == type_name)
    else:
        # type(type_name) is a class 'pyomo.base.sets.SimpleSet'
        # type_name: ('Buy')=>('Elec buy', 'Heat buy')
        return set((sit, com, com_type) for sit, com, com_type in com_tuples
                   if com in type_name)


def get_com_price(instance, tuples):
    """ Calculate commodity prices for each modelled timestep.

    Args:
        instance: a Pyomo ConcreteModel instance
        tuples: a list of (site, commodity, commodity type) tuples

    Returns:
        a Pandas DataFrame with entities as columns and timesteps as index
    """
    com_price = pd.DataFrame(index=instance.tm)
    for c in tuples:
        # check commodity price: fix or has a timeseries
        # type(instance.commodity.loc[c]['price']):
        # float => fix: com price = 0.15
        # string => var: com price = '1.25xBuy' (Buy: refers to timeseries)

        # same commodity price for each hour
        price = instance.commodity.loc[c]['price']
        com_price[c] = pd.Series(price, index=com_price.index)
    return com_price


#TODO: This method comes from regional modelhelper.py, but is never used
def search_sell_buy_tuple(instance, sit_in, pro_in, coin):
    """ Return the equivalent sell-process for a given buy-process.

    Args:
        instance: a Pyomo ConcreteModel instance
        sit_in: a site
        pro_in: a process
        co_in: a commodity

    Returns:
        a process
    """
    pro_output_tuples = list(instance.pro_output_tuples.value)
    pro_input_tuples = list(instance.pro_input_tuples.value)
    # search the output commodities for the "buy" process
    # buy_out = (site,output_commodity)
    buy_out = set([(x[0], x[2])
                   for x in pro_output_tuples
                   if x[1] == pro_in])
    # search the sell process for the output_commodity from the buy process
    sell_output_tuple = ([x
                          for x in pro_output_tuples
                          if x[2] in instance.com_sell])
    for k in range(len(sell_output_tuple)):
        sell_pro = sell_output_tuple[k][1]
        sell_in = set([(x[0], x[2])
                       for x in pro_input_tuples
                       if x[1] == sell_pro])
        # check: buy - commodity == commodity - sell; for a site
        if not(sell_in.isdisjoint(buy_out)):
            return sell_pro
    return None


def extract_number_str(str_in):
    """ Extract first number from a given string and convert to a float number.

    The function works with the following formats (,25), (.25), (2), (2,5),
    (2.5), (1,000.25), (1.000,25) and  doesn't with (1e3), (1.5-0.4j) and
    negative numbers.

    Args:
        str_in: a string ('1,20BUY')

    Returns:
        A float number (1.20)
    """
    import re
    # deletes all char starting after the number
    start_char = re.search('[*:!%$&?a-zA-Z]', str_in).start()
    str_num = str_in[:start_char]

    if re.search('\d+', str_num) is None:
        # no number in str_num
        return 1.0
    elif re.search('^(\d+|\d{1,3}(,\d{3})*)(\.\d+)?$', str_num) is not None:
        # Commas required between powers of 1,000
        # Can't start with "."
        # Pass: (1,000,000), (0.001)
        # Fail: (1000000), (1,00,00,00), (.001)
        str_num = str_num.replace(',', '')
        return float(str_num)
    elif re.search('^(\d+|\d{1,3}(.\d{3})*)(\,\d+)?$', str_num) is not None:
        # Dots required between powers of 1.000
        # Can't start with ","
        # Pass: (1.000.000), (0,001)
        # Fail: (1000000), (1.00.00,00), (,001)
        str_num = str_num.replace('.', '')
        return float(str_num.replace(',', '.'))
    elif re.search('^\d*\.?\d+$', str_num) is not None:
        # No commas allowed
        # Pass: (1000.0), (001), (.001)
        # Fail: (1,000.0)
        return float(str_num)
    elif re.search('^\d*\,?\d+$', str_num) is not None:
        # No dots allowed
        # Pass: (1000,0), (001), (,001)
        # Fail: (1.000,0)
        str_num = str_num.replace(',', '.')
        return float(str_num)

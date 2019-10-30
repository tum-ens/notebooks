# Helper functions

import os
import gurobipy as gp
import pandas as pd
import glob
import numpy as np
import matplotlib as mpl
import matplotlib.pyplot as plt
import matplotlib.dates as dates
import re
from datetime import datetime

def glob_result_files(folder_name):
    """ Glob lp files from specified folder.

    Args:
        folder_name: an absolute or relative path to a directory

    Returns:
        list of filenames that match the pattern '*.h5'
    """
    glob_pattern = os.path.join(folder_name, '*.h5')
    result_files = sorted(glob.glob(glob_pattern))
    return result_files

legend_position = ['center left', (1.01, 0.5)]

def axis_thousand_comma(axes, axis):
    """ Set a comma after thousand for axis

    Args:
        axes: axes object
        axis: list of strings to specify which axes to take, e.g. ['x', 'y'] or just ['y']

    Returns:
        Nothing
    """
    if 'x' in axis:
        axes.xaxis.set_major_formatter(mpl.ticker.StrMethodFormatter('{x:,.0f}'))
    if 'y' in axis:
        axes.yaxis.set_major_formatter(mpl.ticker.StrMethodFormatter('{x:,.0f}'))

def legend_right(axes):
    """ Set legend to right

    Args:
        axes: axes object

    Returns:
        Nothing
    """
    axes.legend(loc=legend_position[0], bbox_to_anchor=legend_position[1])
    
def legend_above(axes, location=3, cols=4, anchorbox=(0., 1.3, 1., .102)):
    """ Set legend to top

    Args:
        axes: axes object

    Returns:
        Nothing
    """
    axes.legend(bbox_to_anchor=anchorbox, loc=location, ncol=cols, mode="expand", borderaxespad=0.)
    
def stack_plot(element, axes, period):
    """ 

    Args:
        element: DataFrame to plot
        axes: axes object
        period: time period to plot

    Returns:
        Nothing
    """
    plot_element = element[plot_periods[period][0]:plot_periods[period][1]]
    (plot_element/1000).plot(kind='area', stacked=True, ax=axes, legend=False, color=color_fuels.values())
    
def concatination(variable, rc, scenario, realization, iteration, subproblems, rc_master=None, com='Elec'):
    """
    Concatinate variable values over iterations
    
    Args:
        variable: string to state extracted variable
        rc: dictionary of result container
        scenario: current scenario
        realization: current uncertaint realization
        iteration: current iteration
        subproblems: list of subproblem numbers
        rc_master: dictionary of master result containers
        com: string to define to extract commodity (default: Elec)
    
    Return:
        Concatenated pandas series
    """
    
    if variable == 'e_pro_out':
        concat_list = [rc[scenario, sub, realization,
                         iteration]._result[variable].xs(com,level='com').unstack().unstack()
                         for sub in subproblems]
        if rc_master:
            concat_list = [rc_master[scenario,
                                     iteration]._result[variable].xs(com,
                                                                     level='com').unstack().unstack()] + concat_list
    elif 'sto' in variable:
        if 'con' in variable:
            concat_list = [rc[scenario, sub, realization,
                             iteration]._result[variable].xs(com,level='com').xs('Pumped storage',
                                                                                    level='sto').unstack()[1:]
                             for sub in subproblems]
            if rc_master:
                concat_list = [rc_master[scenario,
                                         iteration]._result[variable].xs(com,
                                                                         level='com').xs('Pumped storage',
                                                                                         level='sto').unstack()[1:]] + concat_list
        else:
            concat_list = [rc[scenario, sub, realization,
                             iteration]._result[variable].xs(com,level='com').xs('Pumped storage',
                                                                                    level='sto').unstack()
                             for sub in subproblems]
            if rc_master:
                concat_list = [rc_master[scenario,
                                         iteration]._result[variable].xs(com,
                                                                         level='com').xs('Pumped storage',
                                                                                         level='sto').unstack()] + concat_list
    elif 'tra' in variable:
        if 'in' in variable:
            lvl = 'sit_'
        elif 'out' in variable:
            lvl = 'sit'
        
        
        if rc_master:
            concat_list = [rc[scenario, sub, realization,
                             iteration]._result[variable].xs('Elec',
                                                           level='com').xs('hvac',
                                                                           level='tra').unstack(level=lvl).sum(axis=1).unstack()
                             for sub in subproblems]
            if rc_master:
                concat_list = [rc_master[scenario,
                                         iteration]._result[variable].xs('Elec',
                                                           level='com').xs('hvac',
                                                                           level='tra').unstack(level=lvl).sum(axis=1).unstack()]+ concat_list

    series = pd.concat(concat_list).sort_index()
    return series

def concatination_wo_iteration(variable, rc, scenario, realization, subproblems, rc_master=None, com='Elec'):
    """
    Concatinate variable values over iterations
    
    Args:
        variable: string to state extracted variable
        rc: dictionary of result container
        scenario: current scenario
        realization: current uncertaint realization
        subproblems: list of subproblem numbers
        rc_master: dictionary of master result containers
        com: string to define to extract commodity (default: Elec)
    
    Return:
        Concatenated pandas series
    """
    
    if variable == 'e_pro_out':
        concat_list = [rc[scenario, sub, realization]._result[variable].xs(com,level='com').unstack().unstack()
                         for sub in subproblems]
        if rc_master:
            concat_list = [rc_master[scenario]._result[variable].xs(com,
                                                                     level='com').unstack().unstack()] + concat_list
    elif 'sto' in variable:
        if 'con' in variable:
            concat_list = [rc[scenario, sub, realization]._result[variable].xs(com,level='com').xs('Pumped storage',
                                                                                    level='sto').unstack()[1:]
                             for sub in subproblems]
            if rc_master:
                concat_list = [rc_master[scenario]._result[variable].xs(com,
                                                                         level='com').xs('Pumped storage',
                                                                                         level='sto').unstack()[1:]] + concat_list
        else:
            concat_list = [rc[scenario, sub, realization]._result[variable].xs(com,level='com').xs('Pumped storage',
                                                                                    level='sto').unstack()
                             for sub in subproblems]
            if rc_master:
                concat_list = [rc_master[scenario]._result[variable].xs(com,
                                                                         level='com').xs('Pumped storage',
                                                                                         level='sto').unstack()] + concat_list
    elif 'tra' in variable:
        if 'in' in variable:
            lvl = 'sit_'
        elif 'out' in variable:
            lvl = 'sit'
        
        
        if rc_master:
            concat_list = [rc[scenario, sub, realization]._result[variable].xs('Elec',
                                                           level='com').xs('hvac',
                                                                           level='tra').unstack(level=lvl).sum(axis=1).unstack()
                             for sub in subproblems]
            if rc_master:
                concat_list = [rc_master[scenario]._result[variable].xs('Elec',
                                                           level='com').xs('hvac',
                                                                           level='tra').unstack(level=lvl).sum(axis=1).unstack()]+ concat_list

    series = pd.concat(concat_list).sort_index()
    return series

def set_date_index(df, origin):
    """
    Change index of dataframe to datetime index
    
    Args:
        df: Pandas DataFrame with numerical index or Series
        origin: DateTime starting point
    
    Return:
        DataFrame with DateTime index
    """
    
    df.index = pd.to_datetime(pd.to_numeric(df.index), unit='h', origin=origin)
    
    if type(df) == pd.core.frame.DataFrame:
        df.sort_index(axis=1, inplace=True)
    
    df.sort_index(inplace=True)
    
    return df

def date_axis_formatting(ax):
    """
    Set xaxis formatting to datetime
    
    Args:
        ax: Matplotlib axes object
    
    Return:
        Nothing
    """
    ax.xaxis.set_minor_locator(dates.WeekdayLocator(byweekday=(0), interval=1))
    ax.xaxis.set_minor_formatter(dates.DateFormatter('%d\n%a'))
    ax.xaxis.grid(True, which="minor")
    ax.xaxis.set_major_locator(dates.MonthLocator())
    ax.xaxis.set_major_formatter(dates.DateFormatter('%b\n%Y'))
    plt.setp(ax.xaxis.get_majorticklabels(), rotation=0)
    
def hour_axis_formatting(ax):
    """
    Set xaxis formatting to datetime
    
    Args:
        ax: Matplotlib axes object
    
    Return:
        Nothing
    """
    ax.xaxis.set_minor_locator(dates.HourLocator(byhour=range(0,24,4)))
    ax.xaxis.set_minor_formatter(dates.DateFormatter('%H'))
    ax.xaxis.grid(True, which="minor")
    ax.xaxis.set_major_locator(dates.MonthLocator())
    ax.xaxis.set_major_formatter(dates.DateFormatter('%b\n%Y'))
    plt.setp(ax.xaxis.get_majorticklabels(), rotation=0)
    
    
def summarize_plants(help_df):
    # Try to store gas plants in one row and delete original rows
    #import pdb; pdb.set_trace()
    help_df = help_df.stack()
    help_df['Gas plant'] = help_df['CC plant'] + help_df['Natural gas plant']
    help_df = help_df.unstack()
    help_df.drop(['CC plant', 'Natural gas plant'], axis=1, level=0, inplace=True)  

    # Try to delete curtailment and slack rows, if zero
    try: 
        #if help_df['Slack powerplant'].sum().sum() == 0:
        help_df.drop(['Slack powerplant'], axis=1, level=0, inplace=True)
        #if help_df['Curtailment'].sum().sum() == 0:
        help_df.drop(['Curtailment'], axis=1, level=0, inplace=True)
    except:
        pass
    
    return help_df


def summarize_caps(help_df):
    # Try to store gas plants in one row and delete original rows
    #import pdb; pdb.set_trace()
    help_df = help_df.T
    help_df['Gas plant'] = help_df['CC plant'] + help_df['Natural gas plant']
    help_df = help_df
    help_df.drop(['CC plant', 'Natural gas plant'], axis=1, inplace=True)  

    # Try to delete curtailment and slack rows, if zero
    try: 
        #if help_df['Slack powerplant'].sum().sum() == 0:
        help_df.drop(['Slack powerplant'], axis=1, inplace=True)
        #if help_df['Curtailment'].sum().sum() == 0:
        help_df.drop(['Curtailment'], axis=1, inplace=True)
    except:
        pass
    
    return help_df.T

def extract_season(df, season, year='2015'):
    """ Slice dataframe according to season months

    Args:
        df: DataFrame with datetimeindex
        season: string describing season ('spring', 'summer', 'autumn', 'winter')
        year: string selected year, default 2015

    Returns:
        Sliced dataframe with season months
    """
    
    
    # seasons
    seasons = {'spring': [3, 4, 5], 'summer': [6, 7, 8],
           'autumn': [9, 10, 11], 'winter': [1, 2, 12]}
    
    if season in ['spring', 'summer', 'autumn']:
        help_df = df[year+'-'+str(seasons[season][0]):year+'-'+str(seasons[season][2])]
    elif season == 'winter':
        mask = ((df.index <= year+'-'+str(seasons[season][1]))
                | (df.index >= year+'-'+str(seasons[season][2])))
        help_df = df[mask]
    else:
        print(f'{season} is not defined!')
    
    return help_df
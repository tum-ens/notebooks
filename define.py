'''
File for storing important and often used packages, lists, dicts, etc.
'''


### Dicts

# Dict to translate state names to English
states_translation_de_en = {
    'Bayern': 'Bavaria',
    'Hessen': 'Hesse',
    'Niedersachsen': 'Lower Saxony',
    'Nordrhein-Westfalen': 'North Rhine-Westphalia',
    'Rheinland-Pfalz': 'Rhineland-Palatinate',
    'Sachsen': 'Saxony',
    'Sachsen-Anhalt': 'Saxony-Anhalt',
    'Thüringen': 'Thuringia'}

# Dict to translate state names to German    
states_translation_en_de = {y:x for x,y in states_translation_de_en.items()}

# Dict to translate fuel names
fuel_translation_de_en = {
    'Steinkohle': 'Hard coal plant',
    'Braunkohle': 'Lignite plant',
    'Heizöl': 'Oil plant',
    'Erdgas': 'Gas plant',
    'Kernenergie': 'Nuclear plant',
    'Energieträger Sonstige': 'Waste plant',
    'Lauf- und Speicherwasser': 'Hydro plant',
    'Wasserkraft': 'Hydro plant',
    'Windkraft': 'Wind plant',
    'Photovoltaik': 'Solar plant',
    'Biomasse': 'Biomass plant',
    'Sonstige 1)': 'Geothermal plant',
    'Sonstige Erneuerbare': 'Geothermal plant',
    'Sonstige Konventionelle': 'Oil plant',
    'Sonstige Energieträger': 'Other plant'}

# Dict to translate shorten state names to full state names
states_translation_sh_lo = {
    'BB': 'Brandenburg',
    'BE': 'Berlin',
    'BW': 'Baden-Württemberg',
    'BY': 'Bayern',
    'HE': 'Hessen',
    'HB': 'Bremen',
    'HH': 'Hamburg',
    'MV': 'Mecklenburg-Vorpommern',
    'NI': 'Niedersachsen',
    'NW': 'Nordrhein-Westfalen',
    'RP': 'Rheinland-Pfalz',
    'SH': 'Schleswig-Holstein',
    'SL': 'Saarland',
    'SN': 'Sachsen',
    'ST': 'Sachsen-Anhalt',
    'TH': 'Thüringen',
    'Ausschließliche Wirtschaftszone (Wind See)': 'AWZ'}

# Dict of coordinates of the geographical center of each state, 
# except Brandenburg (would be Berlin also) in German
coordinates_states_de = {
    'Baden-Württemberg': (48.3943, 9.0014),
    'Bayern': (48.5647, 11.2415),
    'Berlin': (52.5190, 13.4000),
    'Brandenburg': (52.5347, 12.6236),
    'Bremen': (53.0758, 8.8072),
    'Hamburg': (53.5438, 10.0099),
    'Hessen': (50.6237, 9.0377),
    'Mecklenburg-Vorpommern': (53.7735, 12.5803),
    'Niedersachsen': (52.8240, 9.0805),
    'Nordrhein-Westfalen': (51.4759, 7.5565),
    'Rheinland-Pfalz': (49.9551, 7.3104),
    'Saarland': (49.3841, 6.9536),
    'Sachsen': (50.9294, 13.4583),
    'Sachsen-Anhalt': (52.0090, 11.7026),
    'Schleswig-Holstein': (54.1855, 9.8222),
    'Thüringen': (50.9033, 11.0263),
    'Offshore': (54.7436, 12.6453)}

# Dict of coordinates of the geographical center of each state, 
# except Brandenburg (would be Berlin also) in English	
coordinates_states_en = {
    'Baden-Württemberg': (48.3943, 9.0014),
    'Bavaria': (48.5647, 11.2415),
    'Berlin': (52.5190, 13.4000),
    'Brandenburg': (52.5347, 12.6236),
    'Bremen': (53.0758, 8.8072),
    'Hamburg': (53.5438, 10.0099),
    'Hesse': (50.6237, 9.0377),
    'Mecklenburg-Vorpommern': (53.7735, 12.5803),
    'Lower Saxony': (52.8240, 9.0805),
    'North Rhine-Westphalia': (51.4759, 7.5565),
    'Rhineland-Palatinate': (49.9551, 7.3104),
    'Saarland': (49.3841, 6.9536),
    'Saxony': (50.9294, 13.4583),
    'Saxony-Anhalt': (52.0090, 11.7026),
    'Schleswig-Holstein': (54.1855, 9.8222),
    'Thuringia': (50.9033, 11.0263),
    'Offshore': (54.7436, 12.6453),
    'Lower Bavaria': (48.6588, 12.8783),
    'Lower Franconia': (50.0477, 9.9036),
    'Middle Franconia': (49.4113, 10.8190),
    'Swabia': (48.2231, 10.5089),
    'Upper Bavaria': (48.0613, 11.8770),
    'Upper Palatinate': (49.4634, 12.1486),
    'Upper Franconia': (50.0803, 11.3934)}

# Dict of position in plot of the geographical center of each state, 
# except Brandenburg (would be Berlin also) in English	
cap_positions_en = {
    'Baden-Württemberg': [0.27, 0.15, 0.15, 0.15],
    'Bavaria': [0.52, 0.2, 0.15, 0.15],
    'Berlin': [0.75, 0.68, 0.15, 0.15],
    'Brandenburg': [0.75, 0.6, 0.15, 0.15],
    'Bremen': [0.25, 0.75, 0.15, 0.15],
    'Hamburg': [0.32, 0.8, 0.15, 0.15],
    'Hesse': [0.25, 0.4, 0.15, 0.15],
    'Mecklenburg-Vorpommern': [0.6, 0.8, 0.15, 0.15],
    'Lower Saxony': [0.35, 0.65, 0.15, 0.15],
    'North Rhine-Westphalia': [0.15, 0.5, 0.15, 0.15],
    'Rhineland-Palatinate': [0.14, 0.33, 0.15, 0.15],
    'Saarland': [0.1, 0.25, 0.15, 0.15],
    'Saxony': [0.68, 0.47, 0.15, 0.15],
    'Saxony-Anhalt': [0.53, 0.58, 0.15, 0.15],
    'Schleswig-Holstein': [0.4, 0.83, 0.15, 0.15],
    'Thuringia': [0.47, 0.44, 0.15, 0.15],
    'Offshore': [0.5, 0.92, 0.15, 0.15]
}

	
# Dict for azimuth of solar panels                   
azimuth = {
    'East': 90,
    'South': 180,
    'West': 270}

# Dict for mapping measuring points to state    
mp_to_state =  {'MaxauW15': 'Baden-Württemberg',
                'PassauW15': 'Bayern',#HOFKIRCHEN
                'BorgsdorfW15': 'Berlin',
                'KetzinW15': 'Brandenburg',
                'DreyeW60': 'Bremen',
                'HamburgW1_2015': 'Hamburg',
                'FrankfurtW15': 'Hessen', #Raunheim
                'IntschedeW15': 'Niedersachsen', #Neu Darchau
                'BurowW15': 'Mecklenburg-Vorpommern',
                'StolzenauW15': 'Nordrhein-Westfalen', #Düsseldorf
                'DetzemW15': 'Rheinland-Pfalz', #Cochem
                'FremersdorfW15': 'Saarland', #Fremersdorf
                'DresdenW15': 'Sachsen',
                'AkenW15': 'Sachsen-Anhalt',
                'ToenningW1_2015': 'Schleswig-Holstein',
                'RischmuehleW15': 'Thüringen'} #Throta


### Lists

# List of all German states + Offshore in German
states_de = ['Baden-Württemberg', 'Bayern', 'Berlin', 'Brandenburg',
             'Bremen', 'Hamburg', 'Hessen', 'Mecklenburg-Vorpommern',
             'Niedersachsen', 'Nordrhein-Westfalen', 'Rheinland-Pfalz',
             'Saarland', 'Sachsen-Anhalt', 'Sachsen', 'Schleswig-Holstein',
             'Thüringen', 'Offshore']
             
# List of all German states + Offshore in English
states_en = ['Baden-Württemberg', 'Bavaria', 'Berlin', 'Brandenburg',
             'Bremen', 'Hamburg', 'Hesse', 'Mecklenburg-Vorpommern',
             'Lower Saxony', 'North Rhine-Westphalia', 'Rhineland-Palatinate',
             'Saarland', 'Saxony-Anhalt', 'Saxony', 'Schleswig-Holstein',
             'Thuringia', 'Offshore']
             
#List of regions of Bavaria in English
regions_by_en = ['Lower Bavaria', 'Lower Franconia', 'Middle Franconia', 
                 'Swabia', 'Upper Bavaria', 'Upper Franconia',
                 'Upper Palatinate']
			 
# List of water-level measuring points
measuring_points = ['AkenW15', 'BorgsdorfW15', 'BurowW15', 'DetzemW15', 'DresdenW15', 'DreyeW60', 'FrankfurtW15', 
                    'FremersdorfW15', 'HamburgW1_2015', 'IntschedeW15', 'KetzinW15', 'MaxauW15', 'PassauW15', 
                    'RischmuehleW15', 'StolzenauW15', 'ToenningW1_2015'] 
					#'Hamburg' has extrem tidal range 
			
			
### Others

# Color codes 
tumgreen = '#a2ad00'
tumblue = '#3070b3'
tumdarkerblue = '#005293'
tumdarkblue = '#003359'
tumlightblue = '#98C6EA'
tumlighterblue = '#64A0C8'
tumorange = '#E37222'
tumivory = '#DAD7CB'
tumblack = '0'
tumdarkgrey = '0.2'
tumgrey = '0.5'
tumlightgrey = '0.8'
tumwhite = '1'
tumviolet = '#69085a'
tumturquois = '#00778a'
tumdarkgreen = '#007c30'
tumred = '#c4071b'
tumbrightyellow = '#ffdc00'
tumsenf = '#CAAB29'
tumbrown = '#804704'

color_states ={
    'Baden-Württemberg': tumgreen,
    'Bavaria': tumblue,
    'Berlin': tumdarkerblue,
    'Brandenburg': tumdarkblue,
    'Bremen': tumlightblue,
    'Hamburg': tumlighterblue,
    'Hesse': tumorange,
    'Mecklenburg-Vorpommern': tumivory,
    'Lower Saxony': tumblack,
    'North Rhine-Westphalia': tumgrey,
    'Offshore': tumsenf,
    'Rhineland-Palatinate': tumlightgrey,
    'Saarland': tumviolet,
    'Saxony': tumturquois,
    'Saxony-Anhalt': tumdarkgreen,
    'Schleswig-Holstein': tumred,
    'Thuringia': tumbrightyellow
}

color_fuels = {
               'Storage In': tumdarkblue,
               'Storage Out': tumdarkblue,
               'Biomass': tumgreen,
               'Gas': tumivory,
               'Geothermal': tumviolet,
               'Hard coal': tumgrey,
               'Hydro': tumblue,
               'Lignite': tumbrown,
               'Nuclear': tumred,
               'Oil': tumblack,
               'Other': tumbrightyellow,
               'Solar': tumorange, 
               'Waste': tumturquois,
               'Wind': tumlightblue,
               'Import': tumlighterblue,
               'Export': tumlightgrey
}

months = {
    0:    'January',
    745:  'February',
    1417: 'March',
    2171: 'April',
    2881: 'May',
    3625: 'June',
    4245: 'July',
    5089: 'August',
    5833: 'September',
    6553: 'October',
    7297: 'November',
    8017: 'December'
}



scenario_names = {
    'scenario_base': 'Base',
    'scenario_ls': 'Large storage',
    'scenario_ls_exp': 'Storage expansion'
}

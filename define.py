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
    'Sonstige Konventionelle': 'Oil plant'}

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
    'Offshore': (54.7436, 12.6453)}
	
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

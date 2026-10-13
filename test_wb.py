import requests

url_pop = "https://api.worldbank.org/v2/country/all/indicator/SP.POP.TOTL?format=json&per_page=300&date=2023"
url_gdp = "https://api.worldbank.org/v2/country/all/indicator/NY.GDP.PCAP.CD?format=json&per_page=300&date=2023"

r_pop = requests.get(url_pop).json()[1]
r_gdp = requests.get(url_gdp).json()[1]

pop_data = {item['countryiso3code']: item['value'] for item in r_pop if item['countryiso3code']}
gdp_data = {item['countryiso3code']: item['value'] for item in r_gdp if item['countryiso3code']}

countries = []
for code in pop_data.keys():
    if code in gdp_data and pop_data[code] and gdp_data[code]:
        countries.append((code, pop_data[code], gdp_data[code]))

print(len(countries))
print(countries[:2])

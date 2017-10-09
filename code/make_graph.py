import networkx as nx
import _pickle
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt

import thinkplot
import thinkstats2
from thinkstats2 import Cdf, Pmf

from import_owtrad import import_owtrad





# Import the OWTRAD dataset
nodes, edges = import_owtrad()


# Select the edges that we want to use
edges_to_use = edges.loc[(edges.USES == 'trd') | (edges.USES == 'plg')]
edges_list = zip(edges_to_use['NODE1'], edges_to_use['NODE2'])

# Make nx graph
G = nx.Graph()
G.add_edges_from(edges_list)


print("G Len nodes:", len(G.nodes()))
print("G Len edges:", len(G.edges()))





# Build  networks
trade_edges = edges[edges['USES'] == 'trd']
pilgrimadge_edges = edges[edges['USES'] == 'plg']
print("Trade routes:", len(trade_edges))
print("Pilgrimadge routes:", len(pilgrimadge_edges))
print()

network_trade = nx.Graph()
network_trade.add_edges_from(zip(trade_edges.NODEID1, trade_edges.NODEID2))

network_pilgrimadge = nx.Graph()
network_pilgrimadge.add_edges_from(zip(pilgrimadge_edges.NODEID1, pilgrimadge_edges.NODEID2))


print("Trade nodes:", len(network_trade.nodes()))
print("Pilgrimadge nodes:", len(network_pilgrimadge.nodes()))


def draw_graph(G):
    nx.draw_circular(G,
                     node_size=100,
                     with_labels=True)
    plt.show()

# (SLOW for large graphs)
# draw_graph(G)



def toss(p):
    return np.random.ranf() < p

class CityInfectionModel:
    """ Tracks intra-city SIR models, and inter-city infection transmission rates """
    S = 0
    I = 1
    D = 2
    Itimes = 3


    def __init__(self, nodes, max_steps, init_infected=None, model_rates=None):
        self.node_list = list(nodes)
        self.cur_infected = set()

        if model_rates is None:
            self.infection_rate    = .2
            self.mortality_rate    = .2
            self.transmission_rate = .1
        else:
            self.infection_rate, self.mortality_rate, self.transmission_rate = model_rates


        # Make np array to hold entire history
        # 3D: axis0 = city; axis1=s,i,d (susceptible, infected, dead); axis2=time steps
        self.history = np.zeros((len(self.node_list), 4, max_steps), dtype=np.uint8)
        # Init susceptible population @ time 0 to 100
        self.history[:, 0, 0] = 100

        init_infected = [] if init_infected is None else init_infected
        for city in init_infected:
            self.city_make_infected(city, 0, 10)
            self.cur_infected.add(city)

    def cityI(self, city):
        """ Returns index of city in array by name """
        return self.node_list.index(city)

    def city_make_infected(self, city, time_step, num_infect):
        """ Move num_infected people from susceptible to infected """
        if self.history[self.cityI(city), self.S, time_step] <= num_infect:
            num_infect = self.history[self.cityI(city), self.S, time_step]

        # Remove population from susceptible to infected
        self.history[self.cityI(city), self.S, time_step] -= num_infect
        self.history[self.cityI(city), self.I, time_step] += num_infect

    def city_make_dead(self, city, time_step, num_die):
        """ Move num_dead people from infected to dead """
        if self.history[self.cityI(city), self.I, time_step] <= num_die:
            num_die = self.history[self.cityI(city), self.I, time_step]

        self.history[self.cityI(city), self.I, time_step] -= num_die
        self.history[self.cityI(city), self.D, time_step] += num_die


    def SIR_step_one_city(self, city, time_step):
        """ Updates a city's SIR model at time_step
        Note: you must first copy data from the previous time step into time_step """
        num_susceptible, num_infected, num_dead, _ = self.history[self.cityI(city), :, time_step]

        if num_susceptible > 0:
            num_to_infect = int(num_infected * self.infection_rate)
        else:
            num_to_infect = 0

        num_to_die = int(num_infected * self.mortality_rate)

        # print("i: {}, d: {}".format(num_to_infect, num_to_die))

        self.city_make_infected(city, time_step, num_to_infect)
        self.city_make_dead(city, time_step, num_to_die)

    def SIR_one_step(self, time_step):
        """ Run SIR on all infected cities """
        for city in frozenset(self.cur_infected):
            self.SIR_step_one_city(city, time_step)

    def intercity_step_one_city(self, city, time_step):
        """ Transmits disease between cities """
        # Probability of transmission is the transmission_rate times number of infected in origin city
        # Should this be the infected ratio of origin city?
        p_transmission = self.transmission_rate * self.history[self.cityI(city), self.I, time_step]
        for neighbor in G[city]:
            if toss(p_transmission):
                # print("transmiting from {} to {}".format(city, neighbor))
                # What a "transmission event" actually does
                num_to_transmit = 1

                self.city_make_infected(neighbor, time_step, num_to_transmit)
                self.history[self.cityI(city), self.Itimes, time_step] += 1
                self.cur_infected.add(neighbor) # Add city to cur_infected so that it gets SIR run on it

    def intercity_one_step(self, time_step):
        """ Runs intercity_step_one_city on all infected cities """

        for city in frozenset(self.cur_infected):
            self.intercity_step_one_city(city, time_step)

    def copy_timestep(self, time_step):
        """ Copies S,I,D from time_step-1 into time_step """
        self.history[:, :self.Itimes, time_step] = self.history[:, :self.Itimes, time_step - 1]

    def model_one_step(self, time_step):
        """ Runs a complete step """
        self.copy_timestep(time_step)
        self.SIR_one_step(time_step)
        self.intercity_one_step(time_step)

    def run_model(self, n, init_time_step = 1):
        """ loop through steps and update_city, SIR_step, intercity_step n times starting at init_time_step"""

        for time_step in range(init_time_step, init_time_step + n):
            if time_step%10==0: print("step {}".format(time_step))
            self.model_one_step(time_step)

    def save_to_disk(self, filename):
        _pickle.dump(self.history, open(filename, "wb"))



init_infected = ["Paris"]
plague = CityInfectionModel(G.nodes(), 1500, init_infected=init_infected)
time_step = 0

# Print infection
# print(plague.history[0,0,0])
# print(plague.history[plague.history[:,0,0] != 100])
# print(plague.history[plague.cityI("Paris")])

print()

plague.run_model(1500)

plague.save_to_disk("test_run.pkl")

# print(plague.history[plague.history[:,0,0] != 100])
# print(plague.history[:,:,50])






"""
# Analytics
# print(len(cur_infected))
# print([(city, infected_times[city]) for city in infected_times if infected_times[city]])


# Sum the number of times each city has been infected
# infections_per_city = dict()
# for city in infected_timestamps:
#     infections_per_city[city] = len(infected_timestamps[city])


# infection_cdf = Cdf(infection_count.values())
# t.Cdf(infection_cdf)
# thinkplot.show()


# Plotting degree distribution
degree_of_node = dict()
for node in G.nodes():
    degree_of_node[node] = len(G[node])


def degree_pmf_graph(G):
    degree_of_G_pmf = dict()
    for node in G.nodes():
        try:
            degree_of_G_pmf[len(G[node])] += 1
        except KeyError:
            degree_of_G_pmf[len(G[node])] = 1
    return degree_of_G_pmf

degree_of_G_pmf = degree_pmf_graph(G)
degree_of_trade_pmf = degree_pmf_graph(network_trade)
degree_of_pilgrimadge_pmf = degree_pmf_graph(network_pilgrimadge)

print("mean degree:", np.mean(list(degree_of_node.values())))

# print(degree_of_G_pmf, degree_of_G_pmf.values())
print(degree_of_trade_pmf)
print(list(degree_of_trade_pmf.keys()))
print(list(degree_of_trade_pmf.values()))


plt.title('Our Degree Distribution')
thinkplot.Plot(list(degree_of_G_pmf.keys()), list(degree_of_G_pmf.values()), label="Combined Network")
thinkplot.Plot(list(degree_of_trade_pmf.keys()), list(degree_of_trade_pmf.values()), label="Trade Network")
thinkplot.Plot(list(degree_of_pilgrimadge_pmf.keys()), list(degree_of_pilgrimadge_pmf.values()), label="Pilgrimadge Network")
# thinkplot.show()


plt.title('Degree Distribution Cdf')
degree_cdf = Cdf(degree_of_node.values())
thinkplot.Cdf(degree_cdf)
# thinkplot.show()

# for degree in range(degree_of_node.values().max(), 0, -1):

# print(nodes.info())
# print()
# print(edges.info())
"""

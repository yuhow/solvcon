#!/usr/bin/python
#
# handler_plot.py
#
# Description:
#   provide many helper functions to plot and show the input solutions.
#

import sys
import scipy.optimize as so
import matplotlib.pyplot as plt

# a number to claim two floating number value are equal.
delta_precision = 0.0000000000001

def show_mesh_physical_model(bound):
    """
    Show how 1D Sod tube may look like.
    TODO:
        1. indicate the location of the diaphragm
    """
    from mpl_toolkits.mplot3d import axes3d
    import numpy as np

    fig = plt.figure()
    ax = axes3d.Axes3D(fig,azim=30,elev=30)

    x = np.linspace(-1,1,50)
    y = np.linspace(-1,1,50)

    X, Y = np.meshgrid(x,y)
    Z = np.sqrt(1-X**2)

    ax.plot_wireframe(X,Y,Z)
    ax.plot_wireframe(X,Y,-Z)

    ax.set_xbound(lower=-bound, upper=bound)
    ax.set_zbound(lower=-bound, upper=bound)
    ax.set_xlabel('x-axis')
    ax.set_ylabel('y-axis')
    ax.set_zlabel('z-axis')
    ax.set_xticklabels([])
    ax.set_yticklabels([])
    ax.set_zticklabels([])
    #ax.set_axis_off()

def interact_with_mesh_physical_model():
    """
    build an interactive bar for users to zoom in and out
    the mesh physical model.
    """
    from IPython.html.widgets import interact
    interact(show_mesh_physical_model, bound=(1,50))

class PlotManager():
    """
    Manage how to show the data generated by SodTube.
    Roughly speaking, it is a wrapper of matplotlib
    """
    def __init__(self):
        pass

    def plot_mesh(self, mesh):
        pass

    def plot_solution(self):
        pass

    def show_solution_comparison(self):
        plt.show()

    def get_plot_solutions_fig_rho(self,
                           solution_a,
                           solution_b,
                           solution_a_label="series 1",
                           solution_b_label="series 2"):
        return self.get_plot_solutions_fig(solution_a,
                                           solution_b,
                                           1,
                                           solution_a_label,
                                           solution_b_label)

    def get_plot_solutions_fig_v(self,
                           solution_a,
                           solution_b,
                           solution_a_label="series 1",
                           solution_b_label="series 2"):
        return self.get_plot_solutions_fig(solution_a,
                                           solution_b,
                                           2,
                                           solution_a_label,
                                           solution_b_label)

    def get_plot_solutions_fig_p(self,
                           solution_a,
                           solution_b,
                           solution_a_label="series 1",
                           solution_b_label="series 2"):
        return self.get_plot_solutions_fig(solution_a,
                                           solution_b,
                                           3,
                                           solution_a_label,
                                           solution_b_label)

    def get_plot_solutions_fig(self,
                       solution_a,
                       solution_b,
                       item,
                       solution_a_label="series 1",
                       solution_b_label="series 2"):
        ax = self.get_solution_value_list(solution_a, 0)
        ay = self.get_solution_value_list(solution_a, item)
        bx = self.get_solution_value_list(solution_b, 0)
        by = self.get_solution_value_list(solution_b, item)
        fig = plt.figure()
        ax1 = fig.add_subplot(111)
        ax1.set_title(solution_a_label + " v.s. " + solution_b_label)
        ax1.scatter(ax, ay, s=10, c='b', marker="s", label=solution_a_label)
        ax1.scatter(bx, by, s=10, c='r', marker="o", label=solution_b_label)
        plt.legend(loc='upper left')
        return fig

    def get_solution_value_list(self, solution, item):
        solution_item_list = []
        for i in solution:
            solution_item_list.append(i[item])
        return solution_item_list


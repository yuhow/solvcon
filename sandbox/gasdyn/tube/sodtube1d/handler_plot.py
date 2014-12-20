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

def show_mesh_physical_model(bound=1, tube_radius=10, show_diaphragm=False, show_mesh=False):
    """
    Show how 1D Sod tube may look like.
    TODO:
        1. make a interface for solution input
        2. do not run this function immediately when importing this model. Too slow.
    """
    from mpl_toolkits.mplot3d import axes3d
    import numpy as np
    # how many points you are going to use
    # to visualize the model alone each axis
    model_point_number = 30

    # change unit
    tube_radius = tube_radius*0.1

    fig = plt.figure()
    ax = axes3d.Axes3D(fig,azim=30,elev=30)

    # build the tube
    # generate mesh points
    x_tube = np.linspace(-tube_radius, tube_radius, model_point_number)
    y_tube = np.linspace(-1, 1, model_point_number)
    x_tube_mesh, y_tube_mesh = np.meshgrid(x_tube ,y_tube)
    # build the tube as a cylinder
    z_tube_mesh = np.sqrt(tube_radius**2 - x_tube_mesh**2)
    # show the tube as a wireframe
    ax.plot_wireframe(x_tube_mesh ,y_tube_mesh , z_tube_mesh)
    ax.plot_wireframe(x_tube_mesh ,y_tube_mesh ,-z_tube_mesh)

    if show_diaphragm:
        # build the diaphragm
        x_diaphragm = np.linspace(-tube_radius, tube_radius, model_point_number)
        z_diaphragm = np.linspace(-tube_radius, tube_radius, model_point_number)
        x_diaphragm_mesh, z_diaphragm_mesh = \
                np.meshgrid(x_diaphragm ,z_diaphragm)
        y_diaphragm_mesh = \
                np.zeros(shape=(model_point_number, model_point_number))
        #ax.plot_surface(x_diaphragm_mesh, y_diaphragm_mesh, z_diaphragm_mesh)
        ax.plot_wireframe(x_diaphragm_mesh,
                          y_diaphragm_mesh,
                          z_diaphragm_mesh,
                          color='red')

    if show_mesh:
        # mark the CESE mesh points
        x_solution = np.zeros(shape=1)
        y_solution = np.linspace(-1, 1, model_point_number)
        x_solution_mesh, y_solution_mesh = np.meshgrid(x_solution, y_solution)
        ax.scatter(x_solution_mesh,
                   y_solution_mesh,
                   x_solution_mesh,
                   color='green',
                   marker="o")

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
    interact(show_mesh_physical_model, bound=(1, 10), tube_radius=(1, 10))

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


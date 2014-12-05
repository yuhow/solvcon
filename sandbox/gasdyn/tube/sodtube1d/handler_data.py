#!/usr/bin/python
#
# handler_data.py
#
# Description:
#   helper functions to handle, caculate the solutions.
#

import sys
import scipy.optimize as so
import matplotlib.pyplot as plt

class DataManager():
    """
    Manage how to get extended information by input data.
    """
    def __init__(self):
        pass

    def get_errorNorm(self, solution_a, solution_b):
        return solution_errornorm

    def get_l2_norm(self, solution_a, solution_b, vi=1, filter=[]):
        """
        vi(vector_i)
            1:rho
            2:v
            3:p
        filter = [(x1,x2),(x3,x4),...], x1 < x2, x3 < x4
            when caculating l2 norm,
            data between x1 and x2, and x3 and x4,
            will be ignored.
            data on x1, x2, x3 and x4 will be adopted.
        """
        solution_deviation_square = self.get_deviation_square(solution_a, solution_b)
        l2_norm = 0
        sds = [] # deviation square of the solution

        # remove the deviation square value in the specific intervals
        for solution_dev_sqr_vector in solution_deviation_square:
            if len(filter) > 0:
                sdsv = solution_dev_sqr_vector[vi]
                for interval in filter:
                    if interval[0] < solution_dev_sqr_vector[0] < interval[1]:
                        sdsv = 0.
                sds.append(sdsv)
            else:
                sds.append(solution_dev_sqr_vector[vi])
        return sum(sds)

    def get_deviation(self,
                      solution_a,
                      solution_b,
                      delta_precision=0.0000000000001):
        """
        delta_precision: float,
            a number to claim two floating number value are equal.

        Compare the value of the status on each mesh points of solution_a.

        If the deviation of the mesh point coordinate value
        is smaller than delta_precision, they will be regarded as
        the same location.

        Note:
            only the mesh grid points of solution_a
            will be adopted.
        """

        if not (self.is_a_solution(solution_a) or
                self.is_a_solution(solution_b)):
            sys.exit()

        solution_deviation = []
        if len(solution_a) != len(solution_b):
            print("two solutions have different mesh point numbers!")
            solution_c = []
            for i in solution_a:
                for j in solution_b:
                    if abs(i[0] - j[0]) < delta_precision:
                        solution_c.append(j)
            solution_b = solution_c

        for i in range(len(solution_a)):
            if abs(solution_a[i][0] - solution_b[i][0]) < delta_precision:
                # 0.000000001 is a bad way
                # the mesh points are not the same
                # because they are not generated by the same
                # mesh generator,
                # and the float number will differ in the very small
                # order.
                x = solution_a[i][0]
                drho_abs = abs(solution_a[i][1] - solution_b[i][1])
                dv_abs = abs(solution_a[i][2] - solution_b[i][2])
                dp_abs = abs(solution_a[i][3] - solution_b[i][3])
                solution_deviation.append((x, drho_abs, dv_abs, dp_abs))
            else:
                print("two solutions have different mesh point!!")

        if len(solution_deviation) == len(solution_a):
            return solution_deviation
        else:
            print("sth. wrong when getting deviation!!")

    def get_deviation_percent(self, solution_a, solution_b):
        solution_deviation = self.get_deviation(solution_a, solution_b)
        solution_deviation_precent = []
        for i in range(len(solution_deviation)):
            solution_deviation_precent.append((solution_a[i][0],
                solution_deviation[i][1]/(solution_a[i][1]+1e-20),
                solution_deviation[i][2]/(solution_a[i][2]+1e-20),
                solution_deviation[i][3]/(solution_a[i][3]+1e-20)))
        return solution_deviation_precent

    def get_deviation_square(self, solution_a, solution_b):
        solution_deviation_square = []
        solution_deviation = self.get_deviation(solution_a, solution_b)
        for i in range(len(solution_deviation)):
            solution_deviation_square.append((
                solution_deviation[i][0],
                solution_deviation[i][1]*solution_deviation[i][1],
                solution_deviation[i][2]*solution_deviation[i][2],
                solution_deviation[i][3]*solution_deviation[i][3]))
        return solution_deviation_square

    def dump_solution(self, solution):
        print'x rho v p'
        for i in solution:
            print'%f %f %f %f' % (i[0], i[1], i[2], i[3])

    def is_identical_solution(self, solution_a, solution_b, dp=0.00000001):
        """
        Strictly to check two solutions. Regard them as the same
        solution if:

        1. their length is the same
        2. their deviation is smaller than dp, the delta precision.

        """

        if len(solution_a) != len(solution_b):
            return False

        solution_deviation = self.get_deviation(solution_a, solution_b)
        for i in solution_deviation:
            if not (i[1] < dp and i[2] < dp and i[3] < dp):
                return False

        print("Two solutions are identical.")
        return True

    def is_a_solution(self, solution):
        """
        a solution should be

        1. of the format
            [(x_1, rho_1, v_1, p_1), (x_2, rho_2, v_2, p_2), ...]
        2. x_1 < x_2 < x_3 ...etc., namely, monotonically increasing
        3. length should be larger than zero.

        This helper function will check the input has these features or not.

        return True if it is a such list/solution, otherwise, return false.

        """

        # format: solution is a list
        if not isinstance(solution, list):
            print("solution is not a list.")
            return False

        # format: tuple with 4 elements
        for i in solution:
            if not isinstance(i, tuple):
                print("solution element is not a tuple.")
                return False

        # x_1 < x_2 < x_3 ...etc.
        for i in xrange(len(solution)):
            if i+1 < len(solution):
                if not (solution[i][0] < solution[i+1][0]):
                    print("x is not monotonically increasing")
                    return False

        # length should be larger than zero.
        if len(solution) == 0:
            print("solution has nothing")
            return False

        return True

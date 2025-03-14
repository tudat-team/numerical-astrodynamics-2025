"""
Copyright (c) 2010-2020, Delft University of Technology
All rigths reserved

This file is part of the Tudat. Redistribution and use in source and
binary forms, with or without modification, are permitted exclusively
under the terms of the Modified BSD license. You should have received
a copy of the license with this file. If not, please or visit:
http://tudat.tudelft.nl/LICENSE.
"""

import numpy as np
from tudatpy import constants, numerical_simulation
from tudatpy.astro import element_conversion, two_body_dynamics
from tudatpy.data import save2txt
from tudatpy.interface import spice
from tudatpy.math import interpolators
from tudatpy.numerical_simulation import (
    environment,
    environment_setup,
    propagation_setup,
)

# Define departure/arrival epoch - in seconds since J2000
flyby_initial_time = ...

# student number: 1244779 --> 1244ABC
A = ...
B = ...
C = ...

orbit_initial_time = (
    35.4 * constants.JULIAN_YEAR
    + A * 7.0 * constants.JULIAN_DAY
    + B * constants.JULIAN_DAY
    + C * constants.JULIAN_DAY / 24.0
)

output_directory = "./SimulationOutput/"

central_bodies_per_phase = ["Callisto", "Ganymede"]
initial_times_per_phase = [flyby_initial_time, orbit_initial_time]
propagation_times_per_phase = [8.0 * 3600.0, 24.0 * 3600.0]

global_frame_origin = "Jupiter"
global_frame_orientation = "ECLIPJ2000"


################ HELPER FUNCTIONS: DO NOT MODIFY ########################################


# DO NOT MODIFY THIS FUNCTION (OR, DO SO AT YOUR OWN RISK)
def get_fixed_step_size_integrator_settings(time_step: float):
    """
    This function creates settings for a 7th order multi-stage fixed step-size integrator.
    It uses a variable-step size integrator, and forces it to a fixed step-size

    Parameters
    ----------
    time_step : float
        Fixed time step that the integrator is to take

    Return
    ------
    Integrator settings, defined as specified above and using the user-provided
    step size
    """

    # Define integrator settings, set tolerances to infinity, and initial, minimum and
    # maximum time steps to same value
    coefficient_set = propagation_setup.integrator.rkf_78
    integrator_settings = propagation_setup.integrator.runge_kutta_fixed_step_size(
        time_step, coefficient_set
    )

    return integrator_settings


# DO NOT MODIFY THIS FUNCTION (OR, DO SO AT YOUR OWN RISK)
def get_difference_wrt_kepler_orbit(
    state_history: dict, central_body_gravitational_parameter: float
):
    """
    This function takes a Cartesian state history (dict of time as key and state as value), and
    computes the difference of these Cartesian states w.r.t. an unperturbed orbit. The Keplerian
    elements of the unperturbed trajectory are taken from the first entry of the state_history input
    (converted to Keplerian elements)

    Parameters
    ----------
    state_history : dict
        Cartesian state history
    central_body_gravitational_parameter : float
        Gravitational parameter that is to be used for Cartesian<->Keplerian conversion

    Return
    ------
    Dictionary (time as key, Cartesian state difference as value) of difference of unperturbed trajectory
    (semi-analytically propagated) w.r.t. state_history, at the epochs defined in the state_history.
    """

    # Obtain initial Keplerian elements abd epoch from input
    initial_keplerian_elements = element_conversion.cartesian_to_keplerian(
        list(state_history.values())[0], central_body_gravitational_parameter
    )
    initial_time = list(state_history.keys())[0]

    # Iterate over all epochs, and compute state difference
    keplerian_solution_difference = dict()
    for epoch in state_history.keys():

        # Semi-analytically propagated Keplerian state to current epoch
        propagated_kepler_state = two_body_dynamics.propagate_kepler_orbit(
            initial_keplerian_elements,
            epoch - initial_time,
            central_body_gravitational_parameter,
        )

        # Converted propagated Keplerian state to Cartesian state
        propagated_cartesian_state = element_conversion.keplerian_to_cartesian(
            propagated_kepler_state, central_body_gravitational_parameter
        )

        # Compute difference w.r.t. Keplerian orbit
        keplerian_solution_difference[epoch] = (
            propagated_cartesian_state - state_history[epoch]
        )

    return keplerian_solution_difference


# DO NOT MODIFY THIS FUNCTION (OR, DO SO AT YOUR OWN RISK)
def get_difference_wrt_benchmarks(
    state_history: dict,
    benchmark_interpolator: interpolators.OneDimensionalInterpolatorVector,
):
    """
    This function takes a Cartesian state history (dict of time as key and state as value), and
    interpolator for a benchmark solution, and returns the difference opf the state history w.r.t.
    the benchmark

    Parameters
    ----------
    state_history : dict
        Cartesian state history
    benchmark_interpolator : OneDimensionalInterpolatorVector
        Interpolator that provides a benchmark (e.g. high-accuracy solution) for the dynamical model from which state_history is obtained

    Return
    ------
    Dictionary (time as key, Cartesian state difference as value) of difference of state_history w.r.t
    benchmark. NOTE: the interpolation at the boundaries of the domain may lead to invalid results, see
    interpolation API and/or user guide
    """

    benchmark_difference = dict()
    for epoch in state_history.keys():
        benchmark_difference[epoch] = state_history[
            epoch
        ] - benchmark_interpolator.interpolate(epoch)
    return benchmark_difference


def write_propagation_results_and_analytical_difference_to_file(
    dynamics_simulator: numerical_simulation.SingleArcSimulator,
    file_output_identifier: str,
    central_body_gravitational_parameter: float,
):
    """
    This function will write the results of a numerical propagation, as well as the difference w.r.t. a semi-
    analytically propagated Keplerian state history at the  same epochs, with the Kepler elements determined from the
    first entry in the state history. Two files are always written when calling this function (numerical state history,
    and its difference w.r.t. Keplerian state history). If any dependent variables are saved during the propagation,
    those are also saved to a file

    Parameters
    ----------
    dynamics_simulator : SingleArcSimulator
        Object that was used to propagate the dynamics, and which contains the numerical state and dependent variable results

    file_output_identifier : str
        Directory and file name that will be used to save the output data files

    central_body_gravitational_parameter : float
        Gravitational parameter that is to be used for Cartesian<->Keplerian conversion

    Files written
    -------------

    `<file_output_identifier>_numerical_states.dat`
    `<file_output_identifier>_dependent_variables.dat`
    `<file_output_identifier>_keplerian_difference.dat`

    Return
    ------
    None

    """

    state_history = dynamics_simulator.propagation_results.state_history
    dependent_variable_history = (
        dynamics_simulator.propagation_results.dependent_variable_history
    )

    keplerian_solution_difference = get_difference_wrt_kepler_orbit(
        state_history, central_body_gravitational_parameter
    )

    # Save numerical states
    save2txt(
        solution=state_history,
        filename=output_directory + file_output_identifier + "_numerical_states.dat",
        directory="./",
    )

    # Save Keplerian difference
    save2txt(
        solution=keplerian_solution_difference,
        filename=output_directory
        + file_output_identifier
        + "_keplerian_difference.dat",
        directory="./",
    )

    # Save dependent variables
    dependent_variables = dependent_variable_history
    if len(dependent_variables.keys()) > 0:
        save2txt(
            solution=dependent_variables,
            filename=output_directory
            + file_output_identifier
            + "_dependent_variables.dat",
            directory="./",
        )

    return


def write_propagation_results_and_benchmark_difference_to_file(
    dynamics_simulator: numerical_simulation.SingleArcSimulator,
    file_output_identifier: str,
    benchmark_interpolator: interpolators.OneDimensionalInterpolatorVector,
):
    """
    This function will write the results of a numerical propagation, as well as the difference w.r.t. a benchmark
    solution, represented by an interpolator. Two files are always written when calling this function (numerical state
    history,  and its difference w.r.t. the benchmark). If any dependent variables are saved during the propagation,
    those are also saved to a file

    Parameters
    ----------
    dynamics_simulator : SingleArcSimulator
        Object that was used to propagate the dynamics, and which contains the numerical state and dependent variable results
    file_output_identifier : str
        Directory and file name that will be used to save the output data files
    benchmark_interpolator : OneDimensionalInterpolatorVector
        Interpolator that provides a benchmark (e.g. high-accuracy solution) for the dynamical model from which state_history is obtained

    Files written
    -------------
    `<file_output_identifier>_numerical_states.dat`
    `<file_output_identifier>_dependent_variables.dat`
    `<file_output_identifier>_benchmark_difference.dat`

    Return
    ------
    None
    """

    numerical_solution = dynamics_simulator.propagation_results.state_history
    dependent_variable_solution = (
        dynamics_simulator.propagation_results.dependent_variable_history
    )

    # Compute difference w.r.t. benchmark
    benchmark_difference = get_difference_wrt_benchmarks(
        numerical_solution, benchmark_interpolator
    )

    # Save numerical states
    save2txt(
        solution=numerical_solution,
        filename=file_output_identifier + "_numerical_states.dat",
        directory=output_directory,
    )

    # Save benchmark difference
    save2txt(
        solution=benchmark_difference,
        filename=file_output_identifier + "_benchmark_difference.dat",
        directory=output_directory,
    )

    # Save dependent variables
    if len(dependent_variable_solution.keys()) > 0:
        save2txt(
            solution=dependent_variable_solution,
            filename=file_output_identifier + "_dependent_variables.dat",
            directory=output_directory,
        )


def write_propagation_results_to_file(
    dynamics_simulator: numerical_simulation.SingleArcSimulator,
    file_output_identifier: str,
):
    """
    This function will write the results of a numerical propagation. One file is always written when calling this function
    (numerical state history). If any dependent variables are saved during the propagation,
    those are also saved to a file

    Parameters
    ----------
    dynamics_simulator : SingleArcSimulator
        Object that was used to propagate the dynamics, and which contains the numerical state and dependent variable results
    file_output_identifier : str
        Directory and file name that will be used to save the output data files

    Files written
    -------------
    `<file_output_identifier>_numerical_states.dat`
    `<file_output_identifier>_dependent_variables.dat`

    Return
    ------
    None
    """

    numerical_solution = dynamics_simulator.propagation_results.state_history
    dependent_variable_solution = (
        dynamics_simulator.propagation_results.dependent_variable_history
    )

    # Save numerical states
    save2txt(
        solution=numerical_solution,
        filename=file_output_identifier + "_numerical_states.dat",
        directory=output_directory,
    )

    # Save dependent variables
    if len(dependent_variable_solution.keys()) > 0:
        save2txt(
            solution=dependent_variable_solution,
            filename=file_output_identifier + "_dependent_variables.dat",
            directory=output_directory,
        )


def create_bodies():
    """
    This function creates the environment (as a system of bodies) used for the simulation

    Parameters
    ----------
    None

    Return
    ------
    Set of bodies, stored in a SystemOfBodies, that comprises the environment
    """

    bodies_to_create = [
        "Jupiter",
        "Ganymede",
        "Callisto",
        "Io",
        "Europa",
        "Sun",
        "Saturn",
    ]

    body_settings = environment_setup.get_default_body_settings(
        bodies_to_create, global_frame_origin, global_frame_orientation
    )

    # Ganymede Exponential Atmosphere
    density_scale_height = 40.0e3
    density_at_zero_altitude = 2.0e-9
    body_settings.get("Ganymede").atmosphere_settings = (
        environment_setup.atmosphere.exponential(
            density_scale_height, density_at_zero_altitude
        )
    )

    # Create vehicle object
    body_settings.add_empty_settings("JUICE")
    body_settings.get("JUICE").constant_mass = 2000.0

    spacecraft_reference_area = 100

    # Create aerodynamic coefficients interface
    drag_coefficient = 1.2
    aero_coefficient_settings = environment_setup.aerodynamic_coefficients.constant(
        spacecraft_reference_area, [drag_coefficient, 0, 0]
    )
    body_settings.get("JUICE").aerodynamic_coefficient_settings = (
        aero_coefficient_settings
    )

    # Add radiation pressure interface to vehicle
    radiation_pressure_coefficient = 1.2
    occulting_bodies_dict = dict()
    occulting_bodies_dict["Sun"] = ["Ganymede"]
    vehicle_target_settings = (
        environment_setup.radiation_pressure.cannonball_radiation_target(
            spacecraft_reference_area,
            radiation_pressure_coefficient,
            occulting_bodies_dict,
        )
    )
    body_settings.get("JUICE").radiation_pressure_target_settings = (
        vehicle_target_settings
    )

    bodies = environment_setup.create_system_of_bodies(body_settings)

    return bodies


################ HELPER FUNCTIONS: MODIFY ########################################


def get_unperturbed_accelerations(
    central_body: str, bodies: environment.SystemOfBodies
):
    """
    Creates the acceleration models  for an unperturbed trajectory. NOTE: this function should return the correct
    accelerations for both the GCO500 and flyby propagation

    Parameters
    ----------
    central_body : Body w.r.t. which the state of JUICE is propagated
    bodies : Body objects defining the physical simulation environment

    Return
    ------
    Acceleration models for the perturbed trajectory.
    """

    # Create acceleration models.
    acceleration_models = ...

    return acceleration_models


def get_perturbed_accelerations(central_body: str, bodies: environment.SystemOfBodies):
    """
    Creates the acceleration models  for a perturbed trajectory. NOTE: this function should return the correct
    accelerations for both the GCO500 and flyby propagation

    Parameters
    ----------
    central_body : Body w.r.t. which the state of JUICE is propagated
    bodies : Body objects defining the physical simulation environment

    Return
    ------
    Acceleration models for the perturbed trajectory.
    """

    # Create acceleration models.
    acceleration_models = ...

    return acceleration_models

#Code written by Piotr Karpala, some of the coeffiecient data displayed here
#is also available as part of the AI Search Index. 
# Not integrated in solution yet, use as reference.
#----------------------------------------------------------------------------------------------------
from opentelemetry.trace import get_tracer
tracer = get_tracer(__name__)

# Calculate the energy (E) for Memory in kWh given an energy coefficient for memory utilization.
def calculate_E_memory(memory_coef: float) -> float:
    # Formula: E_memory = 0.38 * energy coefficient for memory utilization (result in kWh)
    return 0.38 * memory_coef

# Calculate the energy (E) for CPU in kWh given an energy coefficient for CPU utilization.
def calculate_E_cpu(cpu_coef: float) -> float:
    # Formula: E_cpu = 270 * energy coefficient for CPU utilization (result in kWh)
    return 270 * cpu_coef


# Sum the energy consumption for CPU and Memory.
def calculate_total_E(memory_coef: float, cpu_coef: float) -> float:
    return calculate_E_memory(memory_coef) + calculate_E_cpu(cpu_coef)

# Calculate the embodied emissions (M) in gCO2eq from the compute instance's embodied coefficients.
def calculate_M(
    embodied_coef: float,
    instance_memory: float,
    platform_memory: float,
    instance_cpu: float,
    platform_cpu: float,
) -> float:
    # Calculate the fraction of 1 hour to a 3-year lifecycle (hours per 3 years = 3 * 365 * 24)
    lifecycle_hours = 3 * 365 * 24
    factor = 1 / lifecycle_hours
    # M is the sum of the embodied emissions for memory and CPU
    M_memory = embodied_coef * factor * (instance_memory / platform_memory)
    M_cpu = embodied_coef * factor * (instance_cpu / platform_cpu)
    return M_memory + M_cpu


def get_energy_coefficient(utilization: float) -> float:
    """
    Returns the energy coefficient based on the utilization percentage using ranges.

    Mapping:
        [0, 2.5)         -> 0.12
        [2.5, 5)         -> 0.17
        [5, 7.5)         -> 0.22
        [7.5, 10)        -> 0.27
        [10, 20)         -> 0.32
        [20, 30)         -> 0.4275
        [30, 40)         -> 0.535
        [40, 50)         -> 0.6425
        [50, 60)         -> 0.75
        [60, 70)         -> 0.804
        [70, 80)         -> 0.858
        [80, 90)         -> 0.912
        [90, 100]        -> 1.02
    """
    if utilization < 0 or utilization > 100:
        raise ValueError("Utilization must be between 0 and 100.")

    match utilization:
        case u if 0 <= u < 2.5:
            return 0.12
        case u if 2.5 <= u < 5:
            return 0.17
        case u if 5 <= u < 7.5:
            return 0.22
        case u if 7.5 <= u < 10:
            return 0.27
        case u if 10 <= u < 20:
            return 0.32
        case u if 20 <= u < 30:
            return 0.4275
        case u if 30 <= u < 40:
            return 0.535
        case u if 40 <= u < 50:
            return 0.6425
        case u if 50 <= u < 60:
            return 0.75
        case u if 60 <= u < 70:
            return 0.804
        case u if 70 <= u < 80:
            return 0.858
        case u if 80 <= u < 90:
            return 0.912
        case u if 90 <= u <= 100:
            return 1.02



@tracer.start_as_current_span("calculate_SCI")  # type: ignore
def calculate_SCI(
    memory_utilization: float,
    cpu_utilization: float,
    grid_intensity: float,
    embodied_coef: float,
    instance_memory: float,
    platform_memory: float,
    instance_cpu: float,
    platform_cpu: float,
) -> float:
    """
    Calculate the Software Carbon Intensity (SCI) for a service in gCO2eq per hour.

    SCI is computed with the formula:
        SCI = (E * I) + M,
    where:
        - E is the total energy consumption (in kWh).
          * For Memory, E_memory = 0.38 * memory_coef, where memory_coef is derived from memory utilization.
          * For CPU,  E_cpu    = 270 * cpu_coef, where cpu_coef is derived from CPU utilization.
          * Total E = E_memory + E_cpu.

        - I is the grid carbon intensity (in gCO2eq/kWh).

        - M represents the embodied emissions (in gCO2eq) calculated as:
              M = (embodied_coef * factor * (instance_memory / platform_memory)) +
                  (embodied_coef * factor * (instance_cpu / platform_cpu))
          where factor is (1 hour / total hours in a 3-year lifecycle), calculated as:
              factor = 1 / (3 * 365 * 24).
    
    :param memory_utilization: The memory utilization percentage (0-100) used to derive memory_coef.
    :type memory_utilization: float
    :param cpu_utilization: The CPU utilization percentage (0-100) used to derive cpu_coef.
    :type cpu_utilization: float
    :param grid_intensity: The grid carbon intensity in gCO2eq per kWh.
    :type grid_intensity: float
    :param embodied_coef: The compute instance's total embodied emissions coefficient. Cannot be zero.
    :type embodied_coef: float
    :param instance_memory: The memory allocated to the instance (e.g., in GB).
    :type instance_memory: float
    :param platform_memory: The baseline platform memory (e.g., in GB).
    :type platform_memory: float
    :param instance_cpu: The CPU allocated to the instance (e.g., number of vCPUs).
    :type instance_cpu: float
    :param platform_cpu: The baseline platform CPU (e.g., number of vCPUs).
    :type platform_cpu: float

    :return: The calculated SCI in gCO2eq per hour.
    :rtype: float
    """
    if (embodied_coef <= 0):
        raise ValueError("The embodied coefficient must be greater than zero.")

    # Derive coefficients from utilizations
    memory_coef = get_energy_coefficient(memory_utilization)
    cpu_coef = get_energy_coefficient(cpu_utilization)

    # Compute energy consumption in kWh for memory and CPU
    E_memory = 0.38 * memory_coef
    E_cpu = 270 * cpu_coef
    E = E_memory + E_cpu

    # Calculate embodied emissions
    lifecycle_hours = 3 * 365 * 24  # Total hours in 3 years
    factor = 1 / lifecycle_hours
    M_memory = embodied_coef * factor * (instance_memory / platform_memory)
    M_cpu = embodied_coef * factor * (instance_cpu / platform_cpu)
    M = M_memory + M_cpu

    # Return the SCI: energy impact (E * grid intensity) plus embodied emissions (M)
    return (E * grid_intensity) + M


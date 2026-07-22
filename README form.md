# READ ME

**TO USE PRIVATE FUNCTION THE ``PRIVATE MODULES`` MUST BE LOCATED IN**

        oriom\
           |
           domain\
           core\
              |
              functions\
                 |
                 private\
                    |
                    private_module_1.py
                    private_module_2.py
            inputs\

The ``Private modules`` will consent to:
- Reuse old simulation
- Evaluate Vessel statistical chart time, vessel reutilization and contract expiration
- ST O&M with forecast API
- Additional KPI of vessel available

If no ``Private modules`` are available, the simulation will simply not take into consideration the above funcionalities

## Excel Input General informations

This file give informations and assist the user to better understand how to compile the input excel form file for ORIOM.

Informations are divided for each sheet of the excel form
---------------------------------------

# ⚙️**INSTALLATION MODE**

To use ORIOM in **Installation Mode**, the workflow is based on:

- creation of pre-existing failures representing installation demand and reuse such failure in the simulation

        
- execution through deferred corrective (installation) operations that creates installation campaign with same starting month
- Manage order of installation using ``preferred_day`` in *Failure* attribute
- Deactivate ``ENERGY_AVAILABILITY_CALCULATION`` from *Config* attribure


Each failure corresponds to a **component to be installed** or an **installation campaign**, depending on the chosen configuration.


##  Core Concept

The installation process is modeled as follows:

1. **Failures creation**
   - Each failure represents a component that must be installed.
   - The number of failures corresponds to the number of devices to install (or grouped campaigns).

    Example of failure creation:

    Two years of campaign with 2 differed opeartion installation, 3 type of components to install (represented as failure)

        datetime	    |id	                |maintenance_strategy	|operation_triggered	|preferred_month
        1/1/2006 9:00	|ofw_fail_type_1	|specific month	        |ofw_op002	            |6
        1/1/2006 9:00	|ofw_fail_type_1	|specific month	        |ofw_op002	            |6
        1/1/2006 9:00	|ofw_fail_type_3	|specific month	        |ofw_op003	            |6
        1/1/2006 9:00	|ofw_fail_type_1	|specific month	        |ofw_op002	            |6
        1/1/2006 9:00	|ofw_fail_type_2	|specific month	        |ofw_op002	            |6
        1/1/2006 9:00	|ofw_fail_type_2	|specific month	        |ofw_op002	            |6
        1/1/2006 9:00	|ofw_fail_type_3	|specific month	        |ofw_op003	            |6
        1/1/2007 9:00	|ofw_fail_type_3	|specific month	        |ofw_op003	            |6
        1/1/2007 9:00	|ofw_fail_type_2	|specific month	        |ofw_op002	            |6
        1/1/2007 9:00	|ofw_fail_type_1	|specific month	        |ofw_op002	            |6
        1/1/2007 9:00	|ofw_fail_type_2	|specific month	        |ofw_op002	            |6
        1/1/2007 9:00	|ofw_fail_type_3	|specific month	        |ofw_op003	            |6

2. **Deferred operations**
   - Each failure is resolved through an installation operation.
   - The operation defines the installation activity and scheduling.

3. **Scheduling**
   - Failures are deferred to specific months.
   - Installation is executed progressively according to the defined campaign strategy.

   **SEE INSTALLATION STRATEGY**

## Installation Strategies

### a) Example A — Single Device per Trip

**Scenario:**
- 5 devices to install
- 1 device installed per trip
- vessel returns to port after each installation

**Implementation:**
```
1. Create 5 failures (one per device)
2. Define an operation to fix each failure
3. Each operation consists of:
   - install 1 device
   - return to port
4. Defer each operation to a target month
```
**Behavior:**
- Devices are installed sequentially
- Each installation requires a separate trip

---

### b) Example B — Batch Installation (All Devices in One Trip)

**Scenario:**
- 5 devices to install
- 5 devices installed in a single trip
- vessel returns to port once

**Implementation:**
```
1. Create 1 failure (representing the full campaign)
2. Define a single operation to install all devices
3. Operation consists of:
   - install 5 devices
   - return to port
4. Defer operation to a target month
```
**Behavior:**
- All devices are installed consecutively
- No intermediate return to port

---

### c) Example C — Partial Batch Installation

**Scenario:**
- 10 devices to install
- batches of 5 devices per trip

**Implementation:**
```
1. Create 2 failures (each representing a batch of 5 devices)
2. Define operations to install 5 devices per campaign
3. Each operation consists of:
   - install 5 devices
   - return to port
4. Defer operations within the same month or scheduled sequence
```
**Behavior:**
- First batch of 5 devices installed consecutively
- Second batch starts after the first campaign completes

    ## ⚠️ Edge Case Handling

    If the last operation contains fewer devices than the batch size:

    - create a **separate operation** for the remaining devices

    - such operation must by with consecutive to the batch operations considering lexicografic order, so if Batch_operation.id == 'op_001' the separate operation must be with an id 'op_002' or higher in order to be conducted as last operation of the campaign

    - schedule it in the same month with a consecutive day respect to the previous ones

    - ensure sequential execution on consecutive days
    
    - complete the installation campaign without loss of remaining units
---------------------------------------
# 🔧 **O&M MODE**

## HARD CODED PARAMETERS

- ### TO CONSIDER DIFFERENT CHANGE IN DISTANCE DUE TO CLOSER PORT FOR CERTAIN TYPE OF VESSEL
    - **diff_distance**: boolean value to say that there are vessel that are considered with other port distance

    - **distance from coast**: The distance might change for vessel type (port facilities differ)

    - **VESSEL_DIST_REDUCED_LIST**: List of vessel type that will have different distances from port as can use a closer port that have reduced port characteristic


- ### OTHER
    - **KM_MOTHER_VESSEL**: The distance on which evaluate the transit when a mother vessel is used. Might change for vessel mother

    - **fuel to add**: Dictionary of vessel id and **YEARLY FUEL COST** cost of fuel to add due to reduced travels (overnight stay at site). The cost will be added only at the averaged results

    - **mobilisation to add**: Dictionary of vessel id and **YEARLT MOBILISATION COST** to add. The cost will be added only at the averaged results

    - **TIME_FAIL_OP_IMMEDIATELY**: This value set a reaction time between a failure and the correspondent operation to plan. To be set in **HOURS**. Works only for IMMEDIATE CORRECTION


## PRIVATE FUNCTIONS
To use Private functions:

Copy and paste the folder with the private modules inside:

        .\oriom\src\core\functions\private

If private functions are not found it will not be possible:
- Consider statistical chart duration of the vessels and recall-reuse mobilitated vessels
- Reuse previous simulations. All data must be recalculated
- Reduced KPI Vessels Insight
- It will not be available to use ORIOM as ShortTerm O&M Simulator

## GEN_INPUTS
- **Use previous run directory**: Insert the path of the previous directory to reuse
    
    If reuse a old simulation, remove from the reuse folder the file to integrate eventuale changes in the files:

        inputs_gen
        inputs_stats
        inputs_tseries
        inputs_cost
        wtg
        timeseries

- **Use previous TimeSeries Analysis**: Clarify if reuse the past timeseries analysis (T/F)

- **Number of runs with same TimeSeries Analysis**: Insert number of simulation to conduct

- **Overwrite previous run directory**: Overwrite the previous directory

- **Consider double shifts**: If consider Day and Night shifts (T/F)

- **Log events file**: Insert the path of the previous "log_events" file directory to reuse

- **Failure events file**: Insert the path of the previous "failure" file directory to reuse

## TSA_inputs

- **Failure scenario selection**:

    This parameter indicate which scenario probability to coniseder when creating failures 

- **The Merge operation vessel**:

    This parameter will set the vessels that will be merged together along the immediate corrective operations that will occurs in the same day.

    **ADVICE merge only CTV**

    This merging strategy can be only done for immediate correction that can drop off personnel. If the vessel is required do not merge

    It is needed to be put as a list of vessels separated by a comma if this functions want to be used. The name used for the vessels must coincide with the "type" attribute in the GEN_Vessels

        Example:
        Merge operation vessel: ctv, sov, juv

- **Metocean files**:
    Metocean files must have the following columns:

            datetime: timestep in DD%MM%YYYY : HH:MM:SS
            hs: Significant Wave variable of the timestep in [m]
            tp: Peak Period variable of the timestep in [s]
            ws: Wind speed variable of the timestep [m/s]
            cs: Current speed variable of the timestep in [m/s]
            


- **Additional Metocean tow file**:

    Addiational metocean tow file will be used in towing operation to consider more metocean location for the towing activities. Such metocean will only be used along the towin (not transit without the device) and it consider the time to reach the point assigned. It need to be coupled with the distance to the site, once the device it is at the middle of the towing from the point A to B, it will start to consider the point B metocean

- **Additional metocean Port file**:
    Addiational metocean port file will be used in port operation to consider the metocean location of the port. If such is not defined same metocean file of the site will be used, forcing Hs, Tp and current velocity as considering protected aread.

- **Energy losses file location**:

    These power losses will be evaluated and applied to the system without considering the operation of the farm under failures or operation activities. Losses are estimated on the full operation of the system. Shutdown of the are not then considered. 
    
    -    **Wake energy losses**:

            This parameter should point to the csv file that define wake energy losses. Wind speed must be the influencing variable, Power losses values of system must be defined as percentage from 0 to 1 and must define the amount of percentage of loss. If not defined, no wake losses will be considered.

    -    **Electric energy losses**:

            This parameter should point to the csv file that define electric energy losses. Power production must be the influencing variable, Power losses values of system must be defined as percentage from 0 to 1 and must define the amount of percentage of loss. If not defined, no electric losses will be considered.


## SA_inputs


- For Time series analysis the start year of the project have to be the start year of the metocean data available


- **Failure rate sensitivity** Is a sensitivity factor to increase or reduce all the failures. Default to 1 or empty

## Gen_PV

- **Layout**: Layout 2 has the layout implemented till the inverter level. Lower component are considered for energy losses evaluation and corrections
    - **NODE/EDGE**: in failure sheet the components level must be:

            a
            b
            c
            d
            .
            .
            .
            .

    - The case on which a nÂº of pv module fail in the same string and cause a string shutdown is not considered in the energy availability. Anyway if it happens it is seen in the logging file. There it say how many time it happen in the lifetime of the farm

## LAYOUT

Create documentation to check which layout are availables

- **Layout_string_disconnection**:
Does not allow for electrical continuity on the array if a device is TOWED. If set to True, a tow device do disconnect all the consecutive devices.


## VESSEL

- **Charter**: put values equal to zero only if you only have long term vessel. No short term vessel will be rented, ideal for inspections or deferred maintenace that do use a vessel only if previous shift is completed. Usually consider both (long_term and short term) so fill both short and long term charts.
Example of not consider short_term: particular vessel charted that should not be used with more than n_vessel long term chart in the same time

- **n_vessel**: This value will indicate the maximum number of vessel that will be considered in deferred operations and in inspection at port

- **Fuel_cons**: Do never put the consumptions equal to zero if you do not want to evaluate the fuel consumptions apart.

    -   **Fuel Consumption must be in l/h!** If you want to have them included in the costs calculations insert specifics values or leave it empty.
    -   If the transit is particularly calculated (example a vessel that stay overnight), put fuel_cons_transit = 0 and in postprocess add the time and cost of the transit.


- **Annual contract** If is monthly charts multiply the monthly cost with the month of contract. Here must be present the yearly cost


- **Months contract** List of months on which the monthly contract are applied


- **monthly_contract_cost** Monthly cost of the vessel contracted for 1 month


- **n_ves_annual_contract** Number of vessel that are yearly contracted


- **n_ves_monthly_contract** Number of vessel that are monthly contracted


- **n_ves_monthly_contract** Number of vessel that are monthly contracted


- **mother_vessel** boolean that indicate if the vessel will be used as mother vessel from other operation. Put it TRUE if you are usign such vessel only for deferred operation or inspections

- **remote reboot** can be simulated. For such failure create a vessel with id v999 and an extremly high speed transit. Assign it to an operation and failure


## MOTHER VESSEL


- mother Vessel should always be the second vessel of the operations vessel_2. Its mobilisation is calculated after log_events_calculation by a specific function. It calculate only one mobilisation so if more are required add externally

- The daily cost of mother vessel are calculated. function reduce the cost calculated of the SOV in case more mother vessel are encountered. This is to reduce the sovraposition of mother vessels

- If the mother vessel is used for inspection campaign, to consider inspection campaign to be done together all the inspections must have the same month of start, otherwise they will be considered in another campaign.


## Technologies definitions


- **power curve file**: must indicate the path and the file name of the power file of the device


the devisce at port and stored at port must be present (if not know = 0)

## Failure File
Check the layout level of nodes and edges to know which failures and at which level must be defined

- **op_trigger**: Each failure must be connected to a operation

- **number_of_element_farm**: Is the number of element present that will be affected by the failure

- **level_failure**: Is the level of the component that is failing. Levels are connected to the layout choosen of the technology. Important for energy calculations.


- **probability_failure**: Is the failure rate expressed in failure/year

- **avoid_month_correction**: If the failure Strategy is immediatly it can be avoided to operate in specific defined months. The failure that will occure in these periods will be considered as deferred operation in the first possible month available

- **bath_tub**: Indicates if this failure will be have a bathtub curve failure characterization

- **fail_variation**: Indicates if this failure will have a failure variation (usefull for sensitivity analysis)

- **perc_shutdown**: Indicates the probability that a failure will lead to a shutdown of a component (if 10% one failure each 10 will lead to a shutdown)

⚠️  **SPECIFIC USE OF FAILURES**
- **Name**: 
    -   In FOPV the layout is setted with inverter resolution. To count failure on "device" or "string" level add "_device" and "_string" in the name of the failure to consider them. The level must be 'device' and 'array_cable' relatively. Event if the layout 4 of OPV do not take into consideration these levels, the availability algorithm will acocunt the reduction of the availability due to solar module and string failure. An eccess of module broken in a single line will cause a shutdown of the entire line

- **level_failure**: 
    - For failure regarding last device of the string it could require specific different operation specially regarding towing operation with additional operation. If so such specific additional operation must be defined in ``Operation Major``

## ALL OPERATIONS (INSPECTION & CORRECTION)

- Do not put in the same operations in vessel 1 & vessel 2 the same vessel type


- Each major and minor corrective operation must have a failure that triggers it.

- Each operation should start with the same prefix:
    - for floating solar:
    ```
    opv
    ```
    - for wave converter:
    ```
    owc
    ```
    - for offshore wind:
    ```
    ofw
    ```
    - Offshore Common Events (TO BE AVOIDED AS NOT IMPLEMENTED):
    ```
    oce
    ```

- The ROV must be present in the first vessel called (vessel_1) otherwhise its cost will not be shown in the economic results


- Operation id or operation name cannot have "tow" except for the towing operations


- The vessel_1 must be the vessel with a mobilisation time, the mobilisation for vessel_2 is not implemented so usually put a vessel with no mobilisation


- **mother Vessel**:

    - should always be the second vessel of the operations vessel_2.

    - Its mobilisation is calculated after log_events_calculation by a specific function. It calculate only one mobilisation so if more are required add externally.

    - If a mother vessel is used for inspection campaign, to consider inspection campaign to be done together all the inspections must have the same month of start, otherwise they will be considered in another campaign.

    - Only use a mother vessel for corrective operations if the failure to correct are deferred



## ALL INSPECTION & MINOR CORRECTION


- **double shift**: The double shift parameters avoid the use of night hours to conduct the shift. Is similar to the ligh restriction. To work along the night day restriction must be empty or false and the double shift must be True

- **other cost & part cost**: This value must be the total of the device inspected if is an ispection, cannot be the amount of part and other cost of sigle device

## In Inspection Site


- For the inspections that require a vessel to be conducted (example export cable inspection) the duration of the inspection must be the total time of the inspection for each  component and the component inspected must be set from 0 to 1 otherwise consider possibility to drop of personnel if rov are not used


- Actually the working shift is considering more rotation of inspection after the first devices inspected. If is possible consider that after one device the crew go to the next device to inspect


- **On rov_drone** column leave empty if no rov are used


- **Day_start** if the inpection is conducted in the same month of another inspection/deferred opeartions, use this value to decide when to schedule the day of inspection. Try to not sovrappose the inspections


- **mother Vessel**:


- **Part Cost**: insert the total part cost of all the inspection, part cost * n_dev_inspected


- **mother vessel**:
    if a mother vessel is used for inspection campaign, to consider inspection campaign to be done together consecutevly:

    - mother vessel should always be the vessel_2 of the operations. Its mobilisation is calculated by a specific function after the end of log_events_calculation. It calculate only one mobilisation per year, so if more are required add need to be added externally.

    - all the inspections to join in same campaign must have the same month and day to start (avoid to put different inspection campaign to be conducted separetly in the same month without specify the day)

    - if different month and day to start, the inspections will be considered in another campaign

    - More than 1 months for inspection campaing is allowed. If requested more than 1 periodicity of such inspecion, the code divide and create 2 campaign

    - Be aware of not create too many inspection campaign for the same inspection, it might create confusion on recognising the campaign selsected

    - Do not create different campaign of the same inspection in the same month



## Corrective MAJOR


- rov_drone column leave empty if no rov are used
- If a drone is used the operation cannot be merged
- An operation that need tow cannot be done with deferred operation, it must be immediate. Otherwise implement an inspection


## Operation TOW

- Tow Operation must be inserted as:
    Technology prefix_action of tow in "id"
    They cannot be changed. For different tech tow use other prefix (ofw,owc,opv)

    The actions of tow are the following:

    - redeploy
    ```
    must contain "deplo" and "tow" int the id_short and *NOT* "deplo"

    must contain "tow" in the name of the activities defined that will tow the device at port
    ```
    - removal
    ```
    must contain "remov" and "tow" int the id_short and *NOT* "deplo"

    must contain "tow" in the name of the activities defined that will tow the device at port
    ```

    - redeploy_removal
    ```
    must contain "remov" and "tow" and "deplo" int the id_short

    must contain "tow" in the name of the activities defined that will tow the device at port
    ```

    Example:
    ```
    ofw_redeploy        "id of tow to site operation"
    ```

- Additional Operations: <br>

    creates an operation required before the tow operation (if removal) or after (if redeploy) to disconnect full string

    - The additional operation must be defined in ``Operation Major``. 
    
        ⚠️ For last device of the string could reqiured a shorter operation due to a reduce amout of cable to disconnect. Such reduced operation must be defined in ``Operation Major`` **WITH THE SAME ID of the normal operation + '_last_string_device'**

        Example:

                Normal cable disconnection: id = ´´ofw_mj1´´
                Last device cable disconnection: id = ´´ofw_mj1_last_string_device´´

        Such use will be managed by the Failure object that should have as level_failure == ``last_string_device``

- String disconnection: <br>

    If additional operations is present and disconnection = TRUE, shutdown the entire string of the device that is towed for the whole duration of the additional operation

- Recommissioning: <br>

    If additional operations is present that shutdown the entire string of the device a recommissioning period can be added. This must be int value and represent the hours of recommision to consider. In Additional Operations activity for TTS add recommissioning activity AFTER the TRANSIT to port as LOCATION == port.

        Example "RECOMMISSION ACTIVITY" in last TTS additional operation:

        DESCR             VALUES
        id	            OWT_MJ2_8
        op_type	        CorrectiveMajor
        op	            ofw_MJ2
        name	            Recommissioning
        location	        port
        wtg_shutdown_dur	TRUE
        duration	        24
        hs	            3

- Combination available for TTP 

    To use recommissioning or string disconnection it must be present an additional operation

    additional_operation = A, string_disconnection = B,  Layout_string_disconnection = C (if a device TOWED no electrical continuity), Recommissioning = D
    
    
           A      B      C      D

        (False, False, False, False),

        (False, False, True,  False),

        (True,  False, False, False)

        (True,  True,  False, False)

        (True,  True,  True,  False)

        (True,  False, True,  True )

        (True,  False, True,  False)

        (True,  False, False, True )
        
        (True,  True,  False, True )

        (True,  True,  True,  True )



- The chart time for Towing operations works as:
    - For additional operation removal:
        - If the mobilisation of the vessel is higher than the operation at port, add the towing operational duration to the statistical chart time
    - For Tow removal:
        - If the mobilisation of the vessel is higher than the operation at port, double the duration of tow to the statistical chart time
    - Other future chart for TTP operations are simply evaluated. If previous contract stipulated cover these lasts operation, the vessel will be reused (PRIVATE FUNCTIONALITIES)

## ACTIVITIES
- More detailed are the activities and better it is, add more activities as refined as possible for long operations. One is a part of the O&M on which the work can be stopped and taken back in another day (when is decided by MAX HOUR BETWEEN ACTIVITY).


- The tech_shutdown_dur (wtg_shutdown_dur	wec_shutdown_dur	pv_shutdown_dur) must be a boolean


- If towing operation with redeploy_removal_tow and the activity must define transit to one device and another in name must be contained "transit" and "next" i.e. ACT1 name: "Transit to next device"

- Avoid to add port activities at the end of the activities if they are not recommissioning.

## KPIs OUTPUT Overview

- **TOTAL_COST_AVERAGED**:
    -   Direct cost comprehend all the farm cost except insurance cost
    -   Indirect cost comprehend insurance cost
    -   Vessel cost comprehend Charting cost and fuel cost
    -   Other costs comprehend other costs of operations, daily port cost of operations, annual port costs, tech annual costs


- **TOTAL_YEARLY_COST_AVERAGED**:
    -   Direct cost comprehend all the cost related to the vessel, represent the yearly lifetime_direct_costs of the vessel (part, other, rov, mobilisation, chart, fuel, tech costs)
    -   fixed_annual_cost cost comprehend insurance cost, annual tech costs and port costs




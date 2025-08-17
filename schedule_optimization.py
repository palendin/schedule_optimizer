import matplotlib.pyplot as plt
import matplotlib.patches as mpatches

# Step order and durations
step_order = ['A', 'B', 'C', 'D', 'E', 'F']
steps = {
    'A': {'setup': 10, 'operation': 5,  'cleaning': 2,  'tanks': ['Tank1', 'Tank2']},
    'B': {'setup': 3, 'operation': 10, 'cleaning': 1.5,'tanks': ['Tank3', 'Tank4']},
    'C': {'setup': 5, 'operation': 14, 'cleaning': 2,  'tanks': ['Tank5', 'Tank6']},
    'D': {'setup': 2, 'operation': 8,  'cleaning': 1,  'tanks': ['Tank1', 'Tank2']},
    'E': {'setup': 3, 'operation': 9,  'cleaning': 1.5,'tanks': ['Tank3', 'Tank4']},
    'F': {'setup': 4, 'operation': 11, 'cleaning': 2,  'tanks': ['Tank5', 'Tank6']},
}

step_durations = {step: values['setup'] + values['operation'] + values['cleaning'] for step, values in steps.items()}
# find max step duration
min_step_duration = min(step_durations.values())

# Tank cleaning durations
tank_cleaning_time = {
    'Tank1': 3, 'Tank2': 2.5, 'Tank3': 2, 'Tank4': 2, 'Tank5': 3, 'Tank6': 2.5
}


####################################### need modification ########################################################
# num of cycles should be calculated based on the gap days between each bioreactor run. for example, if gap day is 14, then need to fit x number of cycles within the 14 days
print(min_step_duration)
bioreactor_days = 14 # days
num_of_bioreactors = 3
cadence = int(bioreactor_days/num_of_bioreactors)
print(f"Cadence (days per bioreactor): {cadence}")
num_cycles = int(cadence*24/min_step_duration)  # number of cycles needed to fit all steps within the bioreactor days
print(f"max of cycles for every step: {num_cycles}")
###############################################################################################


schedule = []

# Track last cleaning end per step across cycles
last_clean_end = {s: 0.0 for s in step_order}

for cycle in range(1, num_cycles + 1):
    # Step 1: compute ideal pipeline times assuming unlimited resources
    pipeline_times = {}
    prev_op_end = 0
    for i, step in enumerate(step_order):
        info = steps[step]
        setup_start = prev_op_end - info['setup']  # this will make op start start of next step align with op end of previous step
        setup_end = setup_start + info['setup']
        op_start = setup_end
        op_end = op_start + info['operation']
        clean_start = op_end
        clean_end = clean_start + info['cleaning']
        pipeline_times[step] = {
            'setup_start': setup_start,
            'setup_end': setup_end,
            'op_start': op_start,
            'op_end': op_end,
            'clean_start': clean_start,
            'clean_end': clean_end
        }
        prev_op_end = op_end  # next step alignment

    # Step 2: find max shift needed to satisfy resource constraints (previous cycle cleaning end for any step)
    shift = 0
    for step in step_order:
        required_shift = max(0, last_clean_end[step] - pipeline_times[step]['setup_start']) # calculate how much to shift the entire cycle so no step starts before its previous cleaning ends. So if setup_start was -10, and shift was 10 or more, the final setup_start becomes 0 or positive.
        if required_shift > shift: # If the step is starting after its last cleaning ended, no delay is needed → required_shift = 0. 
                                   # If the step is starting before its last cleaning ended, it needs to be delayed → required_shift > 0.
            shift = required_shift

    # Step 3: schedule tasks with applied shift
    for step in step_order:
        info = steps[step]
        times = pipeline_times[step]
        setup_start = times['setup_start'] + shift
        setup_end = times['setup_end'] + shift
        op_start = times['op_start'] + shift
        op_end = times['op_end'] + shift
        clean_start = times['clean_start'] + shift
        clean_end = times['clean_end'] + shift

        # Main step tasks
        schedule.append({'task': f'{step} Setup (Cycle {cycle})', 'start': setup_start, 'end': setup_end, 'row': step})
        schedule.append({'task': f'{step} Operation (Cycle {cycle})', 'start': op_start, 'end': op_end, 'row': step})
        schedule.append({'task': f'{step} Cleaning (Cycle {cycle})', 'start': clean_start, 'end': clean_end, 'row': step})

        # Tank cleaning in parallel with setup
        for tank in info['tanks']:
            t_start = setup_start  # start tank cleaning after setup
            t_end = t_start + tank_cleaning_time[tank]
            schedule.append({'task': f'{tank} Cleaning (Cycle {cycle})', 'start': t_start, 'end': t_end, 'row': tank})

        # Update resource availability. Updates the dictionary with the actual cleaning end time for the current cycle of that step, after applying any necessary shift.
        last_clean_end[step] = clean_end

# Sort rows: steps first, then tanks
rows = sorted(set(item['row'] for item in schedule), key=lambda r: (r not in step_order, r))

# Plot Gantt chart
fig, ax = plt.subplots(figsize=(14, 7))
colors = {
    'Setup': 'lightblue',
    'Operation': 'lightgreen',
    'Cleaning': 'salmon',
    'Tank Cleaning': 'gray'
}

for item in schedule:
    print(item)
    if 'Tank' in item['task']:
        ttype = 'Tank Cleaning'
    else:
        ttype = item['task'].split()[1]
    ax.barh(item['row'], item['end'] - item['start'], left=item['start'],
            color=colors[ttype], edgecolor='black', height=0.8)
    ax.text(item['start'] + 0.3, item['row'], item['task'], va='center', ha='left', fontsize=7)

ax.set_xlabel('Time (hours)')
ax.set_ylabel('Steps and Tanks')
ax.set_title(f'Optimized schedule for {num_cycles} Cycles')
ax.grid(True, axis='x')
ax.set_yticks(range(len(rows)))
ax.set_yticklabels(rows)

legend_patches = [mpatches.Patch(color=c, label=l) for l, c in colors.items()]
ax.legend(handles=legend_patches, loc='upper right')

plt.tight_layout()
plt.savefig("pipeline_first_resource_constrained_schedule.png")
plt.show()
import streamlit as st
import plotly.graph_objects as go

def run_simulation(step_order, steps, tank_cleaning_time, bioreactor_days, num_of_bioreactors):
    step_durations = {step: values['setup'] + values['operation'] + values['cleaning'] for step, values in steps.items()}
    min_step_duration = min(step_durations.values())

    st.write(f"Minimum step duration: {min_step_duration}")

    cadence = int(bioreactor_days / num_of_bioreactors)
    st.write(f"Cadence (days per bioreactor): {cadence}")

    num_cycles = int(cadence * 24 / min_step_duration)
    st.write(f"Max cycles for every step: {num_cycles}")

    schedule = []
    last_clean_end = {s: 0.0 for s in step_order}

    for cycle in range(1, num_cycles + 1):
        pipeline_times = {}
        prev_op_end = 0
        for i, step in enumerate(step_order):
            info = steps[step]
            setup_start = prev_op_end - info['setup']
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
            prev_op_end = op_end

        shift = 0
        for step in step_order:
            required_shift = max(0, last_clean_end[step] - pipeline_times[step]['setup_start'])
            if required_shift > shift:
                shift = required_shift

        for step in step_order:
            info = steps[step]
            times = pipeline_times[step]
            setup_start = times['setup_start'] + shift
            setup_end = times['setup_end'] + shift
            op_start = times['op_start'] + shift
            op_end = times['op_end'] + shift
            clean_start = times['clean_start'] + shift
            clean_end = times['clean_end'] + shift

            schedule.append({'task': f'{step} Setup (Cycle {cycle})', 'start': setup_start, 'end': setup_end, 'row': step})
            schedule.append({'task': f'{step} Operation (Cycle {cycle})', 'start': op_start, 'end': op_end, 'row': step})
            schedule.append({'task': f'{step} Cleaning (Cycle {cycle})', 'start': clean_start, 'end': clean_end, 'row': step})

            for tank in info['tanks']:
                t_start = setup_start
                t_end = t_start + tank_cleaning_time[tank]
                schedule.append({'task': f'{tank} Cleaning (Cycle {cycle})', 'start': t_start, 'end': t_end, 'row': tank})

            last_clean_end[step] = clean_end

    # --- Build deterministic row order & mapping ---
 
    # Sort rows: steps first, then tanks
    rows = sorted(set(item['row'] for item in schedule), key=lambda r: (r not in step_order, r))
    
    # --- Create Plotly figure ---
    fig = go.Figure()

    # Create a set to keep track of which task types have been added to the legend
    added_to_legend = set()

    for item in schedule:
        # Determine task type for color
        if 'Tank' in item['task']:
            color = 'gray'
            task_name = 'Tank'
        else:
            color_type = item['task'].split()[1]
            if color_type == "Setup":
                color = 'lightblue'
                task_name = 'Setup'
            elif color_type == "Operation":
                color = 'lightgreen'
                task_name = 'Operation'
            else:  # Cleaning
                color = 'salmon'
                task_name = 'Cleaning'

        # Determine if this is the first time we've seen this task type
        show_legend = task_name not in added_to_legend
        if show_legend:
            added_to_legend.add(task_name)

        fig.add_trace(go.Bar(
            y=[item['row']],
            x=[item['end'] - item['start']],
            base=[item['start']],
            orientation='h',
            # text=[item['task']],
            # textposition="outside",
            marker=dict(color=color),
            name=task_name,  # <--- Use a consistent name
            showlegend=show_legend, # <--- Only show the legend for the first occurrence
            hovertext=[f"{item['task']}<br>Start: {item['start']}<br>End: {item['end']}"],
            width=0.8
        ))
    
        # # --- Add the text as a separate annotation ---
        # fig.add_annotation(
        #     x=item['end'],  # Set the x position to the end of the bar
        #     y=item['row'],  # Set the y position to the center of the bar
        #     text=item['task'],  # The text to display
        #     showarrow=False,  # Hide the arrow
        #     xshift=0,  # Shift the text slightly to the right
        #     yshift=50,  # Shift the text slightly down
        #     font=dict(color='white', size=12),
        # )

    # --- Layout ---
    fig.update_layout(
        title="Pipeline Schedule",
        xaxis_title="Time (hours)",
        yaxis_title="Steps",
        height=max(400, 30*len(rows))
    )

    # --- Display in Streamlit ---
    st.plotly_chart(fig, use_container_width=True)

# ---------------- Streamlit App ---------------- #
st.title("Bioreactor Scheduling App")

st.sidebar.header("General Inputs")

# Step order entry
step_order = st.text_input("Enter step order (comma separated)", "A,B,C").split(",")

steps = {}
for i, step in enumerate(step_order):
    with st.expander("⚙️ Define Steps (click to expand)"):
        st.markdown(f"**Step {step}**")
        setup = st.number_input(f"Setup time for {step}", value=5.0, key=f"{step}_setup")
        operation = st.number_input(f"Operation time for {step}", value=10.0, key=f"{step}_operation")
        cleaning = st.number_input(f"Cleaning time for {step}", value=2.0, key=f"{step}_cleaning")
        tanks = st.text_input(f"Tanks used by {step} (comma separated)", f"Tank{i*2+1},Tank{i*2+2}", key=f"{step}_tanks")
        tanks = [t.strip() for t in tanks.split(",") if t.strip()]
        steps[step] = {"setup": setup, "operation": operation, "cleaning": cleaning, "tanks": tanks}

# Tank cleaning dictionary inside expander
with st.expander("🧴 Define Tank Cleaning Times (click to expand)"):
    tank_cleaning_time = {}
    all_tanks = sorted({tank for s in steps.values() for tank in s["tanks"]})
    for tank in all_tanks:
        ttime = st.number_input(f"Cleaning time for {tank}", value=2.0, key=f"{tank}_time")
        tank_cleaning_time[tank] = ttime

# Bioreactor settings
st.sidebar.subheader("Bioreactor Settings")
bioreactor_days = st.sidebar.number_input("Bioreactor Days", value=14)
num_of_bioreactors = st.sidebar.number_input("Number of Bioreactors", value=3)

# Run simulation
if st.sidebar.button("Generate"):
    run_simulation(step_order, steps, tank_cleaning_time, bioreactor_days, num_of_bioreactors)
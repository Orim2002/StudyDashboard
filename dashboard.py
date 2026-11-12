import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go   
import altair as alt

st.set_page_config(page_title="Deep Work Analytics", layout="wide")
st.title("🧠 Technion Deep Work Analytics")

@st.cache_data(ttl=10)
def load_data():
    try:
        df = pd.read_csv('study_analytics.csv')
        df['Course'] = df['Task'].apply(lambda x: x.split(':')[0] if isinstance(x, str) and ':' in x else x)
        # df['Duration (Hours)'] = df['Duration (Minutes)'] / 60.0
        return df
    except FileNotFoundError:
        return pd.DataFrame()

df = load_data()

if df.empty:
    st.warning("No data found yet! Start a Pomodoro session on your Arduino.")
else:
    total_minutes = df['Duration (Minutes)'].sum()
    total_sessions = len(df)
    fav_course = df.groupby('Course')['Duration (Minutes)'].sum().idxmax()
    
    col1, col2, col3 = st.columns(3)
    col1.metric("Total Study Time", f"{total_minutes / 60:.1f} Hours")
    col2.metric("Completed Sessions", total_sessions)
    col3.metric("Most Studied Course", fav_course)
    
    st.divider()
    
    st.subheader("🎯 Weekly Course Goals Progress")
    today = pd.Timestamp.now().normalize()
    days_since_sunday = (today.weekday() + 1) % 7
    start_of_week = today - pd.Timedelta(days=days_since_sunday)
    df["Datetime_Temp"] = pd.to_datetime(df['Date']).dt.normalize()
    df_current_week = df[df["Datetime_Temp"] >= start_of_week]
    credits = {
        "Calculus": 5.5,
        "Algebra": 4.0,
        "Physics": 3.5,
        "C Intro": 4.0,
        "ECE Intro": 1.0
    }
    HOURS_PER_CREDIT = 1.5
    weekly_goals = {course: credits * HOURS_PER_CREDIT  for course, credits in credits.items()}
    
    course_hours = df_current_week.groupby('Course')['Duration (Minutes)'].sum().to_dict()
    
    cols = st.columns(len(weekly_goals))
    for i, (course, goal) in enumerate(weekly_goals.items()):
        done = course_hours.get(course, 0.0)
        progress = min(done / (goal * 60), 1.0) if goal > 0 else 0.0
        with cols[i]:
            st.metric(label=course, value=f"{done / 60:.1f}h", delta=f"Goal: {goal}h")
            st.progress(progress)

    st.divider()
    
    col_chart1, col_chart2 = st.columns(2)
    
    with col_chart1:
        st.subheader("Time Allocation by Course")
        course_time = df.groupby('Course')['Duration (Minutes)'].sum().reset_index()
        fig_bar = px.bar(course_time, x='Course', y='Duration (Minutes)', 
                         color='Course', text_auto='.1f',
                         color_discrete_sequence=px.colors.qualitative.Pastel)
        st.plotly_chart(fig_bar, use_container_width=True)
        
    with col_chart2:
        st.subheader("Daily Study Trend")
        df['Date_Only'] = pd.to_datetime(df['Date']).dt.strftime('%d/%m/%Y')
        daily_time = df.groupby('Date_Only')['Duration (Minutes)'].sum().reset_index()
        fig_line = px.line(daily_time, x='Date_Only', y='Duration (Minutes)', markers=True)
        fig_line.update_traces(line_color='#00ff00', marker=dict(size=8))
        fig_line.update_layout(xaxis_type='category', xaxis_title='Date')
        st.plotly_chart(fig_line, use_container_width=True)
        
    st.divider()
    
    st.subheader("🔥 Deep Work Streak (Semester A)")
    
    df['Date_DT'] = pd.to_datetime(df['Date']).dt.normalize()
    daily_summary = df.groupby('Date_DT')['Duration (Minutes)'].sum().reset_index()
    
    semester_start = pd.to_datetime('2026-10-25')
    all_dates = pd.date_range(start='2026-10-25', end='2027-03-20', freq='D')
    grid = pd.DataFrame({'Date_DT': all_dates})
    grid['Day'] = grid['Date_DT'].dt.day_name()
    
    grid['Week_Num'] = ((grid['Date_DT'] - semester_start).dt.days // 7) + 1
    grid['Week_Str'] = "Week " + grid['Week_Num'].astype(str)
    
    ordered_weeks = grid['Week_Str'].unique()
    
    merged = pd.merge(grid, daily_summary, on='Date_DT', how='left')
    merged['Duration (Minutes)'] = merged['Duration (Minutes)'].fillna(0)
    
    github_dark_colors = [
        [0.0, '#161b22'],
        [0.01, '#0e4429'],
        [0.3, '#006d32'],
        [0.7, '#26a641'],
        [1.0, '#39d353']
    ]
    
    import plotly.graph_objects as go
    
    fig_heat = go.Figure(data=go.Heatmap(
        z=merged['Duration (Minutes)'],
        x=merged['Week_Str'],
        y=merged['Day'],
        colorscale=github_dark_colors,
        xgap=4, ygap=4,
        hoverongaps=False,
        showscale=False
    ))
    
    fig_heat.update_layout(
        xaxis=dict(
            categoryorder='array',
            categoryarray=ordered_weeks,
            tickfont=dict(size=14),
            tickangle = 0,
            showgrid=False
        ),
        yaxis=dict(
            categoryorder='array', 
            categoryarray=['Saturday', 'Friday', 'Thursday', 'Wednesday', 'Tuesday', 'Monday', 'Sunday'],
            tickfont=dict(size=16),
            showgrid=False
        ),
        #width=len(ordered_weeks) * 45 + 200, 
        width=1500,
        height=500,
        margin=dict(t=20, b=40, l=40, r=20),
        plot_bgcolor='rgba(0,0,0,0)',
        paper_bgcolor='rgba(0,0,0,0)'
    )
    
    st.plotly_chart(fig_heat, use_container_width=False)
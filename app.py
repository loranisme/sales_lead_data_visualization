import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go


# Page Configuration

st.set_page_config(page_title="Sales Lead Analytics", layout="wide")


# Data Processing (ETL)
@st.cache_data
def load_data():
    # Load your dataset
    df = pd.read_csv("sales_leads.csv")
    
    # Standardize dates
    df['Lead Create Date'] = pd.to_datetime(df['Lead Create Date'])
    df['Latest Purchase Date'] = pd.to_datetime(df['Latest Coverage Purchase Date'])
    
    # Create calculated columns
    df['is_enrolled'] = df['Lead Status'].apply(lambda x: 1 if x == 'Enrolled' else 0)
    df['is_group'] = df['Group Connected'].apply(lambda x: 1 if x == 'Yes' else 0)
    
    # Handle missing values
    df['Sales Agent'] = df['Sales Agent'].fillna('Unassigned')
    df['Student Category'] = df['Student Category'].fillna('Unknown')

    
    # Fstrunction categorizes leads based on their insurance history
    def classify_retention(row):
        prev = str(row['Pervious Policy']).strip()
        curr = str(row['Latest Policy']).strip()
        
        if pd.isna(row['Pervious Policy']) or prev == "" or prev == "nan":
            return "New Customer"
        elif prev == curr:
            return "Renewed (Same Plan)"
        else:
            return "Policy Migrated (Upsell/Change)"
            
    df['Retention Category'] = df.apply(classify_retention, axis=1)
    return df

df = load_data()


#Sidebar Filters
st.sidebar.header("Filter Panel")

# Date range selector
date_range = st.sidebar.date_input(
    "Lead Creation Period",
    [df['Lead Create Date'].min(), df['Lead Create Date'].max()]
)

# Multi-select for categories
category_filter = st.sidebar.multiselect(
    "Student Category",
    options=df['Student Category'].unique().tolist(),
    default=df['Student Category'].unique().tolist()
)

# Apply filters
mask = (df['Lead Create Date'].dt.date >= date_range[0]) & \
       (df['Lead Create Date'].dt.date <= date_range[1]) & \
       (df['Student Category'].isin(category_filter))
f_df = df.loc[mask]

# Main Dashboard Layout

st.title("Sales Lead & Conversion Dashboard")
st.markdown(f"Analysis for **{len(f_df)}** leads in the selected period.")

# Row 1: Key Performance Indicators (KPIs)
kpi1, kpi2, kpi3, kpi4 = st.columns(4)
with kpi1:
    st.metric("Total Leads", len(f_df))
with kpi2:
    conv_rate = (f_df['is_enrolled'].mean() * 100)
    st.metric("Conversion Rate", f"{conv_rate:.1f}%")
with kpi3:
    avg_fup = f_df['Follow Up Count'].mean()
    st.metric("Avg Follow-ups", f"{avg_fup:.2f}")
with kpi4:
    group_pct = (f_df['is_group'].mean() * 100)
    st.metric("Group Connection %", f"{group_pct:.1f}%")

st.divider()
# Row 2: Conversion Funnel & Segmentation
col_left, col_right = st.columns(2)

with col_left:
    # 1. Prepare data for Group
    df_group = f_df[f_df['Group Connected'] == 'Yes']
    group_counts = [len(df_group), df_group['is_enrolled'].sum()]
    
    # 2. Prepare data for Individual (Group Connected is No)
    df_indiv = f_df[f_df['Group Connected'] == 'No']
    indiv_counts = [len(df_indiv), df_indiv['is_enrolled'].sum()]
    
    # 3. Define the stages (Simplified for direct comparison)
    stages = ["Total Leads", "Enrolled"]
    
    # 4. Create Comparison Funnel
    fig_funnel = go.Figure()
    
    # Add Group Trace
    fig_funnel.add_trace(go.Funnel(
        name = 'Group Connected',
        y = stages,
        x = group_counts,
        textinfo = "value + percent initial",
        marker = {"color": "#636EFA"}
    ))
    
    # Add Individual Trace
    fig_funnel.add_trace(go.Funnel(
        name = 'Individual',
        y = stages,
        x = indiv_counts,
        textinfo = "value + percent initial",
        marker = {"color": "#EF553B"}
    ))
    
    fig_funnel.update_layout(
        title="Conversion Efficiency: Group vs Individual",
        yaxis_title="Stage",
        legend_title="Leads Type"
    )
    
    st.plotly_chart(fig_funnel, use_container_width=True)
    

with col_right:
    # Status by Category
    fig_bar = px.bar(f_df, x='Student Category', color='Lead Status', 
                     title="Lead Status Distribution by Category",
                     barmode='group')
    st.plotly_chart(fig_bar, use_container_width=True)

# --- Row 3: Product Analysis & Rep Performance ---
st.subheader("Product & Performance Insights")
col_p1, col_p2 = st.columns([1, 2])

with col_p1:
    # Policy Popularity
    fig_pie = px.pie(f_df, names='Latest Policy', title="Market Share by Policy Type", hole=0.3)
    st.plotly_chart(fig_pie, use_container_width=True)
    

with col_p2:
    # Rep Performance
    rep_stats = f_df.groupby('Customer Rep')['is_enrolled'].mean().reset_index()
    rep_stats['is_enrolled'] *= 100
    fig_rep = px.bar(rep_stats, x='is_enrolled', y='Customer Rep', orientation='h',
                     title="Conversion Rate by Customer Rep (%)",
                     labels={'is_enrolled': 'Conv. %'},
                     color='is_enrolled', color_continuous_scale='Blues')
    st.plotly_chart(fig_rep, use_container_width=True)

# Row 4: Retention & Loyalty Analysis
st.divider()
st.subheader("Customer Retention & Loyalty Analysis")
col_ret1, col_ret2 = st.columns([1, 1])

with col_ret1:
    # Calculate the distribution of New vs. Returning customers
    # This helps identify if the business relies on new leads or loyal renewals
    retention_counts = f_df['Retention Category'].value_counts()
    
    fig_ret_pie = px.pie(
        names=retention_counts.index, 
        values=retention_counts.values,
        title="Market Composition: New vs. Returning",
        hole=0.4, # Creates a donut chart for a modern look
        color_discrete_sequence=px.colors.qualitative.Pastel
    )
    # Ensure the chart responds to container width
    st.plotly_chart(fig_ret_pie, use_container_width=True)

with col_ret2:
    # Advanced Insight: Compare conversion rates across customer segments
    # Hypothesis: Returning customers usually have significantly higher conversion rates
    ret_conv = f_df.groupby('Retention Category')['is_enrolled'].mean() * 100
    
    fig_ret_conv = px.bar(
        x=ret_conv.index, 
        y=ret_conv.values,
        title="Conversion Efficiency by Loyalty Segment (%)",
        labels={'x': 'Customer Type', 'y': 'Conversion Rate (%)'},
        color=ret_conv.index,
        color_discrete_sequence=['#636EFA', '#00CC96', '#AB63FA']
    )
    
    # Update layout to show the percentage clearly on the bars
    fig_ret_conv.update_traces(texttemplate='%{y:.1f}%', textposition='outside')
    st.plotly_chart(fig_ret_conv, use_container_width=True)


# --- Row 5: Raw Data Export ---
with st.expander("View Raw Filtered Data"):
    st.dataframe(f_df.sort_values(by='Lead Create Date', ascending=False))
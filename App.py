%%writefile app.py
import streamlit as st
import anthropic
import pandas as pd
import plotly.graph_objects as go
from io import BytesIO
import base64

st.set_page_config(page_title="Brinson Analyzer", layout="wide")
st.title("📊 Brinson Attribution Analyzer")
st.markdown("Upload FactSet CSV → Get analysis + waterfall chart")

# Sidebar
api_key = st.sidebar.text_input("Claude API Key", type="password")
file = st.sidebar.file_uploader("FactSet Attribution CSV", type=['csv'])

if api_key and file:
    @st.cache_data
    def analyze_data(df):
        client = anthropic.Anthropic(api_key=api_key)
        txt = df.to_csv(index=False)
        msg = client.messages.create(
            model="claude-sonnet-4-5",
            max_tokens=1500,
            messages=[{"role": "user", "content": f"""
            Brinson attribution CSV (cols: Sector, Fund_Wt, BM_Wt, Fund_Ret, BM_Ret):
            {txt}
            Compute: Allocation, Selection, Interaction effects (%).
            Respond JSON: {{"table": [...], "insights": "bullets", "risks": "top3"}}
            """ }]
        )
        return msg.content[0].text

    df = pd.read_csv(file)
    st.dataframe(df, use_container_width=True)
    
    # Compute effects (simple formula)
    df['Alloc_Eff'] = (df['Fund_Wt'] - df['BM_Wt']) * df['BM_Ret']
    df['Sel_Eff'] = df['Fund_Wt'] * (df['Fund_Ret'] - df['BM_Ret'])
    df['Inter_Eff'] = (df['Fund_Wt'] - df['BM_Wt']) * (df['Fund_Ret'] - df['BM_Ret'])
    df['Total_Eff'] = df['Alloc_Eff'] + df['Sel_Eff'] + df['Inter_Eff']
    
    st.subheader("Computed Effects")
    st.dataframe(df[['Sector', 'Alloc_Eff', 'Sel_Eff', 'Inter_Eff', 'Total_Eff']].round(3))
    
    # Polished Waterfall Chart
    fig = go.Figure(go.Waterfall(
        name="Attribution",
        orientation="v",
        measure=["relative"] * len(df),
        x=df['Sector'],
        y=df['Total_Eff'],
        connector={"line": {"color": "rgb(63, 63, 63)"}},
        decreasing={"marker": {"color": "red"}},
        increasing={"marker": {"color": "green"}},
        totals_name="Net Attribution"
    ))
    fig.update_layout(title="Brinson Waterfall: Fund vs Benchmark", height=500)
    st.plotly_chart(fig, use_container_width=True)
    
    # Claude Insights
    if st.button("Get AI Insights"):
        insights = analyze_data(df)
        st.markdown("### Claude Analysis")
        st.markdown(insights)
    
    # Download
    csv_buffer = BytesIO()
    df.to_csv(csv_buffer, index=False)
    st.download_button("Download Report CSV", csv_buffer.getvalue(), "brinson_report.csv")

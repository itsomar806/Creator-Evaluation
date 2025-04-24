import streamlit as st
import pandas as pd
import altair as alt
import openai
import os
from dashboard import (
    extract_channel_id_from_url,
    get_channel_metadata,
    get_recent_videos,
    calculate_average_views
)

# Set your OpenAI key securely
openai.api_key = st.secrets["openai"]["api_key"] if "openai" in st.secrets else os.getenv("OPENAI_API_KEY")

# Set page config FIRST
st.set_page_config(page_title="YouTube Creator Evaluation", layout="wide")

# Custom styling using HubSpot Media branding
st.markdown("""
<style>
body {
    background-color: #2E475D;
    color: #EAF0F6;
}
[data-testid="stAppViewContainer"] > .main {
    background-color: #2E475D;
    padding-top: 2rem;
}
#MainMenu, header, footer {visibility: hidden;}
input[type="text"] {
    text-align: center;
    font-size: 1.2rem;
    border-radius: 8px;
    padding: 0.5rem;
}
.video-table table {
    width: 100%;
    border-collapse: collapse;
}
.video-table th, .video-table td {
    padding: 10px;
    border: 1px solid #ddd;
    text-align: left;
    font-size: 15px;
}
.video-table th {
    background-color: #f2f2f2;
}
.video-table tr:hover {
    background-color: #f9f9f9;
}
</style>
""", unsafe_allow_html=True)

st.markdown("<h2 style='text-align: center; color: #213343;'>HubSpot Creator Evaluation</h2>", unsafe_allow_html=True)

if "audit_triggered" not in st.session_state:
    st.session_state.audit_triggered = False

url = st.text_input("Paste a YouTube channel URL:")
if st.button("Run Audit"):
    st.session_state.audit_triggered = True

if st.session_state.audit_triggered and url:
    try:
        channel_id = extract_channel_id_from_url(url)
        metadata = get_channel_metadata(channel_id)
        st.success(f"✅ Channel found: {metadata['title']}")

        videos = get_recent_videos(channel_id)
        for video in videos:
            views = video["views"]
            likes = video["likes"]
            comments = video["comments"]
            video["engagement_rate"] = round(((likes + comments) / views) * 100, 2) if views > 0 else 0

        titles_and_descriptions = "\n".join([
            f"Title: {v['title']}\nDescription: {v.get('description', 'No description')}"
            for v in videos[:30]
        ])
        prompt = f"""
Analyze the following YouTube videos for brand risk and HEART value alignment:

{titles_and_descriptions}

Return the result in this format:
{{
  "brand_risk_score": <1-10>,
  "risk_flags": ["flag1", "flag2"],
  "heart_values": {{
    "Humble": "Yes/No",
    "Empathetic": "Yes/No",
    "Adaptable": "Yes/No",
    "Remarkable": "Yes/No",
    "Transparent": "Yes/No"
  }},
  "summary": "Short explanation of the rating"
}}
"""
        response = openai.ChatCompletion.create(
            model="gpt-4",
            messages=[
                {"role": "system", "content": "You are a brand risk assessment expert for influencer marketing."},
                {"role": "user", "content": prompt}
            ]
        )

        result = response.choices[0].message.content
        st.markdown("---")
        st.subheader("🚨 Brand Safety & HEART Assessment")
        import json
        try:
            parsed_result = json.loads(result)
            heart = parsed_result.get("heart_values", {})
            risk_score = parsed_result.get("brand_risk_score", 10)
            yes_count = list(heart.values()).count("Yes")

            if risk_score <= 3 and yes_count >= 4:
                go_status = "🟢 GO - Strong brand alignment and low risk"
            elif risk_score <= 6 and yes_count >= 3:
                go_status = "🟡 CAUTION - Moderate risk or values alignment; requires mitigation"
            else:
                go_status = "🔴 NO-GO - High risk or poor HEART alignment"

            st.markdown(f"### ✅ Go/No-Go Recommendation\n**{go_status}**")
        except Exception as err:
            st.warning("⚠️ Unable to parse AI response for Go/No-Go logic.")

        st.markdown(f"```json\n{result}\n```")

    except Exception as e:
        st.error(f"Something went wrong: {e}")

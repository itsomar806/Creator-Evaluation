import streamlit as st
import pandas as pd
import altair as alt
import json
import re
import os
import requests
from urllib.parse import urlparse, parse_qs
from serpapi import GoogleSearch
import googleapiclient.discovery
from openai import OpenAI

# --- UTIL FUNCTIONS (inline instead of dashboard.py) ---
[...your existing utility functions remain here...]

# --- Streamlit App Logic ---
st.set_page_config(page_title="YouTube Creator Audit", layout="wide")

st.title("🔍 YouTube Creator Audit")

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

        avg_views = calculate_average_views(videos)

        st.subheader("📌 Creator Overview")
        col1, col2 = st.columns(2)
        with col1:
            st.markdown(f"**👤 Channel Name:** {metadata['title']}")
            st.markdown(f"**🔗 Handle:** `{metadata['handle']}`")
            st.markdown(f"**🆔 Channel ID:** `{metadata['id']}`")
        with col2:
            st.markdown(f"**🌍 Country:** {metadata['country']}")
            st.markdown(f"**👥 Subscribers:** {metadata['subs']:,}")
            st.markdown(f"[🔗 View Channel](https://www.youtube.com/channel/{metadata['id']})")

        st.subheader("📊 Sponsorship Calculator")
        col1, col2 = st.columns(2)
        with col1:
            st.markdown(f"""
            <div style='background-color:#f9f9f9; padding: 1.2rem; border-radius: 10px; border: 1px solid #ccc; text-align: center;'>
                <span style='font-size: 1.2rem;'>💡 <strong>Average Views (last 30 videos):</strong></span>
                <div style='font-size: 1.8rem; color: #FFCD78; font-weight: bold;'>{avg_views:,}</div>
            </div>
            """, unsafe_allow_html=True)
        with col2:
            cpv_options = {
                "Conservative CVR (0.30%)": 0.003,
                "Median CVR (0.35%)": 0.0035,
                "Best Case CVR (0.50%)": 0.005
            }
            selected_label = st.selectbox("🌟 Select a CPV Scenario", options=list(cpv_options.keys()))
            target_cpv = cpv_options[selected_label]
            recommended_price = round(avg_views * target_cpv)
            st.markdown(f"**Target CPV:** ${target_cpv:.4f}")
            st.markdown(f"**Recommended Cost per Video:** ${recommended_price:,}")

        st.subheader("📈 Growth Over Time (by Views)")
        views_df = pd.DataFrame(videos)
        views_df["published"] = pd.to_datetime(views_df["published"])
        views_df = views_df.sort_values(by="published", ascending=True).reset_index(drop=True)
        views_df["label"] = views_df["published"].dt.strftime("%b %d")

        chart = alt.Chart(views_df).mark_bar().encode(
            x=alt.X("label:N", sort=None, title="Publish Date"),
            y=alt.Y("views:Q", title="Views"),
            tooltip=["label", "views", "title"]
        ).properties(height=400)
        st.altair_chart(chart, use_container_width=True)

        st.subheader("🔥 Top 10 Performing Videos")
        df = pd.DataFrame(videos)
        top_videos = df.sort_values(by="views", ascending=False).head(10).reset_index(drop=True)
        top_videos["video_url"] = top_videos["video_id"].apply(lambda x: f"https://www.youtube.com/watch?v={x}")
        top_videos["title"] = top_videos.apply(lambda row: f'<a href="{row.video_url}" target="_blank">{row.title}</a>', axis=1)
        display_df = top_videos[["title", "views", "likes", "comments"]]
        display_df.columns = ["🎬 Title", "👁️ Views", "👍 Likes", "💬 Comments"]
        table_html = display_df.to_html(escape=False, index=False)
        st.markdown(f"<div class='video-table'>{table_html}</div>", unsafe_allow_html=True)

        st.subheader("🚨 Brand Safety & HEART Assessment")
        try:
            search_query = f"{metadata['title']} YouTube creator news OR controversy OR reviews"
            st.markdown(f"🔍 Using enhanced search query: `{search_query}`")
            ai_response = get_brand_safety_assessment(search_query)
            parsed = json.loads(ai_response)
            st.markdown(f"**Brand Risk Score:** {parsed.get('brand_risk_score', 'N/A')}")
            st.markdown(f"**HEART Values:** {parsed.get('heart_values', {})}")
            st.markdown(f"**Summary:** {parsed.get('summary', '')}")
        except Exception:
            st.warning("⚠️ Unable to parse AI response.")
            st.markdown(ai_response)

    except Exception as e:
        st.error(f"Something went wrong: {e}")

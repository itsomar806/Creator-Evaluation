import streamlit as st
import pandas as pd
import altair as alt
from dashboard import (
    extract_channel_id_from_url,
    get_channel_metadata,
    get_recent_videos,
    calculate_average_views
)
import collections
import re

# Set page config FIRST
st.set_page_config(page_title="YouTube Creator Audit", layout="wide")

# Handle session state for rerun persistence
if "audit_triggered" not in st.session_state:
    st.session_state.audit_triggered = False

st.title("🔍 YouTube Creator Audit Dashboard")
url = st.text_input("Paste a YouTube channel URL:")

if st.button("Run Audit"):
    st.session_state.audit_triggered = True

if st.session_state.audit_triggered and url:
    try:
        # Step 1: Extract and display channel metadata
        channel_id = extract_channel_id_from_url(url)
        metadata = get_channel_metadata(channel_id)
        st.success(f"✅ Channel found: {metadata['title']}")

        # Step 2: Fetch video data and calculate engagement
        videos = get_recent_videos(channel_id)
        for video in videos:
            views = video["views"]
            likes = video["likes"]
            comments = video["comments"]
            video["engagement_rate"] = round(((likes + comments) / views) * 100, 2) if views > 0 else 0

        # Step 3: Topic classification
        topic_keywords = {
            "Marketing": ["marketing", "brand", "ads", "advertising", "promotion"],
            "Sales": ["sales", "sell", "pitch", "close"],
            "Entrepreneurship / Business": ["startup", "founder", "entrepreneur", "business", "revenue", "profit"],
            "AI": ["ai", "artificial", "intelligence", "chatgpt", "machine learning"],
            "Skill Development": ["learn", "course", "skills", "habits", "productivity", "growth"],
            "Web Development": ["developer", "web", "html", "css", "javascript", "react"],
            "Operations": ["ops", "operations", "process", "workflow"],
            "Customer Success": ["customer", "support", "success", "retention"],
            "Tech": ["tech", "technology", "software", "tools"]
        }

        topic_counts = {key: 0 for key in topic_keywords}

        for video in videos:
            title = video["title"].lower()
            matched = False
            for category, keywords in topic_keywords.items():
                if any(kw in title for kw in keywords):
                    topic_counts[category] += 1
                    matched = True
                    break

        sorted_topics = [item[0] for item in sorted(topic_counts.items(), key=lambda x: (-x[1], x[0])) if item[1] > 0]
        topic_summary = ", ".join(sorted_topics) if sorted_topics else "No editorial fit."

        # Step 4: Creator Overview
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

        if topic_summary == "No editorial fit.":
            st.markdown("""
<style>
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
<div class="video-table">
""" + top_videos_display.to_html(escape=False, index=False) + "</div>", unsafe_allow_html=True)
            
    except Exception as e:
        st.error(f"Something went wrong: {e}")

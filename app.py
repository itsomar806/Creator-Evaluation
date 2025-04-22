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
</style>
""", unsafe_allow_html=True)

# Center the logo and input
st.markdown("<h2 style='text-align: center; color: #FFCD78;'>HubSpot Creator Audit</h2>", unsafe_allow_html=True)

# Handle session state for rerun persistence
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
            <div style="background-color:#fff4f4; border-left: 4px solid #e74c3c; padding: 1rem; border-radius: 6px; margin-bottom: 1rem;">
                <strong>🧠 Topic Clusters (based on recent videos):</strong><br>
                <span style="color:#e74c3c;">No editorial fit.</span>
            </div>
            """, unsafe_allow_html=True)
        else:
            st.markdown(f"**🧠 Topic Clusters (based on recent videos):** {topic_summary}")

    except Exception as e:
        st.error(f"Something went wrong: {e}")


# Always show a placeholder below regardless of success
st.markdown("---")
st.subheader("📊 Growth Over Time (by Views)")
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

        # Sponsorship calculator
        st.subheader("💰 Sponsorship Calculator")
        avg_views = calculate_average_views(videos)
        cpv_options = {
            "Conservative CVR (0.30%)": 0.003,
            "Median CVR (0.35%)": 0.0035,
            "Best Case CVR (0.50%)": 0.005
        }
        selected_label = st.selectbox("Select a CPV Scenario:", options=list(cpv_options.keys()))
        target_cpv = cpv_options[selected_label]
        recommended_price = round(avg_views * target_cpv)

        st.markdown(f"""
        <div style='background-color:#eafbea; padding: 1rem; border-radius: 8px; border: 1px solid #c7eacc;'>
            <strong>Target CPV:</strong> ${target_cpv:.4f}<br>
            <strong>Average Views:</strong> {avg_views:,}<br>
            <strong>Recommended Cost per Video:</strong> <span style='font-size: 1.5rem;'>${recommended_price:,}</span>
        </div>
        """, unsafe_allow_html=True)

        # Top 10 performing videos
        st.subheader("🔥 Top 10 Performing Videos")
        df = pd.DataFrame(videos)
        top_videos = df.sort_values(by="views", ascending=False).head(10).reset_index(drop=True)
        top_videos["video_url"] = top_videos["video_id"].apply(lambda x: f"https://www.youtube.com/watch?v={x}")
        top_videos["title"] = top_videos.apply(lambda row: f'<a href="{row.video_url}" target="_blank">{row.title}</a>', axis=1)
        top_videos_display = top_videos[["title", "views", "likes", "comments"]]
        top_videos_display.columns = ["🎬 Title", "👁️ Views", "👍 Likes", "💬 Comments"]

        styled_table_html = f"""
        <style>
            .video-table table {{
                width: 100%;
                border-collapse: collapse;
            }}
            .video-table th, .video-table td {{
                padding: 10px;
                border: 1px solid #ddd;
                text-align: left;
                font-size: 15px;
            }}
            .video-table th {{
                background-color: #f2f2f2;
            }}
            .video-table tr:hover {{
                background-color: #f9f9f9;
            }}
        </style>
        <div class="video-table">
        {top_videos_display.to_html(escape=False, index=False)}
        </div>
        """
        st.markdown(styled_table_html, unsafe_allow_html=True)

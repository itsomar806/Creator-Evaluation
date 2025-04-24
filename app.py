import streamlit as st
import pandas as pd
import altair as alt
import openai
import os
import re
import json
from openai import OpenAI
from serpapi import GoogleSearch
from dashboard import (
    extract_channel_id_from_url,
    get_channel_metadata,
    get_recent_videos,
    calculate_average_views
)

# --- Web presence scan via SerpAPI ---
def search_web_presence(query, serpapi_key):
    search = GoogleSearch({
        "q": query,
        "api_key": serpapi_key,
        "num": 10
    })
    results = search.get_dict()
    output = ""

    for res in results.get("organic_results", []):
        title = res.get("title", "")
        snippet = res.get("snippet", "")
        link = res.get("link", "")
        output += f"- {title}\n{snippet}\n{link}\n\n"

    return output.strip()

# --- Keys ---
openai_api_key = st.secrets["openai"]["api_key"] if "openai" in st.secrets else os.getenv("OPENAI_API_KEY")
serpapi_key = st.secrets["serpapi"]["api_key"] if "serpapi" in st.secrets else os.getenv("SERPAPI_API_KEY")
client = OpenAI(api_key=openai_api_key)

st.set_page_config(page_title="YouTube Creator Audit", layout="wide")

# --- Styling ---
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

st.markdown("<h2 style='text-align: center; color: #FFCD78;'>HubSpot Creator Audit</h2>", unsafe_allow_html=True)

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

        # --- Creator Overview ---
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
        st.markdown("---")
        # --- Sponsorship Calculator ---
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
            
        st.markdown("---")

        topic_counts = {key: 0 for key in topic_keywords}
        for video in videos:
            title = video["title"].lower()
            for category, keywords in topic_keywords.items():
                if any(kw in title for kw in keywords):
                    topic_counts[category] += 1
                    break

        sorted_topics = [t for t, c in topic_counts.items() if c > 0]
        if sorted_topics:
            st.markdown(f"**🧠 Topic Clusters (based on recent videos):** {', '.join(sorted_topics)}")
        else:
            st.markdown("""
            <div style="background-color:#fff4f4; border-left: 4px solid #e74c3c; padding: 1rem; border-radius: 6px;">
                <strong>🧠 Topic Clusters:</strong><br>
                <span style="color:#e74c3c;">No editorial fit.</span>
            </div>
            """, unsafe_allow_html=True)

        # --- Growth Over Time ---
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

        # --- Top 10 Videos Table ---
        st.subheader("🔥 Top 10 Performing Videos")
        df = pd.DataFrame(videos)
        top_videos = df.sort_values(by="views", ascending=False).head(10).reset_index(drop=True)
        top_videos["video_url"] = top_videos["video_id"].apply(lambda x: f"https://www.youtube.com/watch?v={x}")
        top_videos["title"] = top_videos.apply(lambda row: f'<a href="{row.video_url}" target="_blank">{row.title}</a>', axis=1)
        top_videos_display = top_videos[["title", "views", "likes", "comments"]]
        top_videos_display.columns = ["🎬 Title", "👁️ Views", "👍 Likes", "💬 Comments"]
        st.markdown("<div class='video-table'>" + top_videos_display.to_html(escape=False, index=False) + "</div>", unsafe_allow_html=True)

        # --- Brand Safety & HEART Assessment ---
        st.markdown("---")
        st.subheader("🚨 Brand Safety & HEART Assessment")
        query = f"{metadata['title']} {metadata['handle']} site:twitter.com OR site:linkedin.com OR site:reddit.com"
        web_summary = search_web_presence(query, serpapi_key)

        prompt = f"""
You're assessing a YouTube creator for brand partnership risk. Below is a summary of their online presence.

Return your response as JSON:
{{
  "brand_risk_score": 1-10,
  "risk_flags": ["list of concern tags"],
  "heart_values": {{
    "Humble": "Yes/No",
    "Empathetic": "Yes/No",
    "Adaptable": "Yes/No",
    "Remarkable": "Yes/No",
    "Transparent": "Yes/No"
  }},
  "summary": "Brief summary"
}}

Online presence:
{web_summary}
"""

        response = client.chat.completions.create(
            model="gpt-4",
            messages=[
                {"role": "system", "content": "You are a brand safety analyst."},
                {"role": "user", "content": prompt}
            ]
        )

        result = response.choices[0].message.content
        try:
            json_text = re.search(r"\{.*\}", result, re.DOTALL).group()
            parsed_result = json.loads(json_text)
            heart = parsed_result["heart_values"]
            score = parsed_result["brand_risk_score"]
            summary = parsed_result["summary"]
            flags = ", ".join(parsed_result.get("risk_flags", []))

            st.markdown(f"**Go/No-Go Score:** {score}/10")
            st.markdown(f"**HEART:** " + ", ".join([f"{k}: {v}" for k, v in heart.items()]))
            st.markdown(f"**Summary:** {summary}")
            st.markdown(f"**Flags:** {flags or 'None'}")
        except:
            st.warning("⚠️ Unable to parse AI response.")
            st.text(result)

    except Exception as e:
        st.error(f"Something went wrong: {e}")

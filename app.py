import streamlit as st
import pandas as pd
import altair as alt
import openai
import os
from openai import OpenAI
from dashboard import (
    extract_channel_id_from_url,
    get_channel_metadata,
    get_recent_videos,
    calculate_average_views
)

openai_api_key = st.secrets["openai"]["api_key"] if "openai" in st.secrets else os.getenv("OPENAI_API_KEY")
client = OpenAI(api_key=openai_api_key)

st.set_page_config(page_title="YouTube Creator Audit", layout="wide")

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

        # Topic Classification
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

        st.markdown(f"**🧠 Topic Clusters (based on recent videos):** {topic_summary}")
        st.markdown("---")

        # Growth Chart
        views_df = pd.DataFrame(videos)
        views_df["published"] = pd.to_datetime(views_df["published"])
        views_df = views_df.sort_values(by="published", ascending=True).reset_index(drop=True)
        views_df["label"] = views_df["published"].dt.strftime("%b %d")

        st.subheader("📈 Growth Over Time (by Views)")
        chart = alt.Chart(views_df).mark_bar().encode(
            x=alt.X("label:N", sort=None, title="Publish Date"),
            y=alt.Y("views:Q", title="Views"),
            tooltip=["label", "views", "title"]
        ).properties(height=400)
        st.altair_chart(chart, use_container_width=True)

        # Top 10 Performing Videos
        st.subheader("🔥 Top 10 Performing Videos")
        df = pd.DataFrame(videos)
        top_videos = df.sort_values(by="views", ascending=False).head(10).reset_index(drop=True)
        top_videos["video_url"] = top_videos["video_id"].apply(lambda x: f"https://www.youtube.com/watch?v={x}")
        top_videos["title"] = top_videos.apply(lambda row: f'<a href="{row.video_url}" target="_blank">{row.title}</a>', axis=1)
        top_videos_display = top_videos[["title", "views", "likes", "comments"]]
        top_videos_display.columns = ["🎬 Title", "👁️ Views", "👍 Likes", "💬 Comments"]
        st.markdown("<div class='video-table'>" + top_videos_display.to_html(escape=False, index=False) + "</div>", unsafe_allow_html=True)

        # Sponsorship Calculator
        st.markdown("---")
        st.subheader("📊 Sponsorship Calculator")
        col1, col2 = st.columns(2)
        with col1:
            st.markdown(f"**📈 Average Views (last 30 videos):** {avg_views:,}")
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

        # Brand Safety + HEART Evaluation
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
        response = client.chat.completions.create(
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
            risk_flags = parsed_result.get("risk_flags", [])
            summary = parsed_result.get("summary", "")
            yes_count = list(heart.values()).count("Yes")

            if risk_score <= 3 and yes_count >= 4:
                go_status = "🟢 GO - Strong brand alignment and low risk"
            elif risk_score <= 6 and yes_count >= 3:
                go_status = "🟡 CAUTION - Moderate risk or values alignment; requires mitigation"
            else:
                go_status = "🔴 NO-GO - High risk or poor HEART alignment"

            st.markdown(f"### ✅ Go/No-Go Recommendation\n**{go_status}**")
            st.markdown(f"#### 🧠 HEART Value Checks")
            st.markdown("""
            <ul style='list-style-type: none; padding-left: 0;'>
            """ + "\n".join([
                f"<li><strong>{k}</strong>: {'✅' if v == 'Yes' else '❌'} {v}</li>"
                for k, v in heart.items()
            ]) + "</ul>", unsafe_allow_html=True)

            st.markdown(f"#### ⚠️ Risk Score: {risk_score}/10")
            st.markdown(f"#### 🚩 Flags: {', '.join(risk_flags) if risk_flags else 'None'}")
            st.markdown(f"#### 📝 Summary: {summary}")

        except Exception as err:
            st.warning("⚠️ Unable to parse AI response for Go/No-Go logic.")
            st.markdown(f"```json\n{result}\n```)\n")

    except Exception as e:
        st.error(f"Something went wrong: {e}")

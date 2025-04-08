import streamlit as st
import pandas as pd
import boto3
from io import StringIO
from wordcloud import WordCloud
import matplotlib.pyplot as plt
import json

# AWS S3 Configuration
bucket_name = "sis-annotation"

# Load AWS credentials from Streamlit secrets
aws_access_key = st.secrets["aws"]["aws_access_key_id"]
aws_secret_key = st.secrets["aws"]["aws_secret_access_key"]
aws_region = st.secrets["aws"]["aws_region"]

# --- Load JSONL Annotation File ---
jsonl_key = "unified_annotations_clean.jsonl"  # Update with new file name if needed

@st.cache_data
def load_annotations():
    s3 = boto3.client(
        "s3",
        region_name=aws_region,
        aws_access_key_id=aws_access_key,
        aws_secret_access_key=aws_secret_key
    )
    obj = s3.get_object(Bucket=bucket_name, Key=jsonl_key)
    lines = obj['Body'].read().decode('utf-8').splitlines()
    annotations = [json.loads(line) for line in lines]
    return annotations

annotations = load_annotations()

# --- UI: Introduction ---
st.markdown(
    """
    # 🎧 SiS:TER  
    **Sound in Stories: Tagging, Exploration, Research**

    This corpus is a collection of short stories, each annotated on two levels:
    - **Lexical annotation** (focused on identifying and categorizing words in the text, e.g., human, nature, mechanic sounds)
    - **Sound volume annotation** (the loudness of the paragraph by three dimensions).

    The corpus comprises *220 short stories* covering the *XX century*. 
    Below, you can explore the **annotation per paragraph**.
    """
)

# --- UI: Paragraph Selector ---
st.markdown("## 📝 Annotated Corpus")

# Get all stories and display titles + authors
stories_info = {}
for a in annotations:
    meta = a.get("metadata", {})
    if "title" in meta and "author" in meta and "year" in meta:
        stories_info[a["story_id"]] = (meta["title"], meta["author"], meta["year"])

story_titles = [f"{info[0]} by {info[1]}" for info in stories_info.values()]
selected_story_title = st.selectbox("Select story:", story_titles)

selected_story_id = next(story_id for story_id, info in stories_info.items() if f"{info[0]} by {info[1]}" == selected_story_title)

# Select part
matching_parts = [a for a in annotations if a["story_id"] == selected_story_id]
parts = sorted(set(a["part"] for a in matching_parts))
selected_part = st.selectbox("Select part:", parts)

selected_entry = next((a for a in annotations if a["story_id"] == selected_story_id and a["part"] == selected_part), None)

if selected_entry:
    meta = selected_entry["metadata"]
    year = int(meta["year"]) if isinstance(meta["year"], float) else meta["year"]

    st.markdown(f"""
    ### 📚 Metadata
    - **Author:** {meta["author"]}
    - **Year:** {year}
    - **Title:** *{meta["title"]}*
    """)

    # Original text
    st.markdown("### Original Text")
    st.write(selected_entry["text"])

    # Lemmatized version
    if st.button("Show Lemmatized Text"):
        st.markdown("### Lemmatized Text")
        st.write(selected_entry["lemmatized_text"])

    # Token-level annotations
    st.markdown("### 🎯 Sound Categories by Words")
    token_labels = selected_entry.get("annotations", {}).get("token_level", {}).get("labels", [])
    if token_labels:
        for tag in token_labels:
            st.markdown(f"- **{tag['text']}** → {', '.join(tag['labels'])} *(lemma: {tag['lemma']})*")
    else:
        st.info("No tags in this part.")

    # Paragraph-level volume
    st.markdown("### 📊 Annotation per Paragraph")
    para_annot = selected_entry["annotations"]["paragraph_level"]
    st.markdown(f"""
    - **Sound Type:** {para_annot["sound_type"]}
    - **Sound Volume:** :blue-background[Human]: {para_annot["volume"]["human"]}/4, :green-background[Nature]: {para_annot["volume"]["nature"]}/4, :red-background[Artificial]: {para_annot["volume"]["artificial"]}/4
    """)

    st.markdown("""
    Sound Type Descriptions:
    - **d (Diegetic)**: Sound that originates within the story world (e.g., footsteps, dialogue).
    - **nd (Non-diegetic)**: Sound that is external to the story world (e.g., description of regular actions, memories, etc.).
    - **dnd (Both types)**: A mix of diegetic and non-diegetic sounds.
    """)

    if st.button("Show Raw JSON"):
        st.write(selected_entry)
else:
    st.warning("No annotation found for this selection.")

# --- Wordcloud Generation ---
file_key = "sound_cats_lemmas_w_freqs.csv"

@st.cache_data
def load_data():
    s3 = boto3.client(
        "s3",
        region_name=aws_region,
        aws_access_key_id=aws_access_key,
        aws_secret_access_key=aws_secret_key
    )
    obj = s3.get_object(Bucket=bucket_name, Key=file_key)
    df = pd.read_csv(StringIO(obj['Body'].read().decode('utf-8')))
    return df

st.markdown("---")
st.markdown("## 🧠 Wordcloud Generation")

st.markdown("""
These word clouds are generated from frequency dictionaries derived from the whole dataset. The word frequencies exclude multiple word expressions.
""")

df = load_data()

categories = df['category'].unique()
selected_category = st.selectbox("Choose category:", categories)

filtered_df = df[df['category'] == selected_category]

if filtered_df.empty:
    st.warning("No words yet :(")
else:
    word_freq = dict(zip(filtered_df['lemma'], filtered_df['freq']))
    wordcloud = WordCloud(width=800, height=400, background_color='white').generate_from_frequencies(word_freq)

    st.subheader(f"Wordcloud for category: {selected_category}")
    fig, ax = plt.subplots()
    ax.imshow(wordcloud, interpolation='bilinear')
    ax.axis("off")
    st.pyplot(fig)

# Show table
st.subheader("🔍 Words in Selected Category")
st.dataframe(filtered_df)

# Footer
st.markdown("---")
st.markdown(
    "<p style='text-align: center; color: gray;'>🚧 This project is a work in progress – part of the SiS:TER corpus exploration.</p>",
    unsafe_allow_html=True
)

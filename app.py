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
jsonl_key = "unified_annotations.jsonl"  # Change to your real S3 path

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
    - **Sound volume annotation** (the loudness of the paragraph by three dimentions).

    The corpus comprises *220 short stories* covering the *XX century*. 
    Below, you can explore the **annotation per paragraph**.
    """
)

# --- UI: Paragraph Selector ---
st.markdown("## 📝 Annotated Corpus")

# Get all stories and display titles + authors
stories_info = {}
for a in annotations:
    # Check if volume_annotation exists and has the necessary keys
    if "volume_annotation" in a and "title" in a["volume_annotation"] and "author" in a["volume_annotation"] and "year" in a["volume_annotation"]:
        title = a["volume_annotation"]["title"]
        author = a["volume_annotation"]["author"]
        year = a["volume_annotation"]["year"]
        stories_info[a["story_id"]] = (title, author, year)

# Create the selectbox with title and author
story_titles = [f"{info[0]} by {info[1]}" for info in stories_info.values()]
selected_story_title = st.selectbox("Select story:", story_titles)

# Find the selected story_id
selected_story_id = next(story_id for story_id, info in stories_info.items() if f"{info[0]} by {info[1]}" == selected_story_title)

# Get matching parts for the selected story_id
matching_parts = [a for a in annotations if a["story_id"] == selected_story_id]
parts = sorted(set(a["part"] for a in matching_parts))
selected_part = st.selectbox("Select part:", parts)

selected_entry = next((a for a in annotations if a["story_id"] == selected_story_id and a["part"] == selected_part), None)

if selected_entry:
    # Display only the general metadata (Author, Year, Title) before the text
    vol = selected_entry["volume_annotation"]
    # Clean up year if necessary (convert float to int)
    year = int(vol["year"]) if isinstance(vol["year"], float) else vol["year"]

    st.markdown(f"""
    ### 📚 Metadata
    - **Author:** {vol["author"]}
    - **Year:** {year}
    - **Title:** *{vol["title"]}*
    """)

    # Display the original text after the general metadata
    st.markdown("### Original Text")
    st.write(selected_entry["text"])

    # Button to show lemmatized text
    if st.button("Show Lemmatized Text"):
        st.markdown("### Lemmatized Text")
        st.write(selected_entry["lemmatized_text"])

    # Display positional tags (annotations)
    st.markdown("### 🎯 Sound Categories by Words")
    if selected_entry["positional_tags"]["tags"]:
        for tag in selected_entry["positional_tags"]["tags"]:
            st.markdown(f"- **{tag['text']}** → {', '.join(tag['labels'])} *(lemma: {tag['lemma']})*")
    else:
        st.info("No tags in this part.")

    # Display volume annotations (sound category info)
    st.markdown("### 📊 Sound Volume per Paragraph")

    vol = selected_entry["volume_annotation"]
    st.markdown(f"""
    - **Sound Type:** {vol["sound_type"]}
    - **Human:** {vol["human"]}/4, **Nature:** {vol["nature"]}/4, **Artificial:** {vol["artificial"]}/4
    """)
    st.markdown("""
 Sound Type Descriptions:
- **d (Diegetic)**: Sound that originates within the story world (e.g., footsteps, dialogue).
- **nd (Non-diegetic)**: Sound that is external to the story world (e.g., description of regular actions, memories, etc.).
- **dnd (Both types)**: A mix of diegetic and non-diegetic sounds.
""")
else:
    st.warning("No annotation found for this selection.")


# --- Load CSV from S3 ---
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

# --- UI: Select Category ---
categories = df['category'].unique()
selected_category = st.selectbox("Choose category:", categories)

# --- Filter & Generate Word Cloud ---
filtered_df = df[df['category'] == selected_category]


if filtered_df.empty:
    st.warning("No words yet :(")
else:
    word_freq = dict(zip(filtered_df['lemma'], filtered_df['freq']))

    wordcloud = WordCloud(
        width=800,
        height=400,
        background_color='white'
    ).generate_from_frequencies(word_freq)

    st.subheader(f"Wordcloud for category: {selected_category}")
    fig, ax = plt.subplots()
    ax.imshow(wordcloud, interpolation='bilinear')
    ax.axis("off")
    st.pyplot(fig)

# Show DataFrame slice for selected category
st.subheader("🔍 Words in Selected Category")
st.dataframe(df[df["category"] == selected_category])

st.markdown("---")
st.markdown(
    "<p style='text-align: center; color: gray;'>🚧 This project is a work in progress – part of the SiS:TER corpus exploration.</p>",
    unsafe_allow_html=True
)

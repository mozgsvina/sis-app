import streamlit as st
import pandas as pd
import boto3
from io import StringIO
from wordcloud import WordCloud
import matplotlib.pyplot as plt
import json
import io


# AWS S3 Configuration
bucket_name = st.secrets["aws"]["aws_bucket_name"]
aws_access_key = st.secrets["aws"]["aws_access_key_id"]
aws_secret_key = st.secrets["aws"]["aws_secret_access_key"]
aws_region = st.secrets["aws"]["aws_region"]
jsonl_key = st.secrets["aws"]["aws_jsonl_key"]

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

st.title("🎧 SiS:TER Corpus Explorer")

import streamlit as st

tab1, tab2, tab3 = st.tabs(["About", "Search", "Wordclouds"])

with tab1:
    st.markdown("""
    **Sound in Stories: Tagging, Exploration, Research**

    This corpus is a collection of short stories, each annotated on two levels:
    - **Lexical annotation** (focused on identifying and categorizing words in the text, e.g., human, nature, mechanic sounds)
    - **Sound volume annotation** (the loudness of the paragraph by three dimensions).

    The corpus comprises *240 short stories* covering the *XX century*. Use the filters on the left bar to explore the **annotation per paragraph**.
    """)

    st.markdown("""
    ### 🧑‍💻 Project Team

    - 📧 Margarita Kirina: [mkirina2412@gmail.com](mailto:mkirina2412@gmail.com)
    - 🛠 Anna Moskvina: [moskvina.anya@gmail.com](mailto:moskvina.anya@gmail.com)
    - 🔍 Ruslan Rodionov: [rrodionov447@gmail.com](mailto:rrodionov447@gmail.com)

    For questions and feedback feel free to reach out!
    """)
with tab2:
    # --- Filters Sidebar ---
    st.sidebar.markdown("<br>", unsafe_allow_html=True)
    st.sidebar.header("🔎 Filters")
    st.sidebar.markdown("Use the filters below to search the annotations. The results are shown on the :blue-background[Search] tab.")
    
    st.sidebar.markdown("### Filter by Sound Type")
    sound_types = ["d", "nd", "dnd"]
    selected_sound_types = st.sidebar.multiselect("Select Sound Type:", sound_types, default=sound_types)

    all_labels = set(
        label for a in annotations
        for l in a.get("annotations", {}).get("token_level", {}).get("labels", [])
        for label in l.get("labels", [])
    )
    st.sidebar.markdown("### Filter by Sound Categories")
    selected_labels = st.sidebar.multiselect("Select Token-Level Labels:", sorted(all_labels))

    years = [a['metadata']['year'] for a in annotations if 'metadata' in a and isinstance(a['metadata'].get('year'), int)]
    min_year, max_year = min(years), max(years)
    st.sidebar.markdown("### Filter by Year Range")

    year_start = st.sidebar.number_input("Start Year", min_value=min_year, max_value=max_year, value=min_year)
    year_end = st.sidebar.number_input("End Year", min_value=min_year, max_value=max_year, value=max_year)
    st.sidebar.markdown("### Filter by Volume Levels (0 to 4)")

    volume_human = st.sidebar.slider("Human Volume", 0, 4, (0, 4))
    volume_nature = st.sidebar.slider("Nature Volume", 0, 4, (0, 4))
    volume_artificial = st.sidebar.slider("Artificial Volume", 0, 4, (0, 4))

    def safe_int(value):
        try:
            return int(value)
        except (ValueError, TypeError):
            return 0


    # --- Filter Logic ---
    def paragraph_matches_filters(entry):
        meta = entry.get("metadata", {})
        year = meta.get("year")

        if year is None or not (year_start <= year <= year_end):
            return False

        para_sound_type = entry.get("annotations", {}).get("paragraph_level", {}).get("sound_type")
        if selected_sound_types and para_sound_type not in selected_sound_types:
            return False

        volume = entry.get("annotations", {}).get("paragraph_level", {}).get("volume", {})
        vol_human = safe_int(volume.get("human", 0))
        vol_nature = safe_int(volume.get("nature", 0))
        vol_artificial = safe_int(volume.get("artificial", 0))

        if not (volume_human[0] <= vol_human <= volume_human[1]):
            return False
        if not (volume_nature[0] <= vol_nature <= volume_nature[1]):
            return False
        if not (volume_artificial[0] <= vol_artificial <= volume_artificial[1]):
            return False


        if selected_labels:
            token_labels = entry.get("annotations", {}).get("token_level", {}).get("labels", [])
            paragraph_labels = {label for t in token_labels for label in t.get("labels", [])}
            if not any(label in paragraph_labels for label in selected_labels):
                return False

        return True


    filtered_annotations = [a for a in annotations if paragraph_matches_filters(a)]
    N_DISPLAY = 20
    filtered_annotations = filtered_annotations[:N_DISPLAY]


    st.markdown("## 🔍 Filtered Paragraphs")
    st.markdown(f"***{len(filtered_annotations)}*** paragraphs found, first ***{N_DISPLAY}*** shown.")


    PAGE_SIZE = 1  # show 1 paragraph per page
    total_pages = len(filtered_annotations) // PAGE_SIZE + (len(filtered_annotations) % PAGE_SIZE > 0)

    # col1, col2, col3 = st.columns([1, 2, 2]) 
    # with col1:
    #     page_number = st.number_input(
    #         label="**Go to page:**",
    #         min_value=1,
    #         max_value=total_pages,
    #         value=1,
    #         step=1,
    #     )



    # start_idx = (page_number - 1) * PAGE_SIZE
    # end_idx = start_idx + PAGE_SIZE
    if 'page_number' not in st.session_state:
        st.session_state.page_number = 1

    col1, col2, col3 = st.columns([1, 1, 1])

    with col1:
        if st.button("⬅️ Previous") and st.session_state.page_number > 1:
            st.session_state.page_number -= 1

    with col3:
        if st.button("Next ➡️") and st.session_state.page_number < total_pages:
            st.session_state.page_number += 1

    st.markdown(f"**Page {st.session_state.page_number} of {total_pages}**")

    start_idx = (st.session_state.page_number - 1) * PAGE_SIZE
    end_idx = start_idx + PAGE_SIZE

    for entry in filtered_annotations[start_idx:end_idx]:
        meta = entry.get("metadata", {})
        st.markdown(f"**Title, Author, Year:** «{meta.get('title', 'Unknown Title')}» by {meta.get('author', 'Unknown Author')} ({meta.get('year', 'Unknown Year')})")

        text = entry["text"]
        token_labels = entry.get("annotations", {}).get("token_level", {}).get("labels", [])

        if selected_labels:
            for token in token_labels:
                if any(lbl in selected_labels for lbl in token['labels']):
                    text = text.replace(token['text'], f":violet-background[{token['text']}]")

        volume = entry["annotations"]["paragraph_level"]["volume"]
        st.markdown(f"**Sound Type & Volume: :orange-badge[{entry['annotations']['paragraph_level']['sound_type']} *] :blue-badge[🗣️ Human: {volume['human']}/4]   :green-badge[🍃 Nature: {volume['nature']}/4]   :red-badge[🖨️ Artificial: {volume['artificial']}/4]**")

        # st.write(text)
        container = st.container(border=True)
        container.write(text)

        st.write("**All Annotations in Paragraph:**")
        if token_labels:
            df_tokens = pd.DataFrame([{
                "Text": t["text"],
                "Lemma": t["lemma"],
                "Labels": ', '.join(t["labels"]),
                "Start-End": f"{t['start']}-{t['end']}"
            } for t in token_labels])
            st.dataframe(df_tokens)
        else:
            st.info("No token-level annotations.")

        st.caption(""" \*
        - **d (Diegetic)**: Sound that originates within the story world (e.g., footsteps, dialogue).
        - **nd (Non-diegetic)**: Sound that is external to the story world (e.g., description of regular actions, memories, etc.).
        - **dnd (Both types)**: A mix of diegetic and non-diegetic sounds.
        """)

    st.markdown("---")

    # --- Export Functionality ---
    st.markdown("## 📤 Export Filtered Results")

    export_format = st.selectbox("Select export format:", ["CSV", "JSONL"])

    if st.button("Download First 20 Results"):
        export_data = filtered_annotations[:N_DISPLAY]
        if export_format == "CSV":
            rows = []
            for e in export_data:
                meta = e.get("metadata", {})
                rows.append({
                    "Story ID": e["story_id"],
                    "Part": e["part"],
                    "Author": meta.get("author"),
                    "Title": meta.get("title"),
                    "Year": meta.get("year"),
                    "Text": e["text"],
                    "Sound Type": e["annotations"]["paragraph_level"]["sound_type"],
                    "Volume Human": e["annotations"]["paragraph_level"]["volume"]["human"],
                    "Volume Nature": e["annotations"]["paragraph_level"]["volume"]["nature"],
                    "Volume Artificial": e["annotations"]["paragraph_level"]["volume"]["artificial"]
                })
            df_export = pd.DataFrame(rows)
            csv_data = df_export.to_csv(index=False)
            st.download_button("Download CSV", csv_data, file_name="filtered_results.csv", mime='text/csv')

        elif export_format == "JSONL":
            jsonl_data = "\n".join(json.dumps(item, ensure_ascii=False) for item in export_data)
            st.download_button("Download JSONL", jsonl_data, file_name="filtered_results.jsonl", mime='application/json')


with tab3:
# --- Wordcloud Section ---
    st.markdown("## 🧠 Sound Wordclouds")
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

    df = load_data()

    categories = df['category'].unique()
    selected_category = st.selectbox("Choose wordcloud category:", categories)

    filtered_df = df[df['category'] == selected_category]

    if not filtered_df.empty:
        word_freq = dict(zip(filtered_df['lemma'], filtered_df['freq']))
        wordcloud = WordCloud(width=800, height=400, background_color='white').generate_from_frequencies(word_freq)

        st.subheader(f"Wordcloud for category: {selected_category}")

        fig, ax = plt.subplots()
        ax.imshow(wordcloud, interpolation='bilinear')
        ax.axis("off")
        st.pyplot(fig)

        st.subheader("🔍 Words in Selected Category")
        st.dataframe(filtered_df)
    else:
        st.warning("No words yet :(")




st.markdown("---")

st.markdown(
    "<p style='text-align: center; color: gray;'>🚧 This project is a work in progress – part of the SiS:TER corpus exploration. The research is conducted within the framework of the project “Text as Big Data: Methods and Models for Working with Large Textual Data”, carried out at the Linguistic Convergence Laboratory, HSE University.</p>",
    unsafe_allow_html=True
)

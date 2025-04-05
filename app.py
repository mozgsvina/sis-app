import streamlit as st
import pandas as pd
import boto3
from io import StringIO
from wordcloud import WordCloud
import matplotlib.pyplot as plt


# AWS S3 Configuration
bucket_name = "sis-annotation"
file_key = "sound_cats_lemmas_w_freqs.csv"

# Load AWS credentials from Streamlit secrets
aws_access_key = st.secrets["aws"]["aws_access_key_id"]
aws_secret_key = st.secrets["aws"]["aws_secret_access_key"]
aws_region = st.secrets["aws"]["aws_region"]

# --- Load CSV from S3 ---
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

# --- UI: Select Category ---

st.markdown(
    """
    # 🎧 SiS:TER  
    **Sound in Stories: Tagging, Exploration, Research**

    Exploring the role of *diegetic* and *non-diegetic* sound in Russian short stories through data annotation and visualization.
    """
)

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

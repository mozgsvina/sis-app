import streamlit as st
import boto3
import pandas as pd
from io import BytesIO
import matplotlib.pyplot as plt

# AWS S3 Configuration
bucket_name = "sis-annotation"
file_key = "tumanova_2.xlsx"

# Load AWS credentials from Streamlit secrets
aws_access_key = st.secrets["aws"]["aws_access_key_id"]
aws_secret_key = st.secrets["aws"]["aws_secret_access_key"]
aws_region = st.secrets["aws"]["aws_region"]

# Initialize S3 client using the secrets
s3 = boto3.client(
    "s3",
    aws_access_key_id=aws_access_key,
    aws_secret_access_key=aws_secret_key,
    region_name=aws_region
)

@st.cache_data  # Cache the result to optimize performance
def load_data():
    # Download the file from S3
    obj = s3.get_object(Bucket=bucket_name, Key=file_key)
    data = obj['Body'].read()
    
    # Read the Excel file into a pandas DataFrame
    df = pd.read_excel(BytesIO(data))
    
    # Data Cleaning:
    # 1) Drop rows where 'sound_type' is 0
    df = df[df['sound_type'] != 0]
    
    # 2) Strip any extra spaces in 'sound_type' column values
    df['sound_type'] = df['sound_type'].str.strip()
    
    return df

# Load the data
df = load_data()

# Preview the dataset
st.title("Sound Annotation Analysis")
st.write(df.head())  # Show the first few rows of the dataset

# Visualize the distribution of sound volume by sound type
st.header("Sound Volume Distribution by Type")
# Group by sound type and calculate the mean of the volumes
volume_columns = ['human', 'nature', 'artificial']
df_grouped = df.groupby('sound_type')[volume_columns].mean()

# Plotting the distribution
fig, ax = plt.subplots(figsize=(10, 6))
df_grouped.plot(kind='bar', ax=ax)
ax.set_title('Average Sound Volume by Sound Type')
ax.set_ylabel('Volume (0-4)')
ax.set_xlabel('Sound Type')

# Display the plot in Streamlit
st.pyplot(fig)

# Modify the line plot: Use the 'year' column for time-based trends
st.header("Sound Volume Trends Over Time")

# Group by year and calculate the mean of the volumes
df_year_grouped = df.groupby('year')[volume_columns].mean()

# Plotting the trends over time (year on the x-axis)
fig2, ax2 = plt.subplots(figsize=(10, 6))
df_year_grouped.plot(kind='line', ax=ax2, marker='o')
ax2.set_title('Sound Volume Trends Over Time')
ax2.set_ylabel('Volume (0-4)')
ax2.set_xlabel('Year')

# Display the line plot in Streamlit
st.pyplot(fig2)

# Add Selectbox for sound_type filter
sound_types = df['sound_type'].unique()  # Get unique sound types from the data
selected_sound_type = st.selectbox('Choose Sound Type:', sound_types)

# Filter the dataframe based on the selected sound type
filtered_df = df[df['sound_type'] == selected_sound_type]

# Add a slider to filter by year range (1900 to 1999)
year_range = st.slider('Select Year Range:', min_value=1900, max_value=1999, value=(1900, 1999))

# Filter the dataframe based on the selected year range
filtered_df = filtered_df[(filtered_df['year'] >= year_range[0]) & (filtered_df['year'] <= year_range[1])]

# Display the filtered data
st.write("Filtered Data:", filtered_df)

# Optionally, you can display some statistics or visualizations
st.write("Summary Statistics:")
st.write(filtered_df.describe())

# Example: You can also display a chart or plot the filtered data
st.bar_chart(filtered_df.groupby('year')['human'].mean())  # Adjust this to fit your needs
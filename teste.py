
import streamlit as st

# Initialize connection.
conn = st.connection("neon", type="sql")

# Perform query.
df = conn.query('SELECT * FROM unimed.base_pep;', ttl="10m")

# Print results.
st.dataframe(df)
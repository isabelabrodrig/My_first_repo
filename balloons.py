import streamlit as st 


b= st.text_input('Nome')
st.write(f"bom dia {b}")
a = st.button('me aperte para ver balões')
print(a)
if a == True:
    st.balloons()
import streamlit as st 
with st.form('Inside form'):
    b= st.text_input('Nome')
    c= st.text_input('data de nascimento')
    d= st.text_input('salario')
    e= st.selectbox('cor favorita', ['azul', 'vermelho', 'rosa', 'amarelo','verde', 'roxo'])
    
    st.form_submit_button()

   
a = st.button(f'me aperte para ver balões {b}')
st.write(f"bom dia {b}")
st.write(f'Cor favorita:{e}')
print(a)
if a == True:
    st.balloons()


  

import streamlit as st
import boto3
import pandas as pd
from config import cargar_configuracion
from app import main as app

# Cargar configuración
aws_access_key, aws_secret_key, region_name, bucket_name, valid_user, valid_password = cargar_configuracion()

# Establecer el modo wide como predeterminado
st.set_page_config(layout="wide")

# Conecta a S3
s3 = boto3.client('s3', aws_access_key_id=aws_access_key, aws_secret_access_key=aws_secret_key, region_name=region_name)

# Definir las variables para el estado de inicio de sesión
logged_in = st.session_state.get("logged_in", False)
user_nombre_apellido = st.session_state.get("user_nombre_apellido", "")
user_rol = st.session_state.get("user_rol", "")

# Función para verificar las credenciales y obtener el rol del usuario
def login(username, password):
    try:
        # Capitalizar el nombre de usuario ingresado
        username = username.strip().title()

        # Verificar si el nombre de usuario y contraseña coinciden con los valores cargados de la configuración
        if username == valid_user and password == valid_password:
            st.session_state.logged_in = True
            st.session_state.user_rol = "admin"  # Puedes personalizar el rol según sea necesario
            st.session_state.user_nombre_apellido = username
            st.session_state.id_usuario = 1  # ID ficticio, puedes asignar otro valor
            st.rerun()
        else:
            st.error("Credenciales incorrectas. Inténtalo de nuevo")
    
    except Exception as e:
        st.error(f"Error al procesar el inicio de sesión: {e}")

# Función para cerrar sesión
def logout():
    st.session_state.logged_in = False
    st.session_state.user_rol = ""
    st.session_state.user_nombre_apellido = ""  # Limpiar el nombre y apellido al cerrar sesión
    st.success("Sesión cerrada exitosamente")

def main():    
    st.markdown("<h1 style='text-align: center;'>Sistema de Gestión de Colectivos</h1>", unsafe_allow_html=True)

    # st.image("img/logo-six-gym-fondo-amarillo.png", use_column_width= "always")

    if logged_in:
        app()
        # st.sidebar.title("Menú")

        # if user_rol == "admin":
        #     selected_option = st.sidebar.selectbox("Seleccione una opción:", ["Reservas","Usuarios"])
        #     if selected_option == 'Reservas':
        #         reservas()

        #     if selected_option == "Usuarios":
        #         st.title('Usuarios')
        #         usuarios()      

        st.write(f"Usuario: {user_nombre_apellido}")

    else:
        with st.form(key="login_form"):
            username = st.text_input("Nombre de Usuario:")
            password = st.text_input("Contraseña:", type="password")

            login_submitted = st.form_submit_button("Iniciar Sesión")

            if login_submitted and username and password:
                login(username, password)

if __name__ == "__main__":
    main()
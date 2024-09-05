# login_module.py

import streamlit as st
from config import cargar_configuracion

def login(username, password):
    # Cargar configuración
    _, _, _, _, valid_user, valid_password = cargar_configuracion()

    # Verifica si el usuario y la contraseña son correctos
    if username == valid_user and password == valid_password:
        st.session_state["authenticated"] = True
        st.session_state["username"] = username  # Guardar el nombre de usuario en sesión
        st.success("Login exitoso")
    else:
        st.error("Usuario o contraseña incorrectos")
        st.session_state["authenticated"] = False

def logout():
    # Limpiar el estado de autenticación
    st.session_state["authenticated"] = False
    st.session_state["username"] = None
    st.success("Sesión cerrada")

def main():
    if "authenticated" not in st.session_state:
        st.session_state["authenticated"] = False

    if st.session_state["authenticated"]:
        # Mostrar contenido de la aplicación
        st.sidebar.button("Cerrar Sesión", on_click=logout)
        st.title("Bienvenido a la Aplicación")
        # Aquí colocas el código de la aplicación
        # Por ejemplo: mostrar datos, formularios, gráficos, etc.
        
        # Mostrar contenido de la aplicación
        # Ejemplo:
        st.write(f"Hola, {st.session_state['username']}")

    else:
        # Mostrar formulario de login
        st.sidebar.title("Inicio de Sesión")

        with st.form(key="login_form"):
            username = st.text_input("Nombre de Usuario:")
            password = st.text_input("Contraseña:", type="password")

            login_submitted = st.form_submit_button("Iniciar Sesión")

            if login_submitted and username and password:
                login(username, password)

if __name__ == "__main__":
    main()

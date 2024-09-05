import streamlit as st
import boto3
import pandas as pd
from io import StringIO
from datetime import datetime
from config import cargar_configuracion

# Lista de números de colectivos válidos
numeros_colectivos = [
    1, 2, 3, 4, 6, 7, 8, 9, 10, 11, 12, 15, 18, 52,
    101, 102, 103, 104, 105, 106, 107, 108, 109, 110,
    111, 112, 113, 114, 115, 116, 117, 118, 119, 120, 121
]

# Establecer el modo wide como predeterminado
st.set_page_config(layout="wide")

# Cargar configuración
aws_access_key, aws_secret_key, region_name, bucket_name, valid_user, valid_password = cargar_configuracion()

# Configuración de AWS S3
s3 = boto3.client(
    's3',
    aws_access_key_id=aws_access_key,
    aws_secret_access_key=aws_secret_key,
    region_name=region_name
)

# Funciones para cargar datos desde S3
def load_csv_from_s3(filename):
    try:
        obj = s3.get_object(Bucket=bucket_name, Key=filename)
        data = pd.read_csv(obj['Body'])
        return data
    except Exception as e:
        st.error(f"Error al cargar {filename}: {e}")
        return pd.DataFrame()

# Cargar los datos
diesel_data = load_csv_from_s3('cargas_diesel.csv')
service_data = load_csv_from_s3('servicios_realizados.csv')

# Funciones de login
def login():
    st.title("Login")

    # Usa el usuario y la contraseña desde el archivo de configuración
    global valid_user, valid_password

    # Crea campos de entrada para el nombre de usuario y la contraseña
    username = st.text_input("Usuario")
    password = st.text_input("Contraseña", type="password")

    # Verifica si el usuario y la contraseña son correctos
    if st.button("Iniciar Sesión"):
        if username == valid_user and password == valid_password:
            st.session_state["authenticated"] = True
            st.success("Login exitoso")
            return True
        else:
            st.error("Usuario o contraseña incorrectos")
            return False

    return False

# Función para actualizar datos en S3
def update_csv_in_s3(data, filename):
    csv_buffer = StringIO()
    data.to_csv(csv_buffer, index=False)
    s3.put_object(Bucket=bucket_name, Key=filename, Body=csv_buffer.getvalue())

# Formulario de Carga de Diésel
def diesel_form(colectivos_list, diesel_data):
    with st.expander("Registrar Carga de Diésel"):
        coche = st.number_input("Número de Coche", min_value=0)
        
        if coche not in colectivos_list:
            st.error("Número de coche no válido. Por favor, ingresa un número de coche válido.")
        else:
            fecha = st.date_input("Fecha", value=datetime.now().date())
            litros = st.number_input("Litros Cargados", min_value=0)
            hora = datetime.now().strftime('%H:%M')
            
            if st.button("Registrar Carga"):
                # Crear una nueva entrada
                new_entry = pd.DataFrame([{'idCarga': len(diesel_data) + 1, 'fecha': fecha, 'hora': hora, 'coche': coche, 'litros': litros, 'litrosServi': 5000 - litros}])
                
                # Agregar la nueva entrada al DataFrame
                diesel_data = pd.concat([diesel_data, new_entry], ignore_index=True)
                
                # Actualizar el archivo CSV en S3
                update_csv_in_s3(diesel_data, 'cargas_diesel.csv')
                
                st.success("Carga de diésel registrada correctamente.")

# Registro de Servicios
def service_form(colectivos_list, diesel_data, service_data):
    with st.expander("Registrar Servicio"):
        coche = st.number_input("Número de Coche Servi", min_value=0)
        if coche not in colectivos_list:
            st.info("Ingrese un número de coche válido")
        else:
            fecha = st.date_input("Fecha del Servicio", value=datetime.now().date())
            hora = datetime.now().strftime('%H:%M')
            
            last_service = service_data[service_data['coche'] == coche].max()
            if not last_service.empty:
                last_service_date = datetime.strptime(last_service['fecha'], '%Y-%m-%d').strftime('%d/%m/%Y')
                st.write(f"Último servicio: {last_service_date}")
            else:
                st.write("No hay registros de servicio previos para este coche.")
            
            litros_cargados = diesel_data[diesel_data['coche'] == coche]['litros'].sum()

            service_done = st.checkbox("Servicio Realizado")

            if service_done and st.button("Registrar Servicio"):
                new_entry = pd.DataFrame([{'idServis': len(service_data) + 1, 'fecha': fecha.strftime('%Y-%m-%d'), 'hora': hora, 'coche': coche, 'litrosTotales': litros_cargados, 'litrosUltimoServi': litros_cargados, 'fechaAnterior': last_service['fecha'] if not last_service.empty else 'N/A'}])
                service_data = pd.concat([service_data, new_entry], ignore_index=True)
                update_csv_in_s3(service_data, 'servicios_realizados.csv')
                
                # Reiniciar litrosServi en diesel_data
                diesel_data.loc[diesel_data['coche'] == coche, 'litrosServi'] = 5000
                update_csv_in_s3(diesel_data, 'cargas_diesel.csv')
                
                st.success("Servicio registrado correctamente")

# Mostrar tabla de Cargas de Diésel
def show_diesel_history(diesel_data):
    with st.expander("Historial de Cargas"):
        # Ordenar el DataFrame por la columna idCarga de mayor a menor
        sorted_diesel_data = diesel_data.sort_values(by='idCarga', ascending=False)
        
        # Función para determinar el color del texto basado en los valores de litrosServi
        def colorize_litros_servi(value):
            if value <= 100:
                return 'color: red'
            elif value <= 500:
                return 'color: yellow'
            else:
                return 'color: green'
        
        # Aplicar el estilo a la columna litrosServi sin mostrar la columna color
        styled_df = sorted_diesel_data.style.applymap(colorize_litros_servi, subset=['litrosServi'])
        st.dataframe(styled_df)

# Mostrar tabla de Servicios
def show_service_history(service_data):
    with st.expander("Historial de Servicios"):
        st.dataframe(service_data.sort_values(by=['fecha', 'hora'], ascending=[False, False]))

# Función Principal
def main():
    if "authenticated" not in st.session_state:
        st.session_state["authenticated"] = False

    if st.session_state["authenticated"] or login():
        st.title("Sistema de Gestión de Colectivos")

        # Ingreso de Datos
        colectivos_list = [coche for coche in numeros_colectivos if coche in diesel_data['coche'].unique()]
        diesel_form(colectivos_list, diesel_data)
        show_diesel_history(diesel_data)
        service_form(colectivos_list, diesel_data, service_data)
    
        show_service_history(service_data)
    else:
        st.warning("Por favor, inicia sesión para continuar")

if __name__ == "__main__":
    main()

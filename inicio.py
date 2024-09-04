import streamlit as st
import boto3
import pandas as pd
from io import StringIO
from datetime import datetime
from config import cargar_configuracion
import altair as alt

# Lista de números de colectivos válidos
numeros_colectivos = [
    1, 2, 3, 4, 6, 7, 8, 9, 10, 11, 12, 15, 18, 52,
    101, 102, 103, 104, 105, 106, 107, 108, 109, 110,
    111, 112, 113, 114, 115, 116, 117, 118, 119, 120, 121
]

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

# Funciones para los Indicadores

# Indicador: Coche Próximo a Servicio
def calculate_service_status(diesel_data):
    # Agrupar los datos por coche y calcular los litros restantes
    diesel_sums = diesel_data.groupby('coche')['litros'].sum().reset_index()
    diesel_sums['litros_restantes'] = 5000 - diesel_sums['litros']
    
    # Crear una columna para el color basado en los litros restantes
    def get_color(litros_restantes):
        if litros_restantes > 500:
            return 'green'
        elif 0 < litros_restantes <= 500:
            return 'yellow'
        else:
            return 'red'
    
    diesel_sums['color'] = diesel_sums['litros_restantes'].apply(get_color)
    
    # Crear el gráfico de columnas con Altair
    chart_service_status = alt.Chart(diesel_sums).mark_bar().encode(
        x=alt.X('coche:O', title='Número de Coche'),
        y=alt.Y('litros_restantes:Q', title='Litros Restantes'),
        color=alt.Color('color:N', scale=alt.Scale(domain=['green', 'yellow', 'red'], range=['green', 'yellow', 'red'])),
        tooltip=['coche', 'litros_restantes']
    ).properties(
        title='Coches Próximos a Servicio',
        width=300,  # Ajustar el ancho del gráfico
        height=200  # Ajustar la altura del gráfico
    )
    
    # Crear dos columnas
    col1, col2 = st.columns(2)

    with col1:
        st.altair_chart(chart_service_status, use_container_width=True)

    with col2:
        # Mostrar gráfico de ranking de colectivos en la segunda columna
        rank_colectivos_by_diesel(diesel_data)

# Indicador: Colectivos con Más Carga de Diésel
def rank_colectivos_by_diesel(diesel_data):
    # Filtra datos para evitar números de coches no válidos
    diesel_data = diesel_data[diesel_data['coche'].isin(numeros_colectivos)]
    
    last_30_days = diesel_data[diesel_data['fecha'] >= (datetime.now() - pd.Timedelta(days=30)).strftime('%Y-%m-%d')]
    top_colectivos = last_30_days.groupby('coche')['litros'].sum().sort_values(ascending=False).reset_index()
    
    # Crear el gráfico de columnas con Altair
    chart_ranking = alt.Chart(top_colectivos).mark_bar().encode(
        x=alt.X('coche:O', title='Número de Coche'),
        y=alt.Y('litros:Q', title='Litros Cargados'),
        color=alt.value('blue'),
        tooltip=['coche', 'litros']
    ).properties(
        title='Ranking de Colectivos por Carga de Diésel en los Últimos 30 Días',
        width=300,  # Ajustar el ancho del gráfico
        height=200  # Ajustar la altura del gráfico
    )
    
    st.altair_chart(chart_ranking, use_container_width=True)

# Indicador: Frecuencia de Servicios
def calculate_service_frequency(service_data):
    service_data['fecha'] = pd.to_datetime(service_data['fecha'])
    frequency = service_data.groupby('coche').apply(lambda x: x['fecha'].diff().mean().days).reset_index(name='dias_promedio')
    frequency = frequency.sort_values(by='dias_promedio')
    st.bar_chart(frequency.set_index('coche')['dias_promedio'])

# Formularios de Ingreso de Datos

# Formulario de Carga de Diésel
def diesel_form(colectivos_list):
    with st.expander("Registrar Carga de Diésel"):
        coche = st.selectbox("Número de Coche Carga", colectivos_list)
        litros = st.number_input("Litros Cargados", min_value=0)
        fecha_hora = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        
        if st.button("Registrar Carga"):
            new_entry = {'fecha': fecha_hora.split()[0], 'hora': fecha_hora.split()[1], 'coche': coche, 'litros': litros}
            diesel_data = diesel_data.append(new_entry, ignore_index=True)
            update_csv_in_s3(diesel_data, 'cargas_diesel.csv')
            st.success("Carga de diésel registrada correctamente.")

# Registro de Servicios
def service_form(colectivos_list, diesel_data, service_data):
    with st.expander("Registrar Servicio"):
        coche = st.selectbox("Número de Coche", colectivos_list, key='selectbox_coche')
        last_service = service_data[service_data['coche'] == coche].max()
        litros_cargados = diesel_data[diesel_data['coche'] == coche]['litros'].sum()

        st.write(f"Último servicio: {last_service['fecha']} a las {last_service['hora']}")
        st.write(f"Litros cargados desde el último servicio: {litros_cargados}")

        service_done = st.checkbox("Servicio Realizado")

        if service_done and st.button("Registrar Servicio"):
            new_entry = {'fecha': datetime.now().strftime('%Y-%m-%d'), 'hora': datetime.now().strftime('%H:%M:%S'), 'coche': coche, 'litros': litros_cargados}
            service_data = service_data.append(new_entry, ignore_index=True)
            update_csv_in_s3(service_data, 'servicios_realizados.csv')
            diesel_data = diesel_data[diesel_data['coche'] != coche]
            update_csv_in_s3(diesel_data, 'cargas_diesel.csv')
            st.success("Servicio registrado correctamente.")

# Funciones para actualizar datos en S3

def update_csv_in_s3(data, filename):
    csv_buffer = StringIO()
    data.to_csv(csv_buffer, index=False)
    s3.put_object(Bucket=bucket_name, Key=filename, Body=csv_buffer.getvalue())

# Visualización de Tablas

def show_diesel_history(diesel_data):
    with st.expander("Historial de Cargas de Diésel"):
        st.dataframe(diesel_data.sort_values(by=['fecha', 'hora'], ascending=[False, False]))

def show_service_history(service_data):
    with st.expander("Historial de Servicios"):
        st.dataframe(service_data.sort_values(by=['fecha', 'hora'], ascending=[False, False]))

# Función Principal

def main():
    if "authenticated" not in st.session_state:
        st.session_state["authenticated"] = False

    if st.session_state["authenticated"] or login():
        st.title("Sistema de Gestión de Colectivos")
        
        # Indicadores
        st.header("Indicadores")
        calculate_service_status(diesel_data)
        # rank_colectivos_by_diesel(diesel_data)
        # calculate_service_frequency(service_data)

        # Ingreso de Datos
        st.header("Registro de Datos")
        colectivos_list = [coche for coche in numeros_colectivos if coche in diesel_data['coche'].unique()]
        diesel_form(colectivos_list)
        service_form(colectivos_list, diesel_data, service_data)

        # Tablas de Historial
        st.header("Historial de Cargas y Servicios")
        show_diesel_history(diesel_data)
        show_service_history(service_data)
    else:
        st.warning("Por favor, inicia sesión para continuar")

if __name__ == "__main__":
    main()

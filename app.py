import streamlit as st
import boto3
import pandas as pd
from io import StringIO
from datetime import datetime
from config import cargar_configuracion
from datetime import datetime
import time

# Establecer el modo wide como predeterminado
st.set_page_config(layout="wide")

# Lista de números de colectivos válidos
numeros_colectivos = [
    1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 18, 52,
    101, 102, 103, 104, 105, 106, 107, 108, 109, 110, 111, 112, 113, 114, 115, 116, 117, 118, 119, 120
]

numeros_tigre = [
    1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 18, 52
]

numeros_alderete = [
    101, 102, 103, 104, 105, 106, 107, 108, 109, 110, 111, 112, 113, 114, 115, 116, 117, 118, 119, 120
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

# Función para actualizar datos en S3
def update_csv_in_s3(data, filename):
    csv_buffer = StringIO()
    data.to_csv(csv_buffer, index=False)
    s3.put_object(Bucket=bucket_name, Key=filename, Body=csv_buffer.getvalue())

# Formulario de Carga de Diésel
def diesel_form(numeros_colectivos, diesel_data):
    # Crear las tres columnas
    col1, col2, col3 = st.columns([2, 1, 1])  # La primera columna es el doble de ancha

    # Formulario en las dos primeras columnas
    with col1:
        st.header("Registrar Carga de Diésel")
        coche = st.number_input("Número de Coche", min_value=0)

        if coche not in numeros_colectivos:
            st.info("Ingrese un número de coche válido")
        else:
            fecha = st.date_input("Fecha", value=datetime.now().date())
            litros = st.number_input("Litros Cargados", min_value=0)
            hora = datetime.now().strftime('%H:%M')

            if st.button("Registrar Carga"):
                # Recargar los datos actuales desde S3 para evitar inconsistencias
                diesel_data = load_csv_from_s3('cargas_diesel.csv')

                # Obtener el valor actual de litrosServi del coche
                if not diesel_data[diesel_data['coche'] == coche].empty:
                    ultimo_servis = diesel_data[diesel_data['coche'] == coche].iloc[-1]['litrosServi']
                else:
                    ultimo_servis = 5000  # Valor inicial si no hay registros previos

                # Calcular los litros restantes después de la nueva carga
                litros_servi_restantes = ultimo_servis - litros

                # Crear una nueva entrada
                new_entry = pd.DataFrame([{
                    'idCarga': len(diesel_data) + 1,
                    'fecha': fecha,
                    'hora': hora,
                    'coche': coche,
                    'litros': litros,
                    'litrosServi': litros_servi_restantes
                }])

                # Agregar la nueva entrada al DataFrame
                diesel_data = pd.concat([diesel_data, new_entry], ignore_index=True)

                # Actualizar el archivo CSV en S3
                update_csv_in_s3(diesel_data, 'cargas_diesel.csv')

                st.success("Carga de diésel registrada correctamente.")

    # Mostrar las tablas de Alderete y Tigre en la tercera columna
    show_custom_tables(diesel_data, col2, col3)

    # Mostrar historial actualizado (esto puede estar en cualquier lugar o ser removido)
    show_diesel_history(diesel_data)

def show_custom_tables(diesel_data, col2, col3):
    # Filtrar datos para Alderete y seleccionar solo las columnas coche y litrosServi
    alderete_data = diesel_data[diesel_data['coche'].isin(numeros_alderete)][['coche', 'litrosServi']]

    # Filtrar datos para Tigre y seleccionar solo las columnas coche y litrosServi
    tigre_data = diesel_data[diesel_data['coche'].isin(numeros_tigre)][['coche', 'litrosServi']]

    # Función para determinar el color del texto basado en los valores de litrosServi
    def colorize_litros_servi(value):
        if value <= 100:
            return 'color: red'
        elif value <= 500:
            return 'color: yellow'
        else:
            return 'color: green'

    # Mostrar la tabla Alderete en la columna col2
    with col2:
        st.markdown('<h3 style="color: yellow;">Alderete</h3>', unsafe_allow_html=True)
        if not alderete_data.empty:
            sorted_alderete_data = alderete_data.sort_values(by='litrosServi', ascending=True)
            styled_alderete_df = sorted_alderete_data.style.applymap(colorize_litros_servi, subset=['litrosServi'])
            st.dataframe(styled_alderete_df, hide_index=True)
        else:
            st.write("No hay datos para Alderete.")

    # Mostrar la tabla Tigre en la columna col3
    with col3:
        st.markdown('<h3 style="color: red;">Tigre</h3>', unsafe_allow_html=True)
        if not tigre_data.empty:
            sorted_tigre_data = tigre_data.sort_values(by='litrosServi', ascending=True)
            styled_tigre_df = sorted_tigre_data.style.applymap(colorize_litros_servi, subset=['litrosServi'])
            st.dataframe(styled_tigre_df, hide_index=True)
        else:
            st.write("No hay datos para Tigre.")

# Mostrar tabla de Cargas de Diésel
def show_diesel_history(diesel_data):
    with st.expander("Historial de Cargas"):

        # Recargar los datos actualizados desde S3 para reflejar cualquier cambio
        diesel_data = load_csv_from_s3('cargas_diesel.csv')

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

# Registro de Servicios
def service_form(numeros_colectivos, diesel_data, service_data):
    with st.expander("Registrar Servicio"):
        coche = st.number_input("Número de Coche Servi", min_value=0)
        
        if coche not in numeros_colectivos:
            st.info("Ingrese un número de coche válido")
        else:
            fecha = st.date_input("Fecha del Servicio", value=datetime.now().date())
            hora = datetime.now().strftime('%H:%M')
            
            # Obtener el último servicio del coche
            last_service = service_data[service_data['coche'] == coche].max()
            
            if not last_service.empty and pd.notna(last_service['fecha']):
                try:
                    # Si la fecha es válida, conviértela al formato correcto
                    last_service_date = datetime.strptime(str(last_service['fecha']), '%Y-%m-%d').strftime('%d/%m/%Y')
                    st.write(f"Último servicio: {last_service_date}")
                except ValueError:
                    st.write("Formato de fecha no válido para el último servicio.")
            else:
                st.write("No hay registros de servicio previos para este coche.")
            
            litros_cargados = diesel_data[diesel_data['coche'] == coche]['litros'].sum()

            service_done = st.checkbox("Servicio Realizado")

            if service_done and st.button("Registrar Servicio"):
                # Crear nueva entrada de servicio
                new_entry = pd.DataFrame([{
                    'idServis': len(service_data) + 1,
                    'fecha': fecha.strftime('%Y-%m-%d'),
                    'hora': hora,
                    'coche': coche,
                    'litrosTotales': litros_cargados,
                    'litrosUltimoServi': litros_cargados,
                    'fechaAnterior': last_service['fecha'] if not last_service.empty and pd.notna(last_service['fecha']) else 'N/A'
                }])
                service_data = pd.concat([service_data, new_entry], ignore_index=True)
                update_csv_in_s3(service_data, 'servicios_realizados.csv')
                
                # Reiniciar litrosServi en diesel_data
                diesel_data.loc[diesel_data['coche'] == coche, 'litrosServi'] = 5000
                update_csv_in_s3(diesel_data, 'cargas_diesel.csv')
                
                st.success("Servicio registrado correctamente.")

                # Esperar 1 segundo antes de recargar la aplicación
                time.sleep(1)
                    
                # Recargar la aplicación
                st.rerun()
                
# Mostrar tabla de Servicios
def show_service_history(service_data):
    with st.expander("Historial de Servicios"):
        service_data = load_csv_from_s3('servicios_realizados.csv')
        st.dataframe(service_data.sort_values(by=['fecha', 'hora'], ascending=[False, False]))

# Función Principal
# def main():
#     # Ingreso de Datos
#     colectivos_list = [coche for coche in numeros_colectivos]
#     diesel_form(colectivos_list, diesel_data)
#     service_form(colectivos_list, diesel_data, service_data)
#     show_service_history(service_data)


# Modificar la función principal para agregar las nuevas tablas
def main():    
    # Ingreso de Datos
    colectivos_list = [coche for coche in numeros_colectivos]
    diesel_form(colectivos_list, diesel_data)
    service_form(colectivos_list, diesel_data, service_data)
    show_service_history(service_data)

if __name__ == "__main__":
    main()
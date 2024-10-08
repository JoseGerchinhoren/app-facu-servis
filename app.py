import streamlit as st
import boto3
import pandas as pd
from io import StringIO
from datetime import datetime
from config import cargar_configuracion
import time

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

# Funciones para cargar y actualizar datos desde y en S3
def load_csv_from_s3(filename):
    try:
        obj = s3.get_object(Bucket=bucket_name, Key=filename)
        data = pd.read_csv(obj['Body'])
        return data
    except Exception as e:
        st.error(f"Error al cargar {filename}: {e}")
        return pd.DataFrame()

def update_csv_in_s3(data, filename):
    csv_buffer = StringIO()
    data.to_csv(csv_buffer, index=False)
    s3.put_object(Bucket=bucket_name, Key=filename, Body=csv_buffer.getvalue())

# Formulario de Carga de Diésel
def diesel_form(diesel_data):
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

    # Mostrar historial actualizado
    show_diesel_history(diesel_data)

def show_custom_tables(diesel_data, col2, col3):
    # Filtrar datos para Alderete y Tigre
    alderete_data = diesel_data[diesel_data['coche'].isin(numeros_alderete)]
    tigre_data = diesel_data[diesel_data['coche'].isin(numeros_tigre)]

    # Asegurarse de que estamos tomando el último valor de litrosServi para cada coche
    alderete_data = alderete_data.groupby('coche').agg({
        'litrosServi': 'last'  # Obtener el último valor de litrosServi para cada coche
    }).reset_index()

    tigre_data = tigre_data.groupby('coche').agg({
        'litrosServi': 'last'  # Obtener el último valor de litrosServi para cada coche
    }).reset_index()

    # Calcular la columna 'litros' como la diferencia entre 5000 y 'litrosServi'
    alderete_data['litros'] = 5000 - alderete_data['litrosServi']
    tigre_data['litros'] = 5000 - tigre_data['litrosServi']

    # Reordenar las columnas
    alderete_data = alderete_data[['coche', 'litros', 'litrosServi']]
    tigre_data = tigre_data[['coche', 'litros', 'litrosServi']]

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
            sorted_alderete_data = alderete_data.sort_values(by='coche', ascending=True)
            styled_alderete_df = sorted_alderete_data.style.applymap(colorize_litros_servi, subset=['litrosServi'])
            st.dataframe(styled_alderete_df, hide_index=True)
        else:
            st.write("No hay datos para Alderete.")

    # Mostrar la tabla Tigre en la columna col3
    with col3:
        st.markdown('<h3 style="color: red;">Tigre</h3>', unsafe_allow_html=True)
        if not tigre_data.empty:
            sorted_tigre_data = tigre_data.sort_values(by='coche', ascending=True)
            styled_tigre_df = sorted_tigre_data.style.applymap(colorize_litros_servi, subset=['litrosServi'])
            st.dataframe(styled_tigre_df, hide_index=True)
        else:
            st.write("No hay datos para Tigre.")

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
        st.dataframe(styled_df, hide_index=True)

def service_form(diesel_data, service_data):
    with st.expander("Registrar Servicio"):
        coche = st.number_input("Número de Coche Servi", min_value=0)
        
        if coche not in numeros_colectivos:
            st.info("Ingrese un número de coche válido")
        else:
            fecha = st.date_input("Fecha del Servicio", value=datetime.now().date())
            hora = datetime.now().strftime('%H:%M')

            # Asegúrate de que 'fecha' es una fecha válida y en formato correcto
            service_data['fecha'] = pd.to_datetime(service_data['fecha'], errors='coerce').dt.strftime('%Y-%m-%d')
            
            # Obtener el último servicio del coche basado en idServis
            last_service = service_data[service_data['coche'] == coche]
            
            # Inicializar variables por defecto
            last_service_date = None
            last_service_litros = 0
            
            if not last_service.empty:
                last_service = last_service.sort_values(by='idServis', ascending=False).iloc[0]
                last_service_date = last_service['fecha'] if pd.notna(last_service['fecha']) else 'No disponible'
                last_service_litros = last_service['litrosTotales'] if pd.notna(last_service['litrosTotales']) else 0
                st.write(f"Último servicio: {last_service_date}, Litros en el último servicio: {last_service_litros}")
            else:
                st.write("No hay registros de servicio previos para este coche.")
            
            # Sumar los litros totales del coche
            litros_cargados = diesel_data[diesel_data['coche'] == coche]['litros'].sum()

            service_done = st.checkbox("Servicio Realizado")

            if service_done and st.button("Registrar Servicio"):
                # Crear nueva entrada de servicio
                new_entry = pd.DataFrame([{
                    'idServis': len(service_data) + 1,
                    'fecha': fecha.strftime('%Y-%m-%d'),  # Guardamos la fecha en el formato deseado
                    'hora': hora,
                    'coche': coche,
                    'litrosTotales': litros_cargados,  # Guardamos los litros totales
                    'litrosUltimoServi': last_service_litros,  # Usamos el valor de litros en el momento del último servicio
                    'fechaAnterior': last_service_date
                }])
                service_data = pd.concat([service_data, new_entry], ignore_index=True)
                update_csv_in_s3(service_data, 'servicios_realizados.csv')
                
                # Actualizar litrosServi solo para el coche que se realizó el servicio
                diesel_data.loc[diesel_data['coche'] == coche, 'litrosServi'] = 5000
                update_csv_in_s3(diesel_data, 'cargas_diesel.csv')

                st.success("Servicio registrado correctamente")

                # Esperar para recargar la aplicación
                time.sleep(3)
                    
                # Recargar la aplicación
                st.rerun()

# Mostrar tabla de Servicios
def show_service_history(service_data):
    with st.expander("Historial de Servicios"):
        # Convertir las columnas a enteros
        service_data['litrosTotales'] = service_data['litrosTotales'].astype(int)
        service_data['litrosUltimoServi'] = service_data['litrosUltimoServi'].astype(int)

        # Ordenar la tabla por 'idServis'
        sorted_service_data = service_data.sort_values(by='idServis', ascending=False)

        # Aplicar formato a las columnas para mostrar sin comas
        styled_df = sorted_service_data.style.format({
            'litrosTotales': '{:.0f}',
            'litrosUltimoServi': '{:.0f}'
        })

        # Mostrar la tabla con el estilo aplicado
        st.dataframe(styled_df, hide_index=True)

def delete_record(diesel_data, service_data):
    with st.expander("Eliminar Registros"):
        col1, col2 = st.columns(2)

        # Columna para eliminar registros de carga
        with col1:
            st.subheader("Eliminar Registro de Carga")
            id_carga = st.number_input("Ingrese el ID de Carga", min_value=0, key="idCarga")
            
            if id_carga > 0:
                carga_info = diesel_data[diesel_data['idCarga'] == id_carga]
                if not carga_info.empty:
                    st.write(carga_info)
                    if st.button("Eliminar Carga", key="deleteCarga"):
                        diesel_data = diesel_data[diesel_data['idCarga'] != id_carga]  # Eliminar la carga
                        update_csv_in_s3(diesel_data, 'cargas_diesel.csv')
                        st.success(f"Registro de carga con ID {id_carga} eliminado correctamente.")
                else:
                    st.warning("No se encontró un registro de carga con ese ID.")

        # Columna para eliminar registros de servicio
        with col2:
            st.subheader("Eliminar Registro de Servicio")
            id_servis = st.number_input("Ingrese el ID de Servicio", min_value=0, key="idServis")

            if id_servis > 0:
                servis_info = service_data[service_data['idServis'] == id_servis]
                if not servis_info.empty:
                    st.write(servis_info)
                    if st.button("Eliminar Servicio", key="deleteServicio"):
                        service_data = service_data[service_data['idServis'] != id_servis]  # Eliminar el servicio
                        update_csv_in_s3(service_data, 'servicios_realizados.csv')
                        st.success(f"Registro de servicio con ID {id_servis} eliminado correctamente.")
                else:
                    st.warning("No se encontró un registro de servicio con ese ID.")

# Función Principal
def main():
    # Cargar los datos
    diesel_data = load_csv_from_s3('cargas_diesel.csv')
    service_data = load_csv_from_s3('servicios_realizados.csv')

    # Llamar a las funciones que gestionan el formulario, la eliminación, y la visualización
    diesel_form(diesel_data)
    service_form(diesel_data, service_data)
    show_service_history(service_data)
    delete_record(diesel_data, service_data)

if __name__ == "__main__":
    main()

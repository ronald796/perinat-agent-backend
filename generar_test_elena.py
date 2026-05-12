import pydicom
from pydicom.dataset import Dataset, FileDataset
from pydicom.uid import ExplicitVRLittleEndian
import datetime

def create_dicom_elena(filename="test_elena_20sem.dcm"):
    # Configuración de metadata DICOM
    file_meta = Dataset()
    file_meta.MediaStorageSOPClassUID = '1.2.840.10008.5.1.4.1.1.6.1'
    file_meta.MediaStorageSOPInstanceUID = "1.2.3.4.5"
    file_meta.ImplementationClassUID = "1.2.3.4.5.6"
    file_meta.TransferSyntaxUID = ExplicitVRLittleEndian

    ds = FileDataset(filename, {}, file_meta=file_meta, preamble=b"\0" * 128)

    # DATOS DE LA PACIENTE (Esto es lo que leerá tu App)
    ds.PatientName = "ELENA^RAMOS"
    ds.PatientID = "ELENA-2026-MORFO"
    ds.ContentDate = datetime.datetime.now().strftime('%Y%m%d')
    ds.ContentTime = datetime.datetime.now().strftime('%H%M%S.%f')
    ds.Modality = "US"  # Ultrasound
    ds.Manufacturer = "ESAOTE"

    # Guardar el archivo
    ds.save_as(filename)
    print(f"--- Archivo DICOM de prueba generado: {filename} ---")
    print("Ahora puedes subirlo a tu Dashboard en el cuadro de 'Captura DICOM'.")

if __name__ == "__main__":
    create_dicom_elena()

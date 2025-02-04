import pytesseract as tess
from PIL import Image, ImageEnhance, ImageFilter
import cv2
import numpy as np
import re
import os

# Configuración de Tesseract
tess.pytesseract.tesseract_cmd = r'C:\Program Files\Tesseract-OCR\tesseract.exe'

def cargar_correcciones(ruta_correcciones):
    correcciones = {}
    with open(ruta_correcciones, 'r', encoding='utf-8') as file:
        lineas = file.readlines()
    
    clave = None
    for linea in lineas:
        linea = linea.strip()
        if linea.startswith('"') and linea.endswith('"'):  # Es una clave
            clave = linea.strip('"')
        elif clave and linea:
            variantes = linea.split(',')
            for variante in variantes:
                correcciones[variante] = clave
    return correcciones

def aplicar_correcciones(archivo_salida, correcciones):
    # Intentar leer con UTF-8 primero
    try:
        with open(archivo_salida, 'r', encoding='utf-8') as file:
            contenido = file.read()
    except UnicodeDecodeError:
        # Si falla, intentamos con Latin-1 (ISO-8859-1)
        with open(archivo_salida, 'r', encoding='ISO-8859-1') as file:
            contenido = file.read()

    # Aplicar las correcciones
    for erroneo, correcto in correcciones.items():
        contenido = re.sub(rf'\b{re.escape(erroneo)}\b', correcto, contenido)

    # Guardar el archivo corregido con UTF-8
    with open(archivo_salida, 'w', encoding='utf-8') as file:
        file.write(contenido)


def detectar_titulo(image):
    titulo = image[0: 60, 0: 1330]
    gris = cv2.cvtColor(titulo, cv2.COLOR_BGR2GRAY)
    threshold_img = cv2.threshold(gris, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)[1]
    gris = cv2.GaussianBlur(gris, (5, 5), 0)
    titulo_extraido = tess.image_to_string(threshold_img, lang="spa")
    return titulo_extraido.strip()

def invertir_colores(imagen):
    return cv2.bitwise_not(imagen)

def verificar_texto(texto, image, my_file):
    patron = r"^[^/]+ / [^/]+ / [^/]+ / [^/]+$"
    
    if re.match(patron, texto):
        my_file.write('*************************************************************************************************************\n')
        my_file.write(texto + "\n")
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        gray = cv2.GaussianBlur(gray, (5, 5), 0)
        edges = cv2.Canny(gray, 50, 150)
        contornos, _ = cv2.findContours(edges, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        array_textos = []
        copy = image.copy()
        
        contornos_filtrados = []
        for contorno in contornos:
            epsilon = 0.02 * cv2.arcLength(contorno, True)
            approx = cv2.approxPolyDP(contorno, epsilon, True)
            if len(approx) == 4:
                x, y, w, h = cv2.boundingRect(approx)
                if w < 20 or h < 20 or h / w > 20:
                    continue
                contornos_filtrados.append((x, y, w, h))
        
        if len(contornos_filtrados) == 3:
            for x, y, w, h in contornos_filtrados:
                cv2.rectangle(copy, (x, y), (x + w, y + h), (255, 255, 255), -1)
                cuadro_recortado = image[y:y + h, x:x + w]
                cuadro_negativo = invertir_colores(cuadro_recortado)
                gray = cv2.cvtColor(cuadro_negativo, cv2.COLOR_BGR2GRAY)
                enhanced = cv2.convertScaleAbs(gray, alpha=2.5, beta=5)
                pil_image = Image.fromarray(enhanced)
                sharpened = pil_image.filter(ImageFilter.SHARPEN)
                texto_extraido = tess.image_to_string(sharpened, lang='spa').strip()
                if texto_extraido:
                    array_textos.append(texto_extraido)
        else:
            for x, y, w, h in contornos_filtrados:
                cv2.rectangle(copy, (x, y), (x + w, y + h), (255, 255, 255), -1)
                cuadro_recortado = image[y:y + h, x:x + w]
                imagen_pil = Image.fromarray(cuadro_recortado)
                enhancer = ImageEnhance.Contrast(imagen_pil)
                imagen_pil = enhancer.enhance(1.1)
                imagen_pil = imagen_pil.filter(ImageFilter.SHARPEN)
                texto_extraido = tess.image_to_string(imagen_pil, lang='spa').strip()
                if texto_extraido:
                    array_textos.append(texto_extraido)
        
        x, y, w, h = 0, 60, 1230, 645
        copy = copy[y:y + h, x:x + w]
        imagen_pil = Image.fromarray(copy)
        enhancer = ImageEnhance.Contrast(imagen_pil)
        imagen_pil = enhancer.enhance(1.1).filter(ImageFilter.SHARPEN)
        texto = tess.image_to_string(imagen_pil, lang='spa')
        my_file.write(texto + '\n')
        for item in reversed(array_textos):
            my_file.write(item + '\n\n')

def procesar_carpeta(carpeta, ruta_correcciones):
    archivos = sorted([f for f in os.listdir(carpeta) if f.startswith("frame") and f.endswith(".jpg")],
                      key=lambda x: int(re.search(r"\d+", x).group()))
    
    nombre_txt = os.path.basename(carpeta) + ".txt"
    ruta_txt = os.path.join(carpeta, nombre_txt)
    
    with open(ruta_txt, 'w') as my_file:
        for archivo in archivos:
            ruta_imagen = os.path.join(carpeta, archivo)
            image = cv2.imread(ruta_imagen)
            x, y, w, h = 0, 180, 1230, 645
            image = image[y:y + h, x:x + w]
            ID = detectar_titulo(image)
            print(f"Procesando: {archivo} en {carpeta}")
            verificar_texto(ID, image, my_file)

    # Aplicar correcciones después de escribir el texto
    correcciones = cargar_correcciones(ruta_correcciones)
    aplicar_correcciones(ruta_txt, correcciones)
    
    nueva_carpeta = os.path.join(os.path.dirname(carpeta), f"{os.path.basename(carpeta)} (LISTO)")
    os.rename(carpeta, nueva_carpeta)

def main():
    ruta_base = "frame_extraction"
    ruta_correcciones = "correccion.txt"
    
    carpetas = [os.path.join(ruta_base, carpeta) for carpeta in os.listdir(ruta_base) 
                if os.path.isdir(os.path.join(ruta_base, carpeta)) and "(LISTO)" not in carpeta]
    
    for carpeta in sorted(carpetas):
        procesar_carpeta(carpeta, ruta_correcciones)
    
if __name__ == "__main__":
    main()

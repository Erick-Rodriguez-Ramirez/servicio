import cv2
import os
import numpy as np
import pytesseract
import re

# Configurar Tesseract
pytesseract.pytesseract.tesseract_cmd = r'C:\Program Files\Tesseract-OCR\tesseract.exe'

# Directorios
video_folder = "Videos"
output_folder = "frame_extraction"

# Asegurar que la carpeta de salida existe
if not os.path.exists(output_folder):
    os.makedirs(output_folder)

# Obtener lista de números de carpetas existentes
existing_folders = sorted([int(re.match(r'^(\d+)', f).group(1)) for f in os.listdir(output_folder) if re.match(r'^\d+', f)])

# Buscar el primer número faltante en la secuencia
next_folder_num = 1
for num in existing_folders:
    if num == next_folder_num:
        next_folder_num += 1
    else:
        break  # Se encontró un hueco en la secuencia

# Obtener la lista de videos
videos = [f for f in os.listdir(video_folder) if f.endswith(('.mp4', '.avi', '.mov'))]

for video in videos:
    video_path = os.path.join(video_folder, video)
    video_output_folder = os.path.join(output_folder, str(next_folder_num))
    os.makedirs(video_output_folder, exist_ok=True)
    
    # Renombrar el video a un número secuencial
    new_video_name = f"{next_folder_num}.mp4"
    new_video_path = os.path.join(video_folder, new_video_name)
    os.rename(video_path, new_video_path)
    
    # Procesar el video
    cam = cv2.VideoCapture(new_video_path)
    currentframe = 0
    previous_frame = None
    last_saved_frame = None
    threshold = 5
    white_threshold = 200
    similarity_threshold = 10
    text_threshold = 300
    
    while True:
        ret, frame = cam.read()
        if not ret:
            break
        
        gray_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        if currentframe == 0:
            name = f'{video_output_folder}/frame{currentframe}.jpg'
            cv2.imwrite(name, frame)
            currentframe += 1
            last_saved_frame = gray_frame
        elif previous_frame is not None:
            diff = cv2.absdiff(previous_frame, gray_frame)
            mean_diff = np.mean(diff)
            white_ratio = np.mean(gray_frame > white_threshold) * 100
            
            similarity_mean = np.mean(cv2.absdiff(last_saved_frame, gray_frame)) if last_saved_frame is not None else float('inf')
            
            if mean_diff > threshold and white_ratio > 10 and similarity_mean > similarity_threshold:
                text = pytesseract.image_to_string(gray_frame)
                if len(text.strip()) > text_threshold:
                    name = f'{video_output_folder}/frame{currentframe}.jpg'
                    cv2.imwrite(name, frame)
                    currentframe += 1
                    last_saved_frame = gray_frame
        
        previous_frame = gray_frame
    
    cam.release()
    cv2.destroyAllWindows()
    
    # Eliminar el video procesado
    os.remove(new_video_path)
